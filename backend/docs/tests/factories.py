import factory

from docs.models import Comment, Document, DocumentAccess
from users.tests.factories import UserFactory


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document

    title = factory.Sequence(lambda n: f'Document {n}')
    content = ''
    is_public = False
    owner = factory.SubFactory(UserFactory)


class DocumentAccessFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentAccess

    document = factory.SubFactory(DocumentFactory)
    user = factory.SubFactory(UserFactory)
    role = 'editor'


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    document = factory.SubFactory(DocumentFactory)
    author = factory.SubFactory(UserFactory)
    quote = 'sample quote'
    from_pos = 0
    to_pos = 10
    content = 'Sample comment text'
