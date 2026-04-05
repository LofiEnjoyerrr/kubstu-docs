from django.urls import path

from docs.views import MeDocumentsListCreateAPIView

urlpatterns = [
    path('me/docs/', MeDocumentsListCreateAPIView.as_view(), name='me_docs_list'),
    path('me/docs/<int:pk>/', ..., name='docs_available'),
]
