import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.fixture
def user(db):
    return User.objects.create_user(username="athlete", password="pw12345")


def test_chat_page_requires_login(client):
    resp = client.get(reverse("chat_page"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.url


@pytest.mark.django_db
def test_chat_page_renders_with_persistent_nav_and_no_dead_code(client, user):
    client.force_login(user)
    resp = client.get(reverse("chat_page"))
    assert resp.status_code == 200
    content = resp.content.decode()

    for marker in ['class="nav-link', 'href="/stats/"', 'href="/usage/"', 'href="/calendar/"']:
        assert marker in content, f"expected '{marker}' in rendered chat page"

    # dead code from the old single-page tab-switcher design must be gone
    for dead_marker in ['view-toggle', 'id="view-calendar"', 'id="cal-btn"', 'id="use-btn"']:
        assert dead_marker not in content, f"'{dead_marker}' should have been removed"
