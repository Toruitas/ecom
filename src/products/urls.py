from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin

from .views import(
    product_detail_view_func,
    ProductDetailView,
    ProductListView,
    VariationListView,
    product_list
)


app_name = 'products'

urlpatterns = [
    # Examples:
    # url(r'^products/', include('products.urls')),  # $ signals end of string
    # url(r'^(?P<id>\d+)', product_detail_view_func, name='product_detail_function'),  #products. == 'products.views.product_detail_function
    url(r'^(?P<pk>\d+)/inventory/?$', VariationListView.as_view(), name='product_inventory'),
    url(r'^(?P<pk>\d+)/$', ProductDetailView.as_view(), name='product_detail'),  # class based version must be pk.. ? after the trailing slash makes it optional in regexp
    url(r'^$', ProductListView.as_view(),name='products'),
    # url(r'^$', product_list,name='products'),
]