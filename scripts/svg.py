"""Renders the profile card as a GitHub pull request, in SVG.

No dependencies: text widths are estimated, so everything is positioned with
plain arithmetic. Two themes are emitted (light / dark) and swapped in the
README with GitHub's #gh-light-mode-only / #gh-dark-mode-only fragments.
"""

W = 880
X = 24                 # card left edge
CW = W - 2 * X         # card width
ROW = 23               # diff line height

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

THEMES = {
    "light": {
        "bg": "#ffffff", "subtle": "#f6f8fa", "border": "#d1d9e0", "line": "#d1d9e0",
        "text": "#1f2328", "muted": "#59636e", "link": "#0969da",
        "green": "#1f883d", "greenText": "#1a7f37", "red": "#cf222e",
        "add": "#e6ffec", "del": "#ffebe9", "addNum": "#cdf2d5", "delNum": "#ffd7d5",
        "tab": "#fd8c73", "white": "#ffffff", "shadow": "0.06", "key": "#0550ae",
    },
    "dark": {
        "bg": "#0d1117", "subtle": "#151b23", "border": "#3d444d", "line": "#2f363d",
        "text": "#e6edf3", "muted": "#9198a1", "link": "#4493f8",
        "green": "#238636", "greenText": "#3fb950", "red": "#f85149",
        "add": "#0f2d1a", "del": "#2a1618", "addNum": "#16391f", "delNum": "#3c1a1d",
        "tab": "#fd8c73", "white": "#ffffff", "shadow": "0.4", "key": "#79c0ff",
    },
}

ICON_PR = ("M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 "
           "3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A3 3 0 0 1 14 5.5v5.628a2.251 2.251 0 "
           "1 1-1.5 0V5.5a1.5 1.5 0 0 0-1.5-1.5h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 "
           "1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 "
           "0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z")
ICON_CHECK_FILL = ("M8 16A8 8 0 1 1 8 0a8 8 0 0 1 0 16Zm3.78-9.72a.751.751 0 0 0-.018-1.042.751.751 0 0 "
                   "0-1.042-.018L6.75 9.19 5.28 7.72a.751.751 0 0 0-1.042.018.751.751 0 0 0-.018 1.042l2 "
                   "2a.75.75 0 0 0 1.06 0Z")
ICON_TICK = "M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L1.72 8.78a.75.75 0 1 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"
ICON_MERGE = ("M5.45 5.154A4.25 4.25 0 0 0 9.25 7.5h1.378a2.251 2.251 0 1 1 0 1.5H9.25A5.734 5.734 0 0 1 5 "
              "7.123v3.505a2.25 2.25 0 1 1-1.5 0V5.372a2.25 2.25 0 1 1 1.95-.218ZM4.25 13.5a.75.75 0 1 0 "
              "0-1.5.75.75 0 0 0 0 1.5Zm8.5-4.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM5 3.25a.75.75 0 1 0 "
              "0 .005V3.25Z")

_NARROW = set("ilj|.,:;'\"!()[]{}ftIr")
_WIDE = set("MWMmwABCDEFGHJKLNOPQRSTUVXYZ@")

ANIM = {"fade": "a", "pop": "p", "slide": "s"}


def w_sans(s, size, bold=False):
    total = 0.0
    for ch in s:
        if ch in _NARROW:
            total += 0.32
        elif ch in _WIDE:
            total += 0.72
        elif ch == " ":
            total += 0.28
        elif ch.isdigit():
            total += 0.56
        else:
            total += 0.545
    return total * size * (1.045 if bold else 1.0)


def w_mono(s, size):
    return len(s) * size * 0.6


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def anim(cls, delay=None):
    """Class attribute for one element. Content is deliberately never animated.

    An SVG that GitHub shows in a README is loaded as an <img>, and WebKit
    holds such an image's animation timeline at t=0 while still applying the
    keyframes' `from` state. Anything faded or slid in is therefore invisible
    for every Safari visitor. So only decoration that is *correct when frozen
    at t=0* gets animation here: the caret (blinks from visible) and the merge
    halo (fades up from nothing). Everything else renders statically.
    """
    if cls in ("caret", "pulse"):
        return ' class="%s"' % cls
    return ""


