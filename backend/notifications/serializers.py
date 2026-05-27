from rest_framework import serializers

from notifications.models import (
    DocumentNotificationSettings,
    PushSubscription,
    UserNotificationSettings,
)


class PushSubscriptionSerializer(serializers.Serializer):
    """
    Mirrors the shape of ``PushSubscription.toJSON()`` from the browser:

        {
          "endpoint": "...",
          "keys": { "p256dh": "...", "auth": "..." }
        }
    """

    endpoint = serializers.URLField(max_length=2048)
    keys = serializers.DictField(child=serializers.CharField())

    def validate_keys(self, value: dict) -> dict:
        missing = {'p256dh', 'auth'} - value.keys()
        if missing:
            raise serializers.ValidationError(
                f'Не хватает ключей: {", ".join(sorted(missing))}',
            )
        return value

    def create(self, validated_data: dict) -> PushSubscription:
        user = self.context['request'].user
        keys = validated_data['keys']
        ua = self.context['request'].META.get('HTTP_USER_AGENT', '')[:512]
        sub, _ = PushSubscription.objects.update_or_create(
            endpoint=validated_data['endpoint'],
            defaults={
                'user': user,
                'p256dh': keys['p256dh'],
                'auth': keys['auth'],
                'user_agent': ua,
            },
        )
        return sub


class PushUnsubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2048)


class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationSettings
        fields = ('edit_notifications_enabled',)


class DocumentNotificationSettingsSerializer(serializers.ModelSerializer):
    document_id = serializers.ReadOnlyField(source='document.id')
    use_global_default = serializers.BooleanField(read_only=True)
    global_edit_notifications_enabled = serializers.SerializerMethodField()

    class Meta:
        model = DocumentNotificationSettings
        fields = (
            'document_id',
            'edit_notifications_enabled',
            'use_global_default',
            'global_edit_notifications_enabled',
        )

    def get_global_edit_notifications_enabled(self, obj):
        settings = UserNotificationSettings.objects.filter(user=obj.document.owner).first()
        if settings is None:
            return True
        return settings.edit_notifications_enabled

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.use_global_default:
            data['edit_notifications_enabled'] = data['global_edit_notifications_enabled']
        return data

    def update(self, instance, validated_data):
        if 'edit_notifications_enabled' in validated_data:
            instance.use_global_default = False
        return super().update(instance, validated_data)
