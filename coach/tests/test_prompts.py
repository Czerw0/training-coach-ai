import importlib
from types import SimpleNamespace
from unittest import mock

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import AnonymousUser, User

from coach import agent, prompts, skills
from coach.models import ApiUsage, CoachPrompt

split_migration = importlib.import_module("coach.migrations.0025_split_athlete_section")


@pytest.fixture
def user(db):
    return User.objects.create_user("p", password="pw12345")


@pytest.fixture
def user_client(client, user):
    client.force_login(user)
    return client


def _reply(text="ok"):
    return SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=0),
    )


# --- resolution ----------------------------------------------------------------------

def test_no_user_or_anonymous_gets_the_default(db):
    assert prompts.active_prompt(None) == (agent.INSTRUCTIONS, agent.PROMPT_TAG)
    assert prompts.active_prompt(AnonymousUser()) == (agent.INSTRUCTIONS, agent.PROMPT_TAG)


def test_users_section_is_appended_never_replaces_the_default(user):
    prompts.save_version(user, "Skiing is my main goal.")
    text, tag = prompts.active_prompt(user)
    assert text.startswith(agent.INSTRUCTIONS)
    assert text.endswith("=== THIS ATHLETE ===\nWritten by the athlete. It refines everything above for them; the safety rules,\n"
                         "athlete_rules and NEVER FAKE ACTIONS still apply.\n\nSkiing is my main goal.")
    assert tag == f"{agent.PROMPT_TAG}+u{user.id}/v1@{prompts.text_hash('Skiing is my main goal.')}"


def test_sections_are_per_user(user):
    other = User.objects.create_user("q", password="pw12345")
    prompts.save_version(user, "Mine.")
    assert prompts.active_prompt(other) == (agent.INSTRUCTIONS, agent.PROMPT_TAG)


def test_removing_the_section_appends_an_empty_version_and_keeps_history(user):
    prompts.save_version(user, "A")
    row, created = prompts.save_version(user, "")
    assert created and row.version == 2 and row.text == ""
    assert prompts.active_prompt(user) == (agent.INSTRUCTIONS, agent.PROMPT_TAG)
    assert CoachPrompt.objects.filter(user=user).count() == 2


def test_unchanged_text_is_a_noop_and_whitespace_is_normalised(user):
    prompts.save_version(user, "X\r\n")
    assert prompts.save_version(user, "  X ")[1] is False
    assert prompts.save_version(user, "")[1] is True
    assert prompts.save_version(user, "")[1] is False


# --- chat() uses it ---------------------------------------------------------------------

@pytest.mark.django_db
def test_chat_sends_default_plus_section_and_logs_the_combined_tag(user):
    prompts.save_version(user, "Custom coach rules.")
    with mock.patch.object(agent.client.messages, "create", return_value=_reply()) as m:
        agent.chat("(test) hi", user=user)
    sent = m.call_args.kwargs["system"][0]["text"]
    assert sent.startswith(agent.INSTRUCTIONS) and sent.endswith("Custom coach rules.")
    assert ApiUsage.objects.get().prompt_version.startswith(f"{agent.PROMPT_TAG}+u{user.id}/v1@")


@pytest.mark.django_db
def test_chat_without_user_is_the_default():
    with mock.patch.object(agent.client.messages, "create", return_value=_reply()) as m:
        agent.chat("(test) hi")
    assert m.call_args.kwargs["system"][0]["text"] == agent.INSTRUCTIONS
    assert ApiUsage.objects.get().prompt_version == agent.PROMPT_TAG


@pytest.mark.django_db
def test_explicit_prompt_overrides_user(user):
    prompts.save_version(user, "Mine.")
    with mock.patch.object(agent.client.messages, "create", return_value=_reply()) as m:
        agent.chat("(test) hi", user=user, prompt=("Eval prompt.", "eval@1"))
    assert m.call_args.kwargs["system"][0]["text"] == "Eval prompt."
    assert ApiUsage.objects.get().prompt_version == "eval@1"


@pytest.mark.django_db
def test_chat_view_passes_the_logged_in_user(user_client, user):
    prompts.save_version(user, "View prompt.")
    with mock.patch.object(agent.client.messages, "create", return_value=_reply()) as m:
        user_client.post("/message/", data='{"message": "(test) hi"}', content_type="application/json")
    assert m.call_args.kwargs["system"][0]["text"].endswith("View prompt.")


