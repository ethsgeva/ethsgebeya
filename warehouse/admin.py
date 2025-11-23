from django.contrib import admin
from . import models
from .models import Wishlist


# Register your models here.



admin.site.register(models.SellerProfile)
admin.site.register(models.Category)
admin.site.register(models.Product)
admin.site.register(models.Image)
admin.site.register(models.ProductImage)
admin.site.register(models.AnalyticsReport)
admin.site.register(models.Order)
admin.site.register(models.CustomerInteraction)
admin.site.register(models.Review)
admin.site.register(models.UserProfile)
admin.site.register(Wishlist)

