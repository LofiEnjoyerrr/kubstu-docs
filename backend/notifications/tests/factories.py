import factory

from docs.tests.factories import DocumentFactory
from notifications.models import (
    DocumentNotificationSettings,
    PushSubscription,
    UserNotificationSettings,
)
from users.tests.factories import UserFactory


class PushSubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PushSubscription

    user = factory.SubFactory(UserFactory)
    endpoint = factory.Sequence(lambda n: f'https://push.example.com/sub/{n}')
    p256dh = 'BLc4xRzKlKORKWlbdgFaBrrPK3yd1MWxRzRWaPLLcytpcg8wXxnxBfXBhgULBSeKkdsTQXmYqI60kVN_qaFfXgI'
    auth = 'tBHItJI5svbpez7KI4CCXg'
    user_agent = 'pytest'


class UserNotificationSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserNotificationSettings

    user = factory.SubFactory(UserFactory)
    edit_notifications_enabled = True


class DocumentNotificationSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentNotificationSettings

    document = factory.SubFactory(DocumentFactory)
    edit_notifications_enabled = True
    use_global_default = False