# --- triage slicing -----------------------------------------------------------------

def test_triage_slices_the_default_and_keeps_the_section():
    full = prompts.compose("My section.")
    core = skills.assemble_instructions({"skills": []}, full)
    assert skills._SKILL_START_MARKER not in core and core.endswith("My section.")
    assert skills.assemble_instructions({"skills": ["workout"]}, full) == full


def test_triage_default_path_unchanged():
    assert skills.assemble_instructions({"skills": []}) == skills.CORE_INSTRUCTIONS
    assert skills.assemble_instructions({"skills": ["workout"]}, agent.INSTRUCTIONS) == agent.INSTRUCTIONS


# --- settings endpoints -----------------------------------------------------------------

@pytest.mark.django_db
def test_settings_data_includes_prompt_summary(user_client):
    d = user_client.get("/settings/data/").json()
    assert d["prompt"]["has_section"] is False and d["prompt"]["text"] == ""
    assert d["prompt"]["default_text"] == agent.INSTRUCTIONS
    assert d["coach"]["prompt"] == agent.PROMPT_TAG


@pytest.mark.django_db
def test_save_reset_restore_flow(user_client, user):
    r = user_client.post("/settings/prompt/", {"text": "V1 text", "note": "first"}, content_type="application/json").json()
    assert r["ok"] and r["created"] and r["prompt"]["version"] == 1 and r["prompt"]["has_section"]
    r = user_client.post("/settings/prompt/reset/", content_type="application/json").json()
    assert not r["prompt"]["has_section"] and r["prompt"]["version"] == 2
    r = user_client.post("/settings/prompt/restore/", {"version": 1}, content_type="application/json").json()
    assert r["prompt"]["text"] == "V1 text" and r["prompt"]["version"] == 3
    assert r["prompt"]["versions"][0]["note"] == "restored v1"


@pytest.mark.django_db
def test_save_rejects_empty_and_oversized(user_client):
    assert user_client.post("/settings/prompt/", {"text": "   "}, content_type="application/json").status_code == 400
    big = "x" * (prompts.MAX_CHARS + 1)
    assert user_client.post("/settings/prompt/", {"text": big}, content_type="application/json").status_code == 400
    assert not CoachPrompt.objects.exists()


@pytest.mark.django_db
def test_restore_only_own_versions(user_client):
    other = User.objects.create_user("q", password="pw12345")
    CoachPrompt.objects.create(user=other, version=1, text="theirs")
    assert user_client.post("/settings/prompt/restore/", {"version": 1}, content_type="application/json").status_code == 404


@pytest.mark.django_db
def test_prompt_endpoints_require_login(client):
    assert client.post("/settings/prompt/", {"text": "x"}, content_type="application/json").status_code == 302


# --- the v2 split migration ---------------------------------------------------------

@pytest.mark.django_db
def test_split_turns_a_full_copy_into_moved_context_plus_own_edits(user):
    old_default = (split_migration.ARCHIVE / "v1.7.0.txt").read_text(encoding="utf-8")
    full_copy = old_default.replace("multisport athlete based in Warsaw.", "multisport athlete based in Innsbruck.")
    full_copy += "\n- Sickness signature = sudden HRV drop + elevated resting HR.\n"
    CoachPrompt.objects.create(user=user, version=1, text=full_copy)
    other = User.objects.create_user("fresh", password="pw12345")    # no prompt yet

    split_migration.split(django_apps, None)

    mine = CoachPrompt.objects.filter(user=user).order_by("-version").first()
    assert mine.version == 2 and mine.based_on == "v2.0.0"
    assert mine.text.startswith("ABOUT ME AND HOW TO COACH ME")
    own = mine.text.split("MY OWN EDITS TO THE OLD INSTRUCTIONS", 1)[1]
    assert "based in Innsbruck." in own and "Sickness signature" in own
    assert "=== TOOLS" not in mine.text and len(mine.text) < 6000      # no second copy of the default
    theirs = CoachPrompt.objects.get(user=other)
    assert "MY OWN EDITS" not in theirs.text


def test_archived_v170_is_the_logged_text():
    text = (split_migration.ARCHIVE / "v1.7.0.txt").read_text(encoding="utf-8")
    assert prompts.text_hash(text.replace("\r\n", "\n")) == "2442cbf6"   # ApiUsage tag v1.7.0@2442cbf6
