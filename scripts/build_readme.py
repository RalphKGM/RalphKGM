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
q = lambda s: urllib.parse.quote(s, safe="")


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
    text = q(label.replace("-", "--").replace("_", "__"))
    return (f"![{label}](https://img.shields.io/badge/{text}-{bg}?style=for-the-badge"
            f"&logo={q(icon or '')}&logoColor={color})")


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def school_line(s):
    if s.get("graduated"):
        return f"{s['degree']} graduate, {s.get('short', s['name'])}"
    ay = TODAY.year if TODAY.month >= s.get("ay_start_month", 8) else TODAY.year - 1
    level = max(1, ay - s["start_year"] + 1)
    return f"{ordinal(level)} year {s['degree']} @ {s.get('short', s['name'])}"


def when(iso, fmt):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime(fmt)


def main():
    cfg = tomllib.loads((ROOT / "profile.toml").read_text())
    about, school, auto = cfg["about"], cfg["school"], cfg.get("auto", {})
    color = cfg.get("header", {}).get("color", "38BDF8")
    font = cfg.get("header", {}).get("font", "JetBrains+Mono")
    grad = cfg.get("header", {}).get("banner_colors", ["0EA5E9", "1E3A8A"])
    exclude = set(auto.get("exclude_repos", [])) | {USER}
    quiet = exclude | set(auto.get("quiet_repos", []))
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

    # ── Header: plain by default; banner / typing / badges are optional extras
    hdr = cfg.get("header", {})
    if hdr.get("show_banner", False):
        w(f'<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:{grad[0]},100:{grad[1]}'
          f'&height=190&section=header&text={q(about["name"])}&fontSize=44&fontColor=ffffff&fontAlignY=36'
          f'&desc={q(sline)}&descSize=18&descAlignY=58" alt="{about["name"]}" />\n')
    else:
        w(f'<h1 align="center">{about["name"]}</h1>\n')
        w(f'<p align="center">{sline}</p>\n')
    if hdr.get("show_typing", False) and about.get("typing_lines"):
        lines = ";".join(q(l.replace("{school_line}", sline)) for l in about["typing_lines"])
        w(f'<p align="center"><img src="https://readme-typing-svg.demolab.com?font={font}'
          f'&weight=600&size=20&pause=1000&color={color}&center=true&vCenter=true&width=520&lines={lines}" '
          f'alt="typing intro" /></p>\n')
    if cfg.get("links"):
        if hdr.get("link_style", "text") == "badges":
            imgs = []
            for l in cfg["links"]:
                label = q(l["label"].replace("-", "--").replace("_", "__"))
                src = (f"https://img.shields.io/badge/{label}-{l.get('color', color)}?style=for-the-badge"
                       f"&logo={q(l.get('icon', ''))}&logoColor=white")
                imgs.append(f'<a href="{l["url"]}"><img src="{src}" alt="{l["label"]}" /></a>')
            w('<p align="center">\n  ' + "\n  ".join(imgs) + "\n</p>\n")
        else:
            w('<p align="center">' + " &nbsp;·&nbsp; ".join(
                f'<a href="{l["url"]}">{l["label"]}</a>' for l in cfg["links"]) + "</p>\n")
    w("---\n")

    # ── About + how I work
    w("## 👋 about me\n")
    w(about.get("intro", "").strip() + "\n")
    if about.get("facts"):
        w("\n".join(f"- {f.replace('{school_line}', sline)}" for f in about["facts"]) + "\n")

    # ── Now
    if cfg.get("now"):
        w("## 🔨 working on now\n")
        for item in cfg["now"]:
            w(f"- {item['text']}")
        w("")

    # ── Featured
    feats = [f for f in cfg.get("featured", []) if f["repo"] in by_name]
    if feats:
        w("## ⭐ featured projects\n")
        w("<table>")
        for i in range(0, len(feats), 2):
            w("<tr>")
            for f in feats[i:i + 2]:
                r = by_name[f["repo"]]
                title = f"{f.get('emoji', '')} {f.get('title', r['name'])}".strip()
                blurb = f.get("blurb") or r.get("description") or ""
                meta = " · ".join(x for x in [
                    f.get("language") or main_lang(r),
                    f"★ {r['stargazers_count']}" if r["stargazers_count"] else "",
                    f"updated {when(r['pushed_at'], '%b %Y')}"] if x)
                demo = f' · <a href="{r["homepage"]}">live demo ↗</a>' if r.get("homepage") else ""
                w(f'<td width="50%" valign="top">\n\n### [{title}]({r["html_url"]})\n{blurb}\n\n'
                  f'<sub>{meta}{demo}</sub>\n\n</td>')
            w("</tr>")
        w("</table>\n")

    # ── More repos
    if auto.get("show_recent_repos", True) and listed:
        featured_names = {f["repo"] for f in feats}
        recent = [r for r in listed if r["name"] not in featured_names][: auto.get("recent_repos_count", 6)]
        if recent:
            w("<details>\n<summary><b>📂 more public repos</b> <sub>(recently updated first)</sub></summary>\n")
            for r in recent:
                desc = f": {r['description']}" if r.get("description") else ""
                lang = f" `{main_lang(r)}`" if main_lang(r) else ""
                w(f"- [{r['name']}]({r['html_url']}){lang}{desc} <sub>{when(r['pushed_at'], '%b %Y')}</sub>")
            w(f"\n[all repos →](https://github.com/{USER}?tab=repositories)\n\n</details>\n")

    # ── Skills
    sk = cfg.get("skills", {})
    levels = [("comfortable", "🟢 comfortable with", "used across several of my projects"),
              ("used_in_projects", "🟡 have used in projects", "built at least one real project with it"),
              ("learning", "🔵 learning", "early days, still figuring it out")]
    if any(sk.get(k) for k, _, _ in levels):
        w("## 🧰 skills <sub>(honest version)</sub>\n")
        for key, label, meaning in levels:
            items = sk.get(key) or []
            if not items:
                continue
            w(f"**{label}** <sub>{meaning}</sub>\n")
            icons = [s["icon"] for s in items if s.get("icon")]
            if icons:
                w(f'<img src="https://skillicons.dev/icons?i={",".join(icons)}&perline=14" alt="{key} icons" />\n')
            w("<sub>" + " · ".join(s["name"] for s in items) + "</sub>\n")

    # ── Languages + activity side by side
    lang_block, act_block = "", ""
    if auto.get("show_languages", True) and listed:
        totals = {}
        for r in listed:
            for lang, n in langs.get(r["name"], {}).items():
                if lang not in ignore:
                    totals[lang] = totals.get(lang, 0) + n
        top = sorted(totals.items(), key=lambda kv: -kv[1])[: auto.get("languages_count", 7)]
        whole = sum(totals.values()) or 1
        if top:
            width = max(len(l) for l, _ in top)
            rows = []
            for lang, n in top:
                pct = n / whole * 100
                filled = round(pct / 100 * 24)
                rows.append(f"{lang.ljust(width)} {'█' * filled}{'░' * (24 - filled)} {pct:4.1f}%")
            lang_block = ("**📊 languages in my public code**\n\n```text\n" + "\n".join(rows) +
                          "\n```\n<sub>measured by the GitHub API, private repos not counted</sub>")
    if auto.get("show_activity", True):
        events = safe(lambda: api(f"/users/{USER}/events/public?per_page=100"), [])
        rows, seen = [], set()
        for e in events:
            repo = e["repo"]["name"].split("/", 1)[-1]
            if repo in quiet:
                continue
            link = f"[{repo}](https://github.com/{e['repo']['name']})"
            p, t = e.get("payload", {}), e["type"]
            if t == "PushEvent":
                txt = f"pushed to {link}"
            elif t == "CreateEvent" and p.get("ref_type") == "repository":
                txt = f"created {link}"
            elif t == "PublicEvent":
                txt = f"open-sourced {link}"
            elif t == "ReleaseEvent":
                txt = f"released {p.get('release', {}).get('tag_name', '')} of {link}"
            elif t == "PullRequestEvent" and p.get("action") in ("opened", "closed"):
                verb = "merged" if p.get("pull_request", {}).get("merged") else p["action"]
                txt = f"{verb} a PR in {link}"
            else:
                continue
            if txt in seen:
                continue
            seen.add(txt)
            rows.append(f"- {txt} <sub>{when(e['created_at'], '%b %-d')}</sub>")
            if len(rows) >= auto.get("activity_count", 6):
                break
        if rows:
            act_block = "**⚡ recent public activity**\n\n" + "\n".join(rows)
    if lang_block or act_block:
        w("## 📈 activity\n")
        w("\n\n".join(b for b in (lang_block, act_block) if b) + "\n")

    stars = sum(r["stargazers_count"] for r in listed)
    since = user.get("created_at", "")[:4]
    if listed and auto.get("show_numbers", False):
        w(f'<p align="center"><sub><b>{len(listed)}</b> public projects · <b>{stars}</b> stars'
          + (f" · on GitHub since <b>{since}</b>" if since else "") + "</sub></p>\n")
    if auto.get("show_streak", True):
        st = f"https://streak-stats.demolab.com?user={USER}&hide_border=true&ring={color}&fire={color}&currStreakLabel={color}"
        w('<p align="center">\n<picture>\n'
          f'  <source media="(prefers-color-scheme: dark)" srcset="{st}&theme=tokyonight&background=0D1117" />\n'
          f'  <img src="{st}&theme=default&background=FFFFFF" alt="GitHub streak" />\n</picture>\n</p>\n')
    if auto.get("show_snake", False):
        base = f"https://raw.githubusercontent.com/{USER}/{USER}/output"
        w('<picture>\n'
          f'  <source media="(prefers-color-scheme: dark)" srcset="{base}/github-snake-dark.svg" />\n'
          f'  <img alt="contribution snake" src="{base}/github-snake.svg" />\n</picture>\n')

    if auto.get("show_views", True):
        w(f'<p align="center"><img src="https://komarev.com/ghpvc/?username={USER}&label=profile%20views&color=0d1117&style=flat-square" alt="profile views" /></p>\n')
    if hdr.get("show_banner", False):
        w(f'<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:{grad[1]},100:{grad[0]}'
          f'&height=110&section=footer" alt="" />\n')
    # Changes once a month so GitHub never disables the daily schedule for inactivity
    w(f"<!-- built from profile.toml by scripts/build_readme.py. Edit profile.toml, not this file. "
      f"refreshed: {TODAY:%Y-%m} -->")

    (ROOT / "README.md").write_text("\n".join(out).rstrip() + "\n")
    print(f"README.md written ({len(listed)} public repos, {len(feats)} featured)")


if __name__ == "__main__":
    main()
