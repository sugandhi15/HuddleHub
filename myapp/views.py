from django.shortcuts import render,HttpResponse
from rest_framework.views import APIView
from .serializers import WebUserSerializer,RoomMemberSerializer
from .models import WebUser
from django.conf import settings
import jwt
import datetime
from django.contrib.auth.hashers import check_password
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from rest_framework.response import Response
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt


from django.http import JsonResponse
import random
import time
from agora_token_builder import RtcTokenBuilder
from .models import RoomMember
import json



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
                payload = {
                    "email": email,
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1), 
                    "iat": datetime.datetime.utcnow(), 
                }
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
                return JsonResponse({
                    "msg":token
                })
            
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
                response=Response({"jwt_token":token})
                response.set_cookie(key='jwt_token',value=token)
                resp = f"token = {token}"
                return HttpResponse(resp)
            else:
                return HttpResponse("Please enter valid password")
        except Exception as e:
            return HttpResponse('Error occured')
        


# function to extract user data from token
def userInfo(request):
    try:
        token  = request.GET.get('token')
        decoded_token = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        email = decoded_token['email']
        return email
    except Exception as e:
        return JsonResponse({
            "msg":str(e)
        })



class ResetPassword(APIView):

    def post(self,request,jwtToken):
        try:
            email = request.data.get('email')
            if not email:
                return Response({
                    "error": "Email is required."
            })
            if not jwtToken:
                return Response({"message":"You have to login"})
            print("success")
            user = WebUser.objects.get(email= email)
            print(user)
            if not user:
                return Response({"message":"No such user exist in database"})
            token = default_token_generator.make_token(user)
            print(token)
            password_reset_link_token = f'http://localhost:8000/password/reset/{token}/{jwtToken}'
            subject = "Password Reset Requested"
            message = render_to_string('reset.html', {
                'password_reset_link_token':password_reset_link_token,
                'username': user.first_name,
            })
            print("working")
            send_mail(subject, message, 'sugandhibansal26@gmail.com', [email])
            return Response({"message": "Password reset link sent."}, status=200)
        except Exception as e:
            return Response({
                "error": str(e)
            })
        

class setPassword(APIView):

    def post(self,request,token,jwtToken):
        try:
            new_password = request.data.get('password')
            print(new_password)
            print(token)   
            decoded_token = jwt.decode(
                jwtToken,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            email = decoded_token['email']
            user = WebUser.objects.get(email = email)
            if default_token_generator.check_token(user, token):
                user.set_password(new_password) 
                user.save()  
                return Response({'message': 'Password updated successfully'})
            return Response({
                "msg":"Please enter a valid credentials"
            })
        except Exception as e:
            return Response({
                "msg":str(e)
            })







def lobby(request):
    return render(request, 'lobby.html')

def room(request):
    return render(request, 'room.html')


def getToken(request):
    appId = "1aa47ae8827d40cab066b64abea5748e"
    appCertificate = "fe1391c6a6da4174b9f157052d61cbd0"
    channelName = request.GET.get('channel')
    uid = random.randint(1, 230)
    expirationTimeInSeconds = 3600
    currentTimeStamp = int(time.time())
    privilegeExpiredTs = currentTimeStamp + expirationTimeInSeconds
    role = 1

    token = RtcTokenBuilder.buildTokenWithUid(appId, appCertificate, channelName, uid, role, privilegeExpiredTs)

    return JsonResponse({'token': token, 'uid': uid}, safe=False)


@csrf_exempt
def createMember(request):
    data = json.loads(request.body)
    member, created = RoomMember.objects.get_or_create(
        name=data['name'],
        uid=data['UID'],
        room_name=data['room_name']
    )
    return JsonResponse({'name':data['name']}, safe=False)



def getMember(request):
    uid = request.GET.get('UID')
    room_name = request.GET.get('room_name')

    member = RoomMember.objects.get(
        uid=uid,
        room_name=room_name,
    )
    name = member.name
    return JsonResponse({'name':name}, safe=False)



@csrf_exempt
def deleteMember(request):
    try:
        data = json.loads(request.body)
        member = RoomMember.objects.get(
            name=data['name'],
            uid=data['UID'],
            room_name=data['room_name']
        )
        member.delete()
        return JsonResponse('Member deleted', safe=False)
    except Exception as e:
        return HttpResponse("Error occured")

