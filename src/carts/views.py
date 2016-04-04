from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, Http404, JsonResponse
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin, DetailView
from django.core.urlresolvers import reverse
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic.edit import FormMixin
from django.contrib import messages
from django.conf import settings

import braintree

from rest_framework import filters
from rest_framework import generics
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.reverse import reverse as api_reverse
from rest_framework.views import APIView

import ast
import base64
import json

from orders.models import UserCheckout, Order, UserAddress
from orders.forms import GuestCheckoutForm
from orders.mixins import CartOrderMixin
from orders.serializers import OrderSerializer, FinalizedOrderSerializer
from products.models import Variation
from .models import Cart, CartItem
from .serializers import CartItemSerializer, CheckoutSerializer
from .mixins import CartUpdateAPIMixin, TokenMixin, CartTokenMixin

#Create your views here.

if settings.DEBUG:
    braintree.Configuration.configure(braintree.Environment.Sandbox,
                                      merchant_id=settings.BRAINTREE_MERCHANT_ID,
                                      public_key=settings.BRAINTREE_PUBLIC,
                                      private_key=settings.BRAINTREE_PRIVATE)

class CartView(SingleObjectMixin,View):
    model = Cart
    template_name = "carts/view.html"

    def get_object(self, *args, **kwargs):
        self.request.session.set_expiry(0)  # 300s = 5 minutes. If 0, will end when browser closes.
        cart_id = self.request.session.get("cart_id")
        if not cart_id:
            cart = Cart()
            # self.request.user.get_tax_percentage
            # cart.tax_percentage = 0.075  # to set it for an individual cart
            cart.save()
            cart_id=cart.id
            # basically the same as Cart.objects.create()
            self.request.session["cart_id"] = cart.id
        cart = Cart.objects.get(id=cart_id)
        if self.request.user.is_authenticated():
            # cart = Cart.objects.get(id=cart_id, user=request.user)
            cart.user = self.request.user
            cart.save()
        return cart

    def get(self, request, *args, **kwargs):
        """
        This shouldn't be used for both the cart and item views, tbh. It sets the qty in the cart to this value, but in
        the item view, it should add the amount instead. Edit later.

        ?item=1&qty=10
        get_or_create returns tuple (object, created)

        Very basic way of creating, removing, or updating item to cart

        Session'd carts.
        https://docs.djangoproject.com/es/1.9/topics/http/sessions/

        assumes user adds to cart

        Basic funct base view

        GET request form based on the URL, not POST request form

        If the request is AJAX, do stuff for product detail form
        https://docs.djangoproject.com/en/1.9/ref/request-response/#jsonresponse-objects
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        # for session variable cart
        cart = self.get_object()
        # if request.is_ajax():
        #     print(request.GET.get("item"))  # prints variation id num
        #     return JsonResponse({"success":True})

        item_id = request.GET.get('item')
        delete_item = request.GET.get('delete',False)
        item_added = False
        flash_message = ""
        if item_id:
            item_instance = get_object_or_404(Variation,id=item_id)
            qty = request.GET.get('qty', 1)  # we assume it is an int, and default 1
            try:
                if int(qty) < 1:
                    delete_item = True
            except:
                raise Http404
            cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item_instance)  #
            if created:  # if item is not in cart and is added for first time
                item_added = True
                flash_message = "Item successfully added to cart"  # could say item itself, but... lazy mode
            if delete_item:
                cart_item.delete()
                print('success deletion')
                flash_message = "Item successfully removed from cart"
            else:
                cart_item.quantity = qty
                cart_item.save()
                print(item_id,qty)
                print('creation/update success')
                if not created:
                    flash_message = "Quantity successfully updated"
            if not request.is_ajax():
                # for when we do manual calls to this page, it will redirect and get rid of the ?item=7&qty=1 bit
                return HttpResponseRedirect(reverse("cart"))
                # return cart_item.cart.get_absolute_url()  # but neither cart nor cart item have this method yet

        if request.is_ajax():
            try:
                line_total = cart_item.line_item_total
            except:
                line_total = None
            try:
                subtotal = cart_item.cart.subtotal
            except:
                subtotal = None
            try:
                cart_total = cart_item.cart.total
            except:
                cart_total = None
            try:
                tax_total = cart_item.cart.tax_total
            except:
                tax_total = None
            #try:
            total_items = cart_item.cart.items.count()  # shouldn't this return 0 if 0 anyway?
            print("total items "+ str(total_items))
            # except:
            #     total_items = 0

            return JsonResponse({"deleted":delete_item,
                                 "item_added":item_added,
                                 'line_total': line_total,
                                 "flash_message":flash_message,
                                 "total_items":total_items,
                                 "subtotal": subtotal,
                                 "tax_total":tax_total,
                                 "cart_total":cart_total
                                 })
        context = {
            'object': cart,
        }
        template = self.template_name
        return render(request, template, context)
        # return HttpResponseRedirect("/")


class ItemCountView(View):
    """
    function(response){
    console.log(response.responseText()) will get response text in the js script
    }
    This gives the number of unique items, not the total quantity of items
    """

    def get(self,request, *args, **kwargs):
        if request.is_ajax():
            cart_id = self.request.session.get("cart_id")
            if not cart_id:
                count = 0
            else:
                cart = Cart.objects.get(id=cart_id)
                count = cart.items.count()
            request.session["cart_item_count"] = count  # set it in the session for speed
            return JsonResponse({"count":count})
        else:
            raise Http404




class CheckoutView(CartOrderMixin, FormMixin, DetailView):
    """
    Mixing before detail view
    Shouldn't be able to continue unless they're logged in or proceeding as a guest
    This redirects to cart if it is empty

    Checkout view handles guest checkout form
    """
    model = Cart
    form_class = GuestCheckoutForm
    template_name = "carts/checkout_view.html"
    # success_url = "/checkout"  # reverse("checkout") can do this way

    def get_object(self, *args, **kwargs):
        """
        helper func
        :param args:
        :param kwargs:
        :return:
        """
        cart = self.get_cart()
        if not cart:
            return None  # what does credits do?
        # cart = Cart.objects.get(id=cart)
        return cart

    def get_context_data(self, *args,**kwargs):
        """
        We will piggyback off of Django registration redux form
        """
        context = super(CheckoutView, self).get_context_data(*args, **kwargs)
        user_can_continue = False
        user_checkout_id = self.request.session.get('user_checkout_id')

        # if not self.request.user.is_authenticated() or not user_checkout_id:  # if no guest id
        #
        # elif self.request.user.is_authenticated() or user_checkout_id: #or is guest
        #     user_can_continue = True
        # else:
        #     pass

        if self.request.user.is_authenticated():
            user_can_continue = True
            user_checkout, created = UserCheckout.objects.get_or_create(email=self.request.user.email)
            user_checkout.user = self.request.user
            user_checkout.save()
            context['client_token'] = user_checkout.get_client_token()
            self.request.session['user_checkout_id'] = user_checkout.id
        elif not self.request.user.is_authenticated() and not user_checkout_id:
            context['login_form'] = AuthenticationForm()
            context['next_url'] = self.request.build_absolute_uri()
        else:
            pass

        if user_checkout_id:
            # kinda interrupts the guest login flow
            user_can_continue = True
            if not self.request.user.is_authenticated():  # for GUEST USER
                user_checkout_2 = UserCheckout.objects.get(id=user_checkout_id)
                context['client_token'] = user_checkout_2.get_client_token()

        # if self.get_cart():
        context['order'] = self.get_order()
        context['user_can_continue'] = user_can_continue
        context['form'] = self.get_form()  # comes from form mixin
        # print(context)
        return context

    def post(self, *args,**kwargs):
        """
        If you don't implement it on a detail view, as well as a form, you get a 405 error. Method not allowed.

        If we were using a FormView, it would already have def post in there, but it isn't in detail view.

        https://docs.djangoproject.com/en/1.9/topics/class-based-views/mixins/#using-formmixin-with-detailview
        """
        self.object = self.get_object()  # for validation stuff
        form = self.get_form()
        if form.is_valid():
            # print(form.cleaned_data)
            email = form.cleaned_data.get('email')
            user_checkout, created = UserCheckout.objects.get_or_create(email=email)  # do get or create, since if already exists
            self.request.session['user_checkout_id'] = user_checkout.id  # to assoc to order
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        """
        or
        :return:
        """
        return reverse('checkout')

    # def get_order(self, *args, **kwargs):
    #     new_order_id = self.request.session.get("order_id")
    #     cart = self.get_object()
    #     if not new_order_id:
    #         new_order = Order.objects.create(cart=cart)
    #         self.request.session["order_id"] = new_order.id
    #     else:
    #         new_order = Order.objects.get(id=new_order_id)
    #     return new_order

    def get(self, request, *args, **kwargs):
        get_data = super(CheckoutView, self).get(request, *args, **kwargs)
        cart = self.get_object()
        if not cart:
            return redirect("cart")
        user_checkout_id = request.session.get('user_checkout_id')
        new_order = self.get_order()
        if user_checkout_id:
            user_checkout = UserCheckout.objects.get(id=user_checkout_id)
            if not new_order.billing_address or not new_order.shipping_address:
                return redirect("order_address")

            # billing_address_id = self.request.session.get("billing_address_id")
            # shipping_address_id = self.request.session.get("shipping_address_id")
            #
            # if not billing_address_id or not shipping_address_id:
            #     return redirect("order_address")
            # else:
            #     billing_address = UserAddress.objects.get(id=billing_address_id)
            #     shipping_address = UserAddress.objects.get(id=shipping_address_id)

            # new_order.cart = cart

            # new_order.billing_address = billing_address
            # new_order.shipping_address = shipping_address

            new_order.user = user_checkout
            new_order.save()
            print("order saved")

        return get_data

class CheckoutFinalView(CartOrderMixin, View):
    """
    https://developers.braintreepayments.com/reference/request/transaction/sale/python#amount
    """
    def post(self, request, *args, **kwargs):

        # nonce for braintree
        nonce = (request.POST.get("payment_method_nonce"))
        order = self.get_order()
        order_total = order.order_total
        if nonce:
            # https://developers.braintreepayments.com/reference/request/transaction/sale/python#amount
            result = braintree.Transaction.sale({
                "amount": order_total,
                "payment_method_nonce": nonce,
                "options": {
                    "submit_for_settlement": True
                },
                "billing":{
                    "postal_code":"{}".format(order.billing_address.zipcode)
                }
            })

            if result.is_success:
                print(result.transaction.id)
                order.mark_completed(order_id=result.transaction.id)
                messages.success(request, "Thanks for your order")
                del request.session["cart_id"]
                del request.session["order_id"]
            else:
                messages.success(request, "{}".format(result.message))  # if not success, will return human readable message
                return redirect("checkout")

        return redirect("checkout", pk=order.pk)  # should now redirect to cart, since in mixin we have none. pk same as id

    def get(self, request, *args, **kwargs):
        return redirect("checkout")



#########
# API Views
#########




class CartAPIView(CartTokenMixin, CartUpdateAPIMixin, APIView):
    # authentication_classes = [SessionAuthentication]
    # permission_classes = [IsAuthenticated]
    token_param = "token"
    cart = None

    # MOVED TO MIXIN
    # def create_token(self, cart_id):
    #     data = {
    #         "cart_id": cart_id
    #     }
    #     # is this how to best encode everywhere?
    #     token = base64.b64encode(bytes(str(data), 'utf-8'))  # need to UTF-8 encode because reasons
    #     # http://stackoverflow.com/questions/8908287/base64-encoding-in-python-3
    #     token = token.decode('utf-8')
    #     self.token = token
    #     return token

    def get_cart(self):
        # cart_id = self.request.GET.get('cart_id')
        # try:
        #     cart = Cart.objects.get(id=cart_id)
        # except:
        #     cart = Cart.objects.all().first()
        # return cart

        data, cart_obj, response_status = self.get_cart_from_token()

        if not cart_obj or not cart_obj.active:
            cart = Cart()
            cart.tax_percentage = 0.075  # setting locally
            if self.request.user.is_authenticated():
                cart.user = self.request.user
            cart.save()
            data = {
                'cart_id': str(cart.id)
            }
            self.create_token(data)
            cart_obj = cart

        return cart_obj


    def get(self, request, format=None):
        cart = self.get_cart()
        self.cart = cart
        self.update_cart()
        # token = self.create_token(cart.id)  # in update_cart()
        items = CartItemSerializer(cart.cartitem_set.all(), many=True)
        print(cart.items.all())
        data = {
            "cart": cart.id,
            "total": cart.total,
            "subtotal": cart.subtotal,
            "tax_total": cart.tax_total,
            # "items": cart.items.count(),
            'token': self.token,
            'count': cart.items.count(),
            'items': items.data
        }
        return Response(data)


class CheckoutAPIView(CartTokenMixin, APIView):
    def get(self, request, format=None):
        # moved to CartTokenMixin
        # cart_token = request.GET.get("cart_token")
        # message = "This requires a valid cart & cart token"
        #
        # cart_token_data = self.parse_token(cart_token)
        # cart_id = cart_token_data.get("cart_id")
        # try:
        #     cart = Cart.objects.get(id=int(cart_id))
        # except:
        #     cart = None
        #
        # if not cart:
        #     data = {
        #         'success':False,
        #         'message':message,
        #     }
        #     return Response(data, status=status.HTTP_400_BAD_REQUEST)
        # else:
        #     data = {
        #         'cart': cart.id,
        #         'success':True,
        #     }
        #     return Response(data)
        data, cart_obj, response_status = self.get_cart_from_token()

        # user_checkout_id = request.GET.get('checkout_id')
        user_checkout_token = self.request.GET.get('checkout_token')
        user_checkout_data = self.parse_token(user_checkout_token)
        user_checkout_id = user_checkout_data.get('user_checkout_id')
        billing_address = self.request.GET.get('billing')
        shipping_address = self.request.GET.get('shipping')
        billing_obj, shipping_obj = None, None
        try:
            user_checkout = UserCheckout.objects.get(id = int(user_checkout_id))
        except:
            user_checkout = None

        if not user_checkout:
            data = {
                'message':'A user or guest user is required to continue.'
            }
            response_status = status.HTTP_400_BAD_REQUEST
            return Response(data, status=response_status)

        if billing_address:
            try:
                billing_obj = UserAddress.objects.get(user=user_checkout,id=int(billing_address))
            except:
                pass

        if shipping_address:
            try:
                shipping_obj = UserAddress.objects.get(user=user_checkout, id=int(shipping_address))  # id = shippingaddy?
            except:
                pass

        if not billing_obj or not shipping_obj:
            data = {
                'message':'A valid billing or shipping address is needed.'
            }
            response_status = status.HTTP_400_BAD_REQUEST
            return Response(data, status=response_status)

        # data["item"] =123
        if cart_obj:
            if cart_obj.items.count() == 0:
                data = {
                    "message":"Your cart is EMPTY"
                }
                response_status = status.HTTP_400_BAD_REQUEST
            else:
                order, created = Order.objects.get_or_create(cart=cart_obj)
                if order.is_complete:
                    order.cart.is_complete()
                    data = {
                        "message":"This order has been completed."
                    }
                    return Response(data)
                order.billing_address = billing_obj
                order.shipping_address = shipping_obj
                order.save()
                data = OrderSerializer(order).data
        return Response(data, status=response_status)

    def post(self, request, format=None):
        data = request.data
        serializer = CheckoutSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            # print("valid data!")
            # print(serializer.data)
            data = serializer.data
            user_checkout_id = data.get('user_checkout_id')
            cart_id = data.get('cart_id')
            billing_address = data.get('billing_address')
            shipping_address = data.get('shipping_address')

            user_checkout = UserCheckout.objects.get(id=user_checkout_id)
            cart_obj = Cart.objects.get(id=cart_id)
            s_a = UserAddress.objects.get(id=shipping_address)
            b_a = UserAddress.objects.get(id=billing_address)
            order, created = Order.objects.get_or_create(cart=cart_obj, user=user_checkout)
            if not order.is_complete:
                order.shipping_address = s_a
                order.billing_address = b_a
                order.save()
                order_data = {
                    'order_id':order.id,
                    'user_checkout_id':user_checkout_id
                }
                order_token = self.create_token(order_data)

        response = {
            "order_token":"order_token"
        }
        return Response(response)

"""
{
	"order_token": "eydvcmRlcl9pZCc6IDUyLCAndXNlcl9jaGVja291dF9pZCc6IDExfQ==",
	"payment_method_nonce": "abc123"

}

