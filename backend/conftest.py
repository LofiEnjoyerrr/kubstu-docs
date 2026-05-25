"""
Top-level pytest fixtures shared across all backend apps.

Anything per-app (e.g. domain factories) lives next to that app's tests.
"""

import pytest
from rest_framework.test import APIClient

from docs.tests.factories import (
    CommentFactory,
    DocumentAccessFactory,
    DocumentFactory,
)
from users.tests.factories import UserFactory


@pytest.fixture
def api_client() -> APIClient:
    """An unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user) -> APIClient:
    """API client logged in as ``user`` via Django session auth."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_auth_client(other_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client


@pytest.fixture
def document(user):
    return DocumentFactory(owner=user)


@pytest.fixture
def public_document(user):
    return DocumentFactory(owner=user, is_public=True)


@pytest.fixture
def document_access(document, other_user):
    """``other_user`` has editor access to ``document`` owned by ``user``."""
    return DocumentAccessFactory(document=document, user=other_user, role='editor')


@pytest.fixture
def viewer_access(document, other_user):
    return DocumentAccessFactory(document=document, user=other_user, role='viewer')


@pytest.fixture
def comment(document, user):
    return CommentFactory(document=document, author=user)
