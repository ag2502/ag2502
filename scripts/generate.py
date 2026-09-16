#!/usr/bin/env python3
"""Render assets/pr-light.svg and assets/pr-dark.svg from profile.config.json.

    python3 scripts/generate.py              # live GitHub data
    python3 scripts/generate.py --demo       # offline sample data
    python3 scripts/generate.py --handle foo # override the account

A GITHUB_TOKEN in the environment unlocks contribution counts and streaks.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gh  # noqa: E402
import svg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    if "--demo" in args:
        data = gh.demo()
        print("> using demo data")
    else:
        data = gh.collect(handle, token)

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


if __name__ == "__main__":
    main()