"""


class CheckoutFinalizeAPIView(TokenMixin,APIView):
    def get(self, request,format=None):
        response = {}
        order_token = request.GET.get('order_token')
        if order_token:
            checkout_id = self.parse_token(order_token).get('user_checkout_id')
            if checkout_id:
                checkout = UserCheckout.objects.get(id=checkout_id)
                client_token = checkout.get_client_token()
                response['client_token'] = client_token
                return Response(response)
        else:
            response['message'] = 'This method is not allowed'
            return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)



    def post(self, request, format=None):
        data = request.data
        response = {}
        serializer = FinalizedOrderSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            request_data = serializer.data
            order_id = request_data.get('order_id')
            order = Order.objects.get(id=order_id)
            if not order.is_complete:
                order_total = order.order_total
                nonce = request_data.get("payment_method_nonce")
                if nonce:
                    result = braintree.Transaction.sale({
                        'amount':order_total,
                        'payment_method_nonce':nonce,
                        'billing':{
                            'postal_code':'{}'.format(order.billing_address.zipcode)
                        },
                        'options':{
                            'submit_for_settlement':True
                        }
                    })
                    success = result.is_success
                    if success:
                        # result.transaction.id to order
                        # order.mark_completed(order_id=result.transaction.id)
                        order.mark_completed(order_id='abc12344423')
                        order.cart.is_complete()
                        response['message'] = 'your order has been completed'
                        response['final_order_id'] = order.order_id
                        response['success'] = True
                    else:
                        #messages.success(request, "there was a problem with your order")
                        error_message = result.message
                        # error_message = "error"
                        response['message'] = error_message
                        response['success'] = False
            else:
                response['message'] = "Order has already been completed"
                response['success'] = False

        return Response(response)