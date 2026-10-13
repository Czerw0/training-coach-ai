"""Settings page: athlete profile, HR zones, instruction days, weather
locations and the coach instructions. Every write is validated before it reaches the database."""
import json
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from pydantic import BaseModel, Field, ValidationError

from coach import agent, athlete_rules, profile_changes, prompts
from coach.models import CoachPrompt
from coach.schemas import format_validation_error
from sync.models import UserProfile, WeatherLocation
from sync.weather import fetch_forecast, geocode


class ProfileIn(BaseModel):
    ftp_watts: Optional[int] = Field(default=None, ge=50, le=600)
    max_hr: Optional[int] = Field(default=None, ge=120, le=230)
    lthr: Optional[int] = Field(default=None, ge=100, le=220)
    weight_kg: Optional[float] = Field(default=None, ge=30, le=200)
    primary_sport: str = Field(default="cycling", max_length=50)
    injury_history: str = Field(default="", max_length=5000)
    athlete_notes: str = Field(default="", max_length=20000)
    instruction_days: list[int] = Field(default_factory=list)
    hr_zones: Optional[list[dict]] = None
    rules: athlete_rules.AthleteRules = Field(default_factory=athlete_rules.AthleteRules)


TEXT_FIELDS = ["injury_history", "athlete_notes", "primary_sport"]
VALUE_FIELDS = ["ftp_watts", "max_hr", "lthr", "weight_kg", "instruction_days", "hr_zones", "rules"]


class PromptIn(BaseModel):
    text: str = Field(max_length=prompts.MAX_CHARS)
    note: str = Field(default="", max_length=200)


class LocationIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(min_length=1, max_length=50)


def _body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _locations():
    now = timezone.now()
    return [{"id": l.id, "name": l.name, "latitude": l.latitude, "longitude": l.longitude,
             "timezone": l.timezone, "is_active": l.is_active,
             "has_forecast": l.hours.filter(datetime__gte=now).exists()}
            for l in WeatherLocation.objects.all()]


@login_required
def settings_page(request):
    return render(request, "coach/settings.html")


@login_required
@require_http_methods(["GET"])
def settings_data(request):
    p, _ = UserProfile.objects.get_or_create(pk=1)
    return JsonResponse({
        "profile": {
            "ftp_watts": p.ftp_watts, "max_hr": p.max_hr, "lthr": p.lthr, "weight_kg": p.weight_kg,
            "primary_sport": p.primary_sport, "injury_history": p.injury_history or "",
            "athlete_notes": p.athlete_notes or "", "instruction_days": p.instruction_days or [],
            "hr_zones": p.hr_zones or [],
            "rules": athlete_rules.as_context(athlete_rules.load(p)),
        },
        "rule_groups": athlete_rules.GROUPS,
        "locations": _locations(),
        "coach": {"model": agent.MODEL, "prompt": prompts.active_prompt(request.user)[1], "config": agent.CONFIG_VERSION,
                  "thinking": agent.THINKING_EFFORT, "max_tokens": agent.MAX_TOKENS},
        "prompt": prompts.summary(request.user),
    })


def _prompt_saved(request, row, created):
    return JsonResponse({"ok": True, "created": created, "prompt": prompts.summary(request.user)})


@login_required
@require_http_methods(["POST"])
def save_prompt(request):
    try:
        data = PromptIn(**_body(request))
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": format_validation_error(exc)}, status=400)
    if not data.text.strip():
        return JsonResponse({"ok": False, "error": "Your section is empty. Use Remove my section instead."}, status=400)
    return _prompt_saved(request, *prompts.save_version(request.user, data.text, data.note))


@login_required
@require_http_methods(["POST"])
def reset_prompt(request):
    return _prompt_saved(request, *prompts.save_version(request.user, "", "reset to default"))


@login_required
@require_http_methods(["POST"])
def restore_prompt(request):
    row = CoachPrompt.objects.filter(user=request.user, version=_body(request).get("version")).first()
    if not row:
        return JsonResponse({"ok": False, "error": "Version not found."}, status=404)
    return _prompt_saved(request, *prompts.save_version(request.user, row.text, f"restored v{row.version}"))


@login_required
@require_http_methods(["POST"])
def save_profile(request):
    try:
        data = ProfileIn(**_body(request))
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": format_validation_error(exc)}, status=400)
    if any(d < 0 or d > 6 for d in data.instruction_days):
        return JsonResponse({"ok": False, "error": "Instruction days must be 0 (Mon) to 6 (Sun)."}, status=400)

    p, _ = UserProfile.objects.get_or_create(pk=1)
    before = {f: getattr(p, f) for f in TEXT_FIELDS + VALUE_FIELDS}
    before["rules"] = athlete_rules.load(p).model_dump()   # normalised, so {} == "no rules"
    for field, value in data.model_dump(exclude={"rules"}).items():
        setattr(p, field, value)
    p.rules = data.rules.model_dump()
    p.instruction_days = sorted(set(data.instruction_days))
    p.hr_zones = data.hr_zones or None
    try:
        p.clean()
    except DjangoValidationError as exc:
        return JsonResponse({"ok": False, "error": "; ".join(sum(exc.message_dict.values(), []))}, status=400)
    p.save()
    # so the coach sees what changed, not only the new state
    for f in TEXT_FIELDS:
        profile_changes.record_text(request.user, f, before[f], getattr(p, f))
    for f in VALUE_FIELDS:
        profile_changes.record_value(request.user, f, before[f] or None, getattr(p, f) or None)
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def add_location(request):
    try:
        data = LocationIn(**_body(request))
        ZoneInfo(data.timezone)
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": format_validation_error(exc)}, status=400)
    except (ZoneInfoNotFoundError, ValueError):
        return JsonResponse({"ok": False, "error": f"Unknown timezone '{data.timezone}'."}, status=400)
    loc = WeatherLocation.objects.create(**data.model_dump(), is_active=not WeatherLocation.objects.exists())
    return JsonResponse({"ok": True, "id": loc.id, "locations": _locations()})


@login_required
@require_http_methods(["POST"])
def activate_location(request):
    loc = WeatherLocation.objects.filter(id=_body(request).get("id")).first()
    if not loc:
        return JsonResponse({"ok": False, "error": "Location not found."}, status=404)
    with transaction.atomic():
        WeatherLocation.objects.exclude(id=loc.id).update(is_active=False)
        loc.is_active = True
        loc.save(update_fields=["is_active"])
    warning = None
    if not loc.hours.filter(datetime__gte=timezone.now()).exists():
        try:
            fetch_forecast(loc)
        except Exception as exc:
            warning = f"Saved, but the forecast couldn't be fetched yet ({exc}). The next weather sync will retry."
    return JsonResponse({"ok": True, "warning": warning, "locations": _locations()})


@login_required
@require_http_methods(["POST"])
def delete_location(request):
    loc = WeatherLocation.objects.filter(id=_body(request).get("id")).first()
    if not loc:
        return JsonResponse({"ok": False, "error": "Location not found."}, status=404)
    if loc.is_active:
        return JsonResponse({"ok": False, "error": "Switch to another location before removing this one."}, status=400)
    loc.delete()
    return JsonResponse({"ok": True, "locations": _locations()})


@login_required
@require_http_methods(["GET"])
def search_location(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    try:
        return JsonResponse({"results": geocode(q)})
    except Exception as exc:
        return JsonResponse({"results": [], "error": f"Search failed: {exc}"}, status=502)
