from django.urls import path

from docs.views import MeDocumentsCreateAPIView, DocumentsRetrieveAPIView, DocumentsAvailableListAPIView

urlpatterns = [
    path('me/', MeDocumentsCreateAPIView.as_view(), name='me_docs_list'),
    path('available/', DocumentsAvailableListAPIView.as_view(), name='docs_available'),
    path('<int:pk>/', DocumentsRetrieveAPIView.as_view(), name='doc'),
]
