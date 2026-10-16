"""Day markers on the calendar: injury (period), illness (period), alcohol (drinks
per day). Read for a date range; edited from the marker sheet. The agent writes
the same rows through log_injury / log_illness / log_alcohol."""
import datetime as dt
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from pydantic import ValidationError

from coach.models import DailyFeeling, Illness, Injury
from coach.schemas import AlcoholIn, IllnessIn, InjuryIn, format_validation_error
from coach.tools import set_alcohol

MAX_RANGE_DAYS = 120


def _day(value):
    return dt.date.fromisoformat((value or "")[:10])


def _days(start, end, first, last):
    """Dates of a period [first, last or open] inside [start, end)."""
    d = max(first, start)
    stop = min(last or end - dt.timedelta(days=1), end - dt.timedelta(days=1))
    while d <= stop:
        yield d
        d += dt.timedelta(days=1)


def collect(start, end, today=None):
    """{"days": {date: [{"kind", "id"}]}, "injuries": {id: row}, "illnesses": {id: row},
    "alcohol": {date: drinks}} for start <= date < end. Open periods end today."""
    today = today or dt.date.today()
    end_open = min(end, today + dt.timedelta(days=1))
    days, injuries, illnesses, alcohol = {}, {}, {}, {}

    def mark(d, item):
        days.setdefault(d.isoformat(), []).append(item)

    for i in Injury.objects.filter(date_started__lt=end).filter(Q(date_resolved__isnull=True) | Q(date_resolved__gte=start)):
        injuries[i.id] = {"id": i.id, "body_part": i.body_part or "", "severity": i.severity, "description": i.description or "",
                          "date_started": i.date_started.isoformat(),
                          "date_resolved": i.date_resolved.isoformat() if i.date_resolved else None,
                          "affects_running": bool(i.affects_running), "affects_cycling": bool(i.affects_cycling)}
        for d in _days(start, end_open if i.date_resolved is None else end, i.date_started, i.date_resolved):
            mark(d, {"kind": "injury", "id": i.id})

    for s in Illness.objects.filter(date_started__lt=end).filter(Q(date_resolved__isnull=True) | Q(date_resolved__gte=start)):
        illnesses[s.id] = {"id": s.id, "symptoms": s.symptoms, "systemic": s.systemic,
                           "date_started": s.date_started.isoformat(),
                           "date_resolved": s.date_resolved.isoformat() if s.date_resolved else None}
        for d in _days(start, end_open if s.date_resolved is None else end, s.date_started, s.date_resolved):
            mark(d, {"kind": "illness", "id": s.id})

    for f in DailyFeeling.objects.filter(date__gte=start, date__lt=end, alcohol_drinks__gt=0).values("date", "alcohol_drinks"):
        alcohol[f["date"].isoformat()] = f["alcohol_drinks"]
        mark(f["date"], {"kind": "alcohol"})

    return {"days": days, "injuries": injuries, "illnesses": illnesses, "alcohol": alcohol}


@login_required
@require_http_methods(["GET"])
def markers(request):
    try:
        start, end = _day(request.GET.get("start")), _day(request.GET.get("end"))
    except ValueError:
        return JsonResponse({"ok": False, "error": "start and end must be dates."}, status=400)
    if end <= start or (end - start).days > MAX_RANGE_DAYS:
        return JsonResponse({"ok": False, "error": f"Range must be 1-{MAX_RANGE_DAYS} days."}, status=400)
    return JsonResponse({"ok": True, **collect(start, end)})


def _parse(request, schema):
    try:
        return schema(**json.loads(request.body or b"{}")), None
    except ValidationError as exc:
        return None, JsonResponse({"ok": False, "error": format_validation_error(exc)}, status=400)
    except (ValueError, TypeError):
        return None, JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)


def _not_future(day):
    return None if day <= dt.date.today() else JsonResponse({"ok": False, "error": "That day hasn't happened yet."}, status=400)


@login_required
@require_http_methods(["POST"])
def save_alcohol(request):
    data, err = _parse(request, AlcoholIn)
    err = err or _not_future(data.date)
    if err:
        return err
    set_alcohol(data.date, data.drinks)
    return JsonResponse({"ok": True})


def _save_period(request, schema, model, fields):
    data, err = _parse(request, schema)
    err = err or _not_future(data.date_started)
    if err:
        return err
    values = {f: getattr(data, f) for f in fields}
    if data.id:
        if not model.objects.filter(id=data.id).update(**values):
            return JsonResponse({"ok": False, "error": "Not found."}, status=404)
        return JsonResponse({"ok": True, "id": data.id})
    return JsonResponse({"ok": True, "id": model.objects.create(**values).id})


def _delete(request, model):
    try:
        pk = int(json.loads(request.body or b"{}").get("id"))
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({"ok": False, "error": "id required."}, status=400)
    deleted, _ = model.objects.filter(id=pk).delete()
    return JsonResponse({"ok": bool(deleted)}, status=200 if deleted else 404)


@login_required
@require_http_methods(["POST"])
def save_illness(request):
    return _save_period(request, IllnessIn, Illness, ["date_started", "date_resolved", "symptoms", "systemic"])


@login_required
@require_http_methods(["POST"])
def delete_illness(request):
    return _delete(request, Illness)


@login_required
@require_http_methods(["POST"])
def save_injury(request):
    return _save_period(request, InjuryIn, Injury, ["body_part", "severity", "description", "date_started",
                                                    "date_resolved", "affects_running", "affects_cycling"])


@login_required
@require_http_methods(["POST"])
def delete_injury(request):
    return _delete(request, Injury)
