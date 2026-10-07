"""
podium.py — What your press-conference answers actually do.

Thursday's presser (presser.py) and the postgame podium (postgame.py) both run
through here. Every answer has a tone, and every tone has an upside and a cost:

  THURSDAY
  confident  recruits like it (+interest)            nobody's buzzing if you're wrong: as an
                                                     underdog, the other locker room pins it up
  measured   your team stays composed late (+poise)  no headlines: recruits shrug, and an AD who
                                                     wants noise notices an all-measured presser
  fiery      your team feeds off it (+Saturday)      emotional team: sloppier late (-poise);
                                                     some ADs love it, some wince
  humble     takes the heat off your players (+)     doesn't sell (-recruits); patient ADs like
                                                     it, win-now ADs want fire

  POSTGAME  the same four, smaller, carried into next week — and after a loss,
            owning it takes pressure off the locker room; swagger can annoy the AD.

Most answers also do something of their own (backing your QB, a shot at the
rival, calling out the officials, crediting a freshman). Some draw a follow-up:
say you're ready for the rival and somebody will ask whether you're
guaranteeing it. You see every answer's upside and cost before you choose,
and a summary of the whole podium at the end.
"""
from effects import apply, by_ad, hint
from ui import C, ask, pad, paint

TONE_COLOR = {"confident": C.BYELLOW, "measured": C.BWHITE, "fiery": C.BRED, "humble": C.BCYAN}
FIERY_AD = {"politician": 1, "booster": 1, "big_game": 1, "patient": -1, "analytics": -1, "budget": -1}
HUMBLE_AD = {"patient": 1, "traditionalist": 1, "politician": -1, "win_now": -1}
HEADLINES_AD = {"default": 0, "brand": 1, "politician": 1, "booster": 1}      # he wants you out front
SPECIAL = ("who", "coord", "stake", "gamble", "ref")


# ═══ Building an answer's effects ═══════════════════════════════════════════

def merge(a, b):
    """Two effect bundles as one. If both name a player (or a stake, or a gamble),
    the second rides along whole instead of being mixed in."""
    a, b = dict(a or {}), dict(b or {})
    if any(k in a for k in SPECIAL if k in b):
        also = a.get("also", [])
        a["also"] = (also if isinstance(also, list) else [also]) + [b]
        return a
    for k, v in b.items():
        if k == "inj":
            a[k] = a.get(k, 1.0) * v
        elif k in ("notes", "also"):
            cur = a.get(k, [])
            cur = cur if isinstance(cur, list) else [cur]
            a[k] = cur + (v if isinstance(v, list) else [v])
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and k not in ("stay",):
            a[k] = a.get(k, 0) + v
        else:
            a[k] = v
    return a


def tone_fx(tone, when, ctx):
    fx = _tone_fx(tone, when, ctx)
    import skills
    if skills.team_has(ctx["team"], "media_savvy"):                  # Media Savvy (coaching tree)
        if tone == "measured":
            fx.pop("recruits", None)
        if tone == "humble" and fx.get("seat", 0) > 0:
            fx.pop("seat")
    return fx


def _tone_fx(tone, when, ctx):
    style = ctx["team"].ad.get("style")
    t = ctx["team"]
    if when == "thu":
        if tone == "confident":
            return {"recruits": 1.0, **({"opp_lift": 0.25} if ctx.get("underdog") else {})}
        if tone == "measured":
            return {"clutch": 0.1, "recruits": -0.3}
        if tone == "fiery":
            return {"lift": 0.3, "clutch": -0.1, "seat": -FIERY_AD.get(style, 0)}
        if tone == "humble":
            return {"lift": 0.15, "recruits": -0.5, "seat": -HUMBLE_AD.get(style, 0)}
    else:
        won = ctx.get("won")
        if tone == "confident":
            return {"recruits": 1.0, **({} if won else {"seat": by_ad(t, {"default": 0, "patient": 1,
                                                                            "traditionalist": 1, "budget": 1})})}
        if tone == "measured":
            return {"clutch": 0.05, "recruits": -0.3}
        if tone == "fiery":
            return {"lift": 0.1, "clutch": -0.05, "seat": -FIERY_AD.get(style, 0)}
        if tone == "humble":
            return {"lift": 0.05, "recruits": -0.3, "seat": -HUMBLE_AD.get(style, 0), **({} if won else {"chem": 1})}
    return {}


UPSIDES = ("lift", "recruits", "clutch", "chem")


def _repeat(fx, n):
    """The same note twice loses its punch: a tone's upside halves each time you go
    back to it in one podium; its cost doesn't (they stack)."""
    if not n:
        return fx
    out = dict(fx)
    for k in UPSIDES:
        if out.get(k, 0) > 0:
            out[k] = round(out[k] * 0.5 ** n, 3)
    if out.get("seat", 0) < 0:
        out["seat"] = 0 if n >= 1 and abs(out["seat"]) <= 1 else out["seat"] + 1
        if not out["seat"]:
            out.pop("seat")
    return out


