from django import forms
from django.forms.models import modelformset_factory

from .models import Variation, Category



class VariationInventoryForm(forms.ModelForm):
    """
    using model form factory. Fields are fields we will edit in the form.
    extra=2 gives two extra fieldsets based on the model, can add another variation.
    However, extra=0 is better practice, should always create dedicated view for adding data.
    """
    class Meta:
        model = Variation
        fields = [
            # 'title',
            "price",
            "sale_price",
            "inventory",
            'active'
        ]
VariationInventoryFormSet = modelformset_factory(Variation,form=VariationInventoryForm,extra=0)

# CAT_CHOICES = (
#     ('electronics','Electronics'),
#     ('accessories','Accessories')
#     #...
# )

class ProductFilterForm(forms.Form):
    q = forms.CharField(label='Search',required=False)
    category_id = forms.ModelMultipleChoiceField(label="Category",
                                                 queryset=Category.objects.all(),  # searches through categories to list
                                                 widget = forms.CheckboxSelectMultiple,
                                                 required=False) # ,choices =CAT_CHOICES
    max_price = forms.DecimalField(decimal_places=2, max_digits=12, required=False)
    min_price = forms.DecimalField(decimal_places=2, max_digits=12, required=False)
