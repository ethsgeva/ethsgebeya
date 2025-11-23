from django.urls import path
from warehouse import api_views

urlpatterns = [
    path('seller/pending-orders-count/', api_views.seller_pending_orders_count, name='seller_pending_orders_count'),
]
