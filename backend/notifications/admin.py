from django.contrib import admin

from notifications.models import PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'short_endpoint', 'user_agent', 'dt_created')
    list_filter = ('dt_created',)
    search_fields = ('user__username', 'user__email', 'endpoint')
    readonly_fields = ('dt_created', 'dt_updated')

    @staticmethod
    @admin.display(description='Endpoint')
    def short_endpoint(obj: PushSubscription) -> str:
        return obj.endpoint[:80] + ('…' if len(obj.endpoint) > 80 else '')
