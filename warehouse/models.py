
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator


class SellerProfile(models.Model):



    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sellerprofile')
    company_name = models.CharField(max_length=255)
    create_logo = models.ImageField(upload_to='warehouse/settings/', blank=True, null=True)
    description = models.TextField(max_length=25000)
    contact_number = models.CharField(max_length=15)
    address = models.TextField()
    opening_time = models.TimeField(verbose_name='Opening Time', default='12:00')
    closing_time = models.TimeField(verbose_name='Closing Time', default='12:00')
    followers = models.ManyToManyField(User, related_name='following_sellers', blank=True)
    # Optional map coordinates (WGS84)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    business_type = models.CharField(
        max_length=50,
        choices=[
            ('product_seller', 'Product Seller'),
            ('cafe_restaurant', 'Cafe and Restaurant'),
            ('service_provider', 'Service Provider'),
        ],
        default='product_seller'
    )
    
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.company_name


class Category(models.Model): 
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)  # Allow blank=True initially
    description = models.TextField(blank=True, null=True)  # Add description field
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:  # Generate slug only on creation
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Product(models.Model):
    PRICING_TYPES = [
        ('fixed', 'Fixed Price'),
        ('hourly', 'Hourly Rate'),
        ('custom', 'Custom Quote'),
    ]
    
    SIZE_CHOICES = [
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Product-specific fields
    size = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=200, blank=True)
    in_stock = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    brand = models.CharField(max_length=255, blank=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    dimensions = models.CharField(max_length=255, blank=True)
    material = models.CharField(max_length=255, blank=True)
    seller_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Service-specific fields
    pricing_type = models.CharField(max_length=10, choices=PRICING_TYPES, default='fixed')
    service_duration = models.CharField(max_length=100, blank=True, help_text="e.g., 2 hours, 1 day")
    service_area = models.TextField(blank=True, help_text="Specific locations where service is available")
    availability_schedule = models.BooleanField(default=False, help_text="Whether scheduling is required")
    available_now = models.BooleanField(default=True)
    
    # Food-specific fields
    ingredients = models.TextField(blank=True, help_text="List of main ingredients")
    preparation_time = models.CharField(max_length=100, blank=True, help_text="e.g., 15-20 minutes")
    dietary_info = models.TextField(blank=True, help_text="Dietary restrictions, allergens, etc.")
    
    # Common fields
    free_delivery = models.BooleanField(default=False)
    delivery_conditions = models.TextField(blank=True, help_text="Conditions for free delivery")
    size_options = models.JSONField(default=dict, blank=True, help_text="Available size options")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    def get_average_rating(self):
        reviews = self.reviews.all()
        if reviews.count() > 0:
            return reviews.aggregate(average=Avg('rating'))['average']
        else:
            return None

    def save(self, *args, **kwargs):
        if not self.seller_phone and self.seller and hasattr(self.seller, 'contact_number'):
            self.seller_phone = self.seller.contact_number
        
        # Auto-set availability based on stock
        if hasattr(self, 'stock_quantity'):
            self.in_stock = self.stock_quantity > 0
            
        super().save(*args, **kwargs)
    
    @property
    def is_service(self):
        return self.category and self.category.category_type == 'service'
    
    @property
    def is_food(self):
        return self.category and self.category.category_type == 'food'
    
    @property
    def is_product(self):
        return self.category and self.category.category_type == 'product'


class Image(models.Model):
    image = models.ImageField(upload_to='warehouse/photos/')


class ProductImage(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')

    def __str__(self):
        return f"Image for {self.product.title}"


class AnalyticsReport(models.Model):
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE)
    sales_data = models.TextField()
    performance_metrics = models.TextField()

    def __str__(self):
        return f"Analytics for {self.seller.company_name}"


class Order(models.Model):
    STATUS_CHOICES = (
        ('P', 'Pending'),
        ('W', 'Waiting for Buyer Confirmation'),
        ('C', 'Completed'),
        ('X', 'Cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_user')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders_as_product')
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    created_at = models.DateTimeField(auto_now_add=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

class CustomerInteraction(models.Model):
    TYPE_CHOICES = (
        ('V', 'Product View'),
        ('C', 'Cart Addition'),
        ('P', 'Purchase'),
    )
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=1, choices=TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.product.title} by {self.user.username}"

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    profile_img = models.ImageField(upload_to='profile/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlists')
    products = models.ManyToManyField('Product', related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist of {self.user.username}"