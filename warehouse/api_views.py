from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from warehouse.models import Order

def seller_pending_orders_count(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'sellerprofile'):
        return JsonResponse({'count': 0})
    count = Order.objects.filter(product__seller=request.user.sellerprofile, status='P').count()
    return JsonResponse({'count': count})
