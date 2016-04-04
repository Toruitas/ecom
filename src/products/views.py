from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.http import Http404
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured

# from django_filters import FilterSet, CharFilter, NumberFilter  # moved-->filters.py
from rest_framework import generics  # view types
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework import filters
from rest_framework.response import Response
from rest_framework.reverse import reverse as api_reverse
from rest_framework.views import APIView

import random

from .forms import VariationInventoryForm, VariationInventoryFormSet, ProductFilterForm
from .models import Product, Variation, Category
from .mixins import LoginRequiredMixin, StaffRequiredMixin
from .serializers import CategorySerializer, ProductSerializer, ProductDetailSerializer,ProductDetailUpdateSerializer
from .pagination import ProductPagination, CategoryPagination
from .filters import ProductFilter

# Create your views here.

##### Function based view for contrast #########

def product_detail_view_func(request, id):
    """
    in template: {{ request.get_full_path }} doesn't actually get the full url. Use {{request.build_absolute_uri }}
    #TODO: add font-awesome
    :param request:
    :param id:
    :return:
    """
    # product_instance = Product.objects.get(id=id)
    product_instance = get_object_or_404(Product, id=id)  # basically = below try block
    try:
        product_instance = get_object_or_404(Product, id=id)
    except Product.DoesNotExist:
        raise Http404
    except:
        raise Http404
    template = "products/product_detail.html"
    context = {
        'object':product_instance,
        'template':template
    }
    return render(request, template, context)

######### CLASS BASED VIEWS BEYOTCH###############

class CategoryListView(ListView):
    model = Category
    queryset = Category.objects.all()
    template_name = "products/product_list.html"

class CategoryDetailView(DetailView):
    """
    {{ object.product_set.all }} will list all products assoc'd with a particular category
    """
    model = Category

    def get_context_data(self, *args,**kwargs):
        """
        So that we can see default category and product set come in no matter what. just in case we set a default but
        didn't include it in the Product's category list
        :param args:
        :param kwargs:
        :return:
        """
        # detail view will have an object, so this gets that instance
        context = super(CategoryDetailView,self).get_context_data(*args,**kwargs)
        obj = self.get_object()
        product_set = obj.product_set.all()
        default_products = obj.default_category.all()
        # since products & default use same model, we can combine easily with |
        products = (product_set | default_products).distinct()
        # .distinct removes duplicate results when combining querysets
        context['products'] = products
        return context



class ProductDetailView(DetailView):
    model = Product
    #template_name = "<appname>/modelname_detail.html" using get or 404
    # template_name = 'product.html' if you want to customize it

    def get_context_data(self, *args, **kwargs):
        """
        overriding stock method
        the .order_by("?")[:6] could go in the model manager if we want that to be the same all the time, on
        every view where related products could be seen. This is random order, limit 6

        however, order_by and distinct don't work very well together, so can replace order_by with Python's sorted.
        or import random, for lambda x: x.id would instead be x: random.random()
        :param kwargs:
        :return:
        """
        context = super(ProductDetailView,self).get_context_data(*args, **kwargs)
        instance = self.get_object()  # self.get_object gets the instance
        context['related'] = sorted(Product.objects.get_related(instance), key=lambda x: random.random(), reverse=True)[:6]
        return context


def product_list(request):
    """
    function based view, but we want class based...
    So disregard this, it is unused
    :param request:
    :return:
    """
    qs = Product.objects.all()
    ordering = request.GET.get('ordering')
    if ordering:
        qs = Product.objects.all().order_by(ordering)
    f = ProductFilter(request.GET,queryset=qs)
    return render(request, "products/product_list.html",
                  {"object_list": f})


class FilterMixin(object):
    filter_class = None
    search_ordering_param = "ordering"

    def get_queryset(self,*args,**kwargs):
        try:
            qs = super(FilterMixin,self).get_queryset(*args,**kwargs)
            return qs
        except:
            raise ImproperlyConfigured("You must have a queryset in order to use the FilterMixin")

    def get_context_data(self, *args, **kwargs):
        context = super(FilterMixin,self).get_context_data(*args,**kwargs)
        qs = self.get_queryset()
        ordering = self.request.GET.get(self.search_ordering_param)
        if ordering:
            qs = qs.order_by(ordering)
        filter_class = self.filter_class
        if filter_class:
            f = filter_class(self.request.GET,queryset=qs)
            context["object_list"] = f
        return context


