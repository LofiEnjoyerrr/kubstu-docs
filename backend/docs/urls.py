from django.urls import path

from docs.views import MeDocumentsListCreateAPIView, DocumentsRetrieveUpdateAPIView, DocumentsAvailableListAPIView

urlpatterns = [
    path('me/', MeDocumentsListCreateAPIView.as_view(), name='me_docs_list'),
    path('<int:pk>/', DocumentsRetrieveUpdateAPIView.as_view(), name='doc'),
    path('available/', DocumentsAvailableListAPIView.as_view(), name='docs_available'),
]
