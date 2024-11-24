from django.contrib import admin
from .models import WebUser , RoomMember

# Register your models here.
admin.site.register(WebUser)

admin.site.register(RoomMember)
