from django import forms
from warehouse.models import Product

class WishlistAddForm(forms.Form):
    product_id = forms.UUIDField()

class WishlistRemoveForm(forms.Form):
    product_id = forms.UUIDField()
