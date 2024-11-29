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
from rest_framework import status
from django.http import JsonResponse
import random
import time
from agora_token_builder import RtcTokenBuilder
from .models import RoomMember
import json
import random
import string



class signup(APIView):

    
     
    def post(self , request):
        try:
            # signup=signupserializer(request.data)
            # if signup.is_valid
            first_name = request.data['first_name']
            last_name = request.data['last_name']
            email = request.data['email']
            if WebUser.objects.filter(email = email).exists():
                return JsonResponse({
                    "msg":"User with this email already exist"
                })
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
                },status=status.HTTP_201_CREATED)
            else:
                return JsonResponse({"msg" : "Please enter valid credentials"})
            
        except Exception as e:
            return JsonResponse({
                "msg" : "Please enter valid credentials"
            })
        


class login(APIView):

    def post(self,request):
        try:
            email = request.data['email']
            password = request.data['password']
            user = WebUser.objects.get(email = email)
            if not user:
                return JsonResponse({"error" : "No user exist with this email"})
            if check_password(password,user.password):
                payload = {
                    "email": email,
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1), 
                    "iat": datetime.datetime.utcnow(), 
                }
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
                response=Response({"jwt_token":token})
                response.set_cookie(key='jwt_token',value=token)
                # resp = f"token = {token}"
                return JsonResponse({
                    "msg":token
                }, status=status.HTTP_200_OK)
            else:
                return JsonResponse({
                "error" : "Please enter valid credentials"
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                "error" : "Please enter valid credentials"
            }, status=status.HTTP_400_BAD_REQUEST)
        


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
            "error":"Please enter valid credentials"
        }, status=status.HTTP_400_BAD_REQUEST)



class ForgetPassword(APIView):

    def post(self,request):
        try:
            email = request.data.get('email')
            if not email:
                return JsonResponse({
                    "error": "Email is required."
                }, status=status.HTTP_400_BAD_REQUEST)
            if WebUser.objects.filter(email = email).exists():
                user = WebUser.objects.get(email= email)
                encoded_info = email.encode('utf-8').hex()
                token = default_token_generator.make_token(user)
                password_reset_link_token = f'http://localhost:8000/setnewpass/{token}/{encoded_info}'
                subject = "Password Reset Requested"
                message = render_to_string('reset.html', {
                    'password_reset_link_token':password_reset_link_token,
                    'username': user.first_name,
                })
                send_mail(subject, message, 'sugandhibansal26@gmail.com', [email])
                return JsonResponse({"message": "Password reset link sent."}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({"error":"Please enter valid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                "error": "Please enter valid credentials"
            }, status=status.HTTP_400_BAD_REQUEST)



class newPassword(APIView):

    def post(self,request,token,encoded_info):
        try:
            new_password = request.data.get('password')
            if not new_password:
                return JsonResponse({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                email = bytes.fromhex(encoded_info).decode('utf-8')
            except ValueError:
                return JsonResponse({'error': 'Sorry u cannot access this page'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                user = WebUser.objects.get(email=email)
            except WebUser.DoesNotExist:
                return JsonResponse({'error': 'User does not exist'}, status=404)
            if default_token_generator.check_token(user, token):
                user.set_password(new_password) 
                user.save()  
                return JsonResponse({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
            return JsonResponse({
                "error":"Please enter a valid credentials"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                "error":str(e)
            }, status=status.HTTP_400_BAD_REQUEST)



class ResetPassword(APIView):

    def post(self,request,jwtToken):
        try:
            email = request.data.get('email')
            if not email:
                return JsonResponse({
                    "error": "Email is required."
            }, status=status.HTTP_400_BAD_REQUEST)
            if not jwtToken:
                return JsonResponse({"error":"You have to login"}, status=status.HTTP_400_BAD_REQUEST)
            print("success")
            user = WebUser.objects.get(email= email)
            if not user:
                return JsonResponse({"error":"No such user exist in database"}, status=status.HTTP_400_BAD_REQUEST)
            token = default_token_generator.make_token(user)
            password_reset_link_token = f'http://localhost:8000/password/reset/{token}/{jwtToken}'
            subject = "Password Reset Requested"
            message = render_to_string('reset.html', {
                'password_reset_link_token':password_reset_link_token,
                'username': user.first_name,
            })
            send_mail(subject, message, 'sugandhibansal26@gmail.com', [email])
            return JsonResponse({"message": "Password reset link sent."}, status=status.HTTP_200_OK)
        except Exception as e:
            return JsonResponse({
                "error": "Please enter valid credentials"
            }, status=status.HTTP_400_BAD_REQUEST)
        


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
                return JsonResponse({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
            return JsonResponse({
                "error":"Please enter a valid credentials"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                "error":"Please enter a valid credentials"
            }, status=status.HTTP_400_BAD_REQUEST)






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
    try:
        data = json.loads(request.body)
        member, created = RoomMember.objects.get_or_create(
            name=data['name'],
            uid=data['UID'],
            room_name=data['room_name']
        )
        return JsonResponse({'name':data['name']}, safe=False)
    except Exception as e:
        return JsonResponse("Sorry , you cannot access this page")



def getMember(request):
    uid = request.GET.get('UID')
    room_name = request.GET.get('room_name')

    member = RoomMember.objects.get(
        uid=uid,
        room_name=room_name,
    )
    name = member.name
    return JsonResponse({'name':name}, safe=False)



class getRoomMember(APIView):

    def get(request,room_name):
        try:
            data = RoomMember.objects.filter(room_name = room_name)
            if not data:
                return JsonResponse({"msg":"Sorry cannot get data"})
            serializer = RoomMemberSerializer(data, many=True)
            return JsonResponse({"users" : serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return JsonResponse({"msg":"Sorry cannot get data"})



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
        return JsonResponse({"msg":"Please enter valid credentials"})

