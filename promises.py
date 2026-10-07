"""
promises.py — What you promise a recruit follows him to campus (Career mode).

On any recruit's card, [M] makes a promise — the one thing a kid (and his
family) really wants to hear:

  START     "You'll start as a freshman."          the biggest pull, the biggest bill
  PLAY      "You'll play real snaps as a freshman." a solid pull, easier to keep
  DEVELOP   "Redshirt, develop, then compete."      a small pull — big with kids who
                                                     care about development

Before you promise anything, the card shows him what he's looking at: the
players in your room at his position who'll still be there next fall, and how
they compare to what he's projected to be. So does the kid — top targets will
ask you straight out where they fit ("you've got two sophomore corners ahead of
me"), and the answer is yours to give.

When he signs, the promise comes with him. He arrives happier. Every week he
isn't getting what he was told, his morale slides. At the end of his first
season it's graded:

  KEPT      a big morale lift, and he tells the next recruits at his position
  BROKEN    his morale craters (portal territory), recruits at his position hear
            about it, and he wants a word with you

And your record follows you: every promise you've kept makes the next one
land a little harder; every one you've broken makes the next one worth less.
"""
from ui import C
from netplay import capture

KINDS = {
    "start":   ("You'll start as a freshman.", 16.0, "playing_time", 2),
    "play":    ("You'll play real snaps as a freshman.", 10.0, "playing_time", 2),
    "develop": ("Redshirt, develop, then compete.", 6.0, "development", 1),
}


def of(recruit):
    return recruit.player.__dict__.get("promised")


def record(team):
    return team.__dict__.setdefault("promise_record", {"kept": 0, "broken": 0})


def credibility(team):
    r = record(team)
    return max(0.5, min(1.3, 1 + 0.08 * r["kept"] - 0.15 * r["broken"]))


def room(team, recruit):
    """Who'll still be in his position room next fall, best first, with a flag for anyone
    at or above what he's projected to be."""
    proj = recruit.projection()
    back = [p for p in team.players_at(recruit.position) if p.year <= 2]
    return [(p, p.overall >= proj - 2) for p in sorted(back, key=lambda p: -p.overall)]


def room_line(team, recruit, n=4):
    rm = room(team, recruit)
    if not rm:
        return f"Nobody coming back at {recruit.position}. The job is open."
    ahead = [p for p, a in rm if a]
    who = ", ".join(f"{p.last_name} ({p.class_label} {__import__('scout').ovr_plain(p)})" for p, _ in rm[:n])
    if not ahead:
        return f"Back next fall at {recruit.position}: {who}. Nobody he projects behind."
    return (f"Back next fall at {recruit.position}: {who}. "
            f"{len(ahead)} at or above his projection.")


def hint(team, recruit, kind):
    """The colored line under each promise, like the inbox."""
    from effects import UP
    label, raw, key, cost = KINDS[kind]
    heavy = key in recruit.known_priorities(team)
    ahead = sum(1 for _, a in room(team, recruit) if a)
    n = 3 if kind == "start" else 2 if kind == "play" else 1
    n = min(3, n + (1 if heavy else 0))
    good = [f"his interest {UP * n}" + (" (it's what he wants)" if heavy else "")]
    bad = [f"costs {cost} recruiting hr{'s' if cost != 1 else ''}"]
    if kind == "start":
        bad.append(f"he expects to start next fall" + (f" — {ahead} ahead of him now" if ahead else ""))
    elif kind == "play":
        bad.append("he expects to play in 6+ games next fall")
    else:
        good.append("can't be broken — playing him early is fine too")
    if kind != "develop":
        bad.append("break it and he's gone, and recruits hear")
    from ui import paint
    return (paint(" · ", C.GRAY).join([paint(g, C.BGREEN) for g in good] + [paint(b, C.BRED) for b in bad]))


def precheck(league, team, recruit):
    """Why a promise can't be made right now (before the menu), or None."""
    if recruit.signed:
        return f"{recruit.name} has already signed."
    if team not in recruit.offers:
        when = " Preseason contact period is open." if league.recruiting.remaining_hours(team) <= 0 else ""
        return f"Offer him first. A promise without an offer is just talk.{when}"
    cur = of(recruit)
    if cur and cur.get("school") == team.school:
        return "You've already made him a promise. Your word is your word."
    if league.recruiting.remaining_hours(team) < min(k[3] for k in KINDS.values()):
        return "No recruiting hours left this week — a promise is made in person."
    return None


