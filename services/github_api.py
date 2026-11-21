"""Network services for TaskFlow Pro - 100% Python standard library.

* Import open issues from any public GitHub repository (urllib + json).
* Fetch a fresh developer/productivity quote from dummyjson.com.
* Post optional Discord / Telegram-style webhook alerts in the background.

All network calls are executed off the Tk main thread, and results are
marshalled back onto the UI thread with ``Tk.after(0, ...)`` so the GUI never
freezes and never touches widgets from a worker thread.
"""
from __future__ import annotations

import json
import re
import threading
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any, Callable

GITHUB_API = "https://api.github.com"
QUOTE_API = "https://dummyjson.com/quotes/random"
REQUEST_TIMEOUT = 12
USER_AGENT = "TaskFlowPro-Desktop/1.0 (+https://github.com/Rg100152/taskflow)"

REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _priority_from_labels(labels: list[str]) -> str:
    names = {str(label).lower() for label in labels}
    if names & {"high", "critical", "urgent", "priority: high", "bug", "p0", "p1"}:
        return "High"
    if names & {"low", "minor", "priority: low", "documentation", "p3"}:
        return "Low"
    return "Medium"


class GitHubService:
    """Fetch public GitHub issues and daily quotes without external packages."""

    def __init__(self, root: Any | None = None) -> None:
        self.root = root

    # ------------------------------------------------------------------ #
    # Thread / UI helpers
    # ------------------------------------------------------------------ #
    def _dispatch(self, callback: Callable[..., None] | None, *args: Any) -> None:
        if not callback:
            return
        try:
            if self.root is not None:
                self.root.after(0, lambda: callback(*args))
            else:
                callback(*args)
        except (RuntimeError, tk.TclError):
            # The window may have been closed (or its mainloop not started) while
            # the worker was online. Never let that crash a daemon thread.
            pass

    @staticmethod
    def _get_json(url: str) -> Any:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    # ------------------------------------------------------------------ #
    # GitHub Issues
    # ------------------------------------------------------------------ #
    def fetch_open_issues(self, repo: str) -> list[dict[str, Any]]:
        """Return open issues as ready-to-insert task dictionaries.

        Raises ValueError for invalid input and RuntimeError for API failures.
        """
        repo = (repo or "").strip().strip("/")
        if not REPO_PATTERN.match(repo):
            raise ValueError("Use the format owner/repository (example: Rg100152/taskflow).")

        owner, name = repo.split("/", 1)
        # The Search API filters out pull requests server-side. The plain
        # /issues endpoint returns PRs too, which can bury real issues on
        # active repositories (e.g. django/django).
        query = urllib.parse.quote(f"repo:{owner}/{name} is:issue is:open")
        url = (
            f"{GITHUB_API}/search/issues?q={query}"
            "&per_page=100&sort=updated&order=desc"
        )
        try:
            response = self._get_json(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise RuntimeError("Repository not found (or it is private).") from exc
            if exc.code == 403:
                raise RuntimeError("GitHub rate limit reached. Try again in a few minutes.") from exc
            if exc.code == 422:
                raise RuntimeError("GitHub could not process that repository query.") from exc
            raise RuntimeError(f"GitHub API error: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Could not reach GitHub: {exc}") from exc

        if not isinstance(response, dict) or not isinstance(response.get("items"), list):
            message = response.get("message", "") if isinstance(response, dict) else ""
            raise RuntimeError(f"Unexpected response from GitHub API. {message}".strip())
        payload = response["items"]

        today = date.today()
        tasks: list[dict[str, Any]] = []
        for issue in payload:
            if not isinstance(issue, dict) or "pull_request" in issue:
                continue  # skip pull requests - they are not tasks
            labels = [
                lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
                for lbl in (issue.get("labels") or [])
            ]
            assignee = issue.get("assignee") or {}
            assignee_name = assignee.get("login", "GitHub Import") if isinstance(assignee, dict) else "GitHub Import"
            body = (issue.get("body") or "").strip()
            tasks.append({
                "title": f"#{issue.get('number', '?')} {issue.get('title', 'Untitled issue')}",
                "description": (body[:500] + "…") if len(body) > 500 else body,
                "status": "To Do",
                "priority": _priority_from_labels(labels),
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=7)).isoformat(),
                "progress": 0,
                "assignee": assignee_name,
                "source": "github",
                "github_id": str(issue.get("id", issue.get("number", ""))),
            })
        return tasks

    def fetch_open_issues_async(
        self,
        repo: str,
        on_success: Callable[[list[dict[str, Any]], str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Non-blocking wrapper. Callbacks run on the Tk UI thread."""
        def worker() -> None:
            try:
                tasks = self.fetch_open_issues(repo)
                self._dispatch(on_success, tasks, repo)
            except (ValueError, RuntimeError) as exc:
                self._dispatch(on_error, str(exc))
            except Exception as exc:  # defensive: never let a worker die silently
                self._dispatch(on_error, f"Unexpected import error: {exc}")

        threading.Thread(target=worker, name="taskflow-github-import", daemon=True).start()

    # ------------------------------------------------------------------ #
    # Daily quote
    # ------------------------------------------------------------------ #
    def fetch_quote(self) -> str:
        try:
            data = self._get_json(QUOTE_API)
            quote = str(data.get("quote", "")).strip()
            author = str(data.get("author", "Unknown")).strip()
            if not quote:
                raise ValueError("empty quote")
            return f"“{quote}” — {author}"
        except Exception:
            return "“Ship small, ship often, keep learning.” — Raj Gautam"

    def fetch_quote_async(self, on_success: Callable[[str], None] | None = None) -> None:
        def worker() -> None:
            self._dispatch(on_success, self.fetch_quote())

        threading.Thread(target=worker, name="taskflow-quote", daemon=True).start()


class WebhookNotifier:
    """Send background alerts to a Discord / Telegram-compatible webhook."""

    def __init__(self, root: Any | None = None, webhook_url: str = "") -> None:
        self.root = root
        self.webhook_url = webhook_url.strip()

    def set_url(self, url: str) -> None:
        self.webhook_url = (url or "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.webhook_url)

    def _post(self, payload: dict[str, Any]) -> None:
        if not self.configured:
            return
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            response.read()

    def notify_high_priority_completion(self, task_title: str) -> None:
        """Fire a webhook when a High-priority task reaches Completed."""
        if not self.configured:
            return
        message = (
            f"✅ **Task Completed by Raj Gautam!**\n"
            f"**{task_title}**\n"
            f"Priority: High • TaskFlow Pro"
        )
        payload = {"content": message, "text": message, "username": "TaskFlow Pro"}
        threading.Thread(
            target=self._safe_post, args=(payload,),
            name="taskflow-webhook", daemon=True,
        ).start()

    def _safe_post(self, payload: dict[str, Any]) -> None:
        try:
            self._post(payload)
        except Exception:
            pass  # notifications must never break the app
