from .models import Document, DocumentAccess


def create_document(user, title):
    return Document.objects.create(
        title=title,
        owner=user
    )


def add_collaborator(document, user, role='editor'):
    return DocumentAccess.objects.update_or_create(
        document=document,
        user=user,
        defaults={'role': role}
    )


def can_view(user, document):
    return (
        user == document.owner or
        DocumentAccess.objects.filter(
            user=user,
            document=document
        ).exists()
    )


def can_edit(user, document):
    if user == document.owner:
        return True

    return DocumentAccess.objects.filter(
        user=user,
        document=document,
        role='editor'
    ).exists()


def update_document_content(document, content):
    document.content = content
    document.save(update_fields=['content'])
    return document
