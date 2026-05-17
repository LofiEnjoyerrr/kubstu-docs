from django.urls import path

from docs.views import (
    MeDocumentsCreateAPIView,
    DocumentsAvailableListAPIView,
    DocumentsRetrieveUpdateAPIView,
    DocumentAccessListCreateAPIView,
    DocumentAccessDetailAPIView,
    MyDocumentAccessAPIView,
    DocumentsSearchAPIView,
    DocumentImageUploadAPIView,
    DocumentCommentsAPIView,
    DocumentCommentDetailAPIView,
)

urlpatterns = [
    path('me/', MeDocumentsCreateAPIView.as_view(), name='me_docs_list'),
    path('available/', DocumentsAvailableListAPIView.as_view(), name='docs_available'),
    path('search/', DocumentsSearchAPIView.as_view(), name='docs_search'),
    path('<int:pk>/', DocumentsRetrieveUpdateAPIView.as_view(), name='doc'),
    path('<int:pk>/my-access/', MyDocumentAccessAPIView.as_view(), name='doc_my_access'),
    path('<int:pk>/accesses/', DocumentAccessListCreateAPIView.as_view(), name='doc_accesses'),
    path('<int:pk>/accesses/<int:access_id>/', DocumentAccessDetailAPIView.as_view(), name='doc_access_detail'),
    path('<int:pk>/images/', DocumentImageUploadAPIView.as_view(), name='doc_image_upload'),
    path('<int:pk>/comments/', DocumentCommentsAPIView.as_view(), name='doc_comments'),
    path('<int:pk>/comments/<int:comment_id>/', DocumentCommentDetailAPIView.as_view(), name='doc_comment_detail'),
]
