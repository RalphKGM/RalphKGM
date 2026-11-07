#!/usr/bin/env python3
"""Builds README.md from profile.toml plus live public GitHub data.

Run locally:  GITHUB_TOKEN=... python3 scripts/build_readme.py
(The token is optional locally, but without it GitHub rate-limits you quickly.)
Needs Python 3.11+ (for tomllib). No other dependencies.
"""
import datetime as dt
import json
import os
import sys
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER = os.environ.get("PROFILE_USER", "RalphKGM")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
TODAY = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))  # Philippine time


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={
        "Accept": "application/vnd.github+json", "User-Agent": "profile-readme-builder",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def safe(fn, default):
    try:
        return fn()
    except Exception as e:  # a failing section should never break the whole README
        print(f"warning: {e}", file=sys.stderr)
        return default


def badge(label, icon, color, bg="0d1117"):
    text = urllib.parse.quote(label.replace("-", "--").replace("_", "__"), safe="")
    return (f"![{label}](https://img.shields.io/badge/{text}-{bg}?style=flat-square"
            f"&logo={urllib.parse.quote(icon or '')}&logoColor={color})")


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def school_line(s):
    if s.get("graduated"):
        return f"{s['degree']} graduate, {s.get('short', s['name'])}"
    ay = TODAY.year if TODAY.month >= s.get("ay_start_month", 8) else TODAY.year - 1
    level = max(1, ay - s["start_year"] + 1)
    return f"{ordinal(level)} year {s['degree']} @ {s.get('short', s['name'])}"


def month_day(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %-d")


def month_year(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %Y")


def main():
    cfg = tomllib.loads((ROOT / "profile.toml").read_text())
    about, school, auto = cfg["about"], cfg["school"], cfg.get("auto", {})
    color = cfg.get("header", {}).get("color", "38BDF8")
    font = cfg.get("header", {}).get("font", "JetBrains+Mono")
    exclude = set(auto.get("exclude_repos", [])) | {USER}
    sline = school_line(school)

    repos = safe(lambda: api(f"/users/{USER}/repos?per_page=100&type=owner&sort=pushed"), [])
    public = [r for r in repos if not r["private"] and not r["fork"] and not r["archived"]]
    by_name = {r["name"]: r for r in public}
    listed = [r for r in public if r["name"] not in exclude]
    user = safe(lambda: api(f"/users/{USER}"), {})
    ignore = set(auto.get("ignore_languages", []))
    langs = {r["name"]: safe(lambda r=r: api(f"/repos/{USER}/{r['name']}/languages"), {}) for r in listed}

    def main_lang(r):
        own = {k: v for k, v in langs.get(r["name"], {}).items() if k not in ignore}
        return max(own, key=own.get) if own else (r.get("language") or "")

    out = []
    w = out.append

    # Header
    lines = ";".join(urllib.parse.quote(l.replace("{school_line}", sline)) for l in about["typing_lines"])
    w(f'<div align="left">\n\n[![Typing SVG](https://readme-typing-svg.demolab.com?font={font}&weight=600'
      f'&size=22&pause=900&color={color}&width=560&lines={lines})](https://ralphkgm.tech)\n\n</div>\n')
    w(about.get("intro", "").strip() + "\n")
    if about.get("how_i_work"):
        w(f"> {about['how_i_work']}\n")

    # Now
    if cfg.get("now"):
        w("### 🔨 working on now\n")
        for item in cfg["now"]:
            w(f"- {item['text']}")
        w("")

    # Skills
    sk = cfg.get("skills", {})
    levels = [("comfortable", "comfortable with", "used across several of my projects"),
              ("used_in_projects", "have used in projects", "built at least one real project with it"),
              ("learning", "learning", "early days, still figuring it out")]
    if any(sk.get(k) for k, _, _ in levels):
        w("### 🧰 skills (honest version)\n")
        w("| level | what that means | |\n|---|---|---|")
        for key, label, meaning in levels:
            if sk.get(key):
                w(f"| **{label}** | {meaning} | " + " ".join(badge(s["name"], s.get("icon"), color) for s in sk[key]) + " |")
        w("")

    # Featured
    feats = [f for f in cfg.get("featured", []) if f["repo"] in by_name]
    if feats:
        w("### ⭐ featured projects\n")
        w("<table>")
        for i in range(0, len(feats), 2):
            w("<tr>")
            for f in feats[i:i + 2]:
                r = by_name[f["repo"]]
                title = f.get("title", r["name"])
                blurb = f.get("blurb") or r.get("description") or ""
                meta = " · ".join(x for x in [
                    f.get("language") or main_lang(r),
                    f"★ {r['stargazers_count']}" if r["stargazers_count"] else "",
                    f"updated {month_year(r['pushed_at'])}"] if x)
                demo = f' · <a href="{r["homepage"]}">live demo</a>' if r.get("homepage") else ""
                w(f'<td width="50%" valign="top">\n\n**[{title}]({r["html_url"]})**<br>\n{blurb}<br>\n'
                  f'<sub>{meta}{demo}</sub>\n\n</td>')
            w("</tr>")
        w("</table>\n")

    # Recently updated
    if auto.get("show_recent_repos", True) and listed:
        featured_names = {f["repo"] for f in feats}
        recent = [r for r in listed if r["name"] not in featured_names][: auto.get("recent_repos_count", 5)]
        if recent:
            w("<details>\n<summary><b>📂 more public repos (recently updated first)</b></summary>\n")
            for r in recent:
                desc = f": {r['description']}" if r.get("description") else ""
                lang = f" `{main_lang(r)}`" if main_lang(r) else ""
                w(f"- [{r['name']}]({r['html_url']}){lang}{desc} <sub>updated {month_year(r['pushed_at'])}</sub>")
            w(f"\n[see all repos →](https://github.com/{USER}?tab=repositories)\n\n</details>\n")

    # Languages
    if auto.get("show_languages", True) and listed:
        totals = {}
        for r in listed:
            for lang, n in langs.get(r["name"], {}).items():
                if lang not in ignore:
                    totals[lang] = totals.get(lang, 0) + n
        top = sorted(totals.items(), key=lambda kv: -kv[1])[: auto.get("languages_count", 8)]
        whole = sum(totals.values()) or 1
        if top:
            w("### 📊 what my public code is actually written in\n")
            w("<sub>Measured from my public repos by the GitHub API, refreshed daily. Private repos are not counted.</sub>\n")
            w("```text")
            width = max(len(l) for l, _ in top)
            for lang, n in top:
                pct = n / whole * 100
                bar = "█" * round(pct / 5) + "░" * (20 - round(pct / 5))
                w(f"{lang.ljust(width)}  {bar}  {pct:5.1f}%")
            w("```\n")

    # Activity
    if auto.get("show_activity", True):
        events = safe(lambda: api(f"/users/{USER}/events/public?per_page=100"), [])
        rows, seen = [], set()
        for e in events:
            repo = e["repo"]["name"].split("/", 1)[-1]
            if repo in exclude:
                continue
            link = f"[{repo}](https://github.com/{e['repo']['name']})"
            p, t = e.get("payload", {}), e["type"]
            if t == "PushEvent":
                txt = f"pushed to {link}"
            elif t == "CreateEvent" and p.get("ref_type") == "repository":
                txt = f"created {link}"
            elif t == "PublicEvent":
                txt = f"made {link} public"
            elif t == "ReleaseEvent":
                txt = f"released {p.get('release', {}).get('tag_name', '')} of {link}"
            elif t == "PullRequestEvent" and p.get("action") in ("opened", "closed"):
                verb = "merged" if p.get("pull_request", {}).get("merged") else p["action"]
                txt = f"{verb} a pull request in {link}"
            else:
                continue
            line = f"- {txt} <sub>{month_day(e['created_at'])}</sub>"
            if txt in seen:  # one line per repo action, newest first
                continue
            seen.add(txt)
            rows.append(line)
            if len(rows) >= auto.get("activity_count", 6):
                break
        if rows:
            w("### ⚡ recent public activity\n")
            w("\n".join(rows) + "\n")

    # Stats
    if listed or user:
        stars = sum(r["stargazers_count"] for r in listed)
        since = user.get("created_at", "")[:4]
        w("### 📈 numbers\n")
        bits = [f"**{len(listed)}** public projects", f"**{stars}** stars"]
        if since:
            bits.append(f"on GitHub since **{since}**")
        w(" · ".join(bits) + "\n")
    if auto.get("show_streak", True):
        w(f'<p align="center"><img src="https://streak-stats.demolab.com?user={USER}&theme=tokyonight&hide_border=true" '
          f'alt="streak" /></p>\n')
    if auto.get("show_snake", True):
        base = f"https://raw.githubusercontent.com/{USER}/{USER}/output"
        w('<picture>\n'
          f'  <source media="(prefers-color-scheme: dark)" srcset="{base}/github-snake-dark.svg" />\n'
          f'  <source media="(prefers-color-scheme: light)" srcset="{base}/github-snake.svg" />\n'
          f'  <img alt="contribution snake" src="{base}/github-snake.svg" />\n</picture>\n')

    # Links
    if cfg.get("links"):
        w("### 📬 find me\n")
        w("&nbsp;".join(f"[{badge(l['label'], l.get('icon'), color)}]({l['url']})" for l in cfg["links"]) + "\n")

    # Footer: changes once a month so GitHub never disables the daily schedule for inactivity
    w(f"<!-- built from profile.toml by scripts/build_readme.py. Edit profile.toml, not this file. "
      f"refreshed: {TODAY:%Y-%m} -->")

    (ROOT / "README.md").write_text("\n".join(out).rstrip() + "\n")
    print(f"README.md written ({len(listed)} public repos, {len(feats)} featured)")


if __name__ == "__main__":
    main()
