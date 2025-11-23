from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def seller_required(view_func):
    @login_required(login_url='/sign-in/')
    def _wrapped_view(request, *args, **kwargs):
        from warehouse.models import UserProfile
        user = request.user
        if not hasattr(user, 'profile'):
            UserProfile.objects.get_or_create(user=user)
            user.refresh_from_db()
        if not hasattr(user, 'profile') or user.profile.role != 'seller':
            messages.warning(request, "You are a buyer. Please update your settings to become a seller.")
            return redirect('setting')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def buyer_required(view_func):
    @login_required(login_url='/sign-in/')
    def _wrapped_view(request, *args, **kwargs):
        from warehouse.models import UserProfile
        user = request.user
        if not hasattr(user, 'profile'):
            UserProfile.objects.get_or_create(user=user)
            user.refresh_from_db()
        if hasattr(user, 'profile') and user.profile.role == 'seller':
            raise PermissionDenied("Sellers cannot access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
