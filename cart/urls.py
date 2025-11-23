from django.urls import path
from .views import cart_add, cart_detail, checkout, cart_remove

urlpatterns = [
    path('add/<uuid:product_id>/', cart_add, name='cart_add'),
    path('remove/<uuid:product_id>/', cart_remove, name='cart_remove'),
    path('detail/', cart_detail, name='cart_detail'),
    path('checkout/', checkout, name='checkout'),
]
