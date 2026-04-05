from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated

from docs.serializers import DocumentSerializer
from docs.selectors import get_user_documents, get_available_documents_sorted, get_available_documents


class MeDocumentsListCreateAPIView(ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_user_documents(self.request.user).select_related('owner')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DocumentsAvailableListAPIView(ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_available_documents_sorted(self.request.user).select_related('owner')


class DocumentsRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_available_documents(self.request.user).select_related('owner')
