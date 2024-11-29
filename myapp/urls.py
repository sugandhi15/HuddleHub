from django.urls import path
from . import views

urlpatterns = [
    path('signup/',views.signup.as_view()),
    path('login/',views.login.as_view()),
    path('reset/<str:jwtToken>',views.ResetPassword.as_view()),
    path('resetpass/<str:token>/<str:jwtToken>',views.setPassword.as_view()),
    path('forgetpass/',views.ForgetPassword.as_view()),
    path('setnewpass/<str:token>/<str:encoded_info>',views.newPassword.as_view()),
    path('', views.lobby),
    path('room/', views.room),
    path('get_token/', views.getToken),
    path('create_member/', views.createMember),
    path('get_all_members/',views.getRoomMember.as_view()),
    path('get_member/', views.getMember),
    path('delete_member/', views.deleteMember),
]