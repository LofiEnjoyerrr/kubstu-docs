"""
End-to-end coverage of the document API surface.

The WebSocket broadcast helper (``_broadcast_to_doc``) is patched at module
scope in every test that touches mutating endpoints — we don't want pytest to
try to reach Redis, and the test channel layer would just discard the message
anyway.
"""

import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from docs.models import Comment, Document, DocumentAccess
from docs.tests.factories import (
    CommentFactory,
    DocumentAccessFactory,
    DocumentFactory,
)
from users.models import FavoriteUser
from users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _silence_broadcasts(mocker):
    """Replace the channel-layer broadcast helper for every doc-view test."""
    return mocker.patch('docs.views._broadcast_to_doc')


# ---------- Document creation / listing ----------

@pytest.mark.django_db
def test_create_document_requires_auth(api_client):
    response = api_client.post(reverse('me_docs_list'), {'title': 'Hi'}, format='json')
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_create_document_sets_owner_to_request_user(auth_client, user):
    response = auth_client.post(
        reverse('me_docs_list'), {'title': 'New doc'}, format='json',
    )
    assert response.status_code == 201
    doc = Document.objects.get(title='New doc')
    assert doc.owner == user


@pytest.mark.django_db
def test_available_documents_split_owner_vs_opened(auth_client, user, other_user):
    own = DocumentFactory(owner=user, title='mine')
    shared = DocumentFactory(owner=other_user, title='theirs')
    DocumentAccessFactory(document=shared, user=user, role='editor')

    response = auth_client.get(reverse('docs_available'))
    assert response.status_code == 200
    owner_ids = {d['id'] for d in response.data['owner_documents']}
    opened_ids = {d['id'] for d in response.data['opened_documents']}
    assert owner_ids == {own.id}
    assert opened_ids == {shared.id}


# ---------- Retrieve / read access ----------

@pytest.mark.django_db
def test_retrieve_public_document_works_for_anonymous(api_client, user):
    doc = DocumentFactory(owner=user, is_public=True)
    response = api_client.get(reverse('doc', args=[doc.pk]))
    assert response.status_code == 200
    assert response.data['id'] == doc.id


