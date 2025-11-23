from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login
from warehouse.forms import CustomUserCreationForm, UserProfileForm
from django.contrib.auth.decorators import login_required
from .auth_utils import already_authenticated_message
from .forms import ResendActivationEmailForm
from django.utils.html import strip_tags
import os
from warehouse.models import SellerProfile
from django.utils import timezone
from django.db.models import Count, Avg, Q
import json

def home(request):
    # Use the new modern homepage design
    return render(request, 'ethsgebeya/home_modern.html')

def sign_up(request):
    if request.user.is_authenticated:
        messages.info(request, 'You are already signed in and have an account.')
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            if not email or not email.endswith('@gmail.com'):
                messages.error(request, 'Only @gmail.com email addresses are allowed.')
                return render(request, 'form/sign_up.html', {'form': form})
            user = form.save(commit=False)
            user.is_active = False  # Deactivate account until email confirmed
            user.save()
            current_site = get_current_site(request)
            subject = 'Activate your ETHSGEBEYA account'
            html_message = render_to_string('registration/account_activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            plain_message = strip_tags(html_message)
            send_mail(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)
            messages.success(request, 'Account created! Please check your email to activate your account.')
            return redirect('sign-in')
    else:
        form = CustomUserCreationForm()
    return render(request, 'form/sign_up.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        return render(request, 'registration/account_activation_success.html')
    else:
        return render(request, 'registration/account_activation_invalid.html')

def landing(request):
    return render(request, 'ethsgebeya/landing.html')

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'registration/profile.html', {'form': form})

def about(request):
    return render(request, 'ethsgebeya/about.html')

def privacy_policy(request):
    return render(request, 'ethsgebeya/privacy_policy.html')

def terms_of_service(request):
    return render(request, 'ethsgebeya/terms_of_service.html')

def contact(request):
    return render(request, 'ethsgebeya/contact.html')

def resend_activation_email(request):
    if request.method == 'POST':
        form = ResendActivationEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                if user.is_active:
                    messages.info(request, 'This account is already active. Please sign in.')
                    return redirect('sign-in')
                current_site = get_current_site(request)
                subject = 'Activate your ETHSGEBEYA account'
                html_message = render_to_string('registration/account_activation_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                })
                plain_message = strip_tags(html_message)
                send_mail(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)
                messages.success(request, 'A new activation email has been sent. Please check your inbox.')
                return redirect('sign-in')
            except User.DoesNotExist:
                messages.error(request, 'No account found with that email address.')
    else:
        form = ResendActivationEmailForm()
    return render(request, 'registration/resend_activation_email.html', {'form': form})

def custom_404_view(request, exception):
    return render(request, '404.html', status=404)
    
def check_env(request):
    db_engine = os.environ.get('DATABASE_ENGINE')
    db_name = os.environ.get('DATABASE_NAME')
    db_user = os.environ.get('DATABASE_USER')
    db_password = os.environ.get('DATABASE_PASSWORD')
    db_host = os.environ.get('DATABASE_HOST')
    db_port = os.environ.get('DATABASE_PORT')
    email_host_user = os.environ.get('EMAIL_HOST_USER')
    email_host_password = os.environ.get('EMAIL_HOST_PASSWORD')
    secret_key = os.environ.get('SECRET_KEY')
    html = f"""
    <h2>Environment Variables:</h2>
    <p><strong>DATABASE_ENGINE:</strong> {db_engine}</p>
    <p><strong>DATABASE_NAME:</strong> {db_name}</p>
    <p><strong>DATABASE_USER:</strong> {db_user}</p>
    <p><strong>DATABASE_PASSWORD:</strong> {db_password}</p>
    <p><strong>DATABASE_HOST:</strong> {db_host}</p>
    <p><strong>DATABASE_PORT:</strong> {db_port}</p>
    <p><strong>EMAIL_HOST_USER:</strong> {email_host_user}</p>
    <p><strong>EMAIL_HOST_PASSWORD:</strong> {email_host_password}</p>
    <p><strong>SECRET_KEY:</strong> {secret_key}</p>
    """
    return HttpResponse(html)
 
 






def companies(request):
    """Companies page: show followed companies first.
    If user follows none, display empty state with Explore button.
    Always also provide full list for optional explore section.
    """
    base_qs = (
        SellerProfile.objects
        .annotate(
            products_count=Count('product', filter=Q(product__is_active=True), distinct=True),
            followers_count=Count('followers', distinct=True),
            avg_rating=Avg('product__reviews__rating'),
        )
        .order_by('-followers_count', 'company_name')
    )

    now_time = timezone.localtime().time()
    all_sellers = list(base_qs)
    user_id = request.user.id if request.user.is_authenticated else None
    for s in all_sellers:
        try:
            s.is_open_now = bool(s.opening_time and s.closing_time and s.opening_time <= now_time <= s.closing_time)
        except Exception:
            s.is_open_now = False
        # Precompute follow status to avoid unsupported queryset method chaining in template
        if user_id:
            s.is_following = s.followers.filter(id=user_id).exists()
        else:
            s.is_following = False

    followed_sellers = [s for s in all_sellers if s.is_following]

    return render(request, 'ethsgebeya/companies.html', {
        'followed_sellers': followed_sellers,
    })

def companies_explore(request):
    """Separate Explore Companies page showing all sellers."""
    base_qs = (
        SellerProfile.objects
        .annotate(
            products_count=Count('product', filter=Q(product__is_active=True), distinct=True),
            followers_count=Count('followers', distinct=True),
            avg_rating=Avg('product__reviews__rating'),
        )
        .order_by('-followers_count', 'company_name')
    )

    now_time = timezone.localtime().time()
    all_sellers = list(base_qs)
    user_id = request.user.id if request.user.is_authenticated else None
    for s in all_sellers:
        try:
            s.is_open_now = bool(s.opening_time and s.closing_time and s.opening_time <= now_time <= s.closing_time)
        except Exception:
            s.is_open_now = False
        s.is_following = s.followers.filter(id=user_id).exists() if user_id else False

    return render(request, 'ethsgebeya/explore_companies.html', {
        'all_sellers': all_sellers,
    })
    
    
@login_required
def follow_seller(request, seller_id):
    """
    View for following a seller
    """
    if request.method == 'POST':
        try:
            seller = SellerProfile.objects.get(id=seller_id)
            
            # Check if user is already following
            if request.user in seller.followers.all():
                return JsonResponse({
                    'status': 'error', 
                    'message': 'You are already following this seller'
                })
            
            seller.followers.add(request.user)
            return JsonResponse({
                'status': 'success',
                'message': f'You are now following {seller.company_name}',
                'followers_count': seller.followers.count()
            })
            
        except SellerProfile.DoesNotExist:
            return JsonResponse({
                'status': 'error', 
                'message': 'Seller not found'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Invalid request method'
    })

@login_required
def unfollow_seller(request, seller_id):
    """
    View for unfollowing a seller
    """
    if request.method == 'POST':
        try:
            seller = SellerProfile.objects.get(id=seller_id)
            
            # Check if user is following
            if request.user not in seller.followers.all():
                return JsonResponse({
                    'status': 'error', 
                    'message': 'You are not following this seller'
                })
            
            seller.followers.remove(request.user)
            return JsonResponse({
                'status': 'success',
                'message': f'You have unfollowed {seller.company_name}',
                'followers_count': seller.followers.count()
            })
            
        except SellerProfile.DoesNotExist:
            return JsonResponse({
                'status': 'error', 
                'message': 'Seller not found'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Invalid request method'
    })

def seller_profile(request, seller_id):
    """
    View for displaying individual seller profile
    """
    seller = get_object_or_404(SellerProfile, id=seller_id)
    
    # Check if user is following this seller
    is_following = False
    if request.user.is_authenticated:
        is_following = request.user in seller.followers.all()
    
    context = {
        'seller': seller,
        'is_following': is_following,
        'followers_count': seller.followers.count(),
    }
    return render(request, 'seller_profile.html', context)

@login_required
def following_companies(request):
    """
    View for displaying companies that the user is following
    """
    sellers = SellerProfile.objects.filter(followers=request.user).order_by('-id')
    
    # Get search query
    search_query = request.GET.get('search', '')
    if search_query:
        sellers = sellers.filter(company_name__icontains=search_query)
    
    # Get filter by business type
    business_type = request.GET.get('business_type', '')
    if business_type:
        sellers = sellers.filter(business_type=business_type)
    
    context = {
        'sellers': sellers,
        'search_query': search_query,
        'selected_business_type': business_type,
    }
    return render(request, 'following_companies.html', context)

def seller_categories(request, category_slug=None):
    """
    View for displaying sellers by category
    """
    sellers = SellerProfile.objects.all().order_by('-id')
    
    # Filter by category if provided
    if category_slug:
        sellers = sellers.filter(categories__slug=category_slug)
    
    # Get search query
    search_query = request.GET.get('search', '')
    if search_query:
        sellers = sellers.filter(company_name__icontains=search_query)
    
    # Get filter by business type
    business_type = request.GET.get('business_type', '')
    if business_type:
        sellers = sellers.filter(business_type=business_type)
    
    context = {
        'sellers': sellers,
        'category_slug': category_slug,
        'search_query': search_query,
        'selected_business_type': business_type,
    }
    return render(request, 'seller_categories.html', context)

def verified_sellers(request):
    """
    View for displaying only verified sellers
    """
    sellers = SellerProfile.objects.filter(is_verified=True).order_by('-id')
    
    # Get search query
    search_query = request.GET.get('search', '')
    if search_query:
        sellers = sellers.filter(company_name__icontains=search_query)
    
    # Get filter by business type
    business_type = request.GET.get('business_type', '')
    if business_type:
        sellers = sellers.filter(business_type=business_type)
    
    context = {
        'sellers': sellers,
        'search_query': search_query,
        'selected_business_type': business_type,
    }
    return render(request, 'verified_sellers.html', context)

# API views for additional functionality
@login_required
def toggle_follow_seller(request, seller_id):
    """
    API view to toggle follow/unfollow a seller
    """
    if request.method == 'POST':
        try:
            seller = SellerProfile.objects.get(id=seller_id)
            
            if request.user in seller.followers.all():
                seller.followers.remove(request.user)
                action = 'unfollowed'
            else:
                seller.followers.add(request.user)
                action = 'followed'
            
            return JsonResponse({
                'status': 'success',
                'action': action,
                'followers_count': seller.followers.count(),
                'is_following': request.user in seller.followers.all()
            })
            
        except SellerProfile.DoesNotExist:
            return JsonResponse({
                'status': 'error', 
                'message': 'Seller not found'
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Invalid request method'
    })

def seller_stats(request, seller_id):
    """
    API view to get seller statistics
    """
    seller = get_object_or_404(SellerProfile, id=seller_id)
    
    stats = {
        'followers_count': seller.followers.count(),
        'is_verified': seller.is_verified,
        'business_type': seller.get_business_type_display(),
        'company_name': seller.company_name,
    }
    
    return JsonResponse({
        'status': 'success',
        'stats': stats
    })

# Utility functions
def get_business_type_display_name(business_type):
    """
    Helper function to get display name for business type
    """
    business_types = {
        'product_seller': 'Product Seller',
        'cafe_restaurant': 'Cafe and Restaurant',
        'service_provider': 'Service Provider',
    }
    return business_types.get(business_type, 'Unknown')

def get_sellers_by_business_type(business_type):
    """
    Helper function to get sellers by business type
    """
    return SellerProfile.objects.filter(business_type=business_type)

def get_popular_sellers(limit=10):
    """
    Helper function to get popular sellers by follower count
    """
    # This is a simplified version - you might want to optimize this
    sellers = SellerProfile.objects.all()
    return sorted(sellers, key=lambda s: s.followers.count(), reverse=True)[:limit]

def get_verified_sellers():
    """
    Helper function to get verified sellers
    """
    return SellerProfile.objects.filter(is_verified=True)