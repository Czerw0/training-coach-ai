#!/usr/bin/env python3
"""List sessions, or print one session's full methodology on demand.

The "detail on demand" half of progressive disclosure. In a plain Anthropic
skill Claude can just read the reference file directly; this script exists so
the same behaviour works from a shell/code tool and so a bad id returns a
helpful error listing valid ids (self-correction) instead of a stack trace.

Usage:
    python sessions.py list
    python sessions.py show gym/lower-eccentric
"""
import sys

from frontmatter import iter_sessions, parse, session_path, use_utf8_stdout


def _all_ids():
    return [sid for sid, _, _ in iter_sessions()]


def show(session_id):
    path = session_path(session_id)
    if not path.is_file():
        avail = ", ".join(_all_ids()) or "(none found)"
        return f"No session '{session_id}'. Available: {avail}."
    _, body = parse(path.read_text(encoding="utf-8"))
    return body.strip()


def main(argv):
    use_utf8_stdout()
    if not argv or argv[0] == "list":
        for sid, meta, _ in iter_sessions():
            print(f"{sid} — {meta.get('description', '')}")
        return 0
    if argv[0] == "show" and len(argv) == 2:
        print(show(argv[1]))
        return 0
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
