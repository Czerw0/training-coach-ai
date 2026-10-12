"""Training metrics shared by the agent context and the dashboard, so both see
the same numbers. Plain functions over the ORM; `today` is injectable for tests."""
import datetime as dt
import statistics

from django.db.models import Sum

from sync.models import Activity, HRVRecord, SleepRecord


def acwr(today=None):
    """(acute_7d, chronic_28d, ratio). Windows include today: 7 and 28 days."""
    today = today or dt.date.today()
    acute = Activity.objects.filter(
        start_time__date__gt=today - dt.timedelta(days=7), start_time__date__lte=today,
    ).aggregate(s=Sum("training_load"))["s"] or 0
    chronic = Activity.objects.filter(
        start_time__date__gt=today - dt.timedelta(days=28), start_time__date__lte=today,
    ).aggregate(s=Sum("training_load"))["s"] or 0
    ratio = round(acute / (chronic / 4), 2) if chronic else None
    return acute, chronic, ratio


def acwr_band(ratio):
    if ratio is None:
        return "unknown"
    if ratio > 1.3:
        return "high"
    if ratio < 0.8:
        return "low"
    return "optimal"


def hrv_baseline(today=None, days=28):
    """(mean, sd) of nightly HRV over the previous `days`, excluding today."""
    today = today or dt.date.today()
    vals = list(HRVRecord.objects.filter(
        date__gte=today - dt.timedelta(days=days), date__lt=today, hrv_rmssd__isnull=False,
    ).values_list("hrv_rmssd", flat=True))
    if len(vals) < 7:
        return None, None
    return statistics.mean(vals), statistics.pstdev(vals)


def readiness(hrv_today, baseline, sleep_score, ratio):
    """0-100 composite: HRV vs personal baseline (40%), last night's sleep
    score (35%), load balance (25%). Missing inputs are dropped and the rest
    re-weighted. Returns (score, parts) or (None, parts)."""
    parts = {}
    mean, sd = baseline
    if hrv_today is not None and mean:
        z = (hrv_today - mean) / sd if sd else 0
        parts["hrv"] = max(0, min(100, 60 + 25 * z))
    if sleep_score is not None:
        parts["sleep"] = sleep_score
    if ratio is not None:
        if ratio > 1.3:
            parts["load"] = max(0, 100 - 200 * (ratio - 1.3))
        elif ratio < 0.8:
            parts["load"] = 85
        else:
            parts["load"] = 100
    weights = {"hrv": .40, "sleep": .35, "load": .25}
    total_w = sum(weights[k] for k in parts)
    if not total_w:
        return None, parts
    score = round(sum(parts[k] * weights[k] for k in parts) / total_w)
    return score, {k: round(v) for k, v in parts.items()}


def readiness_label(score):
    if score is None:
        return "No data", "muted"
    if score >= 75:
        return "Ready for quality", "good"
    if score >= 55:
        return "Train moderate", "warn"
    return "Take it easy", "bad"


def poor_sleep_nights(today=None, days=7, threshold=60):
    today = today or dt.date.today()
    return SleepRecord.objects.filter(
        date__gt=today - dt.timedelta(days=days), date__lte=today, score__lt=threshold,
    ).count()
