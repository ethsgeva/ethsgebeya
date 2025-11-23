from django import forms

class CheckoutForm(forms.Form):
    address = forms.CharField(
        label='Shipping Address', 
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'required': 'required', 'placeholder': 'Enter your address'}), 
        max_length=500,
        required=True,
        error_messages={'required': 'Address is required.'}
    )
    phone = forms.CharField(
        label='Phone Number', 
        max_length=20, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': 'required', 'placeholder': 'Enter your phone number'}),
        required=True,
        error_messages={'required': 'Phone number is required.'}
    )
    # The rest of the fields will be added dynamically in the view for each cart item
