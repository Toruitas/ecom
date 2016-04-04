from django.shortcuts import render, redirect
from django.views.generic.edit import FormView, CreateView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.contrib import messages
from django.http import Http404
from django.contrib.auth import get_user_model

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.authentication import SessionAuthentication


from .forms import AddressForm, UserAddressForm
from .models import UserAddress, UserCheckout, Order
from .mixins import CartOrderMixin, LoginRequiredMixin
from .serializers import UserAddressSerializer, OrderSerializer, OrderDetailSerializer
from .permissions import IsOwnerAndAuth


from carts.mixins import TokenMixin
# Create your views here.

User = get_user_model()

class UserAddressCreateView(CreateView):
    """
    https://docs.djangoproject.com/en/1.9/ref/class-based-views/generic-editing/#createview
    """
    form_class = UserAddressForm
    template_name = "forms.html"  # generic forms template
    success_url = "/checkout/address/"

    def get_checkout_user(self):
        user_checkout_id = self.request.session.get("user_checkout_id")
        user_checkout = UserCheckout.objects.get(id=user_checkout_id)
        return user_checkout

    def form_valid(self, form, *args, **kwargs):
        form.instance.user = self.get_checkout_user()
        return super(UserAddressCreateView, self).form_valid(form, *args, **kwargs)

class AddressSelectFormView(CartOrderMixin, FormView):
    form_class = AddressForm
    template_name = "orders/address_select.html"

    def dispatch(self, request, *args, **kwargs):
        """
        This method is automatically in all the classbased views
        """
        b_address, s_address = self.get_addresses()

        if not b_address:
            messages.success(self.request, "Please add a billing address before continuing")
            return redirect("user_address_create")
        elif not s_address:
            messages.success(self.request, "Please add a shipping address before continuing")
            return redirect("user_address_create")
        else:
            return super(AddressSelectFormView, self).dispatch(request, *args, **kwargs)

    def get_addresses(self, *args, **kwargs):
        user_checkout_id = self.request.session.get("user_checkout_id")
        user_checkout = UserCheckout.objects.get(id=user_checkout_id)

        b_address = UserAddress.objects.filter(
            user=user_checkout,
            type='billing'
        )
        s_address = UserAddress.objects.filter(
            user=user_checkout,
            type='shipping'
        )

        return b_address, s_address

    # here we change the queryset
    def get_form(self, *args, **kwargs):
        form = super(AddressSelectFormView,self).get_form(*args, **kwargs)
        # print(form.fields)  # see fields

        b_address, s_address = self.get_addresses()

        form.fields['billing_address'].queryset = b_address
        form.fields['shipping_address'].queryset = s_address
        return form

    def form_valid(self, form, *args, **kwargs):
        billing_address = form.cleaned_data["billing_address"]
        shipping_address = form.cleaned_data["shipping_address"]

        order = self.get_order()
        order.billing_address = billing_address
        order.shipping_address = shipping_address
        order.save()
        # set shipping ID
        self.request.session['billing_address_id'] = billing_address.id
        self.request.session['shipping_address_id'] = shipping_address.id
        # print(billing_address)
        # print(shipping_address)
        return super(AddressSelectFormView,self).form_valid(form, *args, **kwargs)

    def get_success_url(self, *args, **kwargs):
        return "/checkout/"

class OrderList(LoginRequiredMixin, ListView):
    """
    we override get_queryset
    """
    queryset = Order.objects.all()

    def get_queryset(self):
        # wouldn't work without login req'd
        user_checkout_id = self.request.user.id  # assume this is there
        user_checkout = UserCheckout.objects.get(id=user_checkout_id)
        return super(OrderList, self).get_queryset().filter(user=user_checkout)

class OrderDetail(DetailView):
    model = Order

    def dispatch(self, request, *args, **kwargs):
        """
        This needs to be done based on user session, since anon users can create orders
        """
        try:
            user_checkout_id = self.request.session.get("user_checkout_id")
            user_checkout = UserCheckout.objects.get(id=user_checkout_id)
        except UserCheckout.DoesNotExist:
            # if session variable not in there, but user is auth'd
            user_checkout = UserCheckout.objects.get(id=request.user)
            # user_checkout = request.user.usercheckout would work too, due to db model relationships
        except:
            user_checkout = None

        obj = self.get_object()  # instance method on class for detail view
        if obj.user == user_checkout and user_checkout:  # not none
            return super(OrderDetail, self).dispatch(request, *args, **kwargs)
        else:
            raise Http404


##### DJRF views

class UserCheckoutMixin(TokenMixin, object):

    def user_failure(self, message=None):
        data = {
            'message':'There was an error. Please try again',
            'success': False
        }
        if message:
            data['message'] = message
        return data

    def get_checkout_data(self, user=None, email=None):
        if email and not user:
            user_exists = User.objects.filter(email=email).count()
            if user_exists:
                return self.user_failure(message="This user already exists, please login")

        data = {}
        user_checkout = None

        if user and not email:
            if user.is_authenticated():
                user_checkout = UserCheckout.objects.get_or_create(user=user)[0]  # since tuple
        elif email:
            try:
                user_checkout = UserCheckout.objects.get_or_create(email=email)[0] # (instance, created)

                if user:
                    user_checkout = user
                    user_checkout.save()
            except:
                pass

        else:
            # user_checkout = False
            pass

        if user_checkout:
            data['success'] = True
            # data['token'] = user_checkout.get_client_token()
            data['braintree_id'] = user_checkout.get_braintree_id
            data['user_checkout_id'] = user_checkout.id
            data['user_checkout_token'] = self.create_token(data)  # from TokenMixin

            del data['braintree_id']  # clear after checkout complete?
            del data['user_checkout_id']
        return data

class UserCheckoutAPI(UserCheckoutMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        data = self.get_checkout_data(user=request.user)
        return Response(data)

    def post(self, request, format=None):
        data = {}
        email = request.data.get('email')

        if request.user.is_authenticated():
            if email == request.user.email:
                data = self.get_checkout_data(user=request.user, email=email)
            else:
                data = self.get_checkout_data(user=request.user)
        elif email and not request.user.is_authenticated():
            data = self.get_checkout_data(email=email)
        else:
            data = self.user_failure(message="Make sure you are authenticated or using a valid email.")
        return Response(data)

# class UserAddressCreateAPIView(CreateAPIView):
#     # simple apiview
#     model = UserAddress
#     serializer_class = UserAddressSerializer
#

class UserAddressCreateAPIView(CreateAPIView):
    model = UserAddress
    serializer_class = UserAddressSerializer

class UserAddressListAPIView(TokenMixin,ListAPIView):
    model = UserAddress
    queryset = UserAddress.objects.all()
    serializer_class = UserAddressSerializer

    def get_queryset(self, *args, **kwargs):
        user_checkout_token = self.request.GET.get('checkout_token')
        user_checkout_data = self.parse_token(user_checkout_token)
        user_checkout_id = user_checkout_data.get('user_checkout_id')
        if self.request.user.is_authenticated():
            return UserAddress.objects.filter(user__user=self.request.user)
        elif user_checkout_id:
            return UserAddress.objects.filter(user__id=int(user_checkout_id))
        else:
            return []

class OrderRetrieveAPIView(RetrieveAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOwnerAndAuth]
    model = Order
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer

    def get_queryset(self, *args, **kwargs):
        return Order.objects.filter(user__user=self.request.user)


class OrderListAPIView(ListAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOwnerAndAuth]
    model = Order
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer

    def get_queryset(self, *args, **kwargs):
        return Order.objects.filter(user__user=self.request.user)