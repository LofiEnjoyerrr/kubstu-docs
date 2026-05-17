from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from docs.models import Document, DocumentAccess, Comment
from docs.serializers import (
    GetDocumentSerializer,
    PostDocumentSerializer,
    PatchDocumentSerializer,
    DocumentAccessSerializer,
    PostDocumentAccessSerializer,
    PatchDocumentAccessSerializer,
    MyAccessSerializer,
    CommentSerializer,
    CreateCommentSerializer,
    UpdateCommentSerializer,
)
from docs.selectors import get_user_documents, get_user_opened_documents


def _broadcast_to_doc(doc_id: int, event: dict) -> None:
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(f'doc_{doc_id}', event)


def _get_document_or_404(pk: int) -> Document:
    try:
        return Document.objects.select_related('owner').get(pk=pk)
    except Document.DoesNotExist:
        raise NotFound('Документ не найден')


def _require_owner(document: Document, user) -> None:
    if document.owner != user:
        raise PermissionDenied('Только владелец документа может выполнить это действие')


def _require_read_access(document: Document, user) -> None:
    if document.is_public:
        return
    if not user.is_authenticated:
        raise PermissionDenied('Требуется авторизация')
    if document.owner == user:
        return
    if document.accesses.filter(user=user).exists():
        return
    raise PermissionDenied('У вас нет доступа к этому документу')


class MeDocumentsCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PostDocumentSerializer(),
        responses=GetDocumentSerializer(),
    )
    def post(self, request, *args, **kwargs):
        serializer = PostDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save(owner=request.user)
        return Response(
            GetDocumentSerializer(instance=document).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentsAvailableListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=GetDocumentSerializer(many=True))
    def get(self, request):
        owner_documents = get_user_documents(request.user).select_related('owner')
        opened_documents = get_user_opened_documents(request.user).select_related('owner')
        response_data = {
            'owner_documents': GetDocumentSerializer(owner_documents, many=True).data,
            'opened_documents': GetDocumentSerializer(opened_documents, many=True).data,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class DocumentsRetrieveUpdateAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=GetDocumentSerializer())
    def get(self, request, pk):
        document = _get_document_or_404(pk)
        _require_read_access(document, request.user)
        return Response(GetDocumentSerializer(document).data)

    @extend_schema(request=PatchDocumentSerializer(), responses=GetDocumentSerializer())
    def patch(self, request, pk):
        document = _get_document_or_404(pk)
        _require_owner(document, request.user)
        serializer = PatchDocumentSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(GetDocumentSerializer(document).data)


class DocumentAccessListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_owned_document(self, pk, user) -> Document:
        document = _get_document_or_404(pk)
        _require_owner(document, user)
        return document

    @extend_schema(responses=DocumentAccessSerializer(many=True))
    def get(self, request, pk):
        document = self._get_owned_document(pk, request.user)
        accesses = document.accesses.select_related('user').all()
        return Response(DocumentAccessSerializer(accesses, many=True).data)

    @extend_schema(request=PostDocumentAccessSerializer(), responses=DocumentAccessSerializer())
    def post(self, request, pk):
        document = self._get_owned_document(pk, request.user)
        serializer = PostDocumentAccessSerializer(
            data=request.data,
            context={'document': document},
        )
        serializer.is_valid(raise_exception=True)
        access = serializer.save()
        return Response(
            DocumentAccessSerializer(access).data,
            status=status.HTTP_201_CREATED,
        )


class MyDocumentAccessAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        document = _get_document_or_404(pk)
        if request.user.is_authenticated and document.owner == request.user:
            return Response(MyAccessSerializer({'role': 'owner'}).data)
        if document.is_public:
            role = 'editor' if request.user.is_authenticated else 'viewer'
            return Response(MyAccessSerializer({'role': role}).data)
        if not request.user.is_authenticated:
            raise PermissionDenied('Требуется авторизация')
        try:
            access = DocumentAccess.objects.get(document=document, user=request.user)
            return Response(MyAccessSerializer({'role': access.role}).data)
        except DocumentAccess.DoesNotExist:
            raise PermissionDenied('У вас нет доступа к этому документу')


class DocumentsSearchAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response([])
        documents = (
            Document.objects.filter(is_public=True, title__icontains=q)
            .select_related('owner')
            .order_by('title')[:20]
        )
        return Response(GetDocumentSerializer(documents, many=True).data)


class DocumentCommentsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        document = _get_document_or_404(pk)
        _require_read_access(document, request.user)
        comments = Comment.objects.filter(document=document).select_related('author')
        return Response(CommentSerializer(comments, many=True).data)

    def post(self, request, pk):
        if not request.user.is_authenticated:
            raise PermissionDenied('Требуется авторизация')
        document = _get_document_or_404(pk)
        _require_read_access(document, request.user)
        serializer = CreateCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(document=document, author=request.user)
        data = CommentSerializer(comment).data
        _broadcast_to_doc(pk, {'type': 'broadcast_comment_add', 'comment': dict(data)})
        return Response(data, status=status.HTTP_201_CREATED)


class DocumentCommentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_comment(self, pk, comment_id) -> tuple[Document, Comment]:
        document = _get_document_or_404(pk)
        try:
            comment = Comment.objects.select_related('author').get(pk=comment_id, document=document)
        except Comment.DoesNotExist:
            raise NotFound('Комментарий не найден')
        return document, comment

    def patch(self, request, pk, comment_id):
        document, comment = self._get_comment(pk, comment_id)
        # Only the comment author or document owner may sync positions
        if comment.author != request.user and document.owner != request.user:
            raise PermissionDenied('Нет прав на редактирование комментария')
        serializer = UpdateCommentSerializer(comment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        data = CommentSerializer(comment).data
        _broadcast_to_doc(pk, {'type': 'broadcast_comment_update', 'comment': dict(data)})
        return Response(data)

    def delete(self, request, pk, comment_id):
        document, comment = self._get_comment(pk, comment_id)
        if comment.author != request.user and document.owner != request.user:
            raise PermissionDenied('Нет прав на удаление комментария')
        comment.delete()
        _broadcast_to_doc(pk, {'type': 'broadcast_comment_delete', 'comment_id': comment_id})
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentAccessDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_access(self, pk, access_id, user) -> DocumentAccess:
        document = _get_document_or_404(pk)
        _require_owner(document, user)
        try:
            return DocumentAccess.objects.select_related('user').get(pk=access_id, document=document)
        except DocumentAccess.DoesNotExist:
            raise NotFound('Запись доступа не найдена')

    @extend_schema(request=PatchDocumentAccessSerializer(), responses=DocumentAccessSerializer())
    def patch(self, request, pk, access_id):
        access = self._get_access(pk, access_id, request.user)
        serializer = PatchDocumentAccessSerializer(access, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        access = serializer.save()
        return Response(DocumentAccessSerializer(access).data)

    @extend_schema(responses=None)
    def delete(self, request, pk, access_id):
        access = self._get_access(pk, access_id, request.user)
        access.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
