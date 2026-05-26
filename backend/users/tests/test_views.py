import pytest
from django.urls import reverse

from users.models import FavoriteUser, PasswordResetRequest, RegisterRequest, User
from users.tests.factories import (
    PasswordResetRequestFactory,
    RegisterRequestFactory,
    UserFactory,
)


# ---------- Login / Logout ----------

@pytest.mark.django_db
def test_login_creates_session(api_client):
    user = UserFactory(username='alice')
    user.set_password('s3cret!!')
    user.save()

    response = api_client.post(
        reverse('users_login'),
        {'username': 'alice', 'password': 's3cret!!'},
        format='json',
    )
    assert response.status_code == 200
    # Session auth: a sessionid cookie should now be present.
    assert '_auth_user_id' in api_client.session


@pytest.mark.django_db
def test_login_wrong_password_returns_400(api_client):
    user = UserFactory(username='alice')
    user.set_password('s3cret!!')
    user.save()

    response = api_client.post(
        reverse('users_login'),
        {'username': 'alice', 'password': 'nope'},
        format='json',
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_logout_requires_authentication(api_client):
    response = api_client.post(reverse('users_logout'))
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_logout_clears_session(auth_client):
    response = auth_client.post(reverse('users_logout'))
    assert response.status_code == 200


# ---------- Credentials available ----------

@pytest.mark.django_db
def test_username_available_when_free(api_client):
    response = api_client.get(
        reverse('users_credential_username_available', args=['free']),
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_username_available_returns_400_when_taken(api_client):
    UserFactory(username='taken')
    response = api_client.get(
        reverse('users_credential_username_available', args=['taken']),
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_email_available_returns_400_when_taken(api_client):
    UserFactory(email='taken@example.com')
    response = api_client.get(
        reverse('users_credential_email_available', args=['taken@example.com']),
    )
    assert response.status_code == 400


# ---------- Register ----------

@pytest.mark.django_db
def test_register_creates_request_and_returns_201(api_client, mocker):
    mocker.patch('users.models.send_email_verify.delay')

    response = api_client.post(
        reverse('users_register'),
        {'email': 'new@example.com', 'password': 'long-enough-pwd'},
        format='json',
    )
    assert response.status_code == 201
    assert RegisterRequest.objects.filter(email='new@example.com').exists()


@pytest.mark.django_db
def test_register_uses_client_ip_from_xff(api_client, mocker):
    mocker.patch('users.models.send_email_verify.delay')

    response = api_client.post(
        reverse('users_register'),
        {'email': 'ip@example.com', 'password': 'long-enough-pwd'},
        format='json',
        HTTP_X_FORWARDED_FOR='203.0.113.5',
    )
    assert response.status_code == 201
    req = RegisterRequest.objects.get(email='ip@example.com')
    assert req.ip == '203.0.113.5'


# ---------- Email verify ----------

@pytest.mark.django_db
def test_email_verify_creates_user_and_logs_in(api_client):
    req = RegisterRequestFactory(email='ok@example.com', username='ok_user')

    response = api_client.get(reverse('users_email_verify', args=[req.token]))
    assert response.status_code == 200
    assert User.objects.filter(email='ok@example.com').exists()


@pytest.mark.django_db
def test_email_verify_bad_token_returns_400(api_client):
    response = api_client.get(reverse('users_email_verify', args=['z' * 64]))
    assert response.status_code == 400


# ---------- Me ----------

@pytest.mark.django_db
def test_me_requires_auth(api_client):
    response = api_client.get(reverse('users_me'))
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_me_returns_current_user(auth_client, user):
    response = auth_client.get(reverse('users_me'))
    assert response.status_code == 200
    assert response.data['username'] == user.username
    assert response.data['email'] == user.email


@pytest.mark.django_db
def test_me_patch_updates_first_name(auth_client, user):
    response = auth_client.patch(
        reverse('users_me'),
        {'first_name': 'New'},
        format='json',
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == 'New'


# ---------- Search ----------

@pytest.mark.django_db
def test_search_excludes_self_and_returns_matches(auth_client, user):
    UserFactory(username='alice')
    UserFactory(username='alice_bob')
    UserFactory(username='charlie')

    response = auth_client.get(reverse('users_search'), {'q': 'alice'})
    assert response.status_code == 200
    usernames = {u['username'] for u in response.data}
    assert usernames == {'alice', 'alice_bob'}
    assert user.username not in usernames


@pytest.mark.django_db
def test_search_matches_email_and_marks_favorites(auth_client, user):
    favorite = UserFactory(username='favorite_user', email='shared@example.com')
    UserFactory(username='other_user', email='shared-other@example.com')
    FavoriteUser.objects.create(owner=user, user=favorite)

    response = auth_client.get(reverse('users_search'), {'q': 'shared'})

    assert response.status_code == 200
    by_username = {u['username']: u for u in response.data}
    assert by_username['favorite_user']['is_favorite'] is True
    assert by_username['other_user']['is_favorite'] is False


@pytest.mark.django_db
def test_search_requires_auth(api_client):
    response = api_client.get(reverse('users_search'), {'q': 'alice'})
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_search_validates_empty_query(auth_client):
    response = auth_client.get(reverse('users_search'), {'q': ''})
    assert response.status_code == 400


@pytest.mark.django_db
def test_favorites_add_list_search_and_delete(auth_client, user):
    first = UserFactory(username='alpha', email='alpha@example.com')
    second = UserFactory(username='beta', email='beta@example.com')

    response = auth_client.post(reverse('users_favorites'), {'user_id': first.id}, format='json')
    assert response.status_code == 201
    assert response.data['is_favorite'] is True

    auth_client.post(reverse('users_favorites'), {'user_id': second.id}, format='json')

    response = auth_client.get(reverse('users_favorites'), {'page': 1, 'page_size': 1})
    assert response.status_code == 200
    assert response.data['count'] == 2
    assert response.data['total_pages'] == 2
    assert len(response.data['results']) == 1

    response = auth_client.get(reverse('users_favorites'), {'q': 'beta@example.com'})
    assert response.status_code == 200
    assert [u['username'] for u in response.data['results']] == ['beta']

    response = auth_client.delete(reverse('users_favorite_detail', args=[first.id]))
    assert response.status_code == 204
    assert not FavoriteUser.objects.filter(owner=user, user=first).exists()


@pytest.mark.django_db
def test_favorites_reject_self(auth_client, user):
    response = auth_client.post(reverse('users_favorites'), {'user_id': user.id}, format='json')

    assert response.status_code == 400


# ---------- Password reset ----------


@pytest.mark.django_db
def test_password_reset_creates_request_for_known_email(api_client, mocker):
    send = mocker.patch('users.models.send_password_reset_email.delay')
    UserFactory(email='known@example.com')

    response = api_client.post(
        reverse('users_password_reset'),
        {'email': 'known@example.com'},
        format='json',
    )
    assert response.status_code == 200
    assert PasswordResetRequest.objects.filter(user__email='known@example.com').exists()
    send.assert_called_once()


@pytest.mark.django_db
def test_password_reset_confirm_updates_password(api_client):
    user = UserFactory()
    user.set_password('old-pass-aa')
    user.save()
    req = PasswordResetRequestFactory(user=user)

    response = api_client.post(
        reverse('users_password_reset_confirm'),
        {'token': req.token, 'password': 'brand-new-pass'},
        format='json',
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password('brand-new-pass')
