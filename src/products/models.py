from django.db import models
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save
from django.utils.text import slugify
from django.utils.safestring import mark_safe


#  MODEL MANAGERS
class ProductQuerySet(models.query.QuerySet):
    def active(self):
        # filters all active ones
        # can do Product.object.all().active() now in view queries
        return self.filter(active=True)

class ProductManager(models.Manager):
    """
    https://godjango.com/51-better-models-through-custom-managers-and-querysets/
    http://www.djangobook.com/en/2.0/chapter10.html
    https://docs.djangoproject.com/en/1.9/topics/db/managers/
    """
    def get_queryset(self):
        # model and db related to the query
        return ProductQuerySet(self.model, using=self._db)

    def all(self, *args, **kwargs):
        # overrides standard all queryset, and making sure active is True
        return self.get_queryset().active()

    def get_related(self,instance):
        """
        gets all in the same category, including defaults
        categories__in__exact=  would match only exact
        Goes off the default model ordering, so if we want to change that, can add a Meta to a Product
        :param instance:
        :return:
        """
        products_one = self.get_queryset().filter(categories__in=instance.categories.all())
        products_two = self.get_queryset().filter(default=instance.default)
        qs = (products_one | products_two).exclude(id=instance.id).distinct()
        return qs


# Create your models here.
class Product(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)  # blank means django form doesn't need it filled,
    #  and null means DB can be empty
    price = models.DecimalField(decimal_places=2,max_digits=20)  # decimal places is places after.00; max digits.
    active = models.BooleanField(default=True)
    categories = models.ManyToManyField('Category', blank=True)  # put it within quotes and it will look within the same file
    # without related_name, have a reverse accessor issue. null/blank allowed since even w/o product, want to show
    # it could just be uncategorized. null doesn't matter in many2many fields
    # default is basically the top category in a hierarchy.
    # in our usage, it's for related products that share a category. Simple association.
    default = models.ForeignKey('Category', related_name='default_category', null=True,blank=True)

    #init project manager
    objects = ProductManager()

    class Meta:
        ordering = ["-title"]  # in queries, results shown by title in reverse alpha

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        #return "/products/{}".format(self.pk)
        return reverse("products:product_detail", kwargs={"pk":self.pk})

    def get_image_url(self):
        img = self.productimage_set.first()  # gets first item in queryset or none
        if img:
            return img.image.url
        return img  # which would be NOne

class Variation(models.Model):
    """
    each variation will be better than original product
    Make sure to go to admin.py to add it to the admin panel
    """
    product = models.ForeignKey(Product)
    title = models.CharField(max_length=120)
    price = models.DecimalField(decimal_places=2, max_digits=20)
    sale_price = models.DecimalField(decimal_places=2, max_digits=20, null=True, blank=True)
    active = models.BooleanField(default=True)
    inventory = models.IntegerField(null=True, blank=True)  # we are allowing for negative here, with (default=-1) or null&blank=True referring to unlimited.

    def __str__(self):
        return self.title

    def get_price(self):
        """
        Returns sale price if ther eis one
        :return:
        """
        if self.sale_price is not None:
            return self.sale_price
        else:
            return self.price

    def get_html_price(self):
        """
        mark_safe comes from django utils. Better than {{ xxxx |safe}} everywhere it shows up. DRY principles guys
        :return:
        """
        if self.sale_price is not None:
            html_text = "<span class='sale-price'>{}</span> <span class='og-price'>{}</span>".format(
                self.sale_price,self.price)
        else:
            html_text = "<span class='sale-price'>{}</span>".format(self.price)
        return mark_safe(html_text)

    def get_absolute_url(self):
        return self.product.get_absolute_url()

    def add_to_cart(self):
        return "{}?item={}&qty=1".format(reverse("cart"), self.id)

    def remove_from_cart(self):
        return "{}?item={}&delete=True".format(reverse("cart"), self.id)

    def get_title(self):
        """
        Can't just do self.item since if it's default, we want the item itself
        :return:
        """
        # return self.item.title
        return "{} - {}".format(self.product.title, self.title)


