# Profile card — setup

Your GitHub profile README, rendered as a pull request. Two SVGs (light and dark) are
redrawn every day from live GitHub data by a scheduled Action, so the numbers never go stale.

## Put it live

1. Create a **public** repository named exactly `ag2502` — a repo whose name matches your
   username is what GitHub shows at the top of your profile.
2. Copy the contents of this folder into it and push to `main`:

   ```bash
   git init -b main
   git add .
   git commit -m "feat: profile card"
   git remote add origin git@github.com:ag2502/ag2502.git
   git push -u origin main
   ```

3. On the repo: **Settings → Actions → General → Workflow permissions** → tick
   *Read and write permissions*. The Action needs it to commit the redrawn SVGs.
4. **Actions → profile card → Run workflow** to render it once immediately, then visit
   <https://github.com/ag2502>.

## Change what it says

Everything readable lives in [`profile.config.json`](profile.config.json) — the title, the
diff hunks, the checks, the checklist, the merge note, the footer links. No code to touch.

Values in `{{double braces}}` are filled in from live data at render time:

| Token | Meaning |
| --- | --- |
| `{{commits}}` | Commit contributions in the last year |
| `{{contributions}}` | All contributions in the last year |
| `{{streak}}` | Current day streak |
| `{{repos}}` | Public non-fork repos |
| `{{stars}}` | Stars across your repos |
| `{{top_language}}` | Most-used language, weighted so recent work counts more |
| `{{languages_top3}}` | Top three languages |
| `{{active_repos}}` | Repos pushed in the last 30 days |
| `{{top_repo}}` | Most recently pushed repo |
| `{{years_on_github}}` | Years since you joined |
| `{{today}}` | Render date |

Add `"require": "streak"` to any check or checklist row to hide it when that value is
unavailable. Write a fallback with a pipe: `{{streak|just started}}`.

## Run it locally

```bash
python3 scripts/generate.py           # live data (anonymous: no streak or contributions)
python3 scripts/generate.py --demo    # offline sample data
```

Export a personal access token as `GITHUB_TOKEN` to get contribution counts locally too.
Only `public_repo` scope is needed.

## Notes on how it is built

- **No dependencies.** Standard-library Python and hand-written SVG.
- **Nothing depends on animation.** GitHub serves README images inside an `<img>` tag, and
  WebKit freezes such an image's animation timeline at t=0 while still applying the
  keyframes' starting state — so anything faded or slid in would stay invisible for every
  Safari visitor. The card is fully legible with no animation at all; only the blinking
  caret and the pulse behind the merge button move, and both look correct frozen.
- **Every network call degrades.** No token, rate limit, or offline just means the affected
  row falls back or disappears; the card still renders.
- **Light and dark** are separate files, swapped by GitHub's `#gh-light-mode-only` and
  `#gh-dark-mode-only` fragments.