def txt(x, y, s, size=12.5, fill="#000", mono=False, bold=False, anchor="start", cls="", op=None):
    attrs = [
        'x="%s"' % round(x, 1), 'y="%s"' % round(y, 1),
        'font-size="%s"' % size, 'fill="%s"' % fill,
    ]
    if bold:
        attrs.append('font-weight="600"')
    if anchor != "start":
        attrs.append('text-anchor="%s"' % anchor)
    cls_attr = anim(cls, op)
    if mono:
        if 'class="' in cls_attr:
            cls_attr = cls_attr.replace('class="', 'class="m ', 1)
        else:
            cls_attr = ' class="m"' + cls_attr
    return "<text %s%s>%s</text>" % (" ".join(attrs), cls_attr, esc(s))


def icon(path, x, y, fill, size=16, cls="", delay=None):
    scale = size / 16.0
    return ('<g transform="translate(%s,%s) scale(%.4f)"><path fill="%s" d="%s"%s/></g>'
            % (round(x, 1), round(y, 1), scale, fill, path, anim(cls, delay)))


def rect(x, y, w, h, fill, r=0, stroke=None, cls="", delay=None):
    extra = ""
    if stroke:
        extra += ' stroke="%s"' % stroke
    extra += anim(cls, delay)
    return ('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"%s/>'
            % (round(x, 1), round(y, 1), round(w, 1), round(h, 1), r, fill, extra))


def top_rounded(x, y, w, h, r, fill):
    return ('<path fill="%s" d="M%s %sh%sa%s %s 0 0 1 %s %sv%sh%sv%sa%s %s 0 0 1 %s %sz"/>'
            % (fill, round(x + r, 1), round(y, 1), round(w - 2 * r, 1), r, r, r, r,
               round(h - r, 1), round(-w, 1), round(-(h - r), 1), r, r, r, -r))


def hline(x, y, w, color, op=1.0):
    return ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1" opacity="%s"/>'
            % (round(x, 1), round(y, 1), round(x + w, 1), round(y, 1), color, op))


CSS = """
text{font-family:%s}
.m{font-family:%s}
.caret{animation:blink 1.15s steps(1,end) infinite}
.pulse{animation:pulse 2.8s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes blink{50%%{opacity:0}}
@keyframes pulse{0%%,100%%{opacity:0;transform:scale(1)}50%%{opacity:.22;transform:scale(1.05)}}
@media (prefers-reduced-motion:reduce){.caret,.pulse{animation:none}}
""" % (SANS, MONO)


def fmt(value):
    if value == "":
        return ""      # an unset config field renders as nothing, not a dash
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return "{:,}".format(value)
    if isinstance(value, float):
        return ("%g" % value)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def interpolate(s, data):
    """Replace {{key}} and {{key|fallback}} with values from `data`."""
    out = str(s)
    while "{{" in out and "}}" in out:
        start = out.index("{{")
        end = out.index("}}", start)
        token = out[start + 2:end].strip()
        key, _, fallback = token.partition("|")
        value = data.get(key.strip())
        if value in (None, "", []) and fallback:
            rendered = fallback.strip()
        else:
            rendered = fmt(value)
        out = out[:start] + rendered + out[end + 2:]
    return out


