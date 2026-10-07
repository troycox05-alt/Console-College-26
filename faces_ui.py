"""
faces_ui.py — The portrait-and-facts "hero" at the top of the player, coach and recruit screens.

    ╭──────────────────────╮ ╭─ PLAYER ───────────────────────────────────────────────╮
    │   (20x10 face)       │ │ Auburn Tigers · SEC                           [ JR ]    │
    │                      │ │ Wide Receiver · 6'2", 195 lbs · Alabama                 │
    │                      │ │ OVERALL 88  ████████████████░░░░    Potential A-         │
    ╰──────────────────────╯ ╰────────────────────────────────────────────────────────╯

The numbers rules are unchanged: in Coach Career the game shows words, not ratings (scout.hidden).
"""
import faces
from ui import C, bar, chip, columns, pad, paint, panel, rating

FACE_W = 26                         # the portrait panel: 20 columns of face + frame
HERO_H = 12                         # lines tall (10 of face + a caption)


def _face_panel(lines, color, caption="", height=HERO_H):
    body = [" " + ln for ln in lines]
    body.append("")
    body.append(pad(caption, FACE_W - 4, "center"))
    return panel(None, body, FACE_W, color=color, height=height)


def _hero(face_lines, color, title, right):
    right_w = 100 - FACE_W - 1
    return columns(_face_panel(face_lines, color, right.pop("caption", "")),
                   panel(title, right["lines"], right_w, color=color, title_color=color, height=HERO_H), gap=1)


def player_hero(league, p, color):
    """Portrait, identity, overall, development, morale and tags for one player."""
    import finance as fi
    import morale
    import scout
    import screens
    from models import POSITION_NAMES
    from recruiting_data import STATES
    team = p.team
    hide = scout.hidden(league)
    lines = []
    lines.append(paint(team.full_name, color, C.BOLD) + paint(f"  ·  {team.conference}", C.GRAY))
    home = STATES.get(getattr(p, "home_state", None), (None,))[0]
    lines.append(f"{POSITION_NAMES[p.position]}  ·  {p.height_str}, {p.weight} lbs"
                 + (paint(f"  ·  from {home}", C.GRAY) if home else ""))
    lines.append("")
    art = "an" if scout.ovr_word(p.overall)[0] in "AEIOUaeiou" else "a"
    if hide:
        lines.append(f"{paint('Looks like ' + art, C.GRAY)} {scout.ovr(p)}")
    else:
        pot = getattr(p, "potential_grade", "")
        lines.append(f"{paint('OVERALL', C.GRAY)} {rating(p.overall)}  {bar(p.overall, 24)}"
                     + (f"   {paint('Potential', C.GRAY)} {pot}" if pot else ""))
    lines.append(f"{paint('HS Recruit', C.GRAY)} {screens.stars(p.hs_stars)}   {paint('Development', C.GRAY)} "
                 f"{screens._dev_grade(p)}   {paint('Durability', C.GRAY)} {p.durability.lower()}"
                 + ("" if hide else f" ({p.fundamentals['injury']})"))
    ceil = (f"{p.prof_ceiling:.2f}" if not hide else "looks " + __import__("subprof").word(p.prof_ceiling))
    lines.append(paint(f"Offseasons developed {p.seasons_developed}  ·  ceiling at {p.position}: {ceil}", C.GRAY))
    amt = fi.player_nil(p)
    mv = morale.get(p)
    lines.append(f"{paint('Morale', C.GRAY)} {paint(f'{mv:.0f}', morale.color(mv), C.BOLD)} "
                 f"{paint(morale.word(mv), morale.color(mv))}   {paint('NIL', C.GRAY)} "
                 + (paint(fi.money(amt) + "/yr", C.BGREEN, C.BOLD) if amt else paint("none", C.GRAY)))
    flags = []
    if getattr(p, "inj_games", 0) > 0:
        flags.append(chip(f"OUT {p.inj_games} wk", C.BRED))
    if getattr(p, "generational", False):
        flags.append(chip("GENERATIONAL", C.BMAGENTA))
    tr = screens._transfer_from(p)
    if tr:
        flags.append(chip(f"TRANSFER · {tr}", C.BCYAN))
    try:
        from traits import labels
        for t in labels(p)[:3]:
            flags.append(chip(t, C.BYELLOW))
    except Exception:
        pass
    lines.append("")
    if flags:
        lines.append("  ".join(flags))
    log = [f"{why} ({d:+d})" for _, d, why in p.__dict__.get("mood_log", [])[-2:] if d]
    if log:
        lines.append(paint("lately: " + "; ".join(reversed(log)), C.GRAY))
    cap = f"{p.class_label}  ·  #{p.number}"
    return _hero(faces.player_portrait(p), color, p.position + " ", {"lines": lines, "caption": paint(cap, C.BWHITE, C.BOLD)})