def extra_fx(extra, ctx):
    """An answer's own effects. extra is None, a (kind, value) pair, or a list of them."""
    if not extra:
        return {}
    if isinstance(extra, list):
        out = {}
        for e in extra:
            out = merge(out, extra_fx(e, ctx))
        return out
    kind, v = extra
    qb = ctx.get("qb")
    if kind == "lift":
        return {"lift": v}
    if kind == "recruits":
        return {"recruits": v}
    if kind == "chem":
        return {"chem": v}
    if kind == "clutch":
        return {"clutch": v}
    if kind == "seat":
        return {"seat": v}
    if kind == "seat_humble":
        return {"seat": -1}
    if kind == "jab":
        return {"opp_lift": 0.3, "lift": 0.1, "recruits": 0.5}
    if kind == "qb" and qb is not None:
        if v > 0:
            return {"lift": 0.1, "who": qb, "bought_in": True}
        return {"lift": -0.05, "who": qb,
                "gamble": [(0.6, {}, f"{qb.first_name} shrugged it off."),
                           ({"who": qb, "unhappy": True}, f"{qb.first_name} heard the hedge. He's not happy.")]}
    if kind == "fx":
        return dict(v)
    return {}


# ═══ Follow-up questions ════════════════════════════════════════════════════

def followup(key, ctx):
    """(question, [(tone, answer, extra)]) or None."""
    t, opp = ctx["team"], ctx.get("opp")
    o = opp.school if opp is not None else "them"
    if key == "guarantee":
        return (f"So are you guaranteeing a win over {o}?",
                [("fiery", "Yes. Write it down.",
                  ("fx", {"lift": 0.2, "opp_lift": 0.35,
                          "stake": {"on": "next", "hint": "you guaranteed it",
                                    "win": {"recruits": 2, "seat": -1}, "loss": {"seat": 2, "chem": -2},
                                    "who": f"{t.school} Communications", "subject": "The guarantee",
                                    "wtext": "You guaranteed it and you delivered. That clip is everywhere, "
                                             "and recruits are sharing it.",
                                    "ltext": "You guaranteed a win and didn't get it. That clip is everywhere too."}})),
                 ("measured", "I'm saying we'll be ready. That's all I'm saying.", None),
                 ("humble", "No. I'm saying I believe in our players.", ("chem", 1))])
    if key == "staff":
        oc, dc = getattr(t, "oc", None), getattr(t, "dc", None)
        coords = [c for c in (oc, dc) if c is not None]
        if not coords:
            return None
        return ("Are staff changes coming?",
                [("fiery", "Everything's on the table. Everything.",
                  ("fx", {"seat": -1, "lift": 0.1, "chem": -1,
                          "also": [{"coord": c, "stay": 1} for c in coords]})),
                 ("confident", "No. I believe in this staff.",
                  ("fx", {"seat": by_ad(t, {"default": 1, "patient": 0, "analytics": 0, "win_now": 2}),
                          "also": [{"coord": c, "stay": -1} for c in coords]})),
                 ("measured", "Not tonight. We'll evaluate everything, like always.", None)])
    if key == "qb_hedge":
        qb = ctx.get("qb")
        room = sorted(t.players_at("QB"), key=lambda p: -p.overall)
        backup = room[1] if len(room) > 1 else None
        if qb is None or backup is None:
            return None
        return ("So is there an open quarterback competition?",
                [("fiery", "Yes. Everybody competes. Everybody.",
                  ("fx", {"lift": -0.1, "who": backup, "bought_in": True, "also": {"who": qb, "unhappy": True}})),
                 ("confident", f"No. {qb.first_name}'s our guy.",
                  ("fx", {"who": qb, "bought_in": True, "recruits": -0.3,
                          "notes": [(False, "you just walked back your own answer")]})),
                 ("measured", "I've said what I'm going to say.", ("lift", -0.05))])
    return None


# ═══ Running the podium ═════════════════════════════════════════════════════

