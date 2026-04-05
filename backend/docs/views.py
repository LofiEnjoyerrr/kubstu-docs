from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from docs.serializers import MeDocumentsSerializer
from docs.selectors import get_user_documents


class MeDocumentsListCreateAPIView(ListCreateAPIView):
    serializer_class = MeDocumentsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_user_documents(self.request.user).select_related('owner')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MeDocumentsRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    serializer_class = MeDocumentsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_user_documents(self.request.user).select_related('owner')
