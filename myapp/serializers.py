from .models import WebUser,RoomMember
from rest_framework import serializers


class WebUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)  # write_only ensures that field is only write and cannot be readed

    class Meta:
        model = WebUser
        fields = '__all__'

    def create(self, validated_data):
        user = WebUser(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
        )
        user.set_password(validated_data['password'])  # This hashes the password
        user.save()
        return user
    

class RoomMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomMember
        fields ='__all__'

# class signupserializer(serializers.Serializer):
#     first_name=serializers.CharField()
#     last_name=serializers.CharField()
#     email=

