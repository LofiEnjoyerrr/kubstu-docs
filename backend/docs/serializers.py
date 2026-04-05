from rest_framework import serializers
from .models import Document


class MeDocumentsSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'content',
            'type',
            'owner',
            'dt_created',
            'dt_updated',
        ]
