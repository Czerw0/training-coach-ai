import pytest
from django.core.management import call_command

from sync.management.commands.sync_exercises import EXERCISES
from sync.models import Exercise


@pytest.mark.django_db
def test_sync_exercises_creates_all_seed_rows():
    call_command("sync_exercises")
    assert Exercise.objects.count() == len(EXERCISES)


@pytest.mark.django_db
def test_sync_exercises_is_idempotent():
    call_command("sync_exercises")
    call_command("sync_exercises")
    assert Exercise.objects.count() == len(EXERCISES)
