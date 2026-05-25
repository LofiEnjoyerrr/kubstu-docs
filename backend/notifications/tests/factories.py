import factory

from notifications.models import PushSubscription
from users.tests.factories import UserFactory


class PushSubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PushSubscription

    user = factory.SubFactory(UserFactory)
    endpoint = factory.Sequence(lambda n: f'https://push.example.com/sub/{n}')
    p256dh = 'BLc4xRzKlKORKWlbdgFaBrrPK3yd1MWxRzRWaPLLcytpcg8wXxnxBfXBhgULBSeKkdsTQXmYqI60kVN_qaFfXgI'
    auth = 'tBHItJI5svbpez7KI4CCXg'
    user_agent = 'pytest'
