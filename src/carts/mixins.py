import base64
import ast

from django.shortcuts import get_object_or_404

from rest_framework import status
from .models import Cart, CartItem, Variation

class CartUpdateAPIMixin(object):

    def update_cart(self, *args, **kwargs):
        request = self.request
        cart = self.cart
        if cart:
            item_id = request.GET.get("item")
            delete_item = request.GET.get("delete", False)
            flash_message = ""
            item_added = False
            if item_id:
                item_instance = get_object_or_404(Variation, id=item_id)
                qty = request.GET.get("qty", 1)
                try:
                    if int(qty) < 1:
                        delete_item = True
                except:
                    raise Http404
                # this logic flow doesn't feel right
                cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item_instance)
                if created:
                    flash_message = "Succesfully added to cart"
                    item_added = True
                elif delete_item:
                    flash_message = "Item removed successfully"
                    cart_item.delete()
                else:
                   flash_message = "Quantity has been updated succesfully"
                   cart_item.quantity = qty
                   cart_item.save()

class TokenMixin(object):
    token = None

    def create_token(self, data_dict):
        if isinstance(data_dict, dict):
            token = base64.b64encode(bytes(str(data_dict), 'utf-8'))  # first turn str data to bstring then can encode
            token = token.decode('utf-8')  # to return to string from bstring
            self.token = token
            return token
        else:
            raise ValueError("Creating a token requires a Python dictionary")

    def parse_token(self, token=None):
        if not token:
            return {}
        try:
            token_decoded = base64.b64decode(token).decode('utf-8')
            # token_decoded = token_decoded.decode("utf-8")  # http://stackoverflow.com/questions/8908287/base64-encoding-in-python-3
            token_dict = ast.literal_eval(token_decoded)  # https://docs.python.org/3/library/ast.html
            return token_dict
        except:
            return {}

class CartTokenMixin(TokenMixin, object):
    token_param = "cart_token"  # key for url string
    token = None

    def get_cart_from_token(self):
        request = self.request
        response_status = status.HTTP_200_OK
        cart_token = request.GET.get(self.token_param)
        message = "this requires a valid cart & cart token"

        cart_token_data = self.parse_token(cart_token)  # will this work?
        cart_id = cart_token_data.get('cart_id')
        try:
            cart = Cart.objects.get(id=int(cart_id))
        except:
            cart = None

        if not cart:
            data = {
                "success": False,
                "message": message
            }
            response_status = status.HTTP_400_BAD_REQUEST
            # return Response(data, status = status.HTTP_400_BAD_REQUEST)
        else:
            self.token = cart_token
            data = {
                "cart":cart.id,
                "success": True
            }
            # return Response(data)
        return data, cart, response_status