from .models import SellerProfile

class ProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        #One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # Only auto-create a SellerProfile for users who are sellers.
        # This prevents empty seller profiles from being created for buyers.
        if request.user.is_authenticated:
            user_profile = getattr(request.user, 'profile', None)
            if user_profile and getattr(user_profile, 'role', None) == 'seller':
                if not hasattr(request.user, 'sellerprofile'):
                    # Create a minimal profile with a non-empty name; details can be edited later.
                    SellerProfile.objects.create(
                        user=request.user,
                        company_name=(request.user.get_full_name() or request.user.username or 'New Store'),
                        description='',
                        contact_number='',
                        address='',
                    )
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
    