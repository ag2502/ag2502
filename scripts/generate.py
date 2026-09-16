#!/usr/bin/env python3
"""Render assets/pr-light.svg and assets/pr-dark.svg from profile.config.json.

    python3 scripts/generate.py              # live GitHub data
    python3 scripts/generate.py --demo       # offline sample data
    python3 scripts/generate.py --handle foo # override the account

A GITHUB_TOKEN in the environment unlocks contribution counts and streaks.
"""

import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gh  # noqa: E402
import svg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def stamp_readme(path):
    """Bump a ?v= stamp on the card URLs in the README.

    GitHub serves README images through its own image cache, keyed on a URL
    that otherwise never changes - so a redrawn card can keep showing the old
    version for a while. Changing the query string each render makes it a new
    URL, and the theme fragment stays at the end where GitHub needs it.
    """
    if not os.path.exists(path):
        return
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M")
    with open(path, encoding="utf-8") as fh:
        before = fh.read()
    after = re.sub(
        r"(\./assets/pr-(?:light|dark)\.svg)(?:\?v=[^\"#]*)?",
        lambda m: "%s?v=%s" % (m.group(1), stamp),
        before,
    )
    if after != before:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(after)
        print("  stamped README.md with ?v=%s" % stamp)


def main():
    args = sys.argv[1:]
    config_path = os.path.join(ROOT, "profile.config.json")
    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)

    handle = config.get("handle") or os.environ.get("GITHUB_REPOSITORY_OWNER")
    if "--handle" in args:
        handle = args[args.index("--handle") + 1]
    if not handle:
        sys.exit("no handle: set \"handle\" in profile.config.json or pass --handle")

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("PROFILE_TOKEN")
    demo = "--demo" in args
    if demo:
        data = gh.demo()
        print("> using demo data")
    else:
        data = gh.collect(handle, token)

    # A rate-limited or offline run must never overwrite a good card with an
    # empty one: bail out and leave the committed SVGs in place.
    if not demo and not data.get("repos"):
        sys.exit("aborting: GitHub returned no repositories (rate limited or "
                 "offline). The existing assets were left untouched.")

    # Static config values are addressable as tokens too, so a field like
    # "web" can be written once in the config and used anywhere in the copy.
    for key, value in config.items():
        if isinstance(value, (str, int, float)) and key not in data:
            data[key] = value

    out_dir = os.path.join(ROOT, "assets")
    os.makedirs(out_dir, exist_ok=True)
    for theme in ("light", "dark"):
        markup = svg.render(config, data, theme)
        path = os.path.join(out_dir, "pr-%s.svg" % theme)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(markup)
        print("  wrote assets/pr-%s.svg (%.1f kB)" % (theme, len(markup) / 1024))

    with open(os.path.join(out_dir, "data.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    print("  wrote assets/data.json")

    stamp_readme(os.path.join(ROOT, "README.md"))


if __name__ == "__main__":
    main()