def coach_hero(league, coach, role, where, color=C.BCYAN):
    """Portrait (cap, headset, hair that tells his age), job, rating, schemes, record and contract for a coach."""
    import carousel as cz
    import finance as fi
    import staff
    lines = []
    lines.append(paint(coach.name, C.BWHITE, C.BOLD) + "  " + chip({"HC": "HEAD COACH", "OC": "OFFENSIVE COORD.",
                                                                  "DC": "DEFENSIVE COORD."}.get(role, role), color))
    lines.append(paint(where, C.GRAY))
    lines.append("")
    upside = coach.ceiling - coach.overall
    potential = "maxed out" if upside <= 1 else "some room" if upside <= 5 else "high" if upside <= 12 else "very high"
    lines.append(f"{paint('OVERALL', C.GRAY)} {rating(coach.overall)}  {bar(coach.overall, 24)}   "
                 f"{paint('Potential', C.GRAY)} {potential}")
    fourth = "conservative" if coach.aggression < 42 else "aggressive" if coach.aggression >= 68 else "balanced"
    if role == "OC":
        sch = f"Offense: {coach.offense_scheme}"
    elif role == "DC":
        sch = f"Defense: {coach.defense_scheme}"
    else:
        sch = f"{coach.offense_scheme}  ·  {coach.defense_scheme}"
    lines.append(f"{paint('Scheme', C.GRAY)} {sch}   {paint('4th down', C.GRAY)} {fourth} ({coach.aggression})")
    hist = getattr(coach, "history", None) or []
    w = sum(s["w"] for s in hist)
    l = sum(s["l"] for s in hist)
    t = coach.team
    live = (role not in ("OC", "DC") and t is not None and getattr(t, "coach", None) is coach
            and not (hist and hist[-1].get("year") == league.year) and (t.wins or t.losses))
    if live:                                                   # this season isn't in the book yet
        w, l = w + t.wins, l + t.losses
    titles = sum(1 for s in hist if s.get("title"))
    lines.append(f"{paint('Career', C.GRAY)} " + (f"{w}-{l}" + (f"  ·  {titles} title{'s' if titles != 1 else ''}" if titles else "")
                                                 + paint(f"  ·  {len(hist) + bool(live)} season{'s' if len(hist) + bool(live) != 1 else ''}", C.GRAY)
                                                 if hist or live else paint("no games coached in this world yet", C.GRAY)))
    k = fi.contract(coach) if coach.team is not None else None
    if k:
        lines.append(f"{paint('Contract', C.GRAY)} {fi.deal_line(k, league)}")
    lines.append("")
    try:
        from traits import labels
        tags = [chip(t, C.BYELLOW) for t in labels(coach)[:4]]
        if tags:
            lines.append("  ".join(tags))
    except Exception:
        pass
    cap = f"age {coach.age}"
    return _hero(faces.coach_portrait(coach), color, "COACH ", {"lines": lines, "caption": paint(cap, C.BWHITE, C.BOLD)})


def recruit_header(r, first_line, extras, color):
    """The recruit card's top: his face beside the lines that used to run across the page."""
    lines = [first_line] + [x for x in extras if x]
    cap = paint(f"{r.stars}★  ·  No. {r.national_rank}", C.BYELLOW if r.stars >= 4 else C.BCYAN, C.BOLD)
    face = _face_panel(faces.recruit_portrait(r), color, cap)
    right = panel("PROSPECT ", lines, 100 - FACE_W - 1, color=color, title_color=color, height=HERO_H)
    return columns(face, right, gap=1)


# ═══ Pieces the other screens share ═════════════════════════════════════════

def beside(face_lines, lines, indent=3, gap=2, top=0):
    """A face (equal-width lines) on the left, text on the right, aligned from the top (or `top` rows down)."""
    from ui import visible_len
    fw = visible_len(face_lines[0]) if face_lines else 0
    n = max(len(face_lines) + top, len(lines))
    out = []
    for i in range(n):
        j = i - top
        f = face_lines[j] if 0 <= j < len(face_lines) else " " * fw
        t = lines[i] if i < len(lines) else ""
        out.append(" " * indent + f + " " * gap + t)
    return out


def mini_card(face_lines, lines, width, color, title=None):
    """A small boxed card: a mini face and a few lines (the awards, the draft's top picks)."""
    inner = width - 4
    body = beside(face_lines, lines, indent=0, gap=2)
    return panel(title, body, width, color=color, title_color=color)


def who_kind(m):
    """What sort of sender wrote this message -> (label, color)."""
    ref = m.get("ref")
    if ref is not None and hasattr(ref, "position"):
        return "PLAYER", C.BCYAN
    role = (m.get("role") or "").lower()
    if "coordinator" in role or role == "staff":
        return "STAFF", C.BMAGENTA
    if "athletic director" in role:
        return "AD", C.BYELLOW
    if "recruit" in role:
        return "RECRUITING", C.GRAY
    if role == "career":
        return "CAREER", C.BGREEN
    return "NOTE", C.GRAY


