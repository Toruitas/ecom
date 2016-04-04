from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from carts.models import Cart
from .models import Order

class LoginRequiredMixin(object):
    """
    Makes the views that use this mixin have a login required added to their normal dispatch.

    In the long run, we would have a separate 'app' to handle account related stuff and put it there,
    like with view orders.

    This is just a quick and dirty one
    """
    @method_decorator(login_required())
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)

class CartOrderMixin(object):
    def get_order(self, *args, **kwargs):
        cart = self.get_cart()
        if not cart:
            return None
        new_order_id = self.request.session.get("order_id")
        if not new_order_id:
            new_order = Order.objects.create(cart=cart)
            self.request.session["order_id"] = new_order.id
        else:
            new_order = Order.objects.get(id=new_order_id)
        return new_order

    def get_cart(self, *args, **kwargs):
        """
        returns cart obj or none
        :param args:
        :param kwargs:
        :return:
        """
        cart_id = self.request.session.get("cart_id")
        if not cart_id:
            return None
        cart = Cart.objects.get(id = cart_id)
        if cart.items.count() <= 0:
            return None
        return cart

