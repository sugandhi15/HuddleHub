from django.shortcuts import render,HttpResponse
from rest_framework.views import APIView
from .serializers import WebUserSerializer
from .models import WebUser
from django.conf import settings
import jwt
import datetime
from django.contrib.auth.hashers import check_password


# Create your views here.
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
        

