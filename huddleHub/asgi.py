import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from myapp.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'huddleHub.settings')

application = get_asgi_application()

application = ProtocolTypeRouter({
  "http": get_asgi_application(),
   "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
   ),
})