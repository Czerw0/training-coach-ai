import json
from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.auth.models import User

from coach import agent, profile_changes, prompts
from coach.context import build_context
from coach.models import CoachPrompt, ProfileChange
from sync.models import UserProfile


@pytest.fixture
def user(db):
    return User.objects.create_user("c", password="pw12345")


@pytest.fixture
def user_client(client, user):
    client.force_login(user)
    return client


def _save(client, **fields):
    body = {"primary_sport": "running", "injury_history": "", "athlete_notes": "", **fields}
    return client.post("/settings/profile/", data=json.dumps(body), content_type="application/json").json()


def test_text_diff_keeps_order_and_ignores_whitespace():
    added, removed = profile_changes.text_diff("a\nb\nc", "a\n  b  \nB2\n\nd")
    assert added == ["B2", "d"] and removed == ["c"]
    assert profile_changes.text_diff("x\n", " x") == ([], [])


@pytest.mark.django_db
def test_saving_profile_records_only_what_changed(user_client, user):
    UserProfile.objects.create(pk=1, athlete_notes="BACKGROUND\nBased in Warsaw", ftp_watts=250, primary_sport="running")
    assert _save(user_client, athlete_notes="BACKGROUND\nBased in Innsbruck\nNo bike here", ftp_watts=250)["ok"]
    rows = {r.field: r for r in ProfileChange.objects.all()}
    assert set(rows) == {"athlete_notes"}                      # ftp and sport unchanged
    assert rows["athlete_notes"].added == "Based in Innsbruck\nNo bike here"
    assert rows["athlete_notes"].removed == "Based in Warsaw"
    assert rows["athlete_notes"].user == user


@pytest.mark.django_db
def test_value_fields_record_old_and_new(user_client):
    UserProfile.objects.create(pk=1, ftp_watts=250, primary_sport="running")
    _save(user_client, ftp_watts=262)
    r = ProfileChange.objects.get(field="ftp_watts")
    assert (r.removed, r.added) == ("250", "262")


@pytest.mark.django_db
def test_prompt_save_logs_the_instruction_diff_and_based_on(user):
    custom = agent.INSTRUCTIONS.replace("ONE run per week", "TWO runs per week") + "\nNo bike in Innsbruck."
    row, _ = prompts.save_version(user, custom)
    assert row.based_on == agent.PROMPT_VERSION
    change = ProfileChange.objects.get(field="coach_instructions")
    assert "No bike in Innsbruck." in change.added


@pytest.mark.django_db
def test_context_lists_recent_changes_newest_first():
    ProfileChange.objects.create(field="athlete_notes", added="old")
    ProfileChange.objects.create(field="athlete_notes", added="x" * 5000)
    changes = build_context()["recent_profile_changes"]
    assert changes[0]["added"].endswith("…[cut]") and len(changes[0]["added"]) < 1600
    assert changes[1]["added"] == "old"


@pytest.mark.django_db
def test_data_block_carries_the_prompt_version(user):
    prompts.save_version(user, "Mine.")
    reply = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="ok")],
                            usage=SimpleNamespace(input_tokens=1, output_tokens=1, cache_creation_input_tokens=0, cache_read_input_tokens=0))
    with mock.patch.object(agent.client.messages, "create", return_value=reply) as m:
        agent.chat("(test) which version?", user=user)
    data = m.call_args.kwargs["system"][1]["text"]
    assert f'"coach_instructions_version":"u{user.id}/v1@' in data


def test_default_prompt_has_the_replan_rules():
    assert "recent_profile_changes" in agent.INSTRUCTIONS
    assert "coach_instructions_version" in agent.INSTRUCTIONS
    assert "overrides anything said earlier" in agent.INSTRUCTIONS


@pytest.mark.django_db
def test_settings_flags_a_custom_prompt_made_on_an_older_default(user):
    CoachPrompt.objects.create(user=user, version=1, text="Old custom rules.", based_on="v1.7.0")
    s = prompts.summary(user)
    assert s["default_updated"] and s["based_on"] == "v1.7.0"
    assert "=== CONTINUITY ===" in s["missing_default_lines"]
    CoachPrompt.objects.create(user=user, version=2, text="Fresh.", based_on=agent.PROMPT_VERSION)
    assert prompts.summary(user)["default_updated"] is False
