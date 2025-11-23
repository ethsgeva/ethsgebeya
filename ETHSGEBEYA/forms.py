from django import forms

class ResendActivationEmailForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=254, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email address',
        'autocomplete': 'email',
    }))
