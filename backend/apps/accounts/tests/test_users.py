import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_create_custom_user():
    user = User.objects.create_user(
        email='testuser@example.com',
        password='StrongPassword123!',
        first_name='John',
        last_name='Doe',
        phone='+255712345678'
    )
    assert user.email == 'testuser@example.com'
    assert user.check_password('StrongPassword123!')
    assert user.first_name == 'John'
    assert user.last_name == 'Doe'
    assert user.phone == '+255712345678'
    assert user.is_active is True
    assert user.is_staff is False
    assert user.full_name == 'John Doe'


@pytest.mark.django_db
def test_auth_login_and_me_endpoint():
    User.objects.create_user(
        email='operator@example.com',
        password='SecretPassword123!'
    )
    client = APIClient()

    # Login
    response = client.post('/api/v1/accounts/auth/login/', {
        'email': 'operator@example.com',
        'password': 'SecretPassword123!'
    }, format='json')

    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data
    assert response.data['user']['email'] == 'operator@example.com'

    # Unauthenticated access to /me/ denied
    response_unauth = client.get('/api/v1/accounts/auth/me/')
    assert response_unauth.status_code == 401
    assert response_unauth.data['code'] == 'UNAUTHENTICATED'

    # Authenticated access to /me/ succeeds
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    response_me = client.get('/api/v1/accounts/auth/me/')
    assert response_me.status_code == 200
    assert response_me.data['email'] == 'operator@example.com'
