from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from docs.serializers import GetDocumentSerializer, PostDocumentSerializer
from docs.selectors import get_user_documents, get_available_documents, get_user_opened_documents


class MeDocumentsListCreateAPIView(APIView):
    get_serializer_class = GetDocumentSerializer
    post_serializer_class = PostDocumentSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PostDocumentSerializer(),
        responses=GetDocumentSerializer(),
    )
    def post(self, request, *args, **kwargs):
        serializer = self.post_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save(owner=request.user)
        return Response(
            self.get_serializer_class(instance=document).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentsAvailableListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=GetDocumentSerializer(),
    )
    def get(self, request):
        owner_documents = get_user_documents(self.request.user).select_related('owner')
        opened_documents = get_user_opened_documents(self.request.user).select_related('owner')
        response_data = {
            'owner_documents': GetDocumentSerializer(owner_documents, many=True).data,
            'opened_documents': GetDocumentSerializer(opened_documents, many=True).data,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class DocumentsRetrieveAPIView(RetrieveAPIView):
    serializer_class = GetDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_available_documents(self.request.user).select_related('owner')
