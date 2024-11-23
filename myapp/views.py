from django.shortcuts import render,HttpResponse
from rest_framework.views import APIView
from .serializers import WebUserSerializer
from .models import WebUser
from django.conf import settings
import jwt
import datetime
from django.contrib.auth.hashers import check_password




# 
# import os
# import time
# import json

# from django.http.response import JsonResponse
# from django.contrib.auth import get_user_model
# from django.contrib.auth.decorators import login_required

# from django.shortcuts import render
# from agora_token_builder import RtcTokenBuilder
# # from .agora_key.RtcTokenBuilder import RtcTokenBuilder, Role_Attendee
# import pusher



# # Instantiate a Pusher Client
# pusher_client = pusher.Pusher(
#   app_id='1899801',
#   key='7f2dc4c77087dd47a9bc',
#   secret='3657123368e6065475cb',
#   cluster='ap2',
#   ssl=True
# )
# pusher_client.trigger('my-channel', 'my-event', {'message': 'hello world'})


# # @login_required(login_url='/admin/')
# def index(request):
#     User = get_user_model()
#     all_users = User.objects.exclude(id=request.user.id).only('id', 'username')
#     return render(request, 'agora/index.html', {'allUsers': all_users})


# def pusher_auth(request):
#     payload = pusher_client.authenticate(
#         channel=request.POST['channel_name'],
#         socket_id=request.POST['socket_id'],
#         custom_data={
#             'user_id': request.user.id,
#             'user_info': {
#                 'id': request.user.id,
#                 'name': request.user.username
#             }
#         })
#     return JsonResponse(payload)


# def generate_agora_token(request):
#     appID = os.environ.get('AGORA_APP_ID')
#     appCertificate = os.environ.get('AGORA_APP_CERTIFICATE')
#     channelName = json.loads(request.body.decode(
#         'utf-8'))['channelName']
#     userAccount = request.user.username
#     expireTimeInSeconds = 3600
#     currentTimestamp = int(time.time())
#     privilegeExpiredTs = currentTimestamp + expireTimeInSeconds

#     token = RtcTokenBuilder.buildTokenWithAccount(
#         appID, appCertificate, channelName, userAccount, Role_Attendee, privilegeExpiredTs)

#     return JsonResponse({'token': token, 'appID': appID})


# def call_user(request):
#     body = json.loads(request.body.decode('utf-8'))

#     user_to_call = body['user_to_call']
#     channel_name = body['channel_name']
#     caller = request.user.id

#     pusher_client.trigger(
#         'presence-online-channel',
#         'make-agora-call',
#         {
#             'userToCall': user_to_call,
#             'channelName': channel_name,
#             'from': caller
#         }
#     )
#     return JsonResponse({'message': 'call has been placed'})
















# # Create your views here.
class signup(APIView):
     
    def post(self , request):
        try:
            first_name = request.data['first_name']
            last_name = request.data['last_name']
            email = request.data['email']
            phone_number = request.data['phone_number']
            password = request.data['password']

            data = {
                "first_name" : first_name,
                "last_name" : last_name,
                "email" : email,
                "phone_number" : phone_number,
                "password" : password
            }
            serilizer = WebUserSerializer(data = data)
            if serilizer.is_valid():
                serilizer.save()
                return HttpResponse("user created succesfully")
            
        except Exception as e:
            return HttpResponse(str(e))
        




class login(APIView):

    def post(self,request):
        try:
            email = request.data['email']
            password = request.data['password']
            user = WebUser.objects.get(email = email)
            if not user:
                return HttpResponse("No user exist with this email")
            if check_password(password,user.password):
                payload = {
                    "email": email,
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1), 
                    "iat": datetime.datetime.utcnow(), 
                }
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
                resp = f"token = {token}"
                return HttpResponse(resp)
            else:
                return HttpResponse("Please enter valid password")
        except Exception as e:
            return HttpResponse('Error occured')
        


# function toextract user data from token
def userInfo(request):
    token  = request.GET.get('token')
    decoded_token = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=["HS256"]
    )
    email = decoded_token['email']
    return HttpResponse(email)