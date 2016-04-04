from django.db import models
from django.db.models.signals import pre_save, post_save, post_delete
from django.conf import settings  # get user from here
from django.core.urlresolvers import reverse

from decimal import Decimal

from products.models import Variation  # since variations go in cart

# Create your models here.

class CartItem(models.Model):
    """
    https://docs.djangoproject.com/en/1.9/topics/db/models/#extra-fields-on-many-to-many-relationships
    Using intermediary like this so we can have quantities

    """
    cart = models.ForeignKey("Cart")
    item = models.ForeignKey(Variation)  # one and only one FK to source model
    quantity = models.PositiveIntegerField(default=1)
    line_item_total = models.DecimalField(max_digits=10, decimal_places=2)  # always wanna have this
    # timestamp
    # updated

    def __str__(self):
        return self.item.title

    def remove(self):
        """
        removes self.
        :return:
        """
        # return "{}/?item={}&delete=True".format(reverse("cart"), self.item.id)
        # return "{}?delete=True".format(self.item.add_to_cart())
        return self.item.remove_from_cart()

def cart_item_pre_save_receiver(sender, instance, *args, **kwargs ):
    """
    https://docs.djangoproject.com/en/1.9/ref/signals/#pre-save
    This works since as we create the cart item, it assumes qty is 1.
    :param sender:
    :param instance:
    :param args:
    :param kwargs:
    :return:
    """
    qty = instance.quantity
    if int(qty) >= 1:
        price = instance.item.get_price()  # check if instance method or property
        line_item_total = Decimal(qty) * Decimal(price)
        instance.line_item_total = line_item_total
pre_save.connect(cart_item_pre_save_receiver, sender=CartItem)

def cart_item_post_save_receiver(sender, instance,*args, **kwargs):
    """
    After each save of a cart item, updates the cart's subtotal
    """
    instance.cart.update_subtotal()
post_save.connect(cart_item_post_save_receiver, sender=CartItem)
# to do the same thing after delete, too. Removes leftover subtotal
post_delete.connect(cart_item_post_save_receiver, sender=CartItem)


class Cart(models.Model):
    """
    to access cart item, should use object.cartitem_set.all in a view, just like any related model (backref style)
    Since items just gives default data
    timestamp
    updated field
    subtotal price
    tax
    discounts
    total
    shipping total

    items are a queryset of Variations, but will use CartItem as an intermediate model.
    https://docs.djangoproject.com/en/1.9/topics/db/models/#extra-fields-on-many-to-many-relationships
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)  #
    items = models.ManyToManyField(Variation, through=CartItem)  # object.cartitem_set to get it in a view, dont just .item
    timestamp = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=5, default=0.085)
    subtotal = models.DecimalField(max_digits=50, decimal_places=2, default=0.00)  # adjusted based off of items' lineitems total
    tax_total = models.DecimalField(max_digits=50, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=50, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.id)

    def update_subtotal(self):
        """
        updates subtotal based off lineitem totals
        """
        print('updating')
        subtotal = 0
        items = self.cartitem_set.all()  # not self.items.all()
        for item in items:
            subtotal += item.line_item_total
        self.subtotal = "{0:.2f}".format(subtotal)
        self.save()

    def is_complete(self):
        self.active = False
        self.save()

def do_tax_and_total_receiver(sender, instance, *args, **kwargs):
    """
    Rounding: http://stackoverflow.com/questions/455612/limiting-floats-to-two-decimal-points
    """
    subtotal = Decimal(instance.subtotal)
    tax_total = round(subtotal * Decimal(instance.tax_percentage), 2)  # 8.5%, 2 decimal places
    total = round(subtotal + Decimal(tax_total), 2)
    instance.tax_total = "{0:.2f}".format(tax_total)
    instance.total = "{0:.2f}".format(total)
# presave it otherwise will loop around and around
pre_save.connect(do_tax_and_total_receiver,sender=Cart)