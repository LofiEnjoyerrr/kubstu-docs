from datetime import timedelta

import pytest
from django.utils import timezone

from users.constants import (
    EMAIL_VERIFY_REQUEST_LIFETIME,
    EMAIL_VERIFY_TOKEN_LENGTH,
    MAX_REGISTRATION_ATTEMPTS_PER_WEEK,
    PASSWORD_RESET_REQUEST_LIFETIME,
    PASSWORD_RESET_TOKEN_LENGTH,
)
from users.models import PasswordResetRequest, RegisterRequest, User
from users.serializers.request import (
    EmailVerifySerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserUpdateSerializer,
)
from users.tests.factories import (
    PasswordResetRequestFactory,
    RegisterRequestFactory,
    UserFactory,
)


# ---------- LoginSerializer ----------

@pytest.mark.django_db
def test_login_with_username_succeeds():
    user = UserFactory(username='alice')
    user.set_password('s3cret!!')
    user.save()

    serializer = LoginSerializer(data={'username': 'alice', 'password': 's3cret!!'})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['user'] == user


@pytest.mark.django_db
def test_login_with_email_resolves_to_username():
    user = UserFactory(username='alice', email='alice@example.com')
    user.set_password('s3cret!!')
    user.save()

    serializer = LoginSerializer(
        data={'username': 'alice@example.com', 'password': 's3cret!!'},
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['user'] == user


@pytest.mark.django_db
def test_login_with_wrong_password_fails():
    user = UserFactory(username='alice')
    user.set_password('s3cret!!')
    user.save()

    serializer = LoginSerializer(data={'username': 'alice', 'password': 'wrong'})
    assert not serializer.is_valid()


@pytest.mark.django_db
def test_login_with_unknown_email_fails_cleanly():
    serializer = LoginSerializer(
        data={'username': 'ghost@example.com', 'password': 's3cret!!'},
    )
    assert not serializer.is_valid()


# ---------- RegisterSerializer ----------

@pytest.mark.django_db
def test_register_serializer_creates_request_and_dispatches_email(mocker):
    send = mocker.patch('users.models.send_email_verify.delay')

    data = {
        'email': 'new@example.com',
        'password': 'long-enough-pwd',
        'ip': '127.0.0.1',
    }
    serializer = RegisterSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    req = serializer.save()

    assert isinstance(req, RegisterRequest)
    assert req.email == 'new@example.com'
    # Username was generated from the local-part.
    assert req.username.startswith('new_')
    # Password is hashed before being persisted to the request row.
    assert req.password != 'long-enough-pwd'
    send.assert_called_once_with(req.email, req.token)


@pytest.mark.django_db
def test_register_rejects_short_password(mocker):
    mocker.patch('users.models.send_email_verify.delay')
    data = {
        'email': 'short@example.com',
        'password': 'short',
        'ip': '127.0.0.1',
    }
    serializer = RegisterSerializer(data=data)
    assert not serializer.is_valid()
    assert 'password' in serializer.errors


@pytest.mark.django_db
def test_register_blocks_after_too_many_attempts_from_same_ip(mocker):
    mocker.patch('users.models.send_email_verify.delay')
    email = 'spam@example.com'
    for _ in range(MAX_REGISTRATION_ATTEMPTS_PER_WEEK):
        RegisterRequestFactory(email=email, ip='127.0.0.1')

    serializer = RegisterSerializer(data={
        'email': email,
        'password': 'long-enough-pwd',
        'ip': '127.0.0.1',
    })
    assert not serializer.is_valid()


# ---------- EmailVerifySerializer ----------

@pytest.mark.django_db
def test_email_verify_creates_user_and_closes_request():
    register_request = RegisterRequestFactory(
        email='ready@example.com',
        username='ready_user',
    )
    serializer = EmailVerifySerializer(data={'token': register_request.token})
    assert serializer.is_valid(), serializer.errors

    user = serializer.save()
    assert User.objects.filter(email='ready@example.com').exists()
    assert user.username == 'ready_user'

    register_request.refresh_from_db()
    assert register_request.status == RegisterRequest.RegisterRequestStatus.COMPLETE


@pytest.mark.django_db
def test_email_verify_rejects_unknown_token():
    serializer = EmailVerifySerializer(data={'token': 'x' * EMAIL_VERIFY_TOKEN_LENGTH})
    assert not serializer.is_valid()


@pytest.mark.django_db
def test_email_verify_rejects_expired_token():
    req = RegisterRequestFactory()
    # Push the row past the lifetime cutoff.
    stale = timezone.now() - timedelta(minutes=EMAIL_VERIFY_REQUEST_LIFETIME + 1)
    RegisterRequest.objects.filter(pk=req.pk).update(dt_created=stale)

    serializer = EmailVerifySerializer(data={'token': req.token})
    assert not serializer.is_valid()


# ---------- UserUpdateSerializer ----------

@pytest.mark.django_db
def test_user_update_username_clash_is_rejected():
    me = UserFactory(username='me')
    UserFactory(username='taken')

    serializer = UserUpdateSerializer(me, data={'username': 'taken'}, partial=True)
    assert not serializer.is_valid()
    assert 'username' in serializer.errors


@pytest.mark.django_db
def test_user_update_can_keep_own_username():
    me = UserFactory(username='me')
    serializer = UserUpdateSerializer(me, data={'username': 'me'}, partial=True)
    assert serializer.is_valid(), serializer.errors


# ---------- PasswordResetRequestSerializer ----------

@pytest.mark.django_db
def test_password_reset_request_creates_row_and_sends_email(mocker):
    send = mocker.patch('users.models.send_password_reset_email.delay')
    user = UserFactory(email='who@example.com')

    serializer = PasswordResetRequestSerializer(data={'email': 'who@example.com'})
    assert serializer.is_valid(), serializer.errors
    reset = serializer.save()

    assert isinstance(reset, PasswordResetRequest)
    assert reset.user == user
    send.assert_called_once_with('who@example.com', reset.token)


@pytest.mark.django_db
def test_password_reset_request_unknown_email_does_not_error(mocker):
    """
    The endpoint deliberately doesn't leak whether an email is registered —
    ``create()`` returns ``None`` for unknown emails so no row is written
    and no email is dispatched.

    NOTE: we call ``create()`` directly instead of ``save()`` because DRF's
    ``Serializer.save()`` asserts the return value is not None. The view
    itself is affected by that assertion — see test_views for the related
    xfail.
    """
    send = mocker.patch('users.models.send_password_reset_email.delay')

    serializer = PasswordResetRequestSerializer(data={'email': 'ghost@example.com'})
    assert serializer.is_valid(), serializer.errors

    result = serializer.create(serializer.validated_data)

    assert result is None
    assert not PasswordResetRequest.objects.exists()
    send.assert_not_called()


# ---------- PasswordResetConfirmSerializer ----------

@pytest.mark.django_db
def test_password_reset_confirm_changes_password_and_marks_request_complete():
    user = UserFactory()
    user.set_password('old-pass-aa')
    user.save()
    req = PasswordResetRequestFactory(user=user)

    serializer = PasswordResetConfirmSerializer(data={
        'token': req.token,
        'password': 'brand-new-pass',
    })
    assert serializer.is_valid(), serializer.errors
    serializer.save()

    user.refresh_from_db()
    assert user.check_password('brand-new-pass')

    req.refresh_from_db()
    assert req.status == PasswordResetRequest.PasswordResetRequestStatus.COMPLETE


@pytest.mark.django_db
def test_password_reset_confirm_invalidates_other_pending_requests():
    user = UserFactory()
    pending = PasswordResetRequestFactory(user=user)
    used = PasswordResetRequestFactory(user=user)

    serializer = PasswordResetConfirmSerializer(data={
        'token': used.token,
        'password': 'brand-new-pass',
    })
    assert serializer.is_valid(), serializer.errors
    serializer.save()

    pending.refresh_from_db()
    assert pending.status == PasswordResetRequest.PasswordResetRequestStatus.EXPIRED


@pytest.mark.django_db
def test_password_reset_confirm_rejects_unknown_token():
    serializer = PasswordResetConfirmSerializer(data={
        'token': 'x' * PASSWORD_RESET_TOKEN_LENGTH,
        'password': 'brand-new-pass',
    })
    assert not serializer.is_valid()


@pytest.mark.django_db
def test_password_reset_confirm_rejects_expired_token():
    req = PasswordResetRequestFactory()
    stale = timezone.now() - timedelta(minutes=PASSWORD_RESET_REQUEST_LIFETIME + 1)
    PasswordResetRequest.objects.filter(pk=req.pk).update(dt_created=stale)

    serializer = PasswordResetConfirmSerializer(data={
        'token': req.token,
        'password': 'brand-new-pass',
    })
    assert not serializer.is_valid()
