import time

import pytest

from docs.tests.factories import DocumentFactory


@pytest.mark.django_db
def test_auto_date_mixin_populates_dt_created_and_updated():
    doc = DocumentFactory()
    assert doc.dt_created is not None
    assert doc.dt_updated is not None


@pytest.mark.django_db
def test_auto_date_mixin_updates_dt_updated_on_save():
    doc = DocumentFactory()
    original_created = doc.dt_created
    original_updated = doc.dt_updated

    time.sleep(0.01)
    doc.title = 'changed'
    doc.save()
    doc.refresh_from_db()

    assert doc.dt_created == original_created
    assert doc.dt_updated > original_updated
