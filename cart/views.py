from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from warehouse.models import Product, Order
from warehouse.decorators import buyer_required
from .forms import CheckoutForm

CART_SESSION_ID = 'cart'

class Cart():
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}
        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        del self.session[CART_SESSION_ID]
        self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product
        for item in cart.values():
            item['price'] = float(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(float(item['price']) * item['quantity'] for item in self.cart.values())


def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.add(product=product)
    return redirect('product_detail', product_id=product_id)

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/cart_detail.html', {'cart': cart})

@buyer_required
@login_required
def checkout(request):
    cart = Cart(request)
    cart_items = [item for item in cart if 'product' in item]
    # If a product_id is provided in GET, filter to only that product
    product_id = request.GET.get('product_id')
    if product_id:
        cart_items = [item for item in cart_items if str(item['product'].id) == str(product_id)]
        if not cart_items:
            messages.error(request, "You do not have this product in your cart.")
            return redirect('settings_orders_page')
    # Calculate total only for selected items (on POST) or all items (on GET)
    selected_ids = set()
    if request.method == 'POST':
        for item in cart_items:
            if request.POST.get(f'select_{item["product"].id}', None):
                selected_ids.add(item['product'].id)
        filtered_items = [item for item in cart_items if item['product'].id in selected_ids]
        cart_total = sum(float(request.POST.get(f'quantity_{item["product"].id}', item['quantity'])) * item['price'] for item in filtered_items)
    else:
        filtered_items = cart_items
        cart_total = sum(item['total_price'] for item in filtered_items)
    if not cart_items:
        messages.error(request, "Your cart is empty or contains invalid items.")
        return redirect('cart_detail')

    # Dynamically add quantity and select fields for each cart item
    class DynamicCheckoutForm(CheckoutForm):
        pass
    for idx, item in enumerate(cart_items):
        DynamicCheckoutForm.base_fields[f'select_{item["product"].id}'] = forms.BooleanField(
            label='', required=False, initial=True)
        DynamicCheckoutForm.base_fields[f'quantity_{item["product"].id}'] = forms.IntegerField(
            label='', min_value=1, initial=item['quantity'])

    if request.method == 'POST':
        form = DynamicCheckoutForm(request.POST)
        if form.is_valid():
            address = form.cleaned_data['address']
            phone = form.cleaned_data['phone']
            ordered_any = False
            for item in cart_items:
                selected = form.cleaned_data.get(f'select_{item["product"].id}', False)
                quantity = form.cleaned_data.get(f'quantity_{item["product"].id}', item['quantity'])
                if selected:
                    Order.objects.create(
                        user=request.user,
                        product=item['product'],
                        quantity=quantity,
                        total_price=item['price'] * quantity,
                        address=address,
                        phone=phone,
                    )
                    ordered_any = True
                    # Update cart quantity or remove if set to 0
                    if quantity > 0:
                        cart.add(item['product'], quantity, override_quantity=True)
                    else:
                        cart.remove(item['product'])
            if ordered_any:
                cart.clear()
                messages.success(request, "Order placed successfully! The seller will contact you via the provided phone number.")
                return redirect('settings_orders_page')
            else:
                messages.error(request, "Please select at least one product to order.")
    else:
        form = DynamicCheckoutForm()
    # Use filtered_items instead of cart_items in the template context
    return render(request, 'cart/checkout.html', {'cart_items': filtered_items, 'cart_total': cart_total, 'form': form})

@login_required
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.success(request, "Product removed from your cart.")
    # Redirect to orders and wishlist page instead of cart detail
    return redirect('settings_orders_page')
