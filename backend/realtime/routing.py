from django.urls import re_path
from realtime.consumers import DocumentConsumer

websocket_urlpatterns = [
    re_path(r"ws/docs/(?P<doc_id>\d+)/$", DocumentConsumer.as_asgi()),
]
