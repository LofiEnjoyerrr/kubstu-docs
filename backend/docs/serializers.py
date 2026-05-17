from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from docs.models import Document, DocumentAccess
from users.models import User


class GetDocumentSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    owner_id = serializers.ReadOnlyField(source='owner.id')

    class Meta:
        model = Document
        fields = (
            'id',
            'title',
            'content',
            'is_public',
            'owner',
            'owner_id',
            'dt_created',
            'dt_updated',
        )


class PostDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('title',)


class PatchDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('title', 'is_public')
        extra_kwargs = {
            'title': {'required': False},
            'is_public': {'required': False},
        }


class DocumentAccessSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.id')
    username = serializers.ReadOnlyField(source='user.username')
    first_name = serializers.ReadOnlyField(source='user.first_name')
    last_name = serializers.ReadOnlyField(source='user.last_name')
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    color = serializers.ReadOnlyField(source='user.color')

    class Meta:
        model = DocumentAccess
        fields = (
            'id',
            'user_id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'color',
            'role',
            'dt_created',
            'dt_updated',
        )


class PostDocumentAccessSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user')
    role = serializers.ChoiceField(choices=DocumentAccess.ROLE_CHOICES)

    def validate(self, attrs):
        document = self.context['document']
        user = attrs['user']

        if user == document.owner:
            raise ValidationError('Нельзя добавить доступ для владельца документа')

        if DocumentAccess.objects.filter(user=user, document=document).exists():
            raise ValidationError('Пользователь уже имеет доступ к этому документу')

        return attrs

    def create(self, validated_data):
        return DocumentAccess.objects.create(
            document=self.context['document'],
            **validated_data,
        )


class PatchDocumentAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentAccess
        fields = ('role',)


class MyAccessSerializer(serializers.Serializer):
    role = serializers.CharField()
