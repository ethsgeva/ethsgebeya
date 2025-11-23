from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from warehouse.models import Order, Wishlist
from warehouse.models import CustomerInteraction
from cart.views import Cart

@login_required
def seller_order_notifications(request):
    # Count new/unread orders for the seller
    seller = request.user.sellerprofile
    count = Order.objects.filter(product__seller=seller, status='P').count()  # 'P' = Pending
    return JsonResponse({'count': count})

@login_required
def buyer_cart_count(request):
    cart = Cart(request)
    count = len(cart)
    return JsonResponse({'count': count})

@login_required
def buyer_order_notifications(request):
    # Count orders for this buyer that are waiting for confirmation
    count = Order.objects.filter(user=request.user, status='W').count()  # 'W' = Waiting for confirmation
    return JsonResponse({'count': count})
