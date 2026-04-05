from django.db.models import Q

from docs.models import Document


def get_user_documents(user):
    return Document.objects.filter(owner=user).distinct()


def get_document_by_id(doc_id):
    return Document.objects.get(id=doc_id)
