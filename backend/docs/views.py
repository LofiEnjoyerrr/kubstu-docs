import json
import os
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.files.storage import default_storage
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.parsers import MultiPartParser
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

        # Editors may patch content / headers / footers (e.g. DOCX import).
        # All other fields (title / is_public / page layout) are owner-only.
        requested_fields = set(request.data.keys())

        is_owner = document.owner == request.user

        # Editor-permitted fields. Anything else is owner-only.
        editor_fields = {'content', 'header_content', 'footer_content'}

        if not is_owner:
            if not requested_fields.issubset(editor_fields):
                raise PermissionDenied(
                    'Только владелец документа может изменять эти поля'
                )
            if not request.user.is_authenticated:
                raise PermissionDenied('Требуется авторизация')
            allowed = (
                document.is_public
                or document.accesses.filter(user=request.user, role='editor').exists()
            )
            if not allowed:
                raise PermissionDenied('Нет прав на редактирование документа')

        serializer = PatchDocumentSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        content_changed = 'content' in serializer.validated_data
        page_layout_changed = bool(
            requested_fields & {
                'page_width', 'page_height',
                'margin_top', 'margin_right', 'margin_bottom', 'margin_left',
                'header_content', 'footer_content',
                'show_page_numbers', 'page_number_start',
            }
        )

        if content_changed:
            # Bump version like the WS path does so other clients see the
            # broadcasted edit as a fresh change, not a stale replay.
            document.version = (document.version or 0) + 1
            serializer.save(version=document.version)
        else:
            serializer.save()

        document.refresh_from_db()
        data = GetDocumentSerializer(document).data

        if content_changed:
            # Notify everyone in the doc room that the document was rewritten.
            try:
                content_json = (
                    json.loads(document.content) if document.content else {}
                )
            except (json.JSONDecodeError, TypeError):
                content_json = document.content or {}

            _broadcast_to_doc(pk, {
                'type': 'broadcast_full_replace',
                'content': content_json,
                'version': document.version,
                'user_id': request.user.id,
                'username': request.user.username,
            })

        if page_layout_changed:
            _broadcast_to_doc(pk, {
                'type': 'broadcast_page_layout',
                'page_width': document.page_width,
                'page_height': document.page_height,
                'margin_top': document.margin_top,
                'margin_right': document.margin_right,
                'margin_bottom': document.margin_bottom,
                'margin_left': document.margin_left,
                'header_content': document.header_content,
                'footer_content': document.footer_content,
                'show_page_numbers': document.show_page_numbers,
                'page_number_start': document.page_number_start,
            })

        return Response(data)

    def delete(self, request, pk):
        document = _get_document_or_404(pk)
        _require_owner(document, request.user)
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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


class DocumentImageUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, pk):
        document = _get_document_or_404(pk)
        _require_read_access(document, request.user)

        image = request.FILES.get('image')
        if not image:
            raise ValidationError({'image': 'Файл не передан'})
        if not image.content_type.startswith('image/'):
            raise ValidationError({'image': 'Файл не является изображением'})

        ext = os.path.splitext(image.name)[1].lower() or '.jpg'
        filename = f'{uuid.uuid4().hex}{ext}'
        filepath = f'docs/{pk}/images/{filename}'

        saved = default_storage.save(filepath, image)
        url = settings.MEDIA_URL + saved

        return Response({'url': url}, status=status.HTTP_201_CREATED)


class DocumentDocxImportAPIView(APIView):
    """
    Server-side DOCX import. Parses the uploaded file with our custom
    OOXML reader (preserves direct formatting that mammoth dropped),
    persists the resulting Tiptap JSON + page settings synchronously,
    then broadcasts a ``full_replace`` over the WS so any open editors
    rerender immediately.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, pk):
        document = _get_document_or_404(pk)

        # Editors are allowed to import — same rule as content edit.
        if document.owner != request.user:
            allowed = (
                document.is_public
                or document.accesses.filter(user=request.user, role='editor').exists()
            )
            if not allowed:
                raise PermissionDenied('Нет прав на изменение документа')

        upload = request.FILES.get('file')
        if not upload:
            raise ValidationError({'file': 'Файл не передан'})
        name = (upload.name or '').lower()
        if not name.endswith('.docx'):
            raise ValidationError({'file': 'Ожидается DOCX-файл'})

        # Parse
        from docs.docx_importer import DocxConverter
        try:
            result = DocxConverter(
                upload.read(),
                document_pk=document.pk,
            ).convert()
        except Exception as e:  # noqa: BLE001 — surface the actual cause
            raise ValidationError({'file': f'Не удалось распарсить DOCX: {e}'})

        content_json = result['content']
        page_layout = result['page_layout']
        header_doc = result.get('header_content')
        footer_doc = result.get('footer_content')
        has_pagination = bool(result.get('has_pagination'))

        # Persist atomically. We hand-roll the save instead of going through
        # the serializer so we can update many fields in one shot and bump
        # `version` like the WS path does.
        document.content = json.dumps(content_json)
        document.page_width = page_layout.get('page_width', document.page_width)
        document.page_height = page_layout.get('page_height', document.page_height)
        document.margin_top = page_layout.get('margin_top', document.margin_top)
        document.margin_right = page_layout.get('margin_right', document.margin_right)
        document.margin_bottom = page_layout.get('margin_bottom', document.margin_bottom)
        document.margin_left = page_layout.get('margin_left', document.margin_left)
        if 'page_number_start' in page_layout:
            document.page_number_start = page_layout['page_number_start']
        if header_doc is not None:
            document.header_content = json.dumps(header_doc)
        if footer_doc is not None:
            document.footer_content = json.dumps(footer_doc)
        # When the source DOCX paginates (hard page break, section break,
        # lastRenderedPageBreak, or PAGE field in header/footer) the user
        # expects the editor to behave the same way out of the box.
        if has_pagination:
            document.show_page_numbers = True
        document.version = (document.version or 0) + 1
        document.save()

        # Tell other clients about the new content + (possibly) new layout.
        _broadcast_to_doc(pk, {
            'type': 'broadcast_full_replace',
            'content': content_json,
            'version': document.version,
            'user_id': request.user.id,
            'username': request.user.username,
        })
        _broadcast_to_doc(pk, {
            'type': 'broadcast_page_layout',
            'page_width': document.page_width,
            'page_height': document.page_height,
            'margin_top': document.margin_top,
            'margin_right': document.margin_right,
            'margin_bottom': document.margin_bottom,
            'margin_left': document.margin_left,
            'header_content': document.header_content,
            'footer_content': document.footer_content,
            'show_page_numbers': document.show_page_numbers,
            'page_number_start': document.page_number_start,
        })

        return Response(GetDocumentSerializer(document).data, status=status.HTTP_200_OK)


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
