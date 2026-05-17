from django.urls import path

from docs.views import (
    MeDocumentsCreateAPIView,
    DocumentsAvailableListAPIView,
    DocumentsRetrieveUpdateAPIView,
    DocumentAccessListCreateAPIView,
    DocumentAccessDetailAPIView,
)

urlpatterns = [
    path('me/', MeDocumentsCreateAPIView.as_view(), name='me_docs_list'),
    path('available/', DocumentsAvailableListAPIView.as_view(), name='docs_available'),
    path('<int:pk>/', DocumentsRetrieveUpdateAPIView.as_view(), name='doc'),
    path('<int:pk>/accesses/', DocumentAccessListCreateAPIView.as_view(), name='doc_accesses'),
    path('<int:pk>/accesses/<int:access_id>/', DocumentAccessDetailAPIView.as_view(), name='doc_access_detail'),
]
