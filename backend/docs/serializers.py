from rest_framework import serializers
from docs.models import Document, DocumentAccess


class GetDocumentSerializer(serializers.ModelSerializer):

    class DocumentAccessSerializer(serializers.ModelSerializer):

        user = serializers.ReadOnlyField(source='user.username')
        user_id = serializers.ReadOnlyField(source='user.id')

        class Meta:
            model = DocumentAccess
            fields = (
                'user',
                'user_id',
                'role',
                'dt_created',
                'dt_updated',
            )

    owner = serializers.ReadOnlyField(source='owner.username')
    owner_id = serializers.ReadOnlyField(source='owner.id')
    accesses = DocumentAccessSerializer(many=True)

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
            'accesses',
        )


class PostDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Document
        fields = (
            'title',
        )
