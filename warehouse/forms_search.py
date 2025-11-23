from django import forms
from .models import Category

class ProductSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'placeholder': 'Search products...',
            'class': 'form-control',
            'aria-label': 'Search products',
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label='',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'aria-label': 'Filter by category',
        })
    )
