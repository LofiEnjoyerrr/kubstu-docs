from users.models import User


def validate_credentials(credential_type, credential):
    if credential_type == 'username':
        return not User.objects.filter(username=credential).exists()

    return not User.objects.filter(email=credential).exists()
