from django.contrib import admin
from django.contrib.admin import register

from users.models import FavoriteUser, User


@register(User)
class UserAdmin(admin.ModelAdmin):

    class Meta:
        model = User
        fields = (
            'username',
        )


@register(FavoriteUser)
class FavoriteUserAdmin(admin.ModelAdmin):
    list_display = ('owner', 'user', 'dt_created')
    search_fields = ('owner__username', 'owner__email', 'user__username', 'user__email')
