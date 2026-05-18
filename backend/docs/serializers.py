from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from docs.models import Document, DocumentAccess, Comment
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
            'page_width',
            'page_height',
            'margin_top',
            'margin_right',
            'margin_bottom',
            'margin_left',
            'header_content',
            'footer_content',
            'show_page_numbers',
            'page_number_start',
            'dt_created',
            'dt_updated',
        )


class PostDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('title',)


class PatchDocumentSerializer(serializers.ModelSerializer):
    """
    Owner-only metadata patches. `content` is accepted here too — used by
    bulk operations (DOCX import) that need a synchronous HTTP save so a
    page reload right after the import cannot lose the new content.
    """

    class Meta:
        model = Document
        fields = (
            'title',
            'content',
            'is_public',
            'page_width',
            'page_height',
            'margin_top',
            'margin_right',
            'margin_bottom',
            'margin_left',
            'header_content',
            'footer_content',
            'show_page_numbers',
            'page_number_start',
        )
        extra_kwargs = {
            'title': {'required': False},
            'content': {'required': False},
            'is_public': {'required': False},
            'page_width': {'required': False},
            'page_height': {'required': False},
            'margin_top': {'required': False},
            'margin_right': {'required': False},
            'margin_bottom': {'required': False},
            'margin_left': {'required': False},
            'header_content': {'required': False},
            'footer_content': {'required': False},
            'show_page_numbers': {'required': False},
            'page_number_start': {'required': False},
        }

    def validate_page_width(self, v):
        if v < 320 or v > 2400:
            raise ValidationError('Ширина страницы должна быть от 320 до 2400 px')
        return v

    def validate_page_height(self, v):
        if v < 320 or v > 3600:
            raise ValidationError('Высота страницы должна быть от 320 до 3600 px')
        return v

    def validate_page_number_start(self, v):
        if v < 1 or v > 99999:
            raise ValidationError('Номер первой страницы должен быть от 1 до 99999')
        return v

    def _validate_margin(self, v):
        if v < 0 or v > 600:
            raise ValidationError('Отступ должен быть от 0 до 600 px')
        return v

    validate_margin_top = _validate_margin
    validate_margin_right = _validate_margin
    validate_margin_bottom = _validate_margin
    validate_margin_left = _validate_margin


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


class CommentSerializer(serializers.ModelSerializer):
    author_id = serializers.ReadOnlyField(source='author.id')
    author_username = serializers.ReadOnlyField(source='author.username')
    author_color = serializers.ReadOnlyField(source='author.color')
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)

    class Meta:
        model = Comment
        fields = (
            'id',
            'author_id',
            'author_username',
            'author_color',
            'author_avatar',
            'quote',
            'from_pos',
            'to_pos',
            'content',
            'dt_created',
        )


class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('quote', 'from_pos', 'to_pos', 'content')


class UpdateCommentSerializer(serializers.ModelSerializer):
    """Used to sync shrinking/moving ranges back from the editor."""
    class Meta:
        model = Comment
        fields = ('quote', 'from_pos', 'to_pos')
        extra_kwargs = {
            'quote': {'required': False},
            'from_pos': {'required': False},
            'to_pos': {'required': False},
        }