@capture.hook("rec", "acts", capture.b_promise)
def make(league, team, recruit, kind):
    """Returns (ok, message)."""
    cycle = league.recruiting
    label, raw, key, cost = KINDS[kind]
    if recruit.signed:
        return False, f"{recruit.name} has already signed."
    if team not in recruit.offers:
        return False, "Offer him first. A promise without an offer is just talk."
    cur = of(recruit)
    if cur and cur.get("school") == team.school:
        return False, "You've already made him a promise. Your word is your word."
    if cycle.remaining_hours(team) < cost:
        return False, "Not enough hours left this week — a promise is made in person."
    cycle.hours_used[team] += cost
    from recruiting import priority_weight, clamp
    gain = raw * priority_weight(recruit, key) * credibility(team) * (1 - recruit.interest[team] / 120)
    import skills
    if skills.team_has(team, "promise_keeper"):
        gain *= 1.25                                                 # Promise Keeper (coaching tree)
    recruit.interest[team] = clamp(recruit.interest[team] + gain, 0, 100)
    k = (team, recruit)
    cycle.relationship[k] = clamp(cycle.relationship[k] + 6, 0, 100)
    recruit.player.promised = {"kind": kind, "school": team.school, "year": league.year}
    extra = ""
    r = record(team)
    if r["broken"]:
        extra = " His family asked about the last kid you promised."
    elif r["kept"] >= 2:
        extra = " He's heard you keep your word."
    return True, f"Promised: \"{label}\" — {recruit.name} lit up.{extra}"


# ═══ On campus ══════════════════════════════════════════════════════════════

def arrive(team, recruit, next_year):
    """At signing: the promise comes with him (only if it was yours)."""
    p = recruit.player
    pr = p.__dict__.pop("promised", None)
    if pr and pr.get("school") == team.school:
        p.recruit_promise = {"kind": pr["kind"], "year": next_year}
        p.events[next_year].append(f"Signed on a promise: {KINDS[pr['kind']][0]}")
        import morale
        morale.nudge(p, 8)


def weekly_drag(league, team, p, starter):
    """Extra morale drag for a freshman who isn't getting what he was promised."""
    pr = getattr(p, "recruit_promise", None)
    if not pr or pr.get("year") != league.year or league.week < 3:
        return 0.0
    if pr["kind"] == "start" and not starter:
        return -1.8
    if pr["kind"] == "play" and getattr(p, "games_played", 0) < league.week * 0.5:
        return -1.1
    return 0.0


def grade(league):
    """End of his first season: kept or broken."""
    mine = getattr(getattr(league, "user_coach", None), "team", None)
    if mine is None:
        return
    import morale
    from models import STARTING_LINEUP
    for p in list(mine.roster):
        pr = getattr(p, "recruit_promise", None)
        if not pr or pr.get("year") != league.year or pr.get("graded"):
            continue
        pr["graded"] = True
        n = STARTING_LINEUP.get(p.position, 1)
        room_ = mine.players_at(p.position)
        rank = room_.index(p) if p in room_ else 99
        gp = getattr(p, "games_played", 0)
        kept = (rank < n or gp >= 10) if pr["kind"] == "start" else \
            (gp >= 6 or rank <= n) if pr["kind"] == "play" else True
        rec = record(mine)
        same = [r for r in getattr(mine, "recruiting_targets", []) if not r.signed and r.position == p.position]
        if kept:
            rec["kept"] += 1
            morale.nudge(p, 12, "you kept your recruiting promise", league)
            for r in same:
                r.interest[mine] = min(100, r.interest.get(mine, 0) + 2)
            p.events[league.year].append("The promise he signed on was kept")
            continue
        import skills
        forgiven = mine.__dict__.setdefault("_forgiven", {})
        if skills.team_has(mine, "promise_keeper") and forgiven.get(league.year, 0) < 1:
            forgiven[league.year] = 1                                # Promise Keeper: the first one slides
            morale.nudge(p, -4, "a promise that didn't happen (he let it slide)", league)
            p.events[league.year].append("The promise he signed on wasn't kept — he let it slide")
            import people
            people._post(league, f"{p.position} {p.name}", "Promise Keeper", "It's all good, Coach",
                         f"{p.first_name}'s family let the broken promise slide. They trust you. Don't make it "
                         "a habit.", kind="result", color=C.BGREEN)
            continue
        rec["broken"] += 1
        morale.nudge(p, -28, "a recruiting promise broken", league)
        p.__dict__["disgruntled"] = league.year
        for r in same:
            r.interest[mine] = max(0, r.interest.get(mine, 0) - 4)
        p.events[league.year].append("The promise he signed on was broken")
        import recruit_plus
        recruit_plus.broken_promise(mine, p)                      # his high school hears about it
        _broken_message(league, mine, p, pr["kind"])


