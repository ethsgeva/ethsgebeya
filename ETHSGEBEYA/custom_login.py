from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import redirect

class CustomLoginView(LoginView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, 'You are already signed in and have an account.')
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        return super().dispatch(request, *args, **kwargs)
