# warehouse/views.py
from django.shortcuts import render, redirect, get_object_or_404
import os
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Q, F, Avg
from django.db.models.functions import TruncDate, TruncMonth
from .forms import AnalyticsFilterForm
import json

from importlib.metadata import files
from django.urls import reverse
from warehouse import forms
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail

from warehouse.models import Image, Product, User, Order, CustomerInteraction, Category, Wishlist, SellerProfile, Review

from . import forms

from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from warehouse.forms import BasicUserForm, BasicSellerForm, AddProductForm, EditProductForm
from cart.views import Cart
from warehouse.decorators import seller_required, buyer_required
from .forms_wishlist import WishlistAddForm, WishlistRemoveForm
from .forms_search import ProductSearchForm
from django.db import transaction

@login_required
def dashboard(request):
    user = request.user
    user_type = user.profile.role.capitalize() if hasattr(user, 'profile') else 'Buyer'
    context = {'user_type': user_type}

    if hasattr(user, 'profile') and user.profile.role == 'seller':
        # Seller dashboard stats
        seller_profile = getattr(user, 'sellerprofile', None)
        if seller_profile:
            total_products = Product.objects.filter(seller=seller_profile).count()
            seller_orders = Order.objects.filter(product__seller=seller_profile)
            total_sales = seller_orders.filter(status__in=['C', 'W']).count()
            new_orders = seller_orders.filter(status='P').count()
            # Recent activity: last 5 orders
            recent_activity = seller_orders.order_by('-created_at')[:5]
            context.update({
                'total_products': total_products,
                'total_sales': total_sales,
                'new_orders': new_orders,
                'recent_activity': [
                    {'date': o.created_at.strftime('%Y-%m-%d'), 'description': f"Order for {o.product.title} ({o.get_status_display()})"}
                    for o in recent_activity
                ],
            })
        else:
            context.update({'total_products': 0, 'total_sales': 0, 'new_orders': 0, 'recent_activity': []})
    else:
        # Buyer dashboard stats
        my_orders = Order.objects.filter(user=user).count()
        wishlist = Wishlist.objects.filter(user=user).first()
        wishlist_count = wishlist.products.count() if wishlist else 0
        cart = Cart(request)
        cart_count = len(cart)
        # Recent orders: last 5
        recent_orders_qs = Order.objects.filter(user=user).order_by('-created_at')[:5]
        recent_orders = [
            {
                'date': o.created_at.strftime('%Y-%m-%d'),
                'status': o.get_status_display(),
                'product': o.product.title  # Use only the product title, not the object
            } for o in recent_orders_qs
        ]
        waiting_orders = Order.objects.filter(user=user, status='W')
        context.update({
            'my_orders': my_orders,
            'wishlist_count': wishlist_count,
            'cart_count': cart_count,
            'recent_orders': recent_orders,
            'waiting_orders': waiting_orders,
        })
    return render(request, 'warehouse/home.html', context)


def seller_profile(request, seller_id: int):
    """Public company/store profile page.
    Shows seller info, product grid, about, simple location text and recent product reviews.
    """
    seller = get_object_or_404(SellerProfile, id=seller_id)
    products = Product.objects.filter(seller=seller, is_active=True).select_related('category').prefetch_related('images', 'reviews')
    # Basic stats
    seller_reviews_qs = Review.objects.filter(product__seller=seller)
    stats = {
        'products': products.count(),
        'followers': seller.followers.count() if hasattr(seller, 'followers') else 0,
        'rating': seller_reviews_qs.aggregate(avg=Avg('rating'))['avg'] or 0,
        'rating_count': seller_reviews_qs.count(),
        'sold': Order.objects.filter(product__seller=seller, status__in=['C','W']).count(),
    }
    # Simple recent reviews (limit 5)
    recent_reviews = Review.objects.filter(product__seller=seller).select_related('user', 'product').order_by('-created_at')[:5]
    is_own_store = request.user.is_authenticated and hasattr(request.user, 'sellerprofile') and getattr(request.user, 'sellerprofile', None) and request.user.sellerprofile.id == seller.id

    return render(request, 'warehouse/seller_profile.html', {
        'seller': seller,
        'products': products,
        'stats': stats,
        'recent_reviews': recent_reviews,
        'is_own_store': is_own_store,
        'maptiler_key': os.environ.get('MAPTILER_KEY')
    })

