from coach.agent import INSTRUCTIONS
from coach.skills import CORE_INSTRUCTIONS, WORKOUT_SKILL, assemble_all, assemble_instructions
from coach.triage import ENABLE_TURN_TRIAGE, classify_turn


def test_triage_flag_defaults_to_off():
    assert ENABLE_TURN_TRIAGE is False


def test_default_assembled_prompt_matches_original_instructions_exactly():
    # The safety net: proves splitting INSTRUCTIONS into core + skill didn't
    # silently drop or reword anything, entirely offline.
    assert assemble_all() == INSTRUCTIONS


def test_core_instructions_excludes_workout_skill_text():
    assert "For indoor cycling, pick a workout from indoor_workouts" not in CORE_INSTRUCTIONS


def test_assemble_instructions_includes_workout_skill_when_classified():
    result = assemble_instructions({"skills": ["workout"], "model_tier": "default"})
    assert result == assemble_all()


def test_assemble_instructions_omits_workout_skill_when_not_classified():
    result = assemble_instructions({"skills": ["injury"], "model_tier": "default"})
    assert result == CORE_INSTRUCTIONS
    assert WORKOUT_SKILL not in result


def test_classify_turn_matches_planning():
    result = classify_turn("Can you plan my next 7 days?")
    assert "planning" in result["skills"]
    assert result["model_tier"] == "default"


def test_classify_turn_matches_workout():
    result = classify_turn("I'm on the trainer today, need a workout")
    assert "workout" in result["skills"]


def test_classify_turn_matches_injury():
    result = classify_turn("My knee has been hurting since yesterday")
    assert "injury" in result["skills"]


def test_classify_turn_matches_analysis():
    result = classify_turn("How has my VO2max trend looked lately?")
    assert "analysis" in result["skills"]


def test_classify_turn_default_tier_when_nothing_matches():
    result = classify_turn("Thanks, sounds good!")
    assert result["skills"] == []
    assert result["model_tier"] == "simple"


def test_classify_turn_handles_empty_message():
    result = classify_turn("")
    assert result["skills"] == []
    assert result["model_tier"] == "simple"
