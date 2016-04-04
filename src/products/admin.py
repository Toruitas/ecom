from django.contrib import admin

# Register your models here.
from .models import Product, Variation, ProductImage, Category, ProductFeatured


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class VariationInline(admin.TabularInline):
    """
    Way better way than having a separate Variation manager. basically, plus the inlines below in ProductAdmin,
    adds a Variation section with all associated inlines to Product manager in Admin
    https://docs.djangoproject.com/en/1.9/ref/contrib/admin/#django.contrib.admin.InlineModelAdmin
    """
    model = Variation
    extra = 0  # doesn't show extra empty fields by default
    max_num = 10  # max number of 10 images. Basically limits options


class ProductAdmin(admin.ModelAdmin):
    """
    Must register with model itself. This shows inline info such as price
    """
    list_display = ["__str__", 'price']

    inlines = [
        VariationInline,
        ProductImageInline
    ]

    class Meta:
        model = Product


admin.site.register(Product, ProductAdmin)
# admin.site.register(Variation)
admin.site.register(ProductImage)
admin.site.register(Category)
admin.site.register(ProductFeatured)