@pytest.mark.django_db
def test_retrieve_private_document_forbidden_for_anonymous(api_client, document):
    response = api_client.get(reverse('doc', args=[document.pk]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_retrieve_private_document_forbidden_for_unrelated_user(
    other_auth_client, document,
):
    response = other_auth_client.get(reverse('doc', args=[document.pk]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_retrieve_private_document_allowed_for_editor(
    other_auth_client, document, document_access,
):
    response = other_auth_client.get(reverse('doc', args=[document.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_retrieve_returns_404_for_missing_document(auth_client):
    response = auth_client.get(reverse('doc', args=[9999]))
    assert response.status_code == 404


# ---------- Patch ----------

@pytest.mark.django_db
def test_owner_can_patch_title(auth_client, document):
    response = auth_client.patch(
        reverse('doc', args=[document.pk]), {'title': 'Renamed'}, format='json',
    )
    assert response.status_code == 200
    document.refresh_from_db()
    assert document.title == 'Renamed'


@pytest.mark.django_db
def test_editor_can_patch_content_but_not_title(
    other_auth_client, document, document_access,
):
    # Title is owner-only.
    response = other_auth_client.patch(
        reverse('doc', args=[document.pk]),
        {'title': 'Hacked'},
        format='json',
    )
    assert response.status_code == 403

    # Content is editor-allowed.
    response = other_auth_client.patch(
        reverse('doc', args=[document.pk]),
        {'content': json.dumps({'type': 'doc'})},
        format='json',
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_editor_can_patch_document_status(
    other_auth_client, document, document_access, _silence_broadcasts,
):
    response = other_auth_client.patch(
        reverse('doc', args=[document.pk]),
        {'status_text': 'Готово', 'status_color': '#16a34a'},
        format='json',
    )

    assert response.status_code == 200
    document.refresh_from_db()
    assert document.status_text == 'Готово'
    assert document.status_color == '#16a34a'
    _silence_broadcasts.assert_called_with(
        document.pk,
        {
            'type': 'broadcast_document_status',
            'status_text': 'Готово',
            'status_color': '#16a34a',
        },
    )


@pytest.mark.django_db
def test_public_document_does_not_grant_edit_to_unrelated_user(
    other_auth_client,
    public_document,
):
    response = other_auth_client.patch(
        reverse('doc', args=[public_document.pk]),
        {'content': json.dumps({'type': 'doc'})},
        format='json',
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_public_document_explicit_editor_can_patch_content(
    other_auth_client,
    public_document,
    other_user,
):
    DocumentAccessFactory(document=public_document, user=other_user, role='editor')

    response = other_auth_client.patch(
        reverse('doc', args=[public_document.pk]),
        {'content': json.dumps({'type': 'doc'})},
        format='json',
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_viewer_cannot_patch_content(
    other_auth_client, document, viewer_access,
):
    response = other_auth_client.patch(
        reverse('doc', args=[document.pk]),
        {'content': json.dumps({'type': 'doc'})},
        format='json',
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_patch_content_bumps_version_and_broadcasts(
    auth_client, document, _silence_broadcasts,
):
    document.version = 3
    document.save()
    response = auth_client.patch(
        reverse('doc', args=[document.pk]),
        {'content': json.dumps({'type': 'doc'})},
        format='json',
    )
    assert response.status_code == 200
    document.refresh_from_db()
    assert document.version == 4
    assert _silence_broadcasts.called


@pytest.mark.django_db
def test_patch_page_layout_triggers_layout_broadcast(
    auth_client, document, _silence_broadcasts,
):
    response = auth_client.patch(
        reverse('doc', args=[document.pk]),
        {'margin_top': 100},
        format='json',
    )
    assert response.status_code == 200
    # At least one of the broadcast calls is the layout one.
    types = [c.args[1]['type'] for c in _silence_broadcasts.call_args_list]
    assert 'broadcast_page_layout' in types


@pytest.mark.django_db
def test_patch_validates_page_width_bounds(auth_client, document):
    response = auth_client.patch(
        reverse('doc', args=[document.pk]),
        {'page_width': 100},
        format='json',
    )
    assert response.status_code == 400


# ---------- Delete ----------

@pytest.mark.django_db
def test_owner_can_delete_document(auth_client, document):
    response = auth_client.delete(reverse('doc', args=[document.pk]))
    assert response.status_code == 204
    assert not Document.objects.filter(pk=document.pk).exists()


@pytest.mark.django_db
def test_editor_cannot_delete_document(
    other_auth_client, document, document_access,
):
    response = other_auth_client.delete(reverse('doc', args=[document.pk]))
    assert response.status_code == 403


# ---------- Accesses CRUD ----------

@pytest.mark.django_db
def test_owner_can_list_accesses(auth_client, document, other_user):
    DocumentAccessFactory(document=document, user=other_user, role='editor')
    response = auth_client.get(reverse('doc_accesses', args=[document.pk]))
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['username'] == other_user.username
    assert response.data[0]['is_favorite'] is False


@pytest.mark.django_db
def test_owner_can_list_accesses_with_favorite_flag(auth_client, user, document, other_user):
    DocumentAccessFactory(document=document, user=other_user, role='editor')
    FavoriteUser.objects.create(owner=user, user=other_user)

    response = auth_client.get(reverse('doc_accesses', args=[document.pk]))

    assert response.status_code == 200
    assert response.data[0]['username'] == other_user.username
    assert response.data[0]['is_favorite'] is True


@pytest.mark.django_db
def test_non_owner_cannot_list_accesses(other_auth_client, document):
    response = other_auth_client.get(reverse('doc_accesses', args=[document.pk]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_owner_can_create_access(auth_client, document, other_user):
    response = auth_client.post(
        reverse('doc_accesses', args=[document.pk]),
        {'user_id': other_user.id, 'role': 'viewer'},
        format='json',
    )
    assert response.status_code == 201
    assert DocumentAccess.objects.filter(document=document, user=other_user).exists()


@pytest.mark.django_db
def test_owner_can_patch_access_role(auth_client, document, document_access):
    response = auth_client.patch(
        reverse('doc_access_detail', args=[document.pk, document_access.pk]),
        {'role': 'viewer'},
        format='json',
    )
    assert response.status_code == 200
    document_access.refresh_from_db()
    assert document_access.role == 'viewer'


@pytest.mark.django_db
def test_owner_can_delete_access(auth_client, document, document_access):
    response = auth_client.delete(
        reverse('doc_access_detail', args=[document.pk, document_access.pk]),
    )
    assert response.status_code == 204
    assert not DocumentAccess.objects.filter(pk=document_access.pk).exists()


# ---------- My access ----------

@pytest.mark.django_db
def test_my_access_returns_owner_for_owner(auth_client, document):
    response = auth_client.get(reverse('doc_my_access', args=[document.pk]))
    assert response.status_code == 200
    assert response.data['role'] == 'owner'


@pytest.mark.django_db
def test_my_access_returns_viewer_for_authed_user_on_public_doc(
    other_auth_client, public_document,
):
    response = other_auth_client.get(reverse('doc_my_access', args=[public_document.pk]))
    assert response.status_code == 200
    assert response.data['role'] == 'viewer'


@pytest.mark.django_db
def test_my_access_returns_assigned_editor_on_public_doc(
    other_auth_client,
    public_document,
    other_user,
):
    DocumentAccessFactory(document=public_document, user=other_user, role='editor')

    response = other_auth_client.get(reverse('doc_my_access', args=[public_document.pk]))
    assert response.status_code == 200
    assert response.data['role'] == 'editor'


@pytest.mark.django_db
def test_my_access_returns_viewer_for_anonymous_on_public_doc(
    api_client, public_document,
):
    response = api_client.get(reverse('doc_my_access', args=[public_document.pk]))
    assert response.status_code == 200
    assert response.data['role'] == 'viewer'


@pytest.mark.django_db
def test_my_access_returns_assigned_role(
    other_auth_client, document, viewer_access,
):
    response = other_auth_client.get(reverse('doc_my_access', args=[document.pk]))
    assert response.status_code == 200
    assert response.data['role'] == 'viewer'


@pytest.mark.django_db
def test_my_access_forbidden_for_unrelated_user(other_auth_client, document):
    response = other_auth_client.get(reverse('doc_my_access', args=[document.pk]))
    assert response.status_code == 403


# ---------- Search ----------

@pytest.mark.django_db
def test_search_returns_only_public_docs(api_client, user):
    DocumentFactory(owner=user, title='Public report', is_public=True)
    DocumentFactory(owner=user, title='Private report', is_public=False)

    response = api_client.get(reverse('docs_search'), {'q': 'report'})
    assert response.status_code == 200
    titles = [d['title'] for d in response.data]
    assert titles == ['Public report']


@pytest.mark.django_db
def test_search_empty_query_returns_empty_list(api_client):
    response = api_client.get(reverse('docs_search'), {'q': '   '})
    assert response.status_code == 200
    assert response.data == []


# ---------- Comments ----------

@pytest.mark.django_db
def test_anonymous_can_list_comments_on_public_doc(api_client, public_document):
    CommentFactory(document=public_document, author=public_document.owner)
    response = api_client.get(reverse('doc_comments', args=[public_document.pk]))
    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_create_comment_requires_auth(api_client, public_document):
    response = api_client.post(
        reverse('doc_comments', args=[public_document.pk]),
        {'quote': 'q', 'from_pos': 0, 'to_pos': 5, 'content': 'hi'},
        format='json',
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_unrelated_user_cannot_comment_on_public_doc(
    other_auth_client, public_document, _silence_broadcasts,
):
    response = other_auth_client.post(
        reverse('doc_comments', args=[public_document.pk]),
        {'quote': 'q', 'from_pos': 0, 'to_pos': 5, 'content': 'hi'},
        format='json',
    )
    assert response.status_code == 403
    assert Comment.objects.filter(document=public_document).count() == 0
    assert not _silence_broadcasts.called


@pytest.mark.django_db
def test_user_with_access_can_comment_on_public_doc(
    other_auth_client, public_document, other_user, _silence_broadcasts,
):
    DocumentAccessFactory(document=public_document, user=other_user, role='viewer')

    response = other_auth_client.post(
        reverse('doc_comments', args=[public_document.pk]),
        {'quote': 'q', 'from_pos': 0, 'to_pos': 5, 'content': 'hi'},
        format='json',
    )
    assert response.status_code == 201
    assert Comment.objects.filter(document=public_document).count() == 1
    assert _silence_broadcasts.called


@pytest.mark.django_db
def test_author_can_patch_comment(auth_client, comment):
    response = auth_client.patch(
        reverse('doc_comment_detail', args=[comment.document.pk, comment.pk]),
        {'from_pos': 5, 'to_pos': 15},
        format='json',
    )
    assert response.status_code == 200
    comment.refresh_from_db()
    assert comment.from_pos == 5
    assert comment.to_pos == 15


@pytest.mark.django_db
def test_unrelated_user_cannot_patch_comment(
    other_auth_client, comment,
):
    response = other_auth_client.patch(
        reverse('doc_comment_detail', args=[comment.document.pk, comment.pk]),
        {'from_pos': 5},
        format='json',
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_author_can_delete_own_comment(auth_client, comment):
    response = auth_client.delete(
        reverse('doc_comment_detail', args=[comment.document.pk, comment.pk]),
    )
    assert response.status_code == 204
    assert not Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
def test_document_owner_can_delete_others_comment(
    auth_client, document, other_user,
):
    foreign_comment = CommentFactory(document=document, author=other_user)
    response = auth_client.delete(
        reverse('doc_comment_detail', args=[document.pk, foreign_comment.pk]),
    )
    assert response.status_code == 204


@pytest.mark.django_db
def test_document_owner_can_delete_all_comments(
    auth_client, document, other_user, _silence_broadcasts,
):
    own_comment = CommentFactory(document=document, author=document.owner)
    foreign_comment = CommentFactory(document=document, author=other_user)

    response = auth_client.delete(reverse('doc_comments', args=[document.pk]))

    assert response.status_code == 204
    assert not Comment.objects.filter(pk__in=[own_comment.pk, foreign_comment.pk]).exists()
    assert _silence_broadcasts.call_count == 2


@pytest.mark.django_db
def test_non_owner_cannot_delete_all_comments(
    other_auth_client, document, other_user, _silence_broadcasts,
):
    DocumentAccessFactory(document=document, user=other_user, role='editor')
    comment = CommentFactory(document=document, author=other_user)

    response = other_auth_client.delete(reverse('doc_comments', args=[document.pk]))

    assert response.status_code == 403
    assert Comment.objects.filter(pk=comment.pk).exists()
    assert not _silence_broadcasts.called


@pytest.mark.django_db
def test_missing_comment_returns_404(auth_client, document):
    response = auth_client.delete(
        reverse('doc_comment_detail', args=[document.pk, 9999]),
    )
    assert response.status_code == 404


# ---------- Image upload / download ----------

def _image_bytes() -> bytes:
    """A 1x1 transparent PNG — smallest valid image we can upload."""
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        b'\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4'
        b'\x89\x00\x00\x00\rIDATx\x9cc\xfa\xcf\x00\x00\x00\x02\x00\x01'
        b'\xe5\'\xde\xfc\x00\x00\x00\x00IEND\xaeB`\x82'
    )


@pytest.mark.django_db
def test_upload_image_requires_auth(api_client, public_document):
    upload = SimpleUploadedFile('img.png', _image_bytes(), content_type='image/png')
    response = api_client.post(
        reverse('doc_image_upload', args=[public_document.pk]),
        {'image': upload},
        format='multipart',
    )
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_unrelated_user_cannot_upload_image_to_public_doc(other_auth_client, public_document):
    upload = SimpleUploadedFile('img.png', _image_bytes(), content_type='image/png')
    response = other_auth_client.post(
        reverse('doc_image_upload', args=[public_document.pk]),
        {'image': upload},
        format='multipart',
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_unrelated_user_cannot_import_docx_to_public_doc(other_auth_client, public_document):
    upload = SimpleUploadedFile(
        'doc.docx',
        b'not a real docx',
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    response = other_auth_client.post(
        reverse('doc_import_docx', args=[public_document.pk]),
        {'file': upload},
        format='multipart',
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_upload_image_rejects_non_image(auth_client, document):
    upload = SimpleUploadedFile('bad.txt', b'hello', content_type='text/plain')
    response = auth_client.post(
        reverse('doc_image_upload', args=[document.pk]),
        {'image': upload},
        format='multipart',
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_upload_image_returns_url(auth_client, document):
    upload = SimpleUploadedFile('img.png', _image_bytes(), content_type='image/png')
    response = auth_client.post(
        reverse('doc_image_upload', args=[document.pk]),
        {'image': upload},
        format='multipart',
    )
    assert response.status_code == 201
    assert response.data['url'].startswith('/media/docs/')


@pytest.mark.django_db
def test_image_download_blocks_path_traversal(api_client, public_document):
    response = api_client.get(
        reverse('doc_image_download', args=[public_document.pk, '..\\evil']),
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_image_download_returns_404_when_file_missing(api_client, public_document):
    response = api_client.get(
        reverse('doc_image_download', args=[public_document.pk, 'nope.png']),
    )
    assert response.status_code == 404
