from cart.views import Cart

def cart_count(request):
    if request.user.is_authenticated:
        cart = Cart(request)
        return {'cart_count': len(cart)}
    return {'cart_count': 0}
