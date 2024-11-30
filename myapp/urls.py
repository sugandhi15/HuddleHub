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
    path('get_token/<str:jwtToken>/', views.getToken),
    path('get_token_unauth/', views.unauthgetToken),
    path('create_member/', views.createMember),
    path('participants/<str:room_name>',views.getRoomMember.as_view()),
    path('get_member/', views.getMember),
    path('delete_member/', views.deleteMember),
    path('user_profile/<str:jwtToken>/',views.userProfile.as_view()),
]