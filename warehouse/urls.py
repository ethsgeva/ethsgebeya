from django.urls import path
from warehouse import views
from warehouse.views import product_detail
from . import api_counters


urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('setting/',views.setting_page, name='setting'),
    path('add/',views.add_product, name='add_product'),
    path('seller-products/', views.seller_products, name='seller_products'),


    path('delete-product/<uuid:product_id>/', views.delete_product, name='delete_product'),

    path('edit-product/<uuid:product_id>/', views.edit_product, name='edit_product'), 
    path('customer/', views.customer_page, name='customer_page'),

    path('analytics/', views.analytics_page, name='analytics'),
    path('product/<uuid:product_id>/', product_detail, name='product_detail'),
    path('category/', views.category_list, name='category_list'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('products/', views.product_list, name='product_list'),
    path('product/<uuid:product_id>/remove-image/<int:image_id>/', views.remove_product_image, name='remove_product_image'),
    path('wishlist/add/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('settings-orders/', views.settings_orders_page, name='settings_orders_page'),
    path('order/<int:order_id>/request-complete/', views.request_order_complete, name='request_order_complete'),
    path('order/<int:order_id>/confirm-complete/', views.confirm_order_complete, name='confirm_order_complete'),
    path('dashboard/order_counts/', views.dashboard_order_counts, name='dashboard_order_counts'),
    path('dashboard/buyer_order_counts/', views.dashboard_buyer_order_counts, name='dashboard_buyer_order_counts'),
    path('dashboard/buyer_cart_count/', views.dashboard_buyer_cart_count, name='dashboard_buyer_cart_count'),

    path('api/seller/order-notifications/', api_counters.seller_order_notifications, name='seller_order_notifications'),
    path('api/buyer/cart-count/', api_counters.buyer_cart_count, name='buyer_cart_count'),
    path('api/buyer/order-notifications/', api_counters.buyer_order_notifications, name='buyer_order_notifications'),

    # Public seller profile
    path('store/<int:seller_id>/', views.seller_profile, name='seller_profile'),
    # Follow API
    path('api/seller/<int:seller_id>/toggle-follow/', views.toggle_follow_seller, name='toggle_follow_seller'),
]