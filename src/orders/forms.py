from django import forms
from django.contrib.auth import get_user_model  # allows us to use User obj

from .models import UserAddress


User = get_user_model()


class GuestCheckoutForm(forms.Form):
    email = forms.EmailField()
    email2 = forms.EmailField(label='Confirm email')

    def clean(self):
        cleaned_data = super(GuestCheckoutForm, self).clean()
        # print(cleaned_data)
        email = cleaned_data.get('email')
        email2 = cleaned_data.get('email2')
        if email == email2:
            user_exists = User.objects.filter(email=email).count()
            if user_exists != 0:
                raise forms.ValidationError("This user already exists. Please login instead.")
            return cleaned_data
        else:
            raise forms.ValidationError("Please confirm emails are the same")


class AddressForm(forms.Form):
    """
    Model Choice Field allows us to have choices based off of a queryset from a model
    By default there would be an empty line, we don't want that, so empty_label="--None--" so it would display what is
    inside the quotes. or =None (no quotes) to remove

    forms.RadioSelect widget turns it into a radio field
    """
    billing_address = forms.ModelChoiceField(queryset=UserAddress.objects.filter(type="billing").all(),
                                             empty_label=None,
                                             widget=forms.RadioSelect)
    shipping_address = forms.ModelChoiceField(queryset=UserAddress.objects.filter(type="shipping").all(),
                                              empty_label=None,
                                              widget=forms.RadioSelect)

class UserAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = [
            'street',
            'city',
            'state',
            'zipcode',
            'type'
        ]