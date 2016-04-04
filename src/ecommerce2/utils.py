from django.utils import timezone
# from orders.models import UserCheckout

def jwt_response_payload_handler(token, user, request, *args, **kwargs):
    """
    http://getblimp.github.io/django-rest-framework-jwt/
    https://github.com/GetBlimp/django-rest-framework-jwt
    https://github.com/GetBlimp/django-rest-framework-jwt/blob/master/rest_framework_jwt/views.py
    https://github.com/GetBlimp/django-rest-framework-jwt/blob/master/rest_framework_jwt/serializers.py
    :param token:
    :param user:
    :param request:
    :param args:
    :param kwargs:
    :return:
    """
    data = {
        "token": token,
        "user":user.id,
        "originated_at":timezone.now(),
        # "user_braintree_id":UserCheckout.objects.get(user=user).get_braintree_id
    }
    return data