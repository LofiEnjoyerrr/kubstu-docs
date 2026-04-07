from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from docs.serializers import GetDocumentSerializer, PostDocumentSerializer
from docs.selectors import get_user_documents, get_available_documents, get_user_opened_documents


class MeDocumentsListCreateAPIView(APIView):
    get_serializer_class = GetDocumentSerializer
    post_serializer_class = PostDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        owner_documents = get_user_documents(
            self.request.user,
        ).select_related('owner').prefetch_related('accesses__user')
        serializer = self.get_serializer_class(instance=owner_documents, many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        data = {
            **request.data,
            'owner': self.request.user.id
        }
        serializer = self.post_serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(
            self.get_serializer_class(instance=document).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentsAvailableListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        owner_documents = get_user_documents(self.request.user).select_related('owner')
        opened_documents = get_user_opened_documents(self.request.user).select_related('owner')
        response_data = {
            'owner_documents': GetDocumentSerializer(owner_documents, many=True).data,
            'opened_documents': GetDocumentSerializer(opened_documents, many=True).data,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class DocumentsRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    serializer_class = GetDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_available_documents(self.request.user).select_related('owner')
