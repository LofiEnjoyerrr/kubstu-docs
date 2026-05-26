from rest_framework import serializers

from users.models import User


class UserSerializer(serializers.ModelSerializer):
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
            'avatar',
            'color',
            'is_favorite',
        )

    def get_is_favorite(self, obj):
        favorite_user_ids = self.context.get('favorite_user_ids')
        if favorite_user_ids is None:
            return False
        return obj.id in favorite_user_ids
