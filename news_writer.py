"""
news_writer.py — Headlines that read like a sports desk wrote them: the verb fits the margin,
and the line knows the context — a rivalry and its trophy, a streak made or broken, an
unbeaten record, bowl eligibility, a ranked scalp, overtime.

Each game gets the same headline every time it's shown (the wording is seeded by the game).
"""
import random


def _rng(league, g):
    return random.Random(f"hl:{league.year}:{g.week}:{g.home.school}:{g.away.school}")


def _tag(t, r):
    return f"No. {r} {t.school}" if r else t.school


def _form(team):
    st = team.__dict__.get("tmom")
    return st[2] if st else []


def _streak(res):
    if not res:
        return None, 0
    n = 1
    while n < len(res) and res[-n - 1] == res[-1]:
        n += 1
    return res[-1], n


def result(league, g):
    """(priority, text) for one finished game."""
    rng = _rng(league, g)
    ranks = getattr(g, "ranks", None) or {}
    w, l = g.winner, g.loser
    rw, rl = ranks.get(w), ranks.get(l)
    ws, ls = g.score_for(w), g.score_for(l)
    margin = ws - ls
    ot = getattr(g.box, "ot_round", 0) if getattr(g, "box", None) is not None else 0
    upset = bool(rl and (not rw or rw > rl + 5)) or (getattr(w, "fcs", False) and not getattr(l, "fcs", False))
    riv_name, trophy, holder = None, None, None
    try:
        import rivalries
        riv_name = rivalries.rivalry_name(w, l)
        trophy = rivalries.trophy(w, l)
        if trophy:
            s = rivalries.series(league, w.school, l.school)
            prev = s.games[-2] if len(s.games) >= 2 else None
            holder = "keeps" if prev is not None and prev.winner == w.school else "takes back" if prev is not None else "wins"
    except Exception:                                      # noqa: BLE001, S110
        pass
    W, L = _tag(w, rw), _tag(l, rl)
    if ot:
        verb = rng.choice(("outlasts", "survives", "wins a thriller over", "edges"))
        tail = f" in {'overtime' if ot == 1 else f'{ot} overtimes'}"
    elif upset:
        verb = rng.choice(("stuns", "shocks", "knocks off", "takes down", "upends"))
        tail = ""
    elif margin >= 28:
        verb = rng.choice(("routs", "rolls over", "hammers", "runs away from", "overwhelms"))
        tail = ""
    elif margin >= 14:
        verb = rng.choice(("handles", "pulls away from", "beats", "controls"))
        tail = ""
    elif margin >= 4:
        verb = rng.choice(("beats", "holds off", "gets past", "tops"))
        tail = ""
    else:
        verb = rng.choice(("edges", "survives", "slips past", "squeaks by"))
        tail = ""
    text = f"{W} {verb} {L}, {ws}-{ls}{tail}"
    notes = []
    if trophy and holder:
        notes.append(f"{holder} {trophy}")
    elif riv_name:
        notes.append(f"wins {riv_name}")
    kind_w, n_w = _streak(_form(w))
    kind_l, n_l = _streak(_form(l))
    if w.losses == 0 and w.wins >= 6 and not getattr(w, "fcs", False):
        notes.append(f"stays unbeaten at {w.record}")
    elif kind_w == "W" and n_w >= 4:
        notes.append(f"{n_w} straight wins for {w.school}")
    elif kind_w == "W" and n_w == 1 and len(_form(w)) >= 3 and _form(w)[-2] == "L" and _form(w)[-3] == "L":
        notes.append("snaps a skid")
    if w.wins == 6 and g.week <= 14 and g.game_type in (None, "Regular Season", "Conference"):
        notes.append("bowl eligible")
    if l.losses == 1 and l.wins >= 6 and rl:
        notes.append(f"{l.school}'s first loss")
    elif kind_l == "L" and n_l >= 4:
        notes.append(f"{l.school} has lost {n_l} straight")
    if notes:
        text += " — " + rng.choice(notes) if len(notes) == 1 else " — " + ", ".join(notes[:2])
    pr = 0.0
    if rw and rl and rw <= 10 and rl <= 10:
        pr = 86 - min(rw, rl)
    elif upset and rl:
        pr = 76 - rl * 0.5
    elif upset:
        pr = 50
    elif riv_name or trophy:
        pr = 66 if (rw or rl) else 55
    elif (rw and rw <= 5) or (rl and rl <= 5):
        pr = 48
    elif ot and (rw or rl):
        pr = 54
    elif w.losses == 0 and w.wins >= 8:
        pr = 50
    return pr, text, upset
