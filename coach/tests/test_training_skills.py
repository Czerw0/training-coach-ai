import pytest

from coach.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS, execute_tool
from coach.training_skills import check_week, list_skills, load_principles, load_skill


# --- the on-disk library ---

def test_list_skills_covers_all_categories():
    skills = list_skills()
    pairs = {(s["category"], s["skill"]) for s in skills}
    # the set the user asked for — gym + plyometrics + cycling + running
    expected = {
        ("gym", "upper-body"), ("gym", "lower-isometric"),
        ("gym", "lower-eccentric"), ("gym", "lower-power"),
        ("plyometrics", "extensive"), ("plyometrics", "intensive"),
        ("cycling", "endurance"), ("cycling", "intervals"),
        ("running", "easy-long"), ("running", "tempo-threshold"),
        ("running", "intervals"),
    }
    assert expected <= pairs


def test_every_skill_has_a_description():
    for s in list_skills():
        assert s["description"], f"{s['category']}/{s['skill']} missing description"


def test_intervals_disambiguated_by_category():
    # 'intervals' exists under both cycling/ and running/ — must stay distinct
    cyc = load_skill("cycling", "intervals")
    run = load_skill("running", "intervals")
    assert cyc != run
    assert "FTP" in cyc
    assert "VO2max" in run


def test_load_skill_returns_body_without_frontmatter():
    body = load_skill("gym", "lower-eccentric")
    assert not body.startswith("---")          # frontmatter stripped
    assert "name: lower-eccentric" not in body
    assert "DOMS" in body                       # real methodology present


# --- security: model output must not escape the skills dir ---

@pytest.mark.parametrize("category,skill", [
    ("..", "secret"),
    ("gym", "../../../manage"),
    ("gym/../..", "x"),
    ("gym", "lower eccentric"),   # space -> not a slug
    ("", ""),
])
def test_load_skill_rejects_bad_references(category, skill):
    out = load_skill(category, skill)
    assert out.lower().startswith(("invalid", "no training skill"))


def test_load_skill_missing_file_lists_available():
    out = load_skill("gym", "does-not-exist")
    assert out.startswith("No training skill")
    assert "gym/upper-body" in out


# --- three-places tool registration must agree ---

def test_tool_registered_in_all_three_places():
    assert "load_training_skill" in TOOL_FUNCTIONS
    schema = next(d for d in TOOL_DEFINITIONS if d["name"] == "load_training_skill")
    assert schema["input_schema"]["required"] == ["category", "skill"]
    props = schema["input_schema"]["properties"]
    assert set(props) == {"category", "skill"}


def test_execute_tool_loads_a_real_skill():
    out = execute_tool("load_training_skill", {"category": "plyometrics", "skill": "intensive"})
    assert "contacts" in out.lower()


def test_execute_tool_bad_skill_returns_error_not_exception():
    out = execute_tool("load_training_skill", {"category": "gym", "skill": "nope"})
    assert out.startswith("No training skill")


# --- context carries the index, not the bodies ---

@pytest.mark.django_db
def test_context_includes_training_skills_index():
    from coach.context import build_context
    ctx = build_context()
    assert "training_skills" in ctx
    assert any(s["category"] == "gym" for s in ctx["training_skills"])
    # index only — full methodology bodies are not preloaded into context
    assert all(set(s) == {"category", "skill", "description"} for s in ctx["training_skills"])


# --- principles (shared cross-cutting reasoning) ---

def test_load_principles_returns_both_files():
    p = load_principles()
    assert "Fatigue is not one number" in p          # load-and-recovery
    assert "The order to build a week" in p           # planning-the-week
    assert not p.startswith("---")                     # frontmatter stripped


def test_get_training_principles_tool():
    out = execute_tool("get_training_principles", {})
    assert "interference" in out.lower()


# --- deterministic week checker ---

def test_check_week_clean_week_has_no_violations():
    out = check_week([{"id": "gym/lower-max-strength", "start": "2026-08-10T17:00"}])
    assert "no constraint violations" in out.lower()


def test_check_week_flags_spacing_error():
    # two hard aerobic sessions 24 h apart; both declare 48 h => error
    out = check_week([
        {"id": "cycling/intervals", "start": "2026-08-10T17:00"},
        {"id": "running/tempo-threshold", "start": "2026-08-11T17:00"},
    ])
    assert "ERROR" in out
    assert "spacing" in out
    assert "1 error" in out


def test_check_week_bad_input_returns_message_not_exception():
    assert check_week("not a list").startswith("Invalid week")


def test_check_training_week_tool_runs_the_real_checker():
    out = execute_tool("check_training_week", {"sessions": [
        {"id": "gym/lower-eccentric", "start": "2026-08-10T18:00"},
        {"id": "running/intervals", "start": "2026-08-12T07:00"},  # 37 h; needs 72
    ]})
    assert "ERROR" in out and "spacing" in out


# --- three-places registration for the two new tools ---

@pytest.mark.parametrize("name,required", [
    ("get_training_principles", []),
    ("check_training_week", ["sessions"]),
])
def test_new_tools_registered_in_all_three_places(name, required):
    assert name in TOOL_FUNCTIONS
    schema = next(d for d in TOOL_DEFINITIONS if d["name"] == name)
    assert schema["input_schema"]["required"] == required
