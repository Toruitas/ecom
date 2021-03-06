# just run this. it's not a real test suite, just a test file

import requests
import json

# https://github.com/codingforentrepreneurs/ecommerce-2-api/commit/31d120bd2008b2d266a79010cbe8c566b31381a3

base_url = "http://127.0.0.1:8000/api/"
login_url = base_url + 'auth/token/'
products_url = base_url + "products/"
refresh_url = login_url + "refresh/"
cart_url = base_url + "cart/"
user_checkout_url = base_url + "user/checkout/"

# requests.get()
# requests.post(login_url, data=None, headeres=None, params=None)


# data = {
#     "username":'toruitas',
#     "password":"bananarama"
# }
# # log in with above data
# login_r = requests.post(login_url, data=data)
# login_r.text
# json_data = login_r.json()
#
# import json
#
# print(json.dumps(json_data, indent=2))
#
# token = json_data['token']
# print(token)
#
# headers = {
#     "Content-Type":"application/json",
#     "Authorization":"JWT {}".format(token),
# }
#
# # for getting JSON data from products
# # p_r = requests.get(products_url, headers=headers)
# # print(p_r.text)
# # print(json.dumps(p_r.json(), indent=2))
#
# # refresh URL token
# data = {
#     "token":token
# }
# refresh_r = requests.post(refresh_url, data=data)
# print(refresh_r.json())
# token = refresh_r.json()['token']
# print(token)
#
# cart_r = requests.get(cart_url)
# print("cart token")
#
# cart_token = cart_r.json()["token"]
# print(cart_token)
# new_cart_url = cart_url + "?token=" + cart_token + "&item=10&qty=3"
#
# new_cart_r = requests.get(new_cart_url)
# print(new_cart_r.json())

def create_cart():
    #create cart
    cart_r = requests.get(cart_url)
    # get cart token
    cart_token = cart_r.json()['token']
    return cart_token

def do_api_test(email=None, user_auth=None):
    cart_token = create_cart()
    # add itmes to cart
    new_cart_url = cart_url + "?token=" + cart_token +"&item=10&qty=3"
    new_cart_r = requests.get(new_cart_url)
    print(new_cart_r.text)
    # get user_checkout token
    # user_checkout_url = user_checkout_url
    if email:
        data = {
            'email':email
        }
        # user checkout request
        u_c_r = requests.post(user_checkout_url, data=data)
        print(u_c_r.json())  # problem here

        user_checkout_token = u_c_r.json().get('user_checkout_token')
        print(user_checkout_token)
        addresses = base_url + "user/address/?checkout_token=" + user_checkout_token
        #address = "http://127.0.0.1:8000/api/user/address/?checkout_token=eydicmFpbnRyZWVfaWQnOiB1JzY0ODMxMzkzJywgJ3VzZXJfY2hlY2tvdXRfaWQnOiAxMSwgJ3N1Y2Nlc3MnOiBUcnVlfQ=="
        addresses_r = requests.get(addresses)
        addresses_r_data = addresses_r.json()
        if addresses_r_data['count'] >= 2:
            b_id = addresses_r_data['results'][0]['id']
            s_id = addresses_r_data['results'][1]['id']
        else:
            addresses_create = base_url + 'user/address/create/'  # addy for creating addy
            user_id = 1
            data = {
                "user":user_id,
                'type': 'billing',
                'street':'12345 Test',
                'city':'Newport Beach',
                'zipcode':'92304',
                'state':'CA'
            }
            addresses_create_r = requests.post(addresses_create, data=data)
            b_id = addresses_create_r.json().get("id")
            data = {
                "user": user_id,
                'type': 'shipping',
                'street':'12345 Test',
                'city':'Newport Beach',
                'zipcode':'92304',
                'state':'CA'
            }
            addresses_create_s_r = requests.post(addresses_create, data=data)
            s_id = addresses_create_s_r.json().get('id')

    # do checkout
    data = {
        'billing_address': b_id,
        'shipping_address': s_id,
        'cart_token':cart_token,
        'checkout_token':user_checkout_token
    }
    print(data)
    order=requests.post(user_checkout_url, data=data)
    print(order.text)

do_api_test(email='abc1234@gmail.com')