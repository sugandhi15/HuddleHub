from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.utils import timezone


class WebUser(AbstractBaseUser):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(_("email address"), unique=True)
    phone_regex = RegexValidator(
        regex=r'^\d{10}$',
        message="Phone number must be exactly 10 digits."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=10)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    last_login =  models.DateTimeField(auto_now_add=True,blank=True,null=True)
    date_joined = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.email
    

class RoomMember(models.Model):
    name = models.CharField(max_length=200)
    uid = models.CharField(max_length=1000)
    room_name = models.CharField(max_length=200)
    insession = models.BooleanField(default=True)

    def __str__(self):
        return self.name