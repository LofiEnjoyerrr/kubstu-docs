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

    class DocumentAccessSerializer(serializers.ModelSerializer):

        class Meta:
            model = DocumentAccess
            fields = (
                'user',
                'role',
                'dt_created',
                'dt_updated',
            )

    accesses = DocumentAccessSerializer(many=True, required=False)

    class Meta:
        model = Document
        fields = (
            'title',
            'accesses',
        )

    def create(self, validated_data):
        accesses_data = validated_data.pop('accesses', [])
        document = Document.objects.create(**validated_data)
        for access_data in accesses_data:
            DocumentAccess.objects.create(document=document, **access_data)
        return document

    def update(self, instance, validated_data):
        accesses_data = validated_data.pop('accesses', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # обновление access (пример: просто удалить старые и создать новые)
        instance.accesses.all().delete()
        for access_data in accesses_data:
            DocumentAccess.objects.create(document=instance, **access_data)

        return instance
