import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from coach import agent, skills


@pytest.fixture
def client_in(client, db):
    client.force_login(User.objects.create_user("karol", password="pw12345"))
    return client


def test_prompt_names_apex_and_still_slices_cleanly():
    assert agent.INSTRUCTIONS.startswith("You are Apex")
    assert agent.PROMPT_VERSION == "v2.0.0"
    assert skills.assemble_all() == agent.INSTRUCTIONS


def test_me_page_links_settings_usage_and_sign_out(client_in):
    content = client_in.get(reverse("me_page")).content.decode()
    for marker in ['href="/settings/"', 'href="/usage/"', 'data-theme-toggle', 'action="/accounts/logout/"']:
        assert marker in content


def test_nav_has_four_sections_plus_profile_and_brand(client_in):
    content = client_in.get(reverse("today_page")).content.decode()
    for marker in ['href="/coach/"', 'href="/calendar/"', 'href="/stats/"', 'href="/me/"', "Apex<span>Fit</span>", "in Warsaw"]:
        assert marker in content
    assert ">K<" in content   # avatar initial


def test_me_page_requires_login(client):
    assert client.get(reverse("me_page")).status_code == 302
