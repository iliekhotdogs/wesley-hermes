#!/usr/bin/env python3
"""Canvas LMS API CLI for Hermes Agent.

A thin CLI wrapper around the Canvas REST API.
Authenticates using a personal access token from environment variables.

Usage:
  python canvas_api.py list_courses [--per-page N] [--enrollment-state STATE]
  python canvas_api.py list_assignments COURSE_ID [--per-page N] [--order-by FIELD]
"""

import argparse
from datetime import date, datetime, timedelta
import json
import os
import sys
from zoneinfo import ZoneInfo

import requests

CANVAS_API_TOKEN = os.environ.get("CANVAS_API_TOKEN", "")
CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "").rstrip("/")


def _check_config():
    """Validate required environment variables are set."""
    missing = []
    if not CANVAS_API_TOKEN:
        missing.append("CANVAS_API_TOKEN")
    if not CANVAS_BASE_URL:
        missing.append("CANVAS_BASE_URL")
    if missing:
        hermes_env = os.path.join(
            os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")), ".env"
        )
        print(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Set them in {hermes_env} or export them in your shell.\n"
            "See the canvas skill SKILL.md for setup instructions.",
            file=sys.stderr,
        )
        sys.exit(1)


def _headers():
    return {"Authorization": f"Bearer {CANVAS_API_TOKEN}"}


def _paginated_get(url, params=None, max_items=200):
    """Fetch all pages up to max_items, following Canvas Link headers."""
    results = []
    while url and len(results) < max_items:
        resp = requests.get(url, headers=_headers(), params=params, timeout=30)
        resp.raise_for_status()
        results.extend(resp.json())
        params = None  # params are included in the Link URL for subsequent pages
        url = None
        link = resp.headers.get("Link", "")
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
    return results[:max_items]


# =========================================================================
# Commands
# =========================================================================


def list_courses(args):
    """List enrolled courses."""
    _check_config()
    url = f"{CANVAS_BASE_URL}/api/v1/courses"
    params = {"per_page": args.per_page}
    if args.enrollment_state:
        params["enrollment_state"] = args.enrollment_state
    try:
        courses = _paginated_get(url, params)
    except requests.HTTPError as e:
        print(f"API error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
    output = [
        {
            "id": c["id"],
            "name": c.get("name", ""),
            "course_code": c.get("course_code", ""),
            "enrollment_term_id": c.get("enrollment_term_id"),
            "start_at": c.get("start_at"),
            "end_at": c.get("end_at"),
            "workflow_state": c.get("workflow_state", ""),
        }
        for c in courses
    ]
    print(json.dumps(output, indent=2))


def list_assignments(args):
    """List assignments for a course."""
    _check_config()
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{args.course_id}/assignments"
    params = {"per_page": args.per_page}
    if args.order_by:
        params["order_by"] = args.order_by
    try:
        assignments = _paginated_get(url, params)
    except requests.HTTPError as e:
        print(f"API error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
    output = [
        {
            "id": a["id"],
            "name": a.get("name", ""),
            "description": (a.get("description") or "")[:500],
            "due_at": a.get("due_at"),
            "points_possible": a.get("points_possible"),
            "submission_types": a.get("submission_types", []),
            "html_url": a.get("html_url", ""),
            "course_id": a.get("course_id"),
        }
        for a in assignments
    ]
    print(json.dumps(output, indent=2))


def due_assignments(args):
    """List dated assignments across active courses in a local date range."""
    _check_config()
    try:
        tz = ZoneInfo(args.timezone)
        start = date.fromisoformat(args.start) if args.start else datetime.now(tz).date()
        end = date.fromisoformat(args.end) if args.end else start + timedelta(days=args.days)
        if end < start:
            raise ValueError("end is before start")
    except (ValueError, KeyError) as exc:
        print(f"Invalid date range or timezone: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        courses = _paginated_get(
            f"{CANVAS_BASE_URL}/api/v1/courses",
            {"enrollment_state": "active", "per_page": 100},
            max_items=1000,
        )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        print(f"Unable to list Canvas courses: HTTP {status}" if status else
              f"Unable to list Canvas courses: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)

    assignments = []
    warnings = []
    for course in courses:
        course_id = course.get("id")
        if course_id is None:
            continue
        try:
            items = _paginated_get(
                f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments",
                {"per_page": 100, "order_by": "due_at", "include[]": "submission"},
                max_items=10000,
            )
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            warnings.append(f"Course {course_id}: HTTP {status}" if status else
                            f"Course {course_id}: {type(exc).__name__}")
            continue
        if len(items) >= 10000:
            warnings.append(f"Course {course_id}: assignment limit reached")
        for item in items:
            due_at = item.get("due_at")
            if not due_at:
                continue
            try:
                due = datetime.fromisoformat(due_at.replace("Z", "+00:00")).astimezone(tz)
            except ValueError:
                warnings.append(f"Course {course_id}: invalid due date for assignment {item.get('id')}")
                continue
            if not start <= due.date() <= end:
                continue
            submission = item.get("submission") or {}
            assignments.append({
                "course": course.get("name") or course.get("course_code") or str(course_id),
                "course_id": course_id,
                "id": item.get("id"),
                "name": item.get("name", ""),
                "due_at": due_at,
                "due_local": due.isoformat(timespec="minutes"),
                "html_url": item.get("html_url", ""),
                "submission_status": submission.get("workflow_state"),
                "submitted_at": submission.get("submitted_at"),
                "missing": submission.get("missing"),
            })

    assignments.sort(key=lambda item: (item["due_local"], item["course"], item["name"]))
    print(json.dumps({
        "start": start.isoformat(), "end": end.isoformat(),
        "timezone": args.timezone, "courses_checked": len(courses),
        "assignments": assignments, "warnings": warnings,
    }, indent=2))


# =========================================================================
# CLI parser
# =========================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Canvas LMS API CLI for Hermes Agent"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- list_courses ---
    p = sub.add_parser("list_courses", help="List enrolled courses")
    p.add_argument("--per-page", type=int, default=50, help="Results per page (default 50)")
    p.add_argument(
        "--enrollment-state",
        default="",
        help="Filter by enrollment state (active, invited_or_pending, completed)",
    )
    p.set_defaults(func=list_courses)

    # --- list_assignments ---
    p = sub.add_parser("list_assignments", help="List assignments for a course")
    p.add_argument("course_id", help="Canvas course ID")
    p.add_argument("--per-page", type=int, default=50, help="Results per page (default 50)")
    p.add_argument(
        "--order-by",
        default="",
        help="Order by field (due_at, name, position)",
    )
    p.set_defaults(func=list_assignments)

    # --- due ---
    p = sub.add_parser("due", help="List assignments due across all active courses")
    p.add_argument("--start", default="", help="First local date (YYYY-MM-DD; default today)")
    p.add_argument("--end", default="", help="Last local date, inclusive (YYYY-MM-DD)")
    p.add_argument("--days", type=int, default=7, help="Days after start if --end omitted (default 7)")
    p.add_argument("--timezone", default="America/Vancouver", help="IANA timezone for due dates")
    p.set_defaults(func=due_assignments)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
