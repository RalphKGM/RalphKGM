# How to edit this profile

**Edit `profile.toml` and nothing else.** `README.md` is generated. Anything you type into it gets overwritten.

The easiest way is on github.com: open `profile.toml`, click the pencil, make your change, and click **Commit changes**. About a minute later the README updates.

## Common changes

| I want to... | Do this in `profile.toml` |
|---|---|
| Change the intro | Edit `intro` under `[about]` |
| Change the animated header lines | Edit `typing_lines`. `{school_line}` fills in your year level automatically (e.g. "3rd year BSCS @ Mapúa Makati"). |
| Remove the AI-tools note | Delete the `how_i_work` line |
| Move a skill up a level | Cut the line from `learning` and paste it into `used_in_projects` or `comfortable` |
| Add a skill | Add `{ name = "Go", icon = "go" },`. Find icon names at [simpleicons.org](https://simpleicons.org) (lowercase, no spaces). A wrong icon name just shows the badge without a logo. |
| Add something to "working on now" | Copy a `[[now]]` block and change `text` |
| Feature a project | Copy a `[[featured]]` block. `repo` must be the exact name of a **public** repo. Projects are shown in the order you list them. |
| Un-feature a project | Delete its `[[featured]]` block. It still shows under "more public repos". |
| Hide a repo everywhere | Add its name to `exclude_repos` under `[auto]` |
| Turn a section off | Set `show_activity`, `show_languages`, `show_streak`, `show_snake`, or `show_recent_repos` to `false` |
| After graduating | Set `graduated = true` under `[school]` |
| Change the accent color | Change `color` under `[header]` (hex, no `#`) |

## What updates by itself (daily)

- Year level in the header (rolls over every August)
- Language bar, measured from your public repos
- Featured project details: main language, stars, and last updated
- "More public repos" list, newest first
- Recent public activity
- Public project and star counts
- Contribution snake and streak card

Private repos never show up. The builder only sees public data.

## Running it by hand

Go to the **Actions** tab, pick **Update README**, and click **Run workflow**.

Locally (Python 3.11+): `GITHUB_TOKEN=$(gh auth token) python3 scripts/build_readme.py`

## If something breaks

- **The README didn't update:** open the Actions tab and click the red run to see the error. The usual cause is a typo in `profile.toml`, like a missing quote or comma. You can paste the file into [toml-lint.com](https://www.toml-lint.com) to find it.
- **The snake is off by default:** it needs the **Contribution snake** workflow to run once (Actions tab, Run workflow). After it succeeds, set `show_snake = true`.
- **The streak card is blank:** that's an outside service having a bad day. It comes back on its own.
