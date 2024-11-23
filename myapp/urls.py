from django.urls import path
from . import views

urlpatterns = [
    path('signup/',views.signup.as_view()),
    path('login/',views.login.as_view()),
    path('info/',views.userInfo),
    # path(' ', views.index, name='agora-index'),
    # path('pusher/auth/', views.pusher_auth, name='agora-pusher-auth'),
    # path('token/', views.generate_agora_token, name='agora-token'),
    # path('call-user/', views.call_user, name='agora-call-user'),
]