class ProductListView(FilterMixin, ListView):
    """
    What is the context? In List views, it's auto in get_context_data(SELF).
    queryset using models is auto, too
    """
    model = Product
    queryset = Product.objects.all() # default queryset is <model>.objects.all()
    filter_class = ProductFilter

    def get_context_data(self, *args,**kwargs):
        """
        Sets the new context info on a ProductList View
        GET.get('q'): gets the GET request - the URL - and looks for a parameter q, which if nonexistent sets it to none.
        Can set default value with second param. True, 'string', whatever
        If leave off lowercase get... request.GET('q') and it isn't there, will error out. Same with post data.
        :param args:
        :param kwargs:
        :return:
        """
        context = super(ProductListView, self).get_context_data(*args,**kwargs)
        print(context)
        context["now"] = timezone.now()  # to add more stuff to context, just like adding to dict
        context['query'] = self.request.GET.get('q','default value')  # can set default value with second param
        context['filter_form'] = ProductFilterForm(data=self.request.GET or None)
        return context

    def get_queryset(self, *args, **kwargs):
        """
        by default we want to get teh standard queryset, then do stuff to it
        There are many Q queries to use. __startswith etc.
        Q filters let us add multiple filters at once.
        Then add to context data

        It's a GET method because it uses a query string in the url??
        name=q in the searchbar form since it corresponds to the search call we want

        Using the try/except block we can use text as well as decimals. It was erroring out with just decimals
        .distinct() means we are not getting multiple, so it won't give us two objects
        :param args:
        :param kwargs:
        :return:
        """
        qs = super(ProductListView, self).get_queryset(*args, **kwargs)  # this grabs what the normal query is
        query = self.request.GET.get('q')  # q is the parameter we're using from the bar
        if query:
            qs = self.model.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
                #Q(price=query)  # for price = 19.95 or whatever
            )
            try:
                qs2 = self.model.objects.filter(
                    Q(price=query)
                )
                qs = (qs | qs2).distinct()
            except:
                pass
        return qs

class VariationListView(StaffRequiredMixin, ListView):
    """
    Not quite the same as Product List View
    """
    model = Variation
    queryset = Variation.objects.all()

    def get_context_data(self, *args,**kwargs):
        context = super(VariationListView, self).get_context_data(*args,**kwargs)
        context["formset"] = VariationInventoryFormSet(queryset=self.get_queryset())  # form for editing
        return context

    def get_queryset(self, *args, **kwargs):
        # qs = super(VariationListView, self).get_queryset(*args, **kwargs)
        # query = self.request.GET.get('q')
        product_pk = self.kwargs.get('pk')
        if product_pk:
            product = get_object_or_404(Product,pk=product_pk)
            # qs = qs.filter(product=product)
            qs = Variation.objects.filter(product=product)
            return qs

    def post(self, request, *args,**kwargs):
        """
        Errors out if there is a blank form. Could probably rearrange things to loop through formset and test
        validity of EACH one.

        BETTER: Just don't use formsets to add data, use them only to edit data. If you want to add, create a dedicated view.

        TODO: add a way to dismiss flash messages. There's a way! It's in Bootstrap not Django. .alert-dismissable
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        formset = VariationInventoryFormSet(request.POST, request.FILES)  # request.FILES for uploaded files
        if formset.is_valid():
            formset.save(commit=False)  # doesn't commit save until...
            for form in formset:
                new_item = form.save(commit=False)
                # if new_item.title:
                product_pk = self.kwargs.get("pk")  # could just makea  get product method
                product = get_object_or_404(Product,pk=product_pk)
                new_item.product = product
                new_item.save()
                # form.save()  # here we save & commit
            messages.success(request,"Your inventory and pricing have been updated")
            return redirect("products:products")
        print(request.POST)
        raise Http404


## API class based views

class APIHomeView(APIView):
    # authentication_classes = [SessionAuthentication]
    # permission_classes = [IsAuthenticated]
    def get(self, request, format=None):
        data = {
            "auth":{
                "login_url": api_reverse('auth_login_api', request=request),
                'refresh_url':api_reverse("refresh_token_api", request=request),
                'user_checkout':api_reverse('user_checkout_api',request=request)
            },
            'address':{
                'url':api_reverse('user_address_list_api',request=request),
                'create':api_reverse('user_address_create_api',request=request)
            },
            'checkout':{
                'cart':api_reverse('cart_api',request=request),
                'checkout':api_reverse('checkout_api', request=request),
                'finalize':api_reverse('checkout_finalize_api',request=request)
            },
            "products":{
                "count":Product.objects.all().count(),
                "url":api_reverse("products_api", request=request)
            },
            "categories":{
                "count":Category.objects.all().count(),
                "url":api_reverse("categories_api",request=request)
            }
        }
        return Response(data)


class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # http://www.django-rest-framework.org/api-guide/pagination/
    pagination_class = CategoryPagination


class CategoryRetrieveAPIView(generics.RetrieveAPIView):
    """
    for category detail views e.g. accessories
    """
    # http://www.django-rest-framework.org/api-guide/authentication/#basicauthentication
    # http://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]  # uncomment so it will only work if logged in
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = ProductPagination


class ProductListAPIView(generics.ListAPIView):
    # https://github.com/codingforentrepreneurs/ecommerce-2-api/commit/a14a0d3f8f0d77321d3be19077626c71f4168de6
    permission_classes = [IsAuthenticated]
    # pagination_class is by default ProductPagination
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # http://www.django-rest-framework.org/api-guide/filtering/
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        filters.DjangoFilterBackend
    ]
    search_fields = ['title','description']
    ordering_fields = ['title','id']
    filter_class = ProductFilter
    # pagination_class = ProductPagination


class ProductRetrieveAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]  # can see if non-authenticated but not RUD
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer


class ProductCreateAPIView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductDetailUpdateSerializer
