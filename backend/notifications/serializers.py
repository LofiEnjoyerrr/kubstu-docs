from rest_framework import serializers

from notifications.models import PushSubscription


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
