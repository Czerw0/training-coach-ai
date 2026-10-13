from sync.models import WeatherLocation


def nav(request):
    """Current location for the sidebar profile row; one tiny query, logged-in pages only."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    loc = WeatherLocation.objects.filter(is_active=True).values_list("name", flat=True).first()
    return {"nav_location": loc}
