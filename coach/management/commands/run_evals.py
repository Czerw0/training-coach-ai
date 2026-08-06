import os
import time

import environ
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.test.runner import DiscoverRunner

DIRECT_DB_ENV = "DIRECT_DATABASE_URL"
SETUP_ATTEMPTS = 6
SETUP_RETRY_DELAY_SECONDS = 3


class Command(BaseCommand):
    help = (
        "Run the coaching-agent eval harness (coach/evals/cases.json) against "
        "the real Anthropic API. Makes real API calls — costs real money — so "
        "this is a manual dev tool, not part of CI. Run after every prompt or "
        "model change (see backlog.md item 5)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--case", dest="case_id", default=None,
            help="Run only the case with this id, instead of the whole set.",
        )

    def handle(self, *args, **options):
        from coach.evals.harness import load_cases, run_all

        direct_url = os.getenv(DIRECT_DB_ENV)
        if not direct_url:
            self.stdout.write(self.style.ERROR(
                f"{DIRECT_DB_ENV} is not set. The eval harness needs a direct "
                "(non-pooled) Postgres connection to safely create/drop its "
                "throwaway test database — Supabase's pooled connection "
                "(Supavisor) can't reliably run CREATE/DROP DATABASE (the same "
                "reason CI uses sqlite instead of real Postgres for tests).\n\n"
                "Get it from the Supabase dashboard -> Connect -> "
                "'Direct connection' (usually port 5432, not 6543) and add:\n"
                f"  {DIRECT_DB_ENV}=postgresql://...\n"
                "to your .env, then re-run this command."
            ))
            return

        # points 'default' at the direct connection for the whole run.
        # .update() only, never .clear() — Django puts one-time defaults
        # (TEST, CONN_MAX_AGE, ...) on this same dict at startup; clearing
        # first wipes them with nothing left to reapply (KeyError: 'TEST')
        settings.DATABASES['default'].update(environ.Env.db_url_config(direct_url))
        connections.close_all()

        cases = load_cases()
        case_id = options.get("case_id")
        if case_id:
            cases = [c for c in cases if c["id"] == case_id]
            if not cases:
                self.stdout.write(self.style.ERROR(f"No case with id '{case_id}'"))
                return

        self.stdout.write(
            f"Running {len(cases)} case(s) against the real API in an isolated "
            "test database — this costs real API credits.\n"
        )

        # isolated test DB, same as pytest-django — setup fixtures and every
        # tool call stay off real data. interactive=False so a leftover DB
        # from a crashed run just gets recreated, no y/n prompt
        runner = DiscoverRunner(interactive=False)
        old_config = self._setup_databases_with_retry(runner)
        try:
            results = run_all(cases=cases)
        finally:
            connections.close_all()
            try:
                runner.teardown_databases(old_config)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(
                    f"Could not cleanly drop the test database ({exc}). "
                    "Harmless — it'll be recreated on the next run."
                ))

        self._print_scorecard(results)

    def _terminate_test_db_sessions(self):
        """Best-effort kill of lingering backend sessions on test_postgres —
        even the session pooler doesn't always release instantly, and the
        next create/drop can race it. Cheap insurance before each attempt."""
        conn = connections['default']
        try:
            conn.ensure_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = 'test_postgres' AND pid <> pg_backend_pid()"
                )
        except Exception:
            pass
        finally:
            connections.close_all()

    def _setup_databases_with_retry(self, runner):
        """runner.setup_databases() calls sys.exit(2) on failure, no
        exception to catch — so retry the whole call ourselves. Failure is
        transient (Supavisor releasing a connection a beat late), not real."""
        for attempt in range(1, SETUP_ATTEMPTS + 1):
            self._terminate_test_db_sessions()
            try:
                return runner.setup_databases()
            except SystemExit:
                if attempt == SETUP_ATTEMPTS:
                    raise
                self.stdout.write(self.style.WARNING(
                    f"Test database still busy (attempt {attempt}/{SETUP_ATTEMPTS}), "
                    f"retrying in {SETUP_RETRY_DELAY_SECONDS}s..."
                ))
                time.sleep(SETUP_RETRY_DELAY_SECONDS)

    def _print_scorecard(self, results):
        passed = sum(1 for r in results if r["passed"])
        for r in results:
            mark = self.style.SUCCESS("PASS") if r["passed"] else self.style.ERROR("FAIL")
            self.stdout.write(f"[{mark}] {r['id']}")
            if not r["passed"]:
                for check in r["checks"]:
                    if not check["ok"]:
                        self.stdout.write(f"    - {check['check']}: {check['detail']}")
                self.stdout.write(f"    tools_used: {r['tools_used']}")
                self.stdout.write(f"    reply: {r['final_text'][:300]!r}")

        self.stdout.write("")
        summary = f"{passed}/{len(results)} passed"
        if passed == len(results):
            self.stdout.write(self.style.SUCCESS(summary))
        else:
            self.stdout.write(self.style.ERROR(summary))
