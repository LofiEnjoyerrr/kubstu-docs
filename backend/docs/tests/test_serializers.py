import pytest

from docs.models import DocumentAccess
from docs.serializers import (
    PatchDocumentSerializer,
    PostDocumentAccessSerializer,
)
from docs.tests.factories import DocumentAccessFactory, DocumentFactory
from users.tests.factories import UserFactory


# ---------- PatchDocumentSerializer validation ----------

@pytest.mark.parametrize('value,ok', [
    (320, True),
    (2400, True),
    (319, False),
    (2401, False),
])
def test_patch_document_validate_page_width(value, ok):
    serializer = PatchDocumentSerializer(data={'page_width': value}, partial=True)
    assert serializer.is_valid() is ok


@pytest.mark.parametrize('value,ok', [
    (320, True),
    (3600, True),
    (319, False),
    (3601, False),
])
def test_patch_document_validate_page_height(value, ok):
    serializer = PatchDocumentSerializer(data={'page_height': value}, partial=True)
    assert serializer.is_valid() is ok


@pytest.mark.parametrize('value,ok', [
    (0, True),
    (300, True),
    (600, True),
    (-1, False),
    (601, False),
])
def test_patch_document_validate_margins(value, ok):
    serializer = PatchDocumentSerializer(
        data={'margin_top': value},
        partial=True,
    )
    assert serializer.is_valid() is ok


@pytest.mark.parametrize('value,ok', [
    (0, True),
    (1, True),
    (99999, True),
    (-1, False),
    (100000, False),
])
def test_patch_document_validate_page_number_start(value, ok):
    serializer = PatchDocumentSerializer(
        data={'page_number_start': value},
        partial=True,
    )
    assert serializer.is_valid() is ok


@pytest.mark.parametrize('value,ok', [
    ('Готово', True),
    ('', True),
    ('x' * 30, True),
    ('x' * 31, False),
])
def test_patch_document_validate_status_text(value, ok):
    serializer = PatchDocumentSerializer(data={'status_text': value}, partial=True)
    assert serializer.is_valid() is ok


@pytest.mark.parametrize('value,ok', [
    ('#16a34a', True),
    ('#ABCDEF', True),
    ('16a34a', False),
    ('#12345', False),
    ('#1234567', False),
    ('red', False),
])
def test_patch_document_validate_status_color(value, ok):
    serializer = PatchDocumentSerializer(data={'status_color': value}, partial=True)
    assert serializer.is_valid() is ok


# ---------- PostDocumentAccessSerializer ----------

@pytest.mark.django_db
def test_post_access_creates_row():
    doc = DocumentFactory()
    target = UserFactory()
    serializer = PostDocumentAccessSerializer(
        data={'user_id': target.id, 'role': 'editor'},
        context={'document': doc},
    )
    assert serializer.is_valid(), serializer.errors
    access = serializer.save()
    assert isinstance(access, DocumentAccess)
    assert access.user == target
    assert access.role == 'editor'


@pytest.mark.django_db
def test_post_access_rejects_owner():
    doc = DocumentFactory()
    serializer = PostDocumentAccessSerializer(
        data={'user_id': doc.owner.id, 'role': 'editor'},
        context={'document': doc},
    )
    assert not serializer.is_valid()


@pytest.mark.django_db
def test_post_access_rejects_duplicate():
    doc = DocumentFactory()
    target = UserFactory()
    DocumentAccessFactory(document=doc, user=target, role='viewer')

    serializer = PostDocumentAccessSerializer(
        data={'user_id': target.id, 'role': 'editor'},
        context={'document': doc},
    )
    assert not serializer.is_valid()


@pytest.mark.django_db
def test_post_access_rejects_unknown_role():
    doc = DocumentFactory()
    target = UserFactory()
    serializer = PostDocumentAccessSerializer(
        data={'user_id': target.id, 'role': 'admin'},
        context={'document': doc},
    )
    assert not serializer.is_valid()