def render(config, data, theme="light"):
    c = THEMES[theme]
    p = []
    delay = [0.0]

    def next_delay(step=0.055):
        delay[0] += step
        return round(delay[0], 3)

    def I(s):
        return interpolate(s, data)

    def available(item):
        """Drop rows whose data is missing, e.g. a streak with no token."""
        need = item.get("require")
        return data.get(need) not in (None, "", [], 0) if need else True

    diffs = config.get("diffs", [])
    checks = [ch for ch in config.get("checks", []) if available(ch)]
    reviewers = [r for r in config.get("reviewers", []) if available(r)]

    # ---------------------------------------------------------------- header
    y = 40
    title = I(config.get("title", "feat: update profile"))
    p.append('<text x="%s" y="%s" font-size="21" font-weight="600" fill="%s">'
             '%s <tspan fill="%s" font-weight="400">#%s</tspan></text>'
             % (X, y, c["text"], esc(title), c["muted"], esc(config.get("pr_number", 1))))

    y += 22
    pill_label = config.get("state", "Open")
    pill_w = 22 + 6 + w_sans(pill_label, 12.5, True) + 16
    p.append(rect(X, y, pill_w, 26, c["green"], r=13, cls="pop"))
    p.append(icon(ICON_PR, X + 13, y + 6, c["white"], 14, cls="pop"))
    p.append(txt(X + 33, y + 18, pill_label, 12.5, c["white"], bold=True, cls="pop"))

    commits = fmt(data.get("commits"))
    sub_x = X + pill_w + 12
    p.append('<text x="%s" y="%s" font-size="12.5" fill="%s">'
             '<tspan font-weight="600" fill="%s">%s</tspan> wants to merge '
             '<tspan font-weight="600" fill="%s">%s commits</tspan> into '
             '<tspan class="m" font-weight="600" fill="%s">%s</tspan> from '
             '<tspan class="m" font-weight="600" fill="%s">%s</tspan></text>'
             % (sub_x, y + 18, c["muted"], c["text"], esc(data.get("handle", "")),
                c["text"], commits, c["text"], esc(config.get("base", "main")),
                c["text"], esc(config.get("head", "profile"))))

    # ------------------------------------------------------------------ tabs
    y += 46
    tabs = [
        ("Conversation", len(reviewers)),
        ("Commits", data.get("commits")),
        ("Checks", len(checks)),
        ("Files changed", len(diffs)),
    ]
    tx = X
    for i, (label, count) in enumerate(tabs):
        active = i == len(tabs) - 1
        p.append(txt(tx, y, label, 12.5, c["text"] if active else c["muted"],
                     bold=active, cls="fade", op=0.12 + i * 0.05))
        tw = w_sans(label, 12.5, active)
        if count not in (None, ""):
            badge = fmt(count)
            bw = w_sans(badge, 11) + 14
            p.append(rect(tx + tw + 7, y - 12, bw, 17, c["subtle"], r=8,
                          stroke=c["border"], cls="fade", delay=0.12 + i * 0.05))
            p.append(txt(tx + tw + 7 + bw / 2, y + 1, badge, 11, c["muted"],
                         anchor="middle", cls="fade", op=0.12 + i * 0.05))
            tw += bw + 7
        if active:
            p.append(rect(tx - 2, y + 11, tw + 4, 2, c["tab"], r=1, cls="fade",
                          delay=0.12 + i * 0.05))
        tx += tw + 26
    y += 13
    p.append(hline(X, y, CW, c["line"]))
    y += 26

    # ------------------------------------------------------------ whoami
    intro = config.get("intro")
    if intro:
        line_h = 22
        head_h = 40
        rows = []
        for row in intro.get("rows", []):
            key = row[0] if len(row) else ""
            raw = row[1] if len(row) > 1 else ""
            values = raw if isinstance(raw, list) else [raw]
            values = [v for v in (I(str(v)) for v in values) if v.strip()]
            if not values:
                continue  # an unset value (no web link yet) drops its row
            rows.append((key, values[0]))
            for extra in values[1:]:
                rows.append(("", extra))

        if rows:
            key_w = max(w_mono(k + ":", 12.5) for k, _ in rows) + 16
            card_h = head_h + line_h * len(rows) + 14
            p.append(rect(X, y, CW, card_h, c["bg"], r=6, stroke=c["border"]))
            p.append(top_rounded(X + 0.5, y + 0.5, CW - 1, head_h, 5.5, c["subtle"]))
            p.append(hline(X, y + head_h, CW, c["border"]))
            p.append('<text x="%s" y="%s" font-size="12.5" fill="%s">'
                     '<tspan font-weight="600" fill="%s">%s</tspan> commented'
                     '<tspan fill="%s">  \u00b7  opened this pull request</tspan></text>'
                     % (X + 16, y + 25, c["muted"], c["text"], esc(data.get("handle", "")),
                        c["muted"]))
            p.append(txt(X + CW - 16, y + 25, I(intro.get("file", "")), 12,
                         c["muted"], mono=True, anchor="end"))
            for i, (key, value) in enumerate(rows):
                ry = y + head_h + 12 + line_h * i + 4
                if key:
                    p.append(txt(X + 16, ry, key + ":", 12.5, c["key"], mono=True, bold=True))
                p.append(txt(X + 16 + key_w, ry, value[:96], 12.5, c["text"], mono=True))
            y += card_h + 16

    # ----------------------------------------------------------------- diffs
    delay[0] = 0.2
    for di, d in enumerate(diffs):
        is_last_diff = di == len(diffs) - 1
        lines = d.get("lines", [])
        adds = sum(1 for ln in lines if ln[0] == "add")
        dels = sum(1 for ln in lines if ln[0] == "del")
        body_h = ROW * len(lines) + 8
        card_h = 38 + body_h
        p.append(rect(X, y, CW, card_h, c["bg"], r=6, stroke=c["border"], cls="fade",
                      delay=next_delay(0.09)))
        p.append(top_rounded(X + 0.5, y + 0.5, CW - 1, 38, 5.5, c["subtle"]))
        p.append(hline(X, y + 38, CW, c["border"]))
        p.append(txt(X + 16, y + 24, I(d.get("file", "file")), 12.5, c["text"], mono=True, bold=True))
        p.append('<text x="%s" y="%s" font-size="11.5" text-anchor="end" class="m">'
                 '<tspan fill="%s" font-weight="600">+%d</tspan> '
                 '<tspan fill="%s" font-weight="600">−%d</tspan></text>'
                 % (X + CW - 16, y + 24, c["greenText"], adds, c["red"], dels))

        old_no, new_no = d.get("start", 1), d.get("start", 1)
        ly = y + 38
        last_add = max((i for i, ln in enumerate(lines) if ln[0] == "add"), default=-1)
        for i, ln in enumerate(lines):
            kind, content = ln[0], I(ln[1] if len(ln) > 1 else "")
            content = content[:92]
            row_y = ly + ROW * i
            if kind == "add":
                p.append(rect(X + 1, row_y, CW - 2, ROW, c["add"], cls="fade", delay=next_delay()))
                p.append(rect(X + 1, row_y, 78, ROW, c["addNum"]))
            elif kind == "del":
                p.append(rect(X + 1, row_y, CW - 2, ROW, c["del"], cls="fade", delay=next_delay()))
                p.append(rect(X + 1, row_y, 78, ROW, c["delNum"]))
            else:
                next_delay(0.02)

            base_y = row_y + 16
            left = "" if kind == "add" else str(old_no)
            right = "" if kind == "del" else str(new_no)
            p.append(txt(X + 34, base_y, left, 11, c["muted"], mono=True, anchor="end"))
            p.append(txt(X + 72, base_y, right, 11, c["muted"], mono=True, anchor="end"))
            marker = {"add": "+", "del": "−"}.get(kind, " ")
            marker_fill = {"add": c["greenText"], "del": c["red"]}.get(kind, c["muted"])
            p.append(txt(X + 88, base_y, marker, 12.5, marker_fill, mono=True, bold=True))
            body_fill = c["text"] if kind != "del" else c["muted"]
            cls = "slide" if kind in ("add", "del") else "fade"
            p.append(txt(X + 102, base_y, content, 12.5, body_fill, mono=True, cls=cls,
                         op=round(delay[0], 3)))
            if i == last_add and is_last_diff:
                cx = X + 102 + w_mono(content, 12.5) + 2
                p.append(rect(cx, row_y + 4, 7.5, 15, c["greenText"], cls="caret"))
            if kind != "add":
                old_no += 1
            if kind != "del":
                new_no += 1
        y += card_h + 16

    # ---------------------------------------------------------------- checks
    if checks:
        head_h = 44
        row_h = 40
        card_h = head_h + row_h * len(checks)
        p.append(rect(X, y, CW, card_h, c["bg"], r=6, stroke=c["border"], cls="fade",
                      delay=next_delay(0.08)))
        p.append(top_rounded(X + 0.5, y + 0.5, CW - 1, head_h, 5.5, c["subtle"]))
        p.append(hline(X, y + head_h, CW, c["border"]))
        p.append(icon(ICON_CHECK_FILL, X + 16, y + 14, c["greenText"], 16, cls="pop",
                      delay=next_delay()))
        p.append('<text x="%s" y="%s" font-size="13" fill="%s" font-weight="600">'
                 'All checks have passed<tspan fill="%s" font-weight="400" font-size="12.5">'
                 '  ·  %d successful checks</tspan></text>'
                 % (X + 40, y + 27, c["text"], c["muted"], len(checks)))
        for i, ch in enumerate(checks):
            ry = y + head_h + row_h * i
            if i:
                p.append(hline(X + 1, ry, CW - 2, c["line"], 0.7))
            d0 = next_delay(0.07)
            p.append(icon(ICON_CHECK_FILL, X + 16, ry + 12, c["greenText"], 15, cls="pop", delay=d0))
            name = I(ch.get("name", ""))
            p.append(txt(X + 42, ry + 25, name, 12.5, c["text"], mono=True, bold=True,
                         cls="fade", op=d0))
            nx = X + 42 + w_mono(name, 12.5) + 10
            p.append(txt(nx, ry + 25, I(ch.get("detail", "")), 12, c["muted"], cls="fade", op=d0))
            p.append(txt(X + CW - 16, ry + 25, I(ch.get("value", "")), 12, c["link"],
                         anchor="end", cls="fade", op=d0))
        y += card_h + 16

    # ------------------------------------------------------------- reviewers
    if reviewers:
        head_h = 40
        row_h = 30
        card_h = head_h + row_h * len(reviewers) + 10
        p.append(rect(X, y, CW, card_h, c["bg"], r=6, stroke=c["border"], cls="fade",
                      delay=next_delay(0.08)))
        p.append(top_rounded(X + 0.5, y + 0.5, CW - 1, head_h, 5.5, c["subtle"]))
        p.append(hline(X, y + head_h, CW, c["border"]))
        pending = sum(1 for r in reviewers if not r.get("done", True))
        p.append('<text x="%s" y="%s" font-size="12.5" fill="%s" font-weight="600">'
                 'Reviewer checklist<tspan fill="%s" font-weight="400">  ·  %d pending'
                 '</tspan></text>' % (X + 16, y + 25, c["text"], c["muted"], pending))
        for i, r in enumerate(reviewers):
            ry = y + head_h + 8 + row_h * i
            d0 = next_delay(0.07)
            done = r.get("done", True)
            if done:
                p.append(rect(X + 17, ry + 6, 15, 15, c["green"], r=4, cls="pop", delay=d0))
                p.append(icon(ICON_TICK, X + 19.5, ry + 8.5, c["white"], 10, cls="pop", delay=d0))
            else:
                p.append(rect(X + 17, ry + 6, 15, 15, "none", r=4, stroke=c["muted"],
                              cls="pop", delay=d0))
            fill = c["link"] if r.get("link") else c["text"]
            p.append(txt(X + 42, ry + 18, I(r.get("label", "")), 12.5, fill,
                         bold=bool(r.get("link")), cls="fade", op=d0))
        y += card_h + 16

    # ------------------------------------------------------------- merge box
    merge = config.get("merge", {})
    box_h = 76
    p.append(rect(X, y, CW, box_h, c["bg"], r=6, stroke=c["border"], cls="fade",
                  delay=next_delay(0.08)))
    btn_label = I(merge.get("button", "Merge pull request"))
    btn_w = 30 + w_sans(btn_label, 13.5, True) + 22
    by = y + (box_h - 38) / 2
    p.append(rect(X + 14, by - 2, btn_w + 4, 42, c["green"], r=8, cls="pulse"))
    p.append(rect(X + 16, by, btn_w, 38, c["green"], r=6))
    p.append(icon(ICON_MERGE, X + 30, by + 11, c["white"], 16, cls="pop"))
    p.append(txt(X + 54, by + 24, btn_label, 13.5, c["white"], bold=True, cls="pop"))
    note = I(merge.get("note", ""))
    p.append(txt(X + 16 + btn_w + 18, by + 18, note, 12.5, c["text"], cls="fade"))
    p.append(txt(X + 16 + btn_w + 18, by + 34, I(merge.get("note2", "")), 12, c["muted"], cls="fade"))
    y += box_h + 20

    # ---------------------------------------------------------------- footer
    links = config.get("links", [])
    lx = X
    for i, link in enumerate(links):
        label = I(link.get("label", ""))
        p.append(txt(lx, y, label, 12.5, c["link"], bold=True, cls="fade", op=next_delay()))
        lx += w_sans(label, 12.5, True)
        if i < len(links) - 1:
            p.append(txt(lx + 8, y, "·", 12.5, c["muted"]))
            lx += 20
    p.append(txt(X + CW, y, I(config.get("footer", "")), 11.5, c["muted"], anchor="end", cls="fade"))
    y += 16

    height = y + 10
    head = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'role="img" aria-label="%s" font-family="sans-serif">' % (W, height, W, height,
                                                                  esc(I(config.get("alt", title))))
    )
    parts = [head,
             "<title>%s</title>" % esc(I(config.get("alt", title))),
             "<style>%s</style>" % CSS,
             rect(0.5, 0.5, W - 1, height - 1, c["bg"], r=10, stroke=c["border"])]
    parts.extend(p)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