def run(league, questions, when, ctx):
    """Ask the questions, apply the answers. questions: [(text, [(tone, answer, extra)])].
    Returns (tones said, everything it did as one bundle)."""
    import effects
    show = effects.show_hints()
    said, total, asked_follow = [], {}, False
    queue = list(questions)
    while queue:
        text, answers = queue.pop(0)
        bundles = [merge(_repeat(tone_fx(tone, when, ctx), said.count(tone)), extra_fx(extra, ctx))
                   for tone, _, extra in answers]
        print()
        print("   " + paint("Q: ", C.BYELLOW, C.BOLD) + paint(text, C.BWHITE))
        for i, ((tone, ans, extra), b) in enumerate(zip(answers, bundles), 1):
            print(f"      {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint(pad(tone, 10), TONE_COLOR[tone])}"
                  f"{paint(chr(34) + ans + chr(34), C.GRAY)}")
            if show:
                fol = _follow_key(extra)
                tail = paint("  · draws a follow-up", C.BMAGENTA) if fol and not asked_follow else ""
                again = paint("  · repeat: ½ upside", C.GRAY) if said.count(tone) else ""
                h = hint(b)
                if when == "post":                              # after the game, a lift carries to the next one
                    h = __import__("re").sub(r"(?<!every )Saturday", "next Saturday", h)
                print("                 " + h + tail + again)
        dflt = next((i for i, a in enumerate(answers) if a[0] == "measured"), 0)
        c = ask(f"Your answer (Enter = {answers[dflt][0]}):").strip()
        if c.isdigit() and 1 <= int(c) <= len(answers):
            k = int(c) - 1
        else:
            k = dflt
        tone, ans, extra = answers[k]
        b = bundles[k]
        said.append(tone)
        got = apply(league, b, "postgame press conference" if when == "post" else "press conference")
        total = merge(total, {kk: vv for kk, vv in b.items() if kk not in ("gamble", "stake", "who", "coord", "also")})
        total.setdefault("_answers", []).append(b)
        total["_when"] = when
        line = _react(tone, b, ctx)
        if got:
            line += " " + " ".join(got)
        print(paint("   → " + line, C.BCYAN))
        fol = _follow_key(extra)
        if fol and not asked_follow:
            q = followup(fol, ctx)
            if q is not None:
                asked_follow = True
                queue.insert(0, (paint("Follow-up: ", C.BMAGENTA) + q[0], q[1]))
    # An AD who wants headlines, and got a podium full of nothing.
    if said and all(t == "measured" for t in said) and by_ad(ctx["team"], HEADLINES_AD) > 0:
        apply(league, {"seat": 1}, "a quiet podium")
        total = merge(total, {"seat": 1})
        total.setdefault("_answers", []).append({"seat": 1})
        print(paint("   → Your AD wanted a headline. He didn't get one.", C.BRED))
    return said, total


def _follow_key(extra):
    if not extra:
        return None
    items = extra if isinstance(extra, list) else [extra]
    return next((v for k, v in items if k == "follow"), None)


def _react(tone, b, ctx):
    bits = []
    if b.get("lift", 0) > 0:
        bits.append("The locker room heard it.")
    if b.get("recruits", 0) >= 1:
        bits.append("Recruits on your board were watching.")
    if b.get("opp_lift", 0) > 0:
        opp = ctx.get("opp")
        bits.append(f"{opp.school if opp is not None else 'The other side'} will pin that one up.")
    if b.get("seat", 0) < 0:
        bits.append("Your AD liked it.")
    elif b.get("seat", 0) > 0:
        bits.append("Your AD didn't love it.")
    if b.get("stake"):
        bits.append("That's on the record now.")
    if not bits:
        bits.append({"measured": "Nothing to see here. Sometimes that's the point.",
                     "humble": "It took some heat off your players.",
                     "confident": "Confident, and noted.",
                     "fiery": "The room felt that one."}.get(tone, "Noted."))
    return " ".join(bits)


def summary(total):
    """One line for the end of the podium: every answer's effects, with repeats counted
    (three answers that cost recruits read "recruits ▼ ×3" — they stack)."""
    import effects
    answers = (total or {}).get("_answers")
    if not answers:
        return paint("   Today at the podium: ", C.GRAY) + hint(total)
    parts = effects._collapse([p for b in answers for p in effects._raw_parts(
        {k: v for k, v in b.items() if k not in ("gamble", "stake", "who", "coord", "also")})])
    bits = [paint(t, C.BGREEN if g is True else C.BRED if g is False else C.BYELLOW) for g, t in parts]
    body = paint(" · ", C.GRAY).join(bits) if bits else paint("no real effect", C.GRAY)
    if total.get("_when") == "post":
        body = __import__("re").sub(r"(?<!every )Saturday", "next Saturday", body)
    # wrap on the separators so the line never runs past the screen
    import re
    vis = lambda x: len(re.sub(r"\x1b\[[0-9;]*m", "", x))
    head = paint("   Today at the podium (they stack): ", C.GRAY)
    sep = paint(" · ", C.GRAY)
    lines, cur = [], head
    for piece in body.split(sep):
        add = piece if cur == head else sep + piece
        if vis(cur) + vis(add) > 98 and cur != head:
            lines.append(cur)
            cur = "      " + piece
        else:
            cur += add
    lines.append(cur)
    return "\n".join(lines)
