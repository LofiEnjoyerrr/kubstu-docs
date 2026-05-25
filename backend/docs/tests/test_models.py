import pytest
from django.db import IntegrityError

from docs.tests.factories import (
    CommentFactory,
    DocumentAccessFactory,
    DocumentFactory,
)
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_document_defaults_are_applied():
    doc = DocumentFactory()
    assert doc.is_public is False
    assert doc.version == 0
    assert doc.page_width == 816
    assert doc.page_height == 1056
    assert doc.margin_top == 96
    assert doc.show_page_numbers is False
    assert doc.page_number_start == 1


@pytest.mark.django_db
def test_document_str_uses_title():
    doc = DocumentFactory(title='My report')
    assert str(doc) == 'My report'


@pytest.mark.django_db
def test_document_access_unique_user_document_constraint():
    doc = DocumentFactory()
    user = UserFactory()
    DocumentAccessFactory(document=doc, user=user, role='editor')
    with pytest.raises(IntegrityError):
        DocumentAccessFactory(document=doc, user=user, role='viewer')


@pytest.mark.django_db
def test_comment_str_format():
    comment = CommentFactory()
    expected = f'Comment by {comment.author} on {comment.document}'
    assert str(comment) == expected


@pytest.mark.django_db
def test_comments_default_ordering_is_chronological():
    doc = DocumentFactory()
    first = CommentFactory(document=doc)
    second = CommentFactory(document=doc)
    third = CommentFactory(document=doc)

    ordered_ids = list(doc.comments.values_list('id', flat=True))
    assert ordered_ids == [first.id, second.id, third.id]