def product_post_saved_receiver(sender,instance,created, *args,**kwargs):
    """
    This will create a Default variation for all products, since at first creation there may not be one.
    variation_set is a reverse relation of variations. https://docs.djangoproject.com/en/1.9/ref/models/relations/
    :param sender:
    :param instance:
    :param created:
    :param args:
    :param kwargs:
    :return:
    """
    product = instance
    variations = product.variation_set.all()  # reverse relation
    #variations = Variation.objects.filter(product=product)  # same as above
    if variations.count() == 0:
        new_var = Variation()
        new_var.product = product
        new_var.title = "{}-Default".format(product.title)
        new_var.price = product.price
        new_var.save()
post_save.connect(product_post_saved_receiver, sender=Product)  #since Product model is the one we will be working with

######## product images ##########

def image_upload_to(instance, filename):
    """
    automatically doesn't overwrite, even after all this it will add a new blurb to the end of the file name.
    :param instance:
    :param filename:
    :return:
    """
    title = instance.product.title
    slug = slugify(title)
    basename, file_ext = filename.split('.')#[1]  # if we want to change the filename
    new_filename = "{}-{}.{}".format(basename,instance.id,file_ext)  # changes full name, can replace basename w/ slug too
    return "products/{}/{}".format(slug,new_filename)  # filename)

class ProductImage(models.Model):
    """
    pillow library validates it is actually an image. If pillow doesn't work, use filefield
    https://github.com/codingforentrepreneurs/Guides/blob/master/imagefield_and_pillow.md
    {{ img.image.file }} <!-- where it's being stored -->
    {{ img.image.url }} <!-- where it's being served from -->
    default way is upload_to="products/"
    """
    product = models.ForeignKey(Product)  # foreign key reference
    image = models.ImageField(upload_to=image_upload_to)

    def __str__(self):
        return self.product.title


########## product category ##############

class Category(models.Model):
    title = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True, auto_now=False)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("categories:category_detail", kwargs={"slug":self.slug})


# class ProductCategories(models.Model):
#     """
#     one product has one product category
#     product that will be associated to a group of categories and set a default category
#     default category
#
#     We could do this with just the product itself, so let's do that instead
#     """
#     product = models.OneToOneField(Product)
#     categories = models.ManyToManyField(Category)
#     default = models.ForeignKey(Category)
#
#     def __str__(self):
#         return self.product.title

############## Featured Product stuff #############

def image_upload_to_featured(instance, filename):
    """
    automatically doesn't overwrite, even after all this it will add a new blurb to the end of the file name.
    :param instance:
    :param filename:
    :return:
    """
    title = instance.product.title
    slug = slugify(title)
    basename, file_ext = filename.split('.')#[1]  # if we want to change the filename
    new_filename = "{}-{}.{}".format(basename,instance.id,file_ext)  # changes full name, can replace basename w/ slug too
    return "products/{}/featured/{}".format(slug,new_filename)  # filename)

class ProductFeatured(models.Model):
    product = models.ForeignKey(Product)
    image = models.ImageField(upload_to=image_upload_to_featured)
    title = models.CharField(max_length=120, null=True, blank=True)
    text = models.CharField(max_length=220, null=True, blank=True)
    text_right = models.BooleanField(default=False)  # if we want text on right or left of their div
    text_css_color = models.CharField(max_length=6, null=True, blank=True)  # can do lots of different ways
    show_price = models.BooleanField(default=False)  # since price itself could also be written in text
    active = models.BooleanField(default=True)
    # can do expire_timestamp for when we want it to expire in the future. Create datetime field and a model manager for it
    # to have it disappear at certain times
    make_image_background = models.BooleanField(default=False)

    def __str__(self):
        return self.product.title