def _broken_message(league, team, p, kind):
    import people
    said = KINDS[kind][0].rstrip(".")
    people.choice(league, f"{p.position} {p.name}", f"{p.class_label} · {__import__('scout').ovr_tag(p)} · signed on a promise",
                  "You told me",
                  f"Coach, you sat in my living room and told my mom: \"{said}.\" That didn't happen. "
                  "I need to know if anything you told me was real.",
                  [("I was wrong. Next year the job is yours to win — first in line.",
                    {"who": p, "promise": "made", "morale": 8},
                    f"{p.first_name} wants to believe you. You're on the clock again."),
                   ("You weren't ready. That's the truth, and you know it.",
                    {"who": p, "morale": -6, "chem": 1},
                    "Honest. The room respects it. He doesn't."),
                   ("If you want a fresh start, I'll help you find the right place.",
                    {"who": p, "unhappy": True, "recruits": 1},
                    f"{p.first_name} will probably be in the portal. Recruits hear you didn't fight him on it.")],
                  ref=p, color=C.BRED)


# ═══ The kid asks (an in-season inbox message) ═══════════════════════════════

def depth_question(league, team, rng):
    """A top target asks where he'd fit. Returns True if a message was posted."""
    board = [r for r in getattr(team, "recruiting_targets", []) if not r.signed and team in r.offers
             and r.committed_to in (None, team) and r.interest.get(team, 0) >= 30 and not of(r)]
    asked = league.__dict__.setdefault("_asked_depth", set())
    board = [r for r in board if (league.year, id(r)) not in asked]
    if not board:
        return False
    r = max(board, key=lambda x: (x.stars, x.interest.get(team, 0)))
    ahead = [p for p, a in room(team, r) if a]
    if not ahead and rng.random() < 0.5:
        return False
    asked.add((league.year, id(r)))
    import people
    who = (", ".join(f"{p.name} ({p.class_label})" for p in ahead[:3]) if ahead else "")
    body = (f"Coach, I watched your {r.position}s. " +
            (f"You've got {who} coming back. Where do I fit? Am I playing next year?" if ahead else
             "Looks like the job's open. Can you tell me I'm starting?"))
    nm = r.player.first_name
    opts = []
    for kind in ("start", "play", "develop"):
        label, raw, key, cost = KINDS[kind]
        weight = 1.4 if key in r.priorities[:1] else 1.15 if key in r.priorities else 0.8
        v = round(raw * weight * credibility(team) * 0.6)
        opts.append((f"{label} (a promise)",
                     {"hours": -cost, "recruit": v, "ref": r, "promise_recruit": kind,
                      "notes": [(False, {"start": "he expects to start next fall",
                                         "play": "he expects real snaps next fall",
                                         "develop": "he expects patience"}[kind])]
                                + ([(False, "break it and he's gone")] if kind != "develop" else [])},
                     f"{nm} heard exactly what he wanted. Now it's on the record."))
    wants_truth = "development" in r.priorities or r.personality in ("family_first",)
    opts.append(("The truth: you'll compete. Nothing's promised here." if ahead else
                 "The truth: nothing's handed out, but the door's open.",
                 {"recruit": 3 if wants_truth else -3, "ref": r, "recruits": 0.5},
                 f"{nm} {'respects it' if wants_truth else 'wanted more than that'}. Other kids hear you don't sell fairy tales."))
    people.choice(league, f"{r.stars}★ {r.position} {r.name}", f"{r.home_state} · you offered", "Where do I fit?",
                  body, opts, ref=r, color=C.BYELLOW, silence={"recruit": -3, "ref": r},
                  silence_text=f"{nm} took the silence as an answer.")
    return True
