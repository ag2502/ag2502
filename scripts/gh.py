"""Read-only GitHub data collection. Standard library only.

Every network call is best-effort: if something fails (no token, rate limit,
offline) the field falls back to a sane default so the SVG always renders.
"""

import datetime as dt
import json
import os
import urllib.error
import urllib.request

API = "https://api.github.com"
UA = "profile-pr-generator"


def _get(url, token=None, accept="application/vnd.github+json"):
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", UA)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def _graphql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(API + "/graphql", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=25) as r:
        payload = json.load(r)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "graphql error"))
    return payload["data"]


def _try(label, fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - any failure degrades gracefully
        print("  ~ skipped %s (%s)" % (label, exc))
        return default


CALENDAR_QUERY = """
query($login:String!) {
  user(login:$login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def _calendar(login, token):
    data = _graphql(CALENDAR_QUERY, {"login": login}, token)
    cc = data["user"]["contributionsCollection"]
    days = []
    for week in cc["contributionCalendar"]["weeks"]:
        days.extend(week["contributionDays"])
    return {
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "commits_year": cc["totalCommitContributions"],
        "prs_year": cc["totalPullRequestContributions"],
        "days": days,
    }


def _streak(days):
    """Consecutive days with activity, counted back from today (or yesterday)."""
    by_date = {d["date"]: d["contributionCount"] for d in days}
    today = dt.date.today()
    start = today if by_date.get(today.isoformat(), 0) > 0 else today - dt.timedelta(days=1)
    streak = 0
    cursor = start
    while by_date.get(cursor.isoformat(), 0) > 0:
        streak += 1
        cursor -= dt.timedelta(days=1)
    return streak


def _best_day(days):
    best = max(days, key=lambda d: d["contributionCount"], default=None)
    if not best or not best["contributionCount"]:
        return 0, ""
    return best["contributionCount"], best["date"]


def collect(handle, token=None):
    """Return a flat dict of facts about `handle`."""
    print("> collecting github data for %s%s" % (handle, " (authenticated)" if token else " (anonymous)"))

    user = _try("user", lambda: _get("%s/users/%s" % (API, handle), token), {}) or {}
    repos = _try(
        "repos",
        lambda: _get("%s/users/%s/repos?per_page=100&sort=pushed" % (API, handle), token),
        [],
    ) or []

    own = [r for r in repos if not r.get("fork")]
    own.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)

    now = dt.datetime.now(dt.timezone.utc)

    def age_weight(repo):
        """Recent work should describe you; a 2023 practice repo should not."""
        pushed = repo.get("pushed_at")
        if not pushed:
            return 0.15
        days = (now - dt.datetime.strptime(pushed, "%Y-%m-%dT%H:%M:%SZ")
                .replace(tzinfo=dt.timezone.utc)).days
        if days <= 180:
            return 1.0
        if days <= 365:
            return 0.7
        if days <= 730:
            return 0.35
        return 0.12

    # Byte counts per repo, weighted by recency. Falls back to the coarse
    # repo-level language field if the per-repo calls are unavailable.
    scores = {}
    for r in own[:12]:
        url = r.get("languages_url")
        if not url:
            continue
        per_repo = _try("languages for %s" % r.get("name"), lambda u=url: _get(u, token), {}) or {}
        weight = age_weight(r)
        for lang, byte_count in per_repo.items():
            scores[lang] = scores.get(lang, 0.0) + byte_count * weight
    if not scores:
        for r in own:
            lang = r.get("language")
            if lang:
                scores[lang] = scores.get(lang, 0.0) + age_weight(r)
    languages = [name for name, _ in sorted(scores.items(), key=lambda kv: -kv[1])]
    recent = []
    for r in own:
        pushed = r.get("pushed_at")
        if not pushed:
            continue
        when = dt.datetime.strptime(pushed, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        if (now - when).days <= 30:
            recent.append(r)

    cal = None
    if token:
        cal = _try("contribution calendar", lambda: _calendar(handle, token))
    commits_searched = _try(
        "commit search",
        lambda: _get("%s/search/commits?q=author:%s&per_page=1" % (API, handle), token).get("total_count"),
    )

    contributions = cal["contributions"] if cal else None
    streak = _streak(cal["days"]) if cal else None
    best_count, best_date = _best_day(cal["days"]) if cal else (None, "")
    commits = cal["commits_year"] if cal else commits_searched

    created = (user.get("created_at") or "")[:10]
    years = ""
    if created:
        years = round((now.date() - dt.date.fromisoformat(created)).days / 365.25, 1)

    top = own[0] if own else {}
    data = {
        "handle": handle,
        "name": user.get("name") or handle,
        "bio": user.get("bio") or "",
        "location": user.get("location") or "",
        "blog": user.get("blog") or "",
        "repos": len(own),
        "public_repos": user.get("public_repos") or len(own),
        "followers": user.get("followers") or 0,
        "stars": sum(r.get("stargazers_count", 0) for r in own),
        "languages": languages,
        "top_language": languages[0] if languages else "code",
        "languages_top3": ", ".join(languages[:3]),
        "language_count": len(languages),
        "active_repos": len(recent),
        "active_repo_names": [r["name"] for r in recent],
        "top_repo": top.get("name", ""),
        "top_repo_language": top.get("language") or "",
        "top_repo_pushed": (top.get("pushed_at") or "")[:10],
        "top_repo_desc": top.get("description") or "",
        "commits": commits,
        "contributions": contributions,
        "streak": streak,
        "best_day": best_count,
        "best_day_date": best_date,
        "prs": cal["prs_year"] if cal else None,
        "joined": created,
        "years_on_github": years,
        "today": dt.date.today().isoformat(),
        "year": dt.date.today().year,
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
    }
    print("  repos=%s langs=%s commits=%s contributions=%s streak=%s active30d=%s"
          % (data["repos"], len(languages), commits, contributions, streak, data["active_repos"]))
    return data


def demo():
    """Offline sample data so the renderer can be worked on without network."""
    today = dt.date.today()
    return {
        "handle": "ag2502", "name": "Amogh Gaikwad", "bio": "", "location": "Ireland",
        "blog": "", "repos": 14, "public_repos": 14, "followers": 3, "stars": 0,
        "languages": ["Python", "HTML", "TypeScript"], "top_language": "Python",
        "languages_top3": "Python, HTML, TypeScript",
        "language_count": 3, "active_repos": 3,
        "active_repo_names": ["gridpeer", "Tellerline", "Job-Finder-for-Ireland"],
        "top_repo": "gridpeer", "top_repo_language": "Python",
        "top_repo_pushed": today.isoformat(), "top_repo_desc": "",
        "commits": 342, "contributions": 512, "streak": 6, "best_day": 21,
        "best_day_date": today.isoformat(), "prs": 18, "joined": "2022-10-04",
        "years_on_github": 3.9, "today": today.isoformat(), "year": today.year,
        "generated_at": "demo run",
    }
