from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.auth.models import AnonymousUser, User

from coach import agent, prompts, skills
from coach.models import ApiUsage, CoachPrompt


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


def test_custom_version_wins_and_is_tagged_per_user(user):
    prompts.save_version(user, "Be brief.")
    text, tag = prompts.active_prompt(user)
    assert text == "Be brief."
    assert tag == f"u{user.id}/v1@{prompts.text_hash('Be brief.')}"


def test_versions_are_per_user(user):
    other = User.objects.create_user("q", password="pw12345")
    prompts.save_version(user, "Mine.")
    assert prompts.active_prompt(other)[0] == agent.INSTRUCTIONS


def test_reset_appends_a_default_version_and_keeps_history(user):
    prompts.save_version(user, "A")
    row, created = prompts.save_version(user, "")
    assert created and row.version == 2 and row.text == ""
    assert prompts.active_prompt(user)[1] == agent.PROMPT_TAG
    assert CoachPrompt.objects.filter(user=user).count() == 2


def test_saving_the_default_text_stores_default_and_unchanged_is_noop(user):
    default_from_browser = agent.INSTRUCTIONS.replace("\n", "\r\n") + "\n"
    assert prompts.save_version(user, default_from_browser)[1] is False   # already on the default
    prompts.save_version(user, "X")
    assert prompts.save_version(user, "X")[1] is False
    row, created = prompts.save_version(user, default_from_browser)
    assert created and row.text == ""       # stored as default: still follows future INSTRUCTIONS changes


def test_guardrail_markers_exist_in_default_and_warn_when_removed():
    for marker in prompts.GUARDRAILS:
        assert marker in agent.INSTRUCTIONS
    assert prompts.warnings_for(agent.INSTRUCTIONS) == []
    assert len(prompts.warnings_for("Short prompt.")) == len(prompts.GUARDRAILS)


# --- chat() uses it ---------------------------------------------------------------------

@pytest.mark.django_db
def test_chat_sends_the_users_prompt_and_logs_its_tag(user):
    prompts.save_version(user, "Custom coach rules.")
    with mock.patch.object(agent.client.messages, "create", return_value=_reply()) as m:
        agent.chat("(test) hi", user=user)
    assert m.call_args.kwargs["system"][0]["text"] == "Custom coach rules."
    assert ApiUsage.objects.get().prompt_version.startswith(f"u{user.id}/v1@")


@pytest.mark.django_db
def test_chat_without_user_is_unchanged():
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
    assert m.call_args.kwargs["system"][0]["text"] == "View prompt."


# --- triage slicing on custom text ------------------------------------------------------

def test_triage_slices_custom_text_that_keeps_the_markers():
    custom = agent.INSTRUCTIONS.replace("You are Apex", "You are Apex (custom)")
    full = skills.assemble_instructions({"skills": ["workout"]}, custom)
    core = skills.assemble_instructions({"skills": []}, custom)
    assert full == custom
    assert skills._SKILL_START_MARKER not in core and core.startswith("You are Apex (custom)")


def test_triage_sends_custom_text_without_markers_whole():
    assert skills.assemble_instructions({"skills": []}, "No markers here.") == "No markers here."
    assert skills.assemble_instructions({"skills": ["workout"]}, "No markers here.") == "No markers here."


def test_triage_default_path_unchanged():
    assert skills.assemble_instructions({"skills": []}) == skills.CORE_INSTRUCTIONS
    assert skills.assemble_instructions({"skills": ["workout"]}, agent.INSTRUCTIONS) == agent.INSTRUCTIONS


# --- settings endpoints -----------------------------------------------------------------

@pytest.mark.django_db
def test_settings_data_includes_prompt_summary(user_client):
    d = user_client.get("/settings/data/").json()
    assert d["prompt"]["is_default"] and d["prompt"]["text"] == agent.INSTRUCTIONS
    assert d["coach"]["prompt"] == agent.PROMPT_TAG


@pytest.mark.django_db
def test_save_reset_restore_flow(user_client, user):
    r = user_client.post("/settings/prompt/", {"text": "V1 text", "note": "first"}, content_type="application/json").json()
    assert r["ok"] and r["created"] and r["prompt"]["version"] == 1 and not r["prompt"]["is_default"]
    r = user_client.post("/settings/prompt/reset/", content_type="application/json").json()
    assert r["prompt"]["is_default"] and r["prompt"]["version"] == 2
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
