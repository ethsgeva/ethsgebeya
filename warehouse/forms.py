# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import SellerProfile, Product, Category, Review
from .widgets import MultipleFileField
from .forms_wishlist import WishlistAddForm, WishlistRemoveForm
from .forms_search import ProductSearchForm

class BasicUserForm(forms.ModelForm):
    class Meta:
        model = User 
        fields = ('first_name', 'last_name',)


class BasicSellerForm(forms.ModelForm):
    # Business type field with FontAwesome icons
    BUSINESS_TYPE_CHOICES = [
        ('product_seller', '<i class="fas fa-shopping-bag"></i> Product Seller'),
        ('cafe_restaurant', '<i class="fas fa-utensils"></i> Cafe and Restaurant'),
        ('service_provider', '<i class="fas fa-tools"></i> Service Provider'),
    ]
    
    business_type = forms.ChoiceField(
        choices=BUSINESS_TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'business-type-select',
            'onchange': 'toggleBusinessFields()'
        })
    )

    class Meta:
        model = SellerProfile
        fields = (
            'company_name', 'create_logo', 'business_type', 
            'opening_time', 'closing_time', 'description', 
            'contact_number', 'address', 'latitude', 'longitude'
        )
        widgets = {
            'company_name': forms.TextInput(attrs={
                'placeholder': 'Enter your business name',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Describe your business...',
                'rows': 4,
                'required': 'required'
            }),
            'contact_number': forms.TextInput(attrs={
                'placeholder': 'e.g., +251 91 123 4567',
                'required': 'required'
            }),
            'address': forms.Textarea(attrs={
                'placeholder': 'Enter your business address...',
                'rows': 3,
                'required': 'required'
            }),
            'opening_time': forms.TimeInput(attrs={
                'type': 'time',
                'required': 'required'
            }),
            'closing_time': forms.TimeInput(attrs={
                'type': 'time',
                'required': 'required'
            }),
            'latitude': forms.NumberInput(attrs={
                'step': 'any', 
                'placeholder': 'e.g. 8.5562',
                'min': '-90',
                'max': '90'
            }),
            'longitude': forms.NumberInput(attrs={
                'step': 'any', 
                'placeholder': 'e.g. 39.1234',
                'min': '-180',
                'max': '180'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial business type if editing
        if self.instance and self.instance.pk:
            self.fields['business_type'].initial = self.instance.business_type

    def clean_contact_number(self):
        """Validate contact number"""
        contact_number = self.cleaned_data.get('contact_number')
        if contact_number:
            # Remove any non-digit characters except +
            cleaned_number = ''.join(c for c in contact_number if c.isdigit() or c == '+')
            
            # Basic validation for Ethiopian phone numbers
            if cleaned_number.startswith('+251') and len(cleaned_number) != 13:
                raise forms.ValidationError("Ethiopian international numbers should be +251 followed by 9 digits.")
            elif cleaned_number.startswith('0') and len(cleaned_number) != 10:
                raise forms.ValidationError("Ethiopian local numbers should be 10 digits starting with 0.")
            
            return contact_number
        return contact_number

    def clean_opening_time(self):
        """Validate opening time"""
        opening_time = self.cleaned_data.get('opening_time')
        closing_time = self.cleaned_data.get('closing_time')
        
        if opening_time and closing_time:
            if opening_time >= closing_time:
                raise forms.ValidationError("Opening time must be before closing time.")
        
        return opening_time

    def clean_closing_time(self):
        """Validate closing time"""
        opening_time = self.cleaned_data.get('opening_time')
        closing_time = self.cleaned_data.get('closing_time')
        
        if opening_time and closing_time:
            if closing_time <= opening_time:
                raise forms.ValidationError("Closing time must be after opening time.")
        
        return closing_time

    def clean_latitude(self):
        """Validate latitude"""
        latitude = self.cleaned_data.get('latitude')
        if latitude is not None:
            if latitude < -90 or latitude > 90:
                raise forms.ValidationError("Latitude must be between -90 and 90 degrees.")
        return latitude

    def clean_longitude(self):
        """Validate longitude"""
        longitude = self.cleaned_data.get('longitude')
        if longitude is not None:
            if longitude < -180 or longitude > 180:
                raise forms.ValidationError("Longitude must be between -180 and 180 degrees.")
        return longitude

    def clean(self):
        """Overall form validation"""
        cleaned_data = super().clean()
        
        # Ensure either both coordinates are provided or neither
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if (latitude is not None and longitude is None) or (longitude is not None and latitude is None):
            raise forms.ValidationError("Please provide both latitude and longitude, or leave both blank.")
        
        return cleaned_data


class EditProductForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)
    
    # Product-specific fields
    stock_quantity = forms.IntegerField(
        required=False, 
        min_value=0,
        widget=forms.NumberInput(attrs={'placeholder': 'Available quantity'})
    )
    color = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Red, Blue, Large, Medium'})
    )
    brand = forms.CharField(required=False, max_length=255)
    
    # Service-specific fields
    PRICING_TYPES = [
        ('fixed', 'Fixed Price'),
        ('hourly', 'Hourly Rate'),
        ('custom', 'Custom Quote'),
    ]
    pricing_type = forms.ChoiceField(
        choices=PRICING_TYPES, 
        required=False, 
        initial='fixed'
    )
    service_duration = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 2 hours, 1 day'})
    )
    service_area = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Addis Ababa, Specific locations'})
    )
    
    # Food-specific fields
    ingredients = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'List main ingredients'})
    )
    preparation_time = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 15-20 minutes'})
    )
    
    # Availability options
    available_now = forms.BooleanField(required=False, initial=True)
    availability_schedule = forms.BooleanField(required=False, initial=False)
    
    # Size options (multiple choice)
    SIZE_CHOICES = [
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
    ]
    size_options = forms.MultipleChoiceField(
        choices=SIZE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    # Delivery options
    free_delivery = forms.BooleanField(required=False, initial=False)
    delivery_conditions = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., For orders above 500 Birr, Within 10km radius'})
    )

    class Meta:
        model = Product
        fields = [
            'title', 'description', 'price', 'in_stock', 'is_active', 'category',
            'stock_quantity', 'color', 'brand', 'pricing_type', 'service_duration',
            'service_area', 'ingredients', 'preparation_time', 'available_now',
            'availability_schedule', 'free_delivery', 'delivery_conditions'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'required': 'required',
                'placeholder': 'Enter item name'
            }),
            'price': forms.NumberInput(attrs={
                'required': 'required', 
                'min': '0',
                'step': '0.01',
                'placeholder': 'Price in Birr'
            }),
            'description': forms.Textarea(attrs={
                'required': 'required',
                'placeholder': 'Describe your item...',
                'rows': 4
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make category required in the form
        self.fields['category'].required = True
        
        # If editing an existing instance, populate size_options
        if self.instance and self.instance.pk:
            if self.instance.size_options:
                self.fields['size_options'].initial = list(self.instance.size_options.keys())
            
            # Set initial stock_quantity based on in_stock if not already set
            if not self.instance.stock_quantity and self.instance.in_stock:
                self.fields['stock_quantity'].initial = 1

    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure required fields are filled
        if not cleaned_data.get('title'):
            self.add_error('title', 'Title is required.')
        if not cleaned_data.get('price'):
            self.add_error('price', 'Price is required.')
        if not cleaned_data.get('description'):
            self.add_error('description', 'Description is required.')
        if not cleaned_data.get('category'):
            self.add_error('category', 'Category is required.')
        
        # Validate price is positive
        price = cleaned_data.get('price')
        if price and price < 0:
            self.add_error('price', 'Price cannot be negative.')
        
        # Auto-set in_stock based on stock_quantity
        stock_quantity = cleaned_data.get('stock_quantity', 0)
        if stock_quantity is not None:
            cleaned_data['in_stock'] = stock_quantity > 0
        
        # Process size_options into JSON format
        size_options = cleaned_data.get('size_options', [])
        if size_options:
            cleaned_data['size_options'] = {size: True for size in size_options}
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set in_stock based on stock_quantity
        stock_quantity = self.cleaned_data.get('stock_quantity', 0)
        instance.in_stock = stock_quantity > 0 if stock_quantity is not None else True
        
        if commit:
            instance.save()
            
        return instance




class AddProductForm(forms.ModelForm):
    images = MultipleFileField(required=True)
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=True)
    
    # Product-specific fields
    stock_quantity = forms.IntegerField(
        required=False, 
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={'placeholder': 'Available quantity'})
    )
    color = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Red, Blue, Large, Medium'})
    )
    brand = forms.CharField(required=False, max_length=255)
    
    # Service-specific fields
    PRICING_TYPES = [
        ('fixed', 'Fixed Price'),
        ('hourly', 'Hourly Rate'),
        ('custom', 'Custom Quote'),
    ]
    pricing_type = forms.ChoiceField(
        choices=PRICING_TYPES, 
        required=False, 
        initial='fixed'
    )
    service_duration = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 2 hours, 1 day'})
    )
    service_area = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Addis Ababa, Specific locations'})
    )
    
    # Food-specific fields
    ingredients = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'List main ingredients'})
    )
    preparation_time = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 15-20 minutes'})
    )
    
    # Availability options
    available_now = forms.BooleanField(required=False, initial=True)
    availability_schedule = forms.BooleanField(required=False, initial=False)
    
    # Size options (multiple choice)
    SIZE_CHOICES = [
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
    ]
    size_options = forms.MultipleChoiceField(
        choices=SIZE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    # Delivery options
    free_delivery = forms.BooleanField(required=False, initial=False)
    delivery_conditions = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., For orders above 500 Birr, Within 10km radius'})
    )

    class Meta:
        model = Product
        fields = [
             'title', 'price', 'description', 'category',
            # Product fields
            'stock_quantity', 'is_active', 'color', 'brand',
            # Service fields  
            'pricing_type', 'service_duration', 'service_area',
            # Food fields
            'ingredients', 'preparation_time', 'dietary_info',
            # Common fields
            'available_now', 'availability_schedule', 
            'free_delivery', 'delivery_conditions'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'required': 'required',
                'placeholder': 'Enter item name'
            }),
            'price': forms.NumberInput(attrs={
                'required': 'required', 
                'min': '0',
                'step': '0.01',
                'placeholder': 'Price in Birr'
            }),
            'description': forms.Textarea(attrs={
                'required': 'required',
                'placeholder': 'Describe your item...',
                'rows': 4
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values
        self.fields['available_now'].initial = True
        self.fields['free_delivery'].initial = False
        self.fields['availability_schedule'].initial = False
        
        # Make category required
        self.fields['category'].required = True
        
        # If editing an existing instance, populate size_options
        if self.instance and self.instance.pk and self.instance.size_options:
            self.fields['size_options'].initial = list(self.instance.size_options.keys())

    def clean(self):
        cleaned_data = super().clean()
        images = self.files.getlist('images') if hasattr(self, 'files') else []
        if not images:
            raise forms.ValidationError('At least one product image is required.')
        if len(images) > 5:
            raise forms.ValidationError('You can upload a maximum of 5 images per product.')
        # Ensure required fields are filled
        if not cleaned_data.get('title'):
            self.add_error('title', 'Title is required.')
        if not cleaned_data.get('price'):
            self.add_error('price', 'Price is required.')
        if not cleaned_data.get('description'):
            self.add_error('description', 'Description is required.')
        return cleaned_data


    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set in_stock based on stock_quantity
        stock_quantity = self.cleaned_data.get('stock_quantity', 0)
        instance.in_stock = stock_quantity > 0
        # Handle size_options (convert to JSON)
        size_options = self.cleaned_data.get('size_options', [])
        instance.size_options = {size: True for size in size_options} if size_options else {}
        if commit:
            instance.save()
        return instance
    
class AnalyticsFilterForm(forms.Form):
    DATE_RANGE_CHOICES = (
        ('7', 'Last 7 Days'),
        ('30', 'Last 30 Days'),
        ('90', 'Last 90 Days'),
        ('365', 'Last Year'),
        ('custom', 'Custom Range'),
    )
    
    date_range = forms.ChoiceField(
        choices=DATE_RANGE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='30'
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_range = cleaned_data.get('date_range')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if date_range == 'custom' and (not start_date or not end_date):
            raise forms.ValidationError("Please select both start and end dates for custom range.")
        
        return cleaned_data

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required. Enter a valid email address.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i} Stars') for i in range(1, 6)]),
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your review...'}),
        }

