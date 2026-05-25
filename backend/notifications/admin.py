from django.contrib import admin

from notifications.models import (
    DocumentNotificationSettings,
    PushSubscription,
    UserNotificationSettings,
)


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


@admin.register(UserNotificationSettings)
class UserNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'edit_notifications_enabled', 'dt_updated')
    list_filter = ('edit_notifications_enabled',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('dt_created', 'dt_updated')


@admin.register(DocumentNotificationSettings)
class DocumentNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'document',
        'document_owner',
        'edit_notifications_enabled',
        'dt_updated',
    )
    list_filter = ('edit_notifications_enabled',)
    search_fields = ('document__title', 'document__owner__username', 'document__owner__email')
    readonly_fields = ('dt_created', 'dt_updated')

    @staticmethod
    @admin.display(description='Владелец')
    def document_owner(obj: DocumentNotificationSettings):
        return obj.document.owner
