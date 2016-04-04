from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models.signals import pre_save, post_save
from decimal import Decimal

import braintree

# Create your models here.
from carts.models import Cart

if settings.DEBUG:
    braintree.Configuration.configure(braintree.Environment.Sandbox,
                                      merchant_id=settings.BRAINTREE_MERCHANT_ID,
                                      public_key=settings.BRAINTREE_PUBLIC,
                                      private_key=settings.BRAINTREE_PRIVATE)

class UserCheckout(models.Model):
    """
    Could just do a guest checkout where it's a user checkout and user is optional. It gets email no matter what
    user field could be blank and null so accomodate guests. One user should only have one checkout.

    email
    merchant id
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True)  # not required
    email = models.EmailField(unique=True)  # required
    braintree_id = models.CharField(max_length=120, null=True, blank=True)

    def __str__(self):
        return self.email

    @property
    def get_braintree_id(self):
        instance = self
        if not instance.braintree_id:
            #update it
            result = braintree.Customer.create({
                "email":instance.email,
            })
            if result.is_success:
                print(result)  # it's a dicitonary/JSON return
                instance.braintree_id = result.customer.id
        return instance.braintree_id

    def get_client_token(self):
        customer_id = self.get_braintree_id
        if customer_id:
            client_token = braintree.ClientToken.generate({
                "customer_id":customer_id
            })
            return client_token
        else:
            return None

def update_braintree_id(sender, instance, *args, **kwargs):
    if not instance.braintree_id:
        instance.get_braintree_id  # could work without since it's a property, too
post_save.connect(update_braintree_id, sender=UserCheckout)


ADDRESS_TYPE = (
    # (db entry, Displayed)
    ('billing','Billing'),
    ('shipping','Shipping'),
)

class UserAddress(models.Model):
    """
    usually would put this user stuff in its own app, since you would have lots of validation & management things for them
    Here we skip most of that.
    """
    user = models.ForeignKey(UserCheckout)  # not linked to a user but to a user's checkout process
    type = models.CharField(max_length=120, choices=ADDRESS_TYPE)
    street = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    zipcode = models.CharField(max_length=120)
    state = models.CharField(max_length=120)

    def __str__(self):
        return self.street

    def get_address(self):
        return "{}, {}, {} {}".format(self.street,self.city, self.state, self.zipcode)


ORDER_STATUS_CHOICES = (
    ('created','Created'),
    ('paid','Paid'),
    ('shipped','Shipped'),
    ('refunded','Refunded'),
    # ('abandoned','Abandoned')
)

class Order(models.Model):
    """
    cart
    user (not req'd) --> required. Shadow profile??
    guest (not r) // not doing
    shipping address
    billing add
    shipping total price
    order total price (cart total + shipping )
    order id (custom)
    """
    status = models.CharField(max_length=120, choices=ORDER_STATUS_CHOICES, default='created')
    cart = models.ForeignKey(Cart)
    user = models.ForeignKey(UserCheckout, null=True)
    shipping_address = models.ForeignKey(UserAddress, related_name='shipping_address', null=True)
    billing_address = models.ForeignKey(UserAddress, related_name='billing_address', null=True)
    shipping_total_price = models.DecimalField(max_digits=50, decimal_places=2, default=5.99)
    order_total = models.DecimalField(max_digits=50, decimal_places=2)
    order_id = models.CharField(max_length=20,null=True, blank=True)

    def __str__(self):
        # return str(self.cart.id)
        return "Order_id: {}, Cart_id: {}".format(self.id, self.cart.id)
    class Meta:
        ordering = ['-id']  # most recent order first

    def mark_completed(self, order_id=None):
        """
        Marks an order as completed
        :return:
        """
        self.status = "paid"
        if order_id and not self.order_id:
            self.order_id = order_id
        print("Order completed")
        self.save()

    def get_absolute_url(self):
        return reverse("order_detail", kwargs={"pk":self.pk})

    @property
    def is_complete(self):
        if self.status == "paid":
            return True
        return False


def order_pre_save(sender, instance, *args, **kwargs):
    shipping_total_price = instance.shipping_total_price
    cart_total = instance.cart.total
    order_total = Decimal(shipping_total_price) + Decimal(cart_total)  # one of these already is, but for posterity
    instance.order_total = order_total
pre_save.connect(order_pre_save, sender=Order)

# if status == "refunded":
# braintree refund
# post_save.connect()