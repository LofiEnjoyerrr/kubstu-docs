from rest_framework import serializers
from docs.models import Document, DocumentAccess


class GetDocumentSerializer(serializers.ModelSerializer):

    owner = serializers.ReadOnlyField(source='owner.username')
    owner_id = serializers.ReadOnlyField(source='owner.id')

    class Meta:
        model = Document
        fields = (
            'id',
            'title',
            'content',
            'owner',
            'owner_id',
            'dt_created',
            'dt_updated',
        )


class PostDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Document
        fields = (
            'title',
        )