@login_required
def toggle_follow_seller(request, seller_id: int):
    """Toggle follow/unfollow for the current user on a seller. Returns JSON.
    Method: POST only.
    Response: { followed: bool, followers: int }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    seller = get_object_or_404(SellerProfile, id=seller_id)
    user = request.user
    # Prevent sellers from following themselves
    if hasattr(user, 'sellerprofile') and user.sellerprofile.id == seller.id:
        return JsonResponse({'error': "You can't follow your own store."}, status=400)
    followed = False
    if seller.followers.filter(id=user.id).exists():
        seller.followers.remove(user)
    else:
        seller.followers.add(user)
        followed = True
    followers = seller.followers.count()
    return JsonResponse({'followed': followed, 'followers': followers})

@login_required  
def setting_page(request):
    # Ensure user has a profile
    from warehouse.models import UserProfile
    user = request.user
    if not hasattr(user, 'profile'):
        UserProfile.objects.get_or_create(user=user)
        user.refresh_from_db()
    user_profile = user.profile
    user_form = BasicUserForm(instance=user)
    password_form = PasswordChangeForm(user)
    user_type = user_profile.role.capitalize()
    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'update_profile':
            user_form = BasicUserForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Your profile has been updated')
                return redirect('setting')
        elif action == 'update_store':
            if user_profile.role == 'seller':
                seller_form = BasicSellerForm(request.POST, request.FILES, instance=getattr(user, 'sellerprofile', None))
                if seller_form.is_valid():
                    seller_form.save()
                    messages.success(request, 'Your store settings have been updated')
                    return redirect('setting')
        elif action == 'update_password':
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been updated')
                return redirect('setting')
        elif action == 'switch_to_seller':
            user_profile.role = 'seller'
            user_profile.save()
            messages.success(request, 'You are now a seller. Seller features are enabled.')
            return redirect('setting')
        elif action == 'switch_to_buyer':
            user_profile.role = 'buyer'
            user_profile.save()
            messages.success(request, 'You are now a buyer. Seller features are disabled.')
            return redirect('setting')
    seller_form = None
    if user_profile.role == 'seller':
        seller_form = BasicSellerForm(instance=getattr(user, 'sellerprofile', None))
    context = {
        'user_form': user_form,
        'seller_form': seller_form,
        'password_form': password_form,
        'user_type': user_type
    }
    return render(request, 'warehouse/setting.html', context)





@login_required
def switch_role(request):
    from warehouse.models import UserProfile
    user = request.user
    if not hasattr(user, 'profile'):
        UserProfile.objects.get_or_create(user=user)
        user.refresh_from_db()
    user_profile = user.profile
    if user_profile.role == 'buyer':
        user_profile.role = 'seller'
        messages.success(request, 'You are now a seller. Seller features are enabled.')
    else:
        user_profile.role = 'buyer'
        messages.success(request, 'You are now a buyer. Seller features are disabled.')
    user_profile.save()
    return redirect(request.META.get('HTTP_REFERER', 'setting'))
    
    

@seller_required
@login_required(login_url='/sign-in/')
def add_product(request):
    # Ensure seller profile exists before rendering template to avoid 500 errors
    seller_profile = getattr(request.user, 'sellerprofile', None)
    if seller_profile is None:
        from django.contrib import messages
        messages.warning(request, "Please create your seller profile before adding products.")
        return redirect('setting')
    if request.method == "POST":
        product_form = AddProductForm(request.POST, request.FILES)
        if product_form.is_valid():
            product = product_form.save(commit=False)
            seller_profile = getattr(request.user, 'sellerprofile', None)
            if seller_profile is None:
                from django.contrib import messages
                messages.error(request, "You need a seller profile before adding products.")
                return render(request, 'warehouse/create_product.html', { 'product_form': product_form })
            product.seller = seller_profile
            product.save()  # category is saved by ModelForm
            # Save images
            images = request.FILES.getlist('images')
            from .models import ProductImage
            for image in images:
                ProductImage.objects.create(product=product, image=image)
            from django.contrib import messages
            messages.success(request, "Product uploaded successfully!")
            # Stay on the add product page, do not redirect to product detail
            product_form = AddProductForm()  # Reset the form for new entry
            return render(request, 'warehouse/create_product.html', {
                'product_form': product_form
            })
    else:
        product_form = AddProductForm()

    return render(request, 'warehouse/create_product.html', {
        'product_form': product_form
    })


@seller_required
@login_required(login_url='/sign-in/')
def edit_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id, seller=request.user.sellerprofile)
    except Product.DoesNotExist:
        messages.error(request, "Product not found or you don't have permission to edit it.")
        return redirect('add_product')
    
    if request.method == "POST":
        product_form = EditProductForm(request.POST, request.FILES, instance=product)
        if product_form.is_valid():
            try:
                product = product_form.save()
                messages.success(request, "Product updated successfully!")
                return redirect('add_product')  # or redirect to product list
            except Exception as e:
                messages.error(request, f"Error updating product: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        product_form = EditProductForm(instance=product)

    return render(request, 'warehouse/edit_product.html', {
        'product_form': product_form,
        'product': product
    })
    

@seller_required
@login_required(login_url='/sign-in/')
def seller_products(request):
    form = ProductSearchForm(request.GET or None)
    seller_products = Product.objects.filter(seller=request.user.sellerprofile)

    # Search
    q = request.GET.get('q')
    if q:
        seller_products = seller_products.filter(title__icontains=q)

    # Category
    category = request.GET.get('category')
    if category:
        seller_products = seller_products.filter(category_id=category)

    # In Stock
    in_stock = request.GET.get('in_stock')
    if in_stock == 'on' or in_stock == 'true' or in_stock == '1':
        seller_products = seller_products.filter(in_stock=True)

    # Status
    status = request.GET.get('status')
    if status:
        seller_products = seller_products.filter(is_active=(status == 'active'))

    # Sort
    sort = request.GET.get('sort')
    if sort:
        seller_products = seller_products.order_by(sort)
    else:
        seller_products = seller_products.order_by('-created_at')

    # For category dropdown
    from warehouse.models import Category
    categories = Category.objects.all()

    return render(request, 'show/seller_products.html', {
        'seller_products': seller_products,
        'form': form,
        'categories': categories,
    })

# ... other imports

@seller_required
@login_required
def customer_page(request):
    """
    Displays the customer's page with users who follow them.
    """
    user = request.user
    # Followers of this seller
    followers_qs = (
        User.objects.filter(following_sellers=user.sellerprofile)
        .annotate(
            orders_count=Count(
                'orders_as_user',
                filter=Q(orders_as_user__product__seller=user.sellerprofile)
                & ~Q(orders_as_user__status='X'),
            )
        )
        .distinct()
    )

    now = timezone.now()
    followers_data = []
    for u in followers_qs:
        full_name = f"{u.first_name} {u.last_name}".strip() or u.username
        # Build initials from name or username
        parts = [p for p in full_name.split(' ') if p]
        if parts:
            initials = ''.join([p[0] for p in parts[:2]]).upper()
        else:
            initials = (u.username[:2] or 'U').upper()
        orders = int(u.orders_count or 0)
        is_vip = orders >= 25
        # New if joined within last 30 days and few/no orders, else active if any orders
        days_since_join = (now - getattr(u, 'date_joined', now)).days if getattr(u, 'date_joined', None) else 9999
        status = 'new' if days_since_join <= 30 and orders <= 1 else ('active' if orders > 0 else 'new')
        followers_data.append(
            {
                'id': u.id,
                'name': full_name,
                'username': f"@{u.username}",
                'initial': initials,
                'isOnline': False,  # Placeholder; presence tracking not implemented
                'isVIP': is_vip,
                'orders': orders,
                'status': status,
            }
        )

    context = {
        'followers_json': json.dumps(followers_data),
    }

    return render(request, 'show/customer_page.html', context)

@seller_required
def analytics_page(request):
    form = AnalyticsFilterForm(request.GET or None)
    
    # Default date range (last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    if form.is_valid():
        date_range = form.cleaned_data['date_range']
        
        if date_range == '7':
            start_date = end_date - timedelta(days=7)
        elif date_range == '90':
            start_date = end_date - timedelta(days=90)
        elif date_range == '365':
            start_date = end_date - timedelta(days=365)
        elif date_range == 'custom':
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
    
    # Get seller profile
    seller = request.user.sellerprofile
    
    # Sales metrics
    orders = Order.objects.filter(
        product__seller=seller,
        created_at__range=(start_date, end_date)
    ).exclude(status='X')  # Exclude cancelled orders
    
    total_sales = orders.count()
    total_revenue = orders.aggregate(total=Sum('total_price'))['total'] or 0
    avg_order_value = total_revenue / total_sales if total_sales > 0 else 0
    
    # Sales over time (daily)
    sales_over_time = orders.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id'),
        revenue=Sum('total_price')
    ).order_by('date')
    
    # Prepare sales chart data
    dates = []
    sales_count = []
    sales_revenue = []
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        dates.append(date_str)
        
        # Find sales for this date
        sales_data = next((s for s in sales_over_time if s['date'] == current_date.date()), None)
        
        sales_count.append(sales_data['count'] if sales_data else 0)
        sales_revenue.append(float(sales_data['revenue']) if sales_data else 0.0)
        
        current_date += timedelta(days=1)
    
    # Top products
    top_products = Product.objects.filter(
        seller=seller,
        orders_as_product__created_at__range=(start_date, end_date)
    ).annotate(
        sales_count=Count('orders_as_product'),
        revenue=Sum('orders_as_product__total_price'),
        avg_price=Avg('orders_as_product__total_price')
    ).order_by('-revenue')[:5]
    
    # Customer interactions
    interactions = CustomerInteraction.objects.filter(
        product__seller=seller,
        timestamp__range=(start_date, end_date)
    ).values('interaction_type').annotate(
        count=Count('id')
    )
    
    # Prepare interaction data
    interaction_types = ['V', 'C', 'P']
    interaction_labels = ['Views', 'Cart Adds', 'Purchases']
    interaction_counts = [0, 0, 0]
    
    for interaction in interactions:
        idx = interaction_types.index(interaction['interaction_type'])
        interaction_counts[idx] = interaction['count']
    
    context = {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'dates': json.dumps(dates),
        'sales_count': json.dumps(sales_count),
        'sales_revenue': json.dumps(sales_revenue),
        'top_products': top_products,
        'interaction_labels': json.dumps(interaction_labels),
        'interaction_counts': json.dumps(interaction_counts),
    }
    
    return render(request, 'show/analytics.html', context)


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    from .forms import ReviewForm
    from .models import Review
    reviews = product.reviews.select_related('user').all()
    user_review = None

    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
        if request.method == 'POST':
            form = ReviewForm(request.POST)
            if form.is_valid():
                review, created = Review.objects.update_or_create(
                    product=product, user=request.user,
                    defaults={
                        'rating': form.cleaned_data['rating'],
                        'text': form.cleaned_data['text']
                    }
                )
                messages.success(request, 'Your review has been submitted!')
                return redirect('product_detail', product_id=product.id)
        else:
            form = ReviewForm()
    else:
        form = None

    avg_rating = reviews.aggregate(avg=models.Avg('rating'))['avg']
    return render(request, 'warehouse/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'form': form,
        'user_review': user_review,
        'avg_rating': avg_rating
    })
    
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'warehouse/category_list.html', {'categories': categories})

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.all()
    return render(request, 'warehouse/category_detail.html', {'category': category, 'products': products})

def product_list(request):
    form = ProductSearchForm(request.GET or None)
    products = Product.objects.filter(is_active=True)
    if form.is_valid():
        q = form.cleaned_data.get('q')
        category = form.cleaned_data.get('category')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        in_stock = form.cleaned_data.get('in_stock')
        if q:
            products = products.filter(
                Q(title__icontains=q) | Q(description__icontains=q)
            )
        if category:
            products = products.filter(category=category)
        if min_price is not None:
            products = products.filter(price__gte=min_price)
        if max_price is not None:
            products = products.filter(price__lte=max_price)
        if in_stock:
            products = products.filter(in_stock=True)
    else:
        products = products.filter(in_stock=True)
    return render(request, 'warehouse/product_list.html', {'products': products, 'form': form})

@login_required(login_url='/sign-in/')
def remove_product_image(request, product_id, image_id):
    """
    AJAX endpoint to remove a specific image from a product.
    Returns JSON with success status and message.
    """
    product = get_object_or_404(Product, id=product_id, seller=request.user.sellerprofile)
    from warehouse.models import ProductImage
    image = get_object_or_404(ProductImage, id=image_id, product=product)
    image.delete()
    return JsonResponse({'success': True, 'message': 'Image removed successfully.'})

@login_required()
def settings_orders_page(request):
    user = request.user
    context = {}
    if hasattr(user, 'profile') and user.profile.role == 'seller':
        # Seller: show orders for their products
        seller_profile = getattr(user, 'sellerprofile', None)
        seller_orders = []
        seller_pending_orders = []
        seller_waiting_orders = []
        seller_completed_orders = []
        seller_pending_orders_count = 0
        if seller_profile:
            all_orders = Order.objects.filter(product__seller=seller_profile).select_related('user', 'product').order_by('-created_at')
            seller_orders = all_orders
            seller_pending_orders = all_orders.filter(status='P')
            seller_waiting_orders = all_orders.filter(status='W')
            seller_completed_orders = all_orders.filter(status='C')
            seller_pending_orders_count = seller_pending_orders.count()
        context['seller_orders'] = seller_orders
        context['seller_pending_orders'] = seller_pending_orders
        context['seller_waiting_orders'] = seller_waiting_orders
        context['seller_completed_orders'] = seller_completed_orders
        context['seller_pending_orders_count'] = seller_pending_orders_count
        context['role'] = 'seller'
    else:
        # Buyer: show cart and their orders
        cart = Cart(request)
        buyer_orders = Order.objects.filter(user=user).select_related('product').order_by('-created_at')
        waiting_orders = [o for o in buyer_orders if o.status == 'W']
        completed_orders = [o for o in buyer_orders if o.status == 'C']
        pending_orders = [o for o in buyer_orders if o.status == 'P']
        context['cart'] = cart
        context['buyer_orders'] = buyer_orders
        context['waiting_orders'] = waiting_orders
        context['completed_orders'] = completed_orders
        context['pending_orders'] = pending_orders
        context['role'] = 'buyer'
    return render(request, 'warehouse/settings_orders.html', context)

@login_required()
def add_to_wishlist(request):
    if request.method == 'POST':
        form = WishlistAddForm(request.POST)
        if form.is_valid():
            product_id = form.cleaned_data['product_id']
            product = get_object_or_404(Product, id=product_id)
            wishlist, created = Wishlist.objects.get_or_create(user=request.user)
            wishlist.products.add(product)
            messages.success(request, 'Product added to your wishlist!')
        else:
            messages.error(request, 'Invalid product.')
    return redirect(request.META.get('HTTP_REFERER', 'product_list'))

@login_required()
def remove_from_wishlist(request):
    if request.method == 'POST':
        form = WishlistRemoveForm(request.POST)
        if form.is_valid():
            product_id = form.cleaned_data['product_id']
            product = get_object_or_404(Product, id=product_id)
            wishlist = Wishlist.objects.filter(user=request.user).first()
            if wishlist:
                wishlist.products.remove(product)
                messages.success(request, 'Product removed from your wishlist!')
            else:
                messages.error(request, 'Wishlist not found.')
        else:
            messages.error(request, 'Invalid product.')
    return redirect(request.META.get('HTTP_REFERER', 'product_list'))

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@csrf_exempt
@login_required
@seller_required
@require_POST
def request_order_complete(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        if order.status != 'P':
            return JsonResponse({'success': False, 'error': 'Order is not pending.'})
        order.status = 'W'  # Waiting for buyer confirmation
        order.save()
        # Send email to buyer (advanced: include order details)
        send_mail(
            subject='Order Completion Confirmation Needed',
            message=f'''Dear {order.user.username},\n\nThe seller has marked your order for {order.product.title} as completed.\n\nOrder Details:\n- Product: {order.product.title}\n- Quantity: {order.quantity}\n- Total Price: ${order.total_price}\n- Your Phone: {order.phone or 'N/A'}\n- Your Address: {order.address or 'N/A'}\n\nPlease log in to your account and confirm the order completion.\n\nThank you!''',
            from_email=None,
            recipient_list=[order.user.email],
            fail_silently=True,
        )
        return JsonResponse({'success': True, 'message': 'Order marked as completed. Waiting for buyer confirmation.'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found.'})

@csrf_exempt
@login_required
def confirm_order_complete(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id)
            if order.status != 'W':
                return JsonResponse({'success': False, 'error': 'Order is not waiting for buyer confirmation.'})
            if order.user != request.user:
                return JsonResponse({'success': False, 'error': 'You are not authorized to confirm this order.'})
            order.status = 'C'
            order.save()
            # Send email to seller
            send_mail(
                subject='Order Completed',
                message=f'Dear {order.product.seller.user.username},\n\nThe buyer has confirmed completion of the order for {order.product.title}.\n\nThank you!',
                from_email=None,
                recipient_list=[order.product.seller.user.email],
                fail_silently=True,
            )
            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order not found.'})
    return JsonResponse({'success': False, 'error': 'Invalid request.'})

@login_required
def dashboard_order_counts(request):
    user = request.user
    if not hasattr(user, 'profile') or user.profile.role != 'seller':
        return JsonResponse({'success': False, 'error': 'Not a seller'})
    seller_profile = getattr(user, 'sellerprofile', None)
    if not seller_profile:
        return JsonResponse({'success': True, 'new_orders': 0, 'total_sales': 0})
    seller_orders = Order.objects.filter(product__seller=seller_profile)
    new_orders = seller_orders.filter(status='P').count()
    total_sales = seller_orders.filter(status__in=['C', 'W']).count()
    return JsonResponse({'success': True, 'new_orders': new_orders, 'total_sales': total_sales})

@login_required
def dashboard_buyer_order_counts(request):
    user = request.user
    if not hasattr(user, 'profile') or user.profile.role != 'buyer':
        return JsonResponse({'success': False, 'error': 'Not a buyer'})
    waiting_orders = Order.objects.filter(user=user, status='W').count()
    return JsonResponse({'success': True, 'waiting_orders': waiting_orders})

@login_required
def dashboard_buyer_cart_count(request):
    user = request.user
    if not hasattr(user, 'profile') or user.profile.role != 'buyer':
        return JsonResponse({'success': False, 'error': 'Not a buyer'})
    cart = Cart(request)
    cart_count = len(cart)
    return JsonResponse({'success': True, 'cart_count': cart_count})

@seller_required
@login_required(login_url='/sign-in/')
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user.sellerprofile)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product has been deleted successfully.')
        return redirect('seller_products')
    return render(request, 'warehouse/confirm_delete_product.html', {'product': product})