def sender_portrait(league, m, mini=False):
    """The face of whoever wrote a message (a player, a coordinator, the AD), or None for an office or a note."""
    if not faces.enabled():
        return None
    ref = m.get("ref")
    if ref is not None and hasattr(ref, "position"):
        return faces.player_portrait(ref, mini=mini)
    team = getattr(league, "user_team", None)
    name, role = m.get("sender", ""), (m.get("role") or "")
    if team is not None:
        for c in (getattr(team, "oc", None), getattr(team, "dc", None), team.coach):
            if c is not None and c.name == name:
                return faces.coach_portrait(c, mini=mini)
        if "Athletic Director" in role or name.startswith("AD "):
            ad = getattr(team, "ad", None) or {}
            return faces.exec_portrait(ad.get("name", name.replace("AD ", "")), ad.get("age", 56), team.school, mini=mini)
    return None


def message_header(league, m, wrap=66):
    """The reader's top: his face, who he is, and what he wrote — or None when there's no face to show."""
    import textwrap
    face = sender_portrait(league, m)
    if face is None:
        return None
    kind, kcol = who_kind(m)
    right = [paint(m["sender"], m.get("color") or C.BWHITE, C.BOLD) + "   " + paint(m["role"], C.GRAY), ""]
    for ln in textwrap.wrap(m["body"], wrap):
        right.append(paint(ln, C.BWHITE))
    h = max(HERO_H, len(right))
    right_w = 100 - FACE_W - 1
    return columns(_face_panel(face, kcol, paint(kind, kcol, C.BOLD), height=h),
                   panel(kind, right, right_w, color=kcol, title_color=kcol, height=h), gap=1)


def next_up(league, m, waiting):
    """The inbox's top card: the next message that needs you, with his face."""
    import textwrap
    import ui
    face = sender_portrait(league, m, mini=True)
    kind, kcol = who_kind(m)
    lines = [paint(m["sender"], m.get("color") or C.BWHITE, C.BOLD) + "   " + paint(m["role"], C.GRAY),
             paint(m["subject"], C.BYELLOW, C.BOLD)]
    for ln in textwrap.wrap(m["body"], 80)[:2]:
        lines.append(paint(ln, C.GRAY))
    lines.append(paint("[A]", ui.ACCENT, C.BOLD) + paint(" opens it and works the rest of the queue", C.GRAY))
    body = beside(face, lines, indent=0, gap=2) if face else lines
    return panel(f"NEXT UP  ·  {waiting} WAITING ON YOU", body, 100, color=ui.ACCENT, title_color=ui.ACCENT)


def winner_hero(p, team, line, color, mark="", caption="HEISMAN"):
    """Awards: the winner's full portrait beside who he is and what he did."""
    import faces as f
    lines = [chip(team.school.upper(), color) + mark, "",
             paint(p.name, C.BWHITE, C.BOLD), paint(f"{p.position}  ·  {p.class_label}", C.GRAY), "",
             paint(line, C.BWHITE)]
    right_w = 100 - FACE_W - 1
    return columns(_face_panel(f.player_portrait(p, team=team), color, paint(caption, color, C.BOLD), height=9),
                   panel(None, lines, right_w, color=color, height=9), gap=1)


def pick_card(x, you_school, width=32):
    """One of the draft's top picks: a mini face, the pick, the team, the player."""
    import ui
    face = faces.name_portrait(x["name"], school=x["school"], year=faces.class_year(x["cls"]), mini=True,
                               weight=x.get("wt") or getattr(x.get("player"), "weight", None))
    star = paint(" ★", C.BMAGENTA) if you_school and x["school"] == you_school else ""
    lines = [paint(f"#{x['overall_pick']}", ui.ACCENT, C.BOLD) + " " + paint(ui.truncate(x["nfl"], 12), C.BWHITE),
             paint(ui.truncate(x["name"], 16), C.BWHITE, C.BOLD),
             paint(f"{x['pos']} · {ui.truncate(x['school'], 11)}", C.GRAY) + star,
             paint(x["cls"], C.GRAY)]
    return mini_card(face, lines, width, C.GRAY)


def coach_in_panel(league, team, panel_fn, w):
    """The dashboard's head coach panel with his mini portrait to its left (same total width)."""
    c = team.coach
    if c is None or not faces.enabled():
        return panel_fn(league, team, w)
    p = panel_fn(league, team, w - 12)
    mini = faces.coach_portrait(c, mini=True)
    top = max(0, (len(p) - len(mini)) // 2)
    out = []
    for i in range(len(p)):
        j = i - top
        out.append((mini[j] if 0 <= j < len(mini) else " " * 10) + "  " + p[i])
    return out
