import pytest

from docs.selectors import (
    get_available_documents,
    get_available_documents_sorted,
    get_user_documents,
    get_user_opened_documents,
)
from docs.tests.factories import DocumentAccessFactory, DocumentFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_get_user_documents_returns_only_owned():
    alice = UserFactory()
    bob = UserFactory()
    alice_doc = DocumentFactory(owner=alice)
    DocumentFactory(owner=bob)

    qs = get_user_documents(alice)
    assert list(qs) == [alice_doc]


@pytest.mark.django_db
def test_get_user_opened_documents_returns_shared():
    alice = UserFactory()
    bob = UserFactory()
    shared = DocumentFactory(owner=alice)
    DocumentAccessFactory(document=shared, user=bob, role='viewer')

    # Bob does not own anything.
    assert list(get_user_documents(bob)) == []
    # But sees what was shared with him.
    assert list(get_user_opened_documents(bob)) == [shared]


@pytest.mark.django_db
def test_get_available_documents_is_union():
    alice = UserFactory()
    bob = UserFactory()
    bob_owned = DocumentFactory(owner=bob)
    bob_shared = DocumentFactory(owner=alice)
    DocumentAccessFactory(document=bob_shared, user=bob, role='editor')

    available = set(get_available_documents(bob))
    assert available == {bob_owned, bob_shared}


@pytest.mark.django_db
def test_get_available_documents_does_not_duplicate():
    """If a user has both an access row AND is the owner, the doc shows once."""
    user = UserFactory()
    doc = DocumentFactory(owner=user)
    # Pathological case — shouldn't normally happen, but distinct() must hold.
    DocumentAccessFactory(document=doc, user=user, role='editor')

    assert list(get_available_documents(user)) == [doc]


@pytest.mark.django_db
def test_get_available_documents_sorted_puts_owned_first():
    alice = UserFactory()
    bob = UserFactory()
    shared = DocumentFactory(owner=bob)
    DocumentAccessFactory(document=shared, user=alice, role='editor')
    own = DocumentFactory(owner=alice)

    sorted_docs = list(get_available_documents_sorted(alice))
    assert sorted_docs[0] == own
    assert sorted_docs[1] == shared
