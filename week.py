"""
week.py — A week that feels like a week.

Before each of your games (Coach Career), the week has a shape:

  MONDAY     Film — what the tape says about Saturday
  TUESDAY    Inbox — your AD, your players, your recruits, your staff
  WEDNESDAY  Practice — pick the week's focus; each one is a trade-off
  THURSDAY   Press conference — optional; how you answer has consequences
  FRIDAY     Injury report, the walkthrough, and the game plan ([G]): one key on
             offense, one on defense, and whether to script your openers
  SATURDAY   Kickoff — sim it, play the big moments, coach every snap, or watch

It's one screen. Enter goes straight to Saturday with your usual practice
plan, so a quick week is one keystroke. Settings can turn the week hub off.

ROUTINES  (the week in one key)
  A routine is a practice focus + a Friday game plan + scripted openers, saved.
  [1]-[5] on the hub are built in (Standard · Big game · Banged up · Recruiting ·
  Close games), [6]-[8] are yours ([Y] saves this week's setup, picks a default,
  deletes one). "The film's plan" means the keys your staff recommends against
  whoever you play, so a routine works every week. Your default routine is loaded
  when the hub opens, and it's what sim weeks and a hub turned off use.

AFTER THE GAME  (week_report)
  "The week's work": every decision, credited — the practice focus, the Thursday
  presser, your inbox replies, last week's podium — in rating points of game-day
  form and in points on the scoreboard, with what came of the side effects
  (injuries, the weather, poise late, recruiting hours, who came back early), the
  game plan's keys (working or not) and the scripted openers (snaps, yards, first
  downs). The hub shows last week's line; the team keeps a ledger (week_ledger).

PRACTICE FOCUS  (applies to this Saturday only)
  Game-plan heavy       +0.8 game-day lift        injuries more likely (x1.25)
  Balanced              +0.4
  Ball security         +0.5, and fewer self-inflicted mistakes late
  Situational football  +0.3, and much sharper in one-score fourth quarters
  Physical, full pads   +0.7                      injuries more likely (x1.3)
  Rest & recover        no lift                   injuries less likely (x0.75),
                                                  short injuries heal a week sooner
  Recruiting week       -0.3                      +8 recruiting hours this week
  Weather prep          +0.3                      the weather (rain, snow, wind, cold, heat,
                                                  altitude) hits your team half as hard

PRESS CONFERENCE  (two questions from the real week; see presser.py and podium.py)
  Each question has its own three answers, each with a tone, and every tone
  has an upside and a cost:
  Confident   recruits like it — as an underdog it's bulletin-board material
  Measured    composed late (+poise) — no headlines, recruits shrug
  Fiery       your team feeds off it (+0.3) — emotional late; ADs split on it
  Humble      takes the heat off your players (+0.15) — doesn't sell recruits

WHAT YOUR ANSWERS BANK
  Inbox replies and podium answers can put form, poise, injury risk or the
  other team's fire onto this Saturday (or the game after). It's all added
  when you head to Saturday; the THURSDAY panel shows what's banked.
"""
import random

import scout
from ui import C, ask, clear, columns, key, pad, paint, panel, pause, rule, title_bar, truncate, visible_len

# key -> (label, blurb, lift, injury multiplier, recruiting hours, clutch)
FOCUS = {
    "gameplan":    ("Game-plan heavy", "+0.8 Saturday · injuries x1.25", 0.8, 1.25, 0, 0.0),
    "balanced":    ("Balanced", "+0.4 Saturday", 0.4, 1.0, 0, 0.0),
    "ball":        ("Ball security", "+0.5 · steadier late", 0.5, 1.0, 0, 0.2),
    "situational": ("Situational football", "+0.3 · sharp in close 4th quarters", 0.3, 1.0, 0, 0.6),
    "physical":    ("Physical, full pads", "+0.7 · injuries x1.3", 0.7, 1.3, 0, 0.0),
    "rest":        ("Rest & recover", "no lift · injuries x0.75 · heal faster", 0.0, 0.75, 0, 0.0),
    "recruit":     ("Recruiting week", "-0.3 Saturday · +8 recruiting hours", -0.3, 1.0, 8, 0.0),
    "weather":     ("Weather prep", "+0.3 · wet balls, the wind: half the weather's effect", 0.3, 1.0, 0, 0.0),
}
FOCUS_KEYS = list(FOCUS)


def _team(league):
    me = getattr(league, "user_coach", None)
    if getattr(league, "mode", None) != "career" or me is None:
        return None
    return me.team


def next_game(league, team):
    """Your game in the coming week, or None (a bye)."""
    wk = league.week + 1
    return next((g for g in league.schedule.get(wk, []) if team in (g.home, g.away) and not g.played), None)


def apply_prep(league, team, focus, presser=None, silent=False, routine=None):
    """Put the week's plan on the team: read by game_sim, injuries and recruiting."""
    label, _, lift, inj, hours, clutch = FOCUS[focus]
    presser = presser or {}
    import skills
    if skills.team_has(team, "film_room") and lift > 0:
        lift *= 1.25                                               # Film Room (coaching tree)
    if skills.team_has(team, "clock_manager"):
        clutch += 0.25                                             # Clock Manager (coaching tree)
    import effects
    extra = effects.take(league, team)                # what your inbox and your podium answers put on this week
    # Who put what on Saturday — kept so the postgame can credit each decision (week_report).
    parts = {"practice": {"lift": lift, "clutch": clutch, "inj": inj}}
    for src, fx in (extra.get("_src") or {}).items():
        parts[src] = dict(fx)
    if presser.get("lift"):                           # an older save's podium lift
        parts.setdefault("podium", {})["lift"] = parts.get("podium", {}).get("lift", 0.0) + presser["lift"]
    team.week_prep = {"year": league.year, "week": league.week + 1, "focus": focus,
                      "lift": lift + presser.get("lift", 0.0) + extra.get("lift", 0.0),
                      "injury": inj * extra.get("inj", 1.0), "hours": hours,
                      "clutch": clutch + presser.get("clutch", 0.0) + extra.get("clutch", 0.0),
                      "opp_lift": presser.get("opp_lift", 0.0) + extra.get("opp_lift", 0.0),
                      "parts": parts, "routine": routine, "pressed": bool(presser.get("said"))}
    if focus == "rest":
        healed = []
        for p in team.roster:
            if 1 <= getattr(p, "inj_games", 0) <= 2 and not getattr(p, "suspended", False):
                p.inj_games -= 1
                if p.inj_games == 0:
                    healed.append(f"{p.position} {p.name}")
        team.week_prep["healed"] = healed
    league.__dict__.setdefault("_prep_done", set()).add((league.year, league.week + 1))


def prep_for(team, week=None):
    """The week's plan if it's still live, else {}."""
    wp = getattr(team, "week_prep", None) or {}
    return wp


def settle(league, games):
    """After the week: make sure your game's credit is in the ledger (the postgame screen
    already did it when you played it; a simmed week does it here, quietly)."""
    team = _team(league)
    if team is None:
        return
    for g in games:
        if g.played and team in (g.home, g.away):
            led = team.__dict__.get("week_ledger") or []
            if not any((x["year"], x["week"]) == (league.year, g.week) for x in led):
                try:
                    credit(league, g, team)
                except Exception:
                    pass
            _keep_decisions(league, g, team)


def clear_prep(league):
    for t in league.teams:
        if getattr(t, "week_prep", None):
            t.week_prep = None


def auto_week(league):
    """Sim weeks (and the hub turned off): the people still talk, and your default routine
    (or your usual practice plan) is used."""
    team = _team(league)
    if team is None:
        return
    import people
    people.weekly(league)
    g = next_game(league, team)
    if g is not None:
        import settings
        r = default_routine()
        if r is not None:
            focus, plan = routine_setup(league, team, g, r)
            import sideline
            sideline.set_plan(team, league.year, league.week + 1, plan["off"], plan["def"], plan["script"])
            apply_prep(league, team, focus, silent=True, routine=r["name"])
        else:
            apply_prep(league, team, settings.load().get("practice_focus", "balanced"), silent=True)


# ═══ Routines: the week in one key ══════════════════════════════════════════
# A routine is a practice focus, a game plan and the openers, saved. Five come with
# the game; you can save three of your own. One of them can be your default: the
# hub opens with it loaded, and it's what sim weeks (and the hub turned off) use.

ROUTINES = {
    "standard": ("Standard", "staff", "film", "film", False,
                 "the staff's focus (weather prep when it's coming), the film's plan"),
    "big":      ("Big game", "gameplan", "film", "film", True,
                 "game-plan heavy, the film's plan, openers scripted"),
    "banged":   ("Banged up", "rest", "film", "film", False,
                 "rest & recover (short injuries heal a week sooner), the film's plan"),
    "recruit":  ("Recruiting", "recruit", "film", "film", False,
                 "recruiting week (+8 hours, -0.3 Saturday), the film's plan"),
    "close":    ("Close games", "situational", "film", "film", False,
                 "situational football (sharp in one-score 4th quarters), the film's plan"),
}
ROUTINE_KEYS = list(ROUTINES)
MAX_CUSTOM = 3


def _custom():
    import settings
    return settings.load().setdefault("routines", [])


def routine_list():
    """Every routine, in hub order: [(key, dict)] — the five built in, then yours (u1..u3)."""
    out = []
    for k in ROUTINE_KEYS:
        name, focus, off, dfk, script, blurb = ROUTINES[k]
        out.append((k, {"name": name, "focus": focus, "off": off, "def": dfk, "script": script, "blurb": blurb}))
    for i, r in enumerate(_custom()[:MAX_CUSTOM], 1):
        d = dict(r)
        d.setdefault("blurb", describe(d))
        out.append((f"u{i}", d))
    return out


def routine_by_key(k):
    return dict(routine_list()).get(k)


def default_routine():
    import settings
    k = settings.load().get("routine_default")
    return routine_by_key(k) if k else None


def describe(r):
    import sideline
    f = "the staff's focus" if r["focus"] == "staff" else FOCUS.get(r["focus"], ("?",))[0]
    plan = ("the film's plan" if r["off"] == "film" and r["def"] == "film" else
            f"{'the film' if r['off'] == 'film' else sideline.OFF_KEYS.get(r['off'], ('?',))[0]} / "
            f"{'the film' if r['def'] == 'film' else sideline.DEF_KEYS.get(r['def'], ('?',))[0]}")
    return f"{f}, {plan}" + (", openers scripted" if r.get("script") else "")


def routine_setup(league, team, g, r):
    """(focus, plan) this routine means against this week's opponent."""
    import sideline
    import weather
    opp = g.opponent_of(team)
    s_off, s_def, _ = sideline.recommend(team, opp)
    focus = r["focus"]
    if focus == "staff":
        focus = getattr(league, "_suggested_focus", None) or (
            "weather" if weather.wants_prep(league, team, g) else "balanced")
    if focus not in FOCUS:
        focus = "balanced"
    off = s_off if r["off"] == "film" or r["off"] not in sideline.OFF_KEYS else r["off"]
    dfk = s_def if r["def"] == "film" or r["def"] not in sideline.DEF_KEYS else r["def"]
    return focus, {"off": off, "def": dfk, "script": bool(r.get("script"))}


def save_routine(league, team, g, focus, plan, name=None):
    """Save this week's setup as one of your routines. Keys that match the film's read are
    saved as 'the film' so the routine keeps working against every opponent."""
    import settings
    import sideline
    s_off, s_def, _ = sideline.recommend(team, g.opponent_of(team))
    plan = plan or {"off": s_off, "def": s_def, "script": False}
    r = {"name": (name or "").strip()[:24] or f"My routine {len(_custom()) + 1}", "focus": focus,
         "off": "film" if plan["off"] == s_off else plan["off"],
         "def": "film" if plan["def"] == s_def else plan["def"], "script": bool(plan.get("script"))}
    cust = _custom()
    if len(cust) >= MAX_CUSTOM:
        return None
    cust.append(r)
    settings.save()
    return f"u{len(cust)}"


def routines_screen(league, team, g, focus, plan, color=C.BCYAN):
    """Look over the routines, save this week's, pick a default, delete yours.
    Returns a routine key to use this week, or None."""
    import settings
    msg = ""
    while True:
        clear()
        print(title_bar("ROUTINES  ·  THE WEEK IN ONE KEY", color))
        print(paint("\n   A routine is a practice focus, a game plan and the openers, saved. The film's plan means the\n"
                    "   keys your staff recommends against whoever you play — it works every week.", C.GRAY))
        st = settings.load()
        dflt = st.get("routine_default")
        print()
        for i, (k, r) in enumerate(routine_list(), 1):
            star = paint("  ★ default", C.BGREEN, C.BOLD) if k == dflt else ""
            mine = paint(" (yours)", C.BMAGENTA) if k not in ROUTINES else ""
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(paint(r['name'], C.BWHITE, C.BOLD) + mine, 34)}"
                  f"{paint(truncate(r['blurb'], 60), C.GRAY)}{star}")
        print()
        cur = {"focus": focus, "off": (plan or {}).get("off", "film"), "def": (plan or {}).get("def", "film"),
               "script": bool((plan or {}).get("script"))}
        print(paint("   This week so far: ", C.GRAY) + paint(describe(cur), C.BCYAN))
        if msg:
            print(paint("   " + msg, C.BYELLOW))
        print()
        print("   " + "   ".join([key("#", "use it this week", C.BGREEN), key("S", "save this week's setup"),
                                  key("D#", "make # the default"), key("D0", "no default"),
                                  key("X#", "delete one of yours"), key("Enter", "back", C.GRAY)]))
        c = ask("Routines:").strip().lower()
        msg = ""
        lst = routine_list()
        if c in ("", "b"):
            return None
        if c.isdigit() and 1 <= int(c) <= len(lst):
            return lst[int(c) - 1][0]
        if c == "s":
            if len(_custom()) >= MAX_CUSTOM:
                msg = f"You have {MAX_CUSTOM} of your own — delete one first (X#)."
                continue
            name = ask("Name it (Enter = a number):").strip()
            k = save_routine(league, team, g, focus, plan, name)
            msg = f"Saved as [{len(lst) + 1}]." if k else "Couldn't save it."
            if k and ask("Make it your default? (y/n)").strip().lower() in ("y", "yes"):
                st["routine_default"] = k
                settings.save()
            continue
        if c.startswith("d") and c[1:].isdigit():
            n = int(c[1:])
            if n == 0:
                st.pop("routine_default", None)
                msg = "No default: the hub opens with your usual practice focus and the staff's plan."
            elif 1 <= n <= len(lst):
                st["routine_default"] = lst[n - 1][0]
                msg = f"Default: {lst[n - 1][1]['name']}. Sim weeks and the hub turned off use it too."
            settings.save()
            continue
        if c.startswith("x") and c[1:].isdigit():
            n = int(c[1:])
            if 1 <= n <= len(lst) and lst[n - 1][0] not in ROUTINES:
                idx = int(lst[n - 1][0][1:]) - 1
                cust = _custom()
                gone = cust.pop(idx)
                d = st.get("routine_default")
                if d and d not in ROUTINES:
                    di = int(d[1:]) - 1
                    if di == idx:
                        st.pop("routine_default", None)
                    elif di > idx:
                        st["routine_default"] = f"u{di}"
                settings.save()
                msg = f"Deleted {gone['name']}."
            else:
                msg = "Only your own routines can be deleted."
            continue


# ═══ After the game: what the week bought ═══════════════════════════════════
PTS_PER_FORM = 1.7                                   # points of margin per rating point of game-day form


def _pts(x):
    return x * PTS_PER_FORM


def _signed(x, digits=2):
    return f"{x:+.{digits}f}"


def credit(league, g, team):
    """What each of the week's decisions put on the field, and what came of it. Returns a dict
    (also kept on the game's sideline record and in the team's ledger), or None."""
    prep = getattr(team, "week_prep", None) or {}
    if not prep or prep.get("week") != g.week and prep.get("week") != league.week:
        return None
    box = getattr(g, "box", None)
    sl = box.__dict__.get("sl") if box is not None else None
    parts = prep.get("parts") or {"practice": {"lift": prep.get("lift", 0.0)}}
    opp = g.opponent_of(team)
    rows = []                                         # (day, what, lift, note, color)
    total = 0.0
    focus = prep.get("focus", "balanced")
    label = FOCUS.get(focus, ("?",))[0]
    pr = parts.get("practice", {})
    lift = pr.get("lift", 0.0)
    total += lift
    notes = []
    hurt = [i for i in (getattr(box, "injuries", None) or []) if len(i) >= 7 and i[2] is team and i[5] != "shaken"]
    inj = pr.get("inj", 1.0)
    if inj > 1.0:
        notes.append(f"injuries x{inj:.2f}: " + (f"{len(hurt)} hurt today ({', '.join(i[3].last_name for i in hurt[:3])})"
                                                 if hurt else "nobody got hurt"))
    elif inj < 1.0:
        notes.append(f"injuries x{inj:.2f}: " + (f"still {len(hurt)} hurt" if hurt else "nobody got hurt"))
    if prep.get("healed"):
        notes.append("back a week early: " + ", ".join(prep["healed"][:3]))
    if prep.get("hours"):
        notes.append(f"+{prep['hours']} recruiting hours this week")
    if focus == "weather":
        import weather
        wx = getattr(g, "wx", None) or getattr(box, "wx", None) or {}
        sev = weather.severity(wx) if wx else 0
        notes.append(f"{weather.label(wx).lower()} day: it hit you half as hard" if sev >= 2 else
                     "the weather never really showed up")
    if focus == "gameplan":
        notes.append("both game-plan keys sharpened (x1.25)")
    close_late = _close_late(box, team)
    if pr.get("clutch"):
        notes.append(f"poise +{pr['clutch']:.1f} late — " + ("and it was a one-score fourth quarter" if close_late
                                                            else "never needed: no one-score fourth quarter"))
    rows.append(("WED", f"Practice: {label}", lift, "; ".join(notes)))
    for src, day, what in (("press", "THU", "Press conference"), ("inbox", "TUE", "Inbox replies"),
                           ("podium", "LAST", "Last week's podium"), ("season", "ALL", "Season-long")):
        fx = parts.get(src)
        if not fx:
            continue
        lf = fx.get("lift", 0.0)
        total += lf
        bits = []
        if fx.get("clutch"):
            bits.append(f"poise {fx['clutch']:+.2f} late" + ("" if close_late else " (not needed)"))
        if fx.get("opp_lift"):
            bits.append(f"{opp.school} {fx['opp_lift']:+.2f} (bulletin board)")
            total -= fx["opp_lift"]
        if fx.get("inj", 1.0) != 1.0:
            bits.append(f"injuries x{fx['inj']:.2f}")
        if lf or bits:
            rows.append((day, what, lf, "; ".join(bits)))
    other = prep.get("lift", 0.0) - sum(p.get("lift", 0.0) for p in parts.values())
    if abs(other) >= 0.01:
        rows.append(("", "Other things this week", other, ""))
        total += other
    if not prep.get("pressed") and "press" not in parts:
        rows.append(("THU", "Press conference", 0.0, "skipped"))
    # Friday: the plan.
    plan_rows = []
    gp = (sl.gp.get(team) if sl is not None and isinstance(getattr(sl, "gp", None), dict) else None) or {}
    if gp:
        import sideline
        whose = "yours" if gp.get("mine") else "the staff's"
        try:
            checks = {lab: (v, c) for lab, v, c in sideline.plan_check(box, team)}
        except Exception:
            checks = {}
        for side, table in (("off", sideline.OFF_KEYS), ("def", sideline.DEF_KEYS)):
            k = gp.get(side, "balanced")
            name = table.get(k, (k,))[0]
            if k == "balanced":
                plan_rows.append((name, "no edge, no risk", C.GRAY))
                continue
            edge = (gp.get("edge") or {}).get(k)
            fitw = ""
            if edge is not None:
                f = sideline.fit(edge)
                fitw = ("a real edge" if f >= 1.2 else "should help" if f >= 0.95 else
                        "fighting uphill" if f >= 0.65 else "the film said no")
            v, c = checks.get(name, ("", C.GRAY))
            plan_rows.append((name, ", ".join(x for x in (fitw, v) if x), c))
        sc = sl.__dict__.get("script") if sl is not None else None
        if gp.get("script"):
            import sideline as _s
            total -= _s.SCRIPT_COST
            if sc and sc.get("snaps"):
                ypp = sc["yards"] / sc["snaps"]
                plan_rows.append(("Scripted openers", f"{sc['snaps']} snaps, {sc['yards']} yds ({ypp:.1f} a play), "
                                  f"{sc['firsts']} first downs" + (f", {sc['td']} TD" if sc.get("td") else "")
                                  + (f", {sc['to']} turnover" if sc.get("to") else ""),
                                  C.BGREEN if ypp >= 5.5 else C.BYELLOW if ypp >= 4.0 else C.BRED))
            else:
                plan_rows.append(("Scripted openers", "the script never got going", C.GRAY))
    else:
        whose = None
    margin = g.score_for(team) - g.score_for(opp)
    res = {"year": league.year, "week": g.week, "opp": opp.school, "margin": margin, "total": round(total, 2),
           "pts": round(_pts(total), 1), "rows": rows, "plan": plan_rows, "whose": whose,
           "routine": prep.get("routine"), "focus": focus}
    if sl is not None:
        sl.credit = {k: v for k, v in res.items() if k not in ("plan",)}
    led = team.__dict__.setdefault("week_ledger", [])
    led[:] = [x for x in led if (x["year"], x["week"]) != (league.year, g.week)][-24:]
    led.append({k: v for k, v in res.items() if k in ("year", "week", "opp", "margin", "total", "pts", "routine")})
    return res


def _keep_decisions(league, g, team):
    """Every game's decisions, kept for good (league.decision_log) so Export to Sheets can list what you
    chose each week: practice focus, routine, game plan, scripted openers, and every headset call.
    Runs from settle() after every played game of yours, whether or not you set a practice plan.
    Plain values only. Never lets a logging problem touch the game."""
    try:
        prep = getattr(team, "week_prep", None) or {}
        if prep and prep.get("week") not in (g.week, league.week):
            prep = {}
        box = getattr(g, "box", None)
        sl = box.__dict__.get("sl") if box is not None else None
        gp = (sl.gp.get(team) if sl is not None and isinstance(getattr(sl, "gp", None), dict) else None) or {}
        res = getattr(sl, "credit", None) or {}
        log = league.__dict__.setdefault("decision_log", [])
        log[:] = [x for x in log if (x["year"], x["week"]) != (league.year, g.week)]
        opp = g.opponent_of(team)
        import sideline
        calls = []
        for e in (getattr(sl, "log", None) or []):
            score = e.get("score")
            calls.append({"q": e.get("q"), "clock": e.get("clock"), "kind": e.get("kind"),
                          "text": str(e.get("text", "")), "staff": e.get("staff"),
                          "yours": str(e.get("yours")) if e.get("yours") is not None else "",
                          "chart": str(e.get("chart")) if e.get("chart") is not None else "",
                          "result": str(e.get("result")) if e.get("result") is not None else "",
                          "score": list(score) if score else None})
        log.append({
            "year": league.year, "week": g.week, "opp": opp.school, "home": g.home is team,
            "result": "W" if g.score_for(team) > g.score_for(opp) else "L",
            "score": [g.score_for(team), g.score_for(opp)],
            "focus": FOCUS[prep["focus"]][0] if prep.get("focus") in FOCUS else "",
            "routine": prep.get("routine") or res.get("routine") or "",
            "pressed": bool(prep.get("pressed")) if prep else None,
            "plan_off": (sideline.OFF_KEYS.get(gp.get("off", "balanced"), (gp.get("off", "balanced"),))[0] if gp else ""),
            "plan_def": (sideline.DEF_KEYS.get(gp.get("def", "balanced"), (gp.get("def", "balanced"),))[0] if gp else ""),
            "script": bool(gp.get("script")) if gp else False,
            "plan_by": res.get("whose") or "",
            "lift": res.get("total"), "pts": res.get("pts"), "margin": res.get("margin"),
            "calls": calls})
        del log[:-400]
    except Exception:
        pass


def _close_late(box, team):
    tl = getattr(box, "timeline", None) or []
    for q, _, hs, as_ in tl:
        if q >= 4 and abs(hs - as_) <= 8:
            return True
    return False


def week_report(league, g, team):
    """The postgame screen: the week, decision by decision, in rating points and in points."""
    import guide
    guide.tip(league, "report")
    res = credit(league, g, team)
    if res is None:
        return None
    opp = g.opponent_of(team)
    clear()
    print(title_bar(f"THE WEEK'S WORK  ·  {team.school.upper()} {g.score_for(team)}, "
                    f"{opp.school.upper()} {g.score_for(opp)}", league.conference_color(team.conference)))
    if res.get("routine"):
        print(paint(f"   Routine: {res['routine']}", C.GRAY))
    print(paint("   What each decision put on the field (rating points of game-day form; about "
                f"{PTS_PER_FORM:.1f} points on the scoreboard apiece).", C.GRAY))
    print()
    for day, what, lift, note in res["rows"]:
        col = C.BGREEN if lift > 0.005 else C.BRED if lift < -0.005 else C.GRAY
        print(f"   {paint(pad(day, 6), C.GRAY)}{pad(paint(what, C.BWHITE), 33)}"
              f"{pad(paint(_signed(lift), col, C.BOLD), 8)}" + paint(f'≈ {_pts(lift):+.1f} pts', col))
        for bit in [b for b in note.split("; ") if b]:
            print(paint(f"   {'':6}  · {truncate(bit, 86)}", C.GRAY))
    if res["plan"]:
        print()
        print(paint(f"   FRI   Game plan ({res['whose']})", C.BWHITE))
        for name, verdict, col in res["plan"]:
            print(f"         {pad(paint(name, C.BCYAN), 34)}{paint(verdict, col)}")
    print()
    tot, pts, m = res["total"], res["pts"], res["margin"]
    col = C.BGREEN if tot > 0 else C.BRED if tot < 0 else C.GRAY
    print("   " + paint("The week in all: ", C.GRAY) + paint(f"{tot:+.2f} form", col, C.BOLD)
          + paint(f"  ≈ {pts:+.1f} points", col))
    res_w = "Won" if m > 0 else "Lost" if m < 0 else "Tied"
    if abs(pts) < 0.3:
        line = f"{res_w} by {abs(m)}. The week put next to nothing on the scoreboard — it was about more than Saturday."
    elif m > 0 and 0 < pts and m <= pts + 0.5:
        line = f"You won by {m}. The week was worth about {pts:.1f} — it was the difference."
    elif m < 0 and pts < 0 and -m <= -pts + 0.5:
        line = f"You lost by {-m}. The week cost about {-pts:.1f} — that's the game."
    elif m < 0 and pts > 0 and -m <= 3:
        line = f"You lost by {-m}. The week was worth about {pts:.1f}; it wasn't quite enough."
    elif m > 0 and pts < 0 and m <= -pts + 3:
        line = f"You won by {m} despite a week that cost about {-pts:.1f}."
    elif abs(m) <= abs(pts) + 7:
        line = f"{res_w} by {abs(m)}. The week was worth about {pts:+.1f} of that."
    else:
        line = f"{res_w} by {abs(m)} — more than anything the week decided."
    print(paint("   " + line, C.BWHITE))
    pause()
    return res


def last_credit_line(team):
    led = team.__dict__.get("week_ledger") or []
    if not led:
        return None
    x = led[-1]
    col = C.BGREEN if x["pts"] > 0 else C.BRED if x["pts"] < 0 else C.GRAY
    season = [y for y in led if y["year"] == x["year"]]
    tail = f" · this season {sum(y['pts'] for y in season):+.1f} over {len(season)} game{'s' if len(season) != 1 else ''}" \
        if len(season) > 1 else ""
    return paint("   Last week's work: ", C.GRAY) + paint(f"{x['pts']:+.1f} pts vs {x['opp']}", col) + paint(tail, C.GRAY)


# ═══ The game plan ══════════════════════════════════════════════════════════

def game_plan_screen(league, team, opp, cur=None):
    """Friday: one offensive key, one defensive key, and the openers. Returns the plan (or None)."""
    import guide
    guide.tip(league, "game_plan")
    import sideline
    m = sideline.matchup(team, opp)
    s_off, s_def, lines = sideline.recommend(team, opp, m)
    off = (cur or {}).get("off", s_off)
    dfk = (cur or {}).get("def", s_def)
    script = (cur or {}).get("script", False)
    while True:
        clear()
        print(title_bar(f"FRIDAY  ·  GAME PLAN vs {opp.school.upper()}", league.conference_color(team.conference)))
        print(paint("\n   What the film shows:", C.GRAY, C.BOLD))
        for ln in lines:
            print(paint("   · " + ln, C.BCYAN))

        def worth(k):
            if k == "balanced":
                return paint("no edge, no risk", C.GRAY)
            f = sideline.fit(m.get(k, 0))
            return paint("a real edge" if f >= 1.2 else "should help" if f >= 0.95 else
                         "fighting uphill" if f >= 0.65 else "the film says no", C.BGREEN if f >= 0.95 else
                         C.BYELLOW if f >= 0.65 else C.BRED)
        for title, table, pick, rec, keyc in (("OFFENSE", sideline.OFF_KEYS, off, s_off, "O"),
                                             ("DEFENSE", sideline.DEF_KEYS, dfk, s_def, "D")):
            print()
            print(paint(f"   {title}", C.BYELLOW, C.BOLD))
            for i, (k, (label, blurb)) in enumerate(table.items(), 1):
                mark = paint("●", C.BGREEN, C.BOLD) if k == pick else " "
                tag = paint("  ← staff", C.BCYAN) if k == rec else ""
                print(f"   {mark} {paint(f'[{keyc}{i}]', C.BYELLOW, C.BOLD)} {pad(label, 32)}{pad(paint(blurb, C.GRAY), 48)}"
                      f"{worth(k)}{tag}")
        print()
        sc = paint("ON", C.BGREEN, C.BOLD) if script else paint("OFF", C.GRAY)
        print(f"   {paint('[S]', C.BYELLOW, C.BOLD)} Script the openers: {sc}   "
              + paint(f"sharp first ten snaps (+{sideline.SCRIPT_LIFT:.1f}) · costs a practice period "
                      f"(-{sideline.SCRIPT_COST:.1f} Saturday)", C.GRAY))
        print(paint("   A key that fits the matchup is worth more. 'Game-plan heavy' practice sharpens both keys.", C.GRAY))
        print("   " + "   ".join([key("O#", "offense"), key("D#", "defense"), key("S", "script"),
                                  key("Enter", "done", C.BGREEN), key("R", "take the staff's plan")]))
        c = ask("Game plan:").strip().lower()
        if c == "":
            return {"off": off, "def": dfk, "script": script}
        if c == "r":
            off, dfk = s_off, s_def
            continue
        if c == "s":
            script = not script
            continue
        if len(c) >= 2 and c[0] in "od" and c[1:].isdigit():
            n = int(c[1:])
            table = sideline.OFF_KEYS if c[0] == "o" else sideline.DEF_KEYS
            if 1 <= n <= len(table):
                if c[0] == "o":
                    off = list(table)[n - 1]
                else:
                    dfk = list(table)[n - 1]
        elif c == "b":
            return cur


# ═══ The press conference ═══════════════════════════════════════════════════
# Built from the week you're actually having — see presser.py.

def press_conference(league, team, g):
    import guide
    guide.tip(league, "presser")
    import presser
    return presser.press_conference(league, team, g)


# ═══ The hub ════════════════════════════════════════════════════════════════

def hub(league):
    """The week before your game. Returns True to play Saturday, False to go back."""
    import settings
    team = _team(league)
    if team is None:
        return True
    g = next_game(league, team)
    import people
    people.weekly(league)
    if g is None:
        return True
    if (league.year, league.week + 1) in league.__dict__.get("_prep_done", set()):
        return True
    st = settings.load()
    if not st.get("week_hub", True):
        c = ask("[D] Depth  [F] Formation subs  [K] Retention  Enter = let staff handle the week:").strip().lower()
        if c == "d":
            import depth_ui
            depth_ui.manage(league, team)
        elif c == "f":
            import formation_subs
            formation_subs.screen(league, team)
        elif c == "k":
            import retention
            retention.screen(league, team)
        auto_week(league)
        return True
    import guide
    guide.tip(league, "week_hub")
    import weather
    if getattr(league, "_suggested_focus", None) is None and weather.wants_prep(league, team, g):
        league._suggested_focus = "weather"          # the staff has seen the forecast
    focus = getattr(league, "_suggested_focus", None) or st.get("practice_focus", "balanced")
    presser = None
    import carousel as cz
    import dashboard
    import sideline
    wk = league.week + 1
    gplan = sideline.plan_of(team, league.year, wk)
    hs = league.__dict__.get("_hub_state") or {}
    routine = None
    if hs.get("yw") == (league.year, wk):             # back on the hub this week: as you left it
        focus, routine, presser = hs.get("focus", focus), hs.get("routine"), hs.get("presser")
    else:
        r0 = default_routine()
        if r0 is not None and gplan is None:          # your default routine, loaded
            focus, gplan = routine_setup(league, team, g, r0)
            sideline.set_plan(team, league.year, wk, gplan["off"], gplan["def"], gplan["script"])
            routine = r0["name"]

    def keep():
        league.__dict__["_hub_state"] = {"yw": (league.year, wk), "focus": focus, "routine": routine,
                                         "presser": presser}

    def use(k):
        nonlocal focus, gplan, routine
        r = routine_by_key(k)
        if r is None:
            return
        focus, gplan = routine_setup(league, team, g, r)
        sideline.set_plan(team, league.year, wk, gplan["off"], gplan["def"], gplan["script"])
        routine = r["name"]

    def edited():
        nonlocal routine
        if routine and not routine.endswith("(adjusted)"):
            routine += " (adjusted)"

    while True:
        keep()
        clear()
        opp = g.opponent_of(team)
        at = "vs" if g.home is team or g.neutral else "at"
        rk = league.rankings.rank_of(opp)
        print(title_bar(f"{league.week_name(league.week + 1).upper()}  ·  {at.upper()} "
                        f"{('#' + str(rk) + ' ') if rk else ''}{opp.school.upper()}", league.conference_color(team.conference)))
        site = 0 if g.neutral else (1 if g.home is team else -1)
        wp = cz.win_prob(team, opp, site, league)
        riv = cz.PRIMARY_RIVAL.get(team.school) == opp.school
        rk_us, rk_them = league.rankings.rank_of(team), league.rankings.rank_of(opp)
        top = [(f"{'#' + str(rk_us) + ' ' if rk_us else ''}{paint(team.school, C.BWHITE, C.BOLD)} {team.record}  "
                f"{'vs' if g.home is team or g.neutral else 'at'}  {'#' + str(rk_them) + ' ' if rk_them else ''}"
                f"{paint(opp.school, C.BWHITE, C.BOLD)} {opp.record}"),
               (f"Us {scout._w(scout.TEAM, team.team_ovr).replace('below average', 'below avg')} · Them "
                f"{scout._w(scout.TEAM, opp.team_ovr).replace('below average', 'below avg')} · "
                f"{scout.odds(wp).replace(chr(39).join(['you', 're ']), '')}" if scout.hidden(league)
                else f"OVR {team.team_ovr} vs {opp.team_ovr} · {scout.odds(wp)}"),
               paint("RIVALRY WEEK" if riv else f"HC {opp.coach.name if opp.coach else '—'} · "
                                                  f"{opp.coach.offense_scheme if opp.coach else ''}", C.BYELLOW if riv else C.GRAY)]
        last = next((x for x in reversed(league.team_games(team)) if x.played), None)
        film = [n for n, _ in people.film_notes(league, team, last)] if last is not None else \
            ["Fall camp's over. The film starts Saturday."]
        n_un, n_wait = people.unread(league), len(people.waiting(league))
        inbox_lines = [f"{paint(str(n_un), C.BYELLOW, C.BOLD)} unread · {paint(str(n_wait), C.BMAGENTA, C.BOLD)} want a reply"]
        for m in list(reversed(people.inbox(league)))[:3]:
            dot = "●" if not m["read"] else "·"
            inbox_lines.append(paint(dot + " ", C.BYELLOW) + truncate(f"{people.sender_label(m, short=True)}: {m['subject']}", 40))
        label, blurb, *_ = FOCUS[focus]
        sug = getattr(league, "_suggested_focus", None)
        prac = [paint(label, C.BGREEN, C.BOLD), paint(blurb, C.GRAY)]
        try:
            import practice
            nb = len(practice.battles(league, team))
            prac.append(paint(f"[R] report: {nb} position battle{'s' if nb != 1 else ''}" if nb else
                              "[R] practice report", C.BYELLOW))
        except Exception:
            pass
        if sug and sug != focus:
            prac.append(paint(f"Staff suggests: {FOCUS[sug][0]}", C.BCYAN))
        press = [paint("Done: " + ", ".join(presser.get("said", [])), C.GRAY) if presser else
                 paint("Optional. Two questions.", C.GRAY)]
        import effects
        banked, theirs = effects.pending_lift(team)
        if banked or theirs:
            press.append(paint(f"Banked for Saturday: {banked:+.2f} form" +
                               (f" · them {theirs:+.2f}" if theirs else ""), C.BGREEN if banked >= 0 else C.BRED))
        hurt = [p for p in team.injured() if p in team.players_at(p.position)[:3]][:4]
        inj = [paint(f"OUT {p.position} {p.name} ({p.inj_games} wk)", C.BRED) for p in hurt] or \
            [paint("Everybody's available.", C.BGREEN)]
        if gplan:
            inj = [paint("Plan: ", C.GRAY) + paint(truncate(f"{sideline.OFF_KEYS[gplan['off']][0]} / "
                                                             f"{sideline.DEF_KEYS[gplan['def']][0]}"
                                                             + (" · scripted" if gplan.get("script") else ""), 42),
                                                    C.BGREEN)] + inj[:2]
        else:
            inj = [paint("Plan: the staff's ([G] to set yours)", C.GRAY)] + inj[:2]
        fc = weather.forecast(g, league, 0)
        fc_col = C.BRED if fc["severity"] >= 3 else C.BYELLOW if fc["severity"] >= 2 else C.BCYAN
        top.append(paint("Forecast: ", C.GRAY) + paint(truncate(fc["headline"] + (f" · {fc['temp']}°" if not fc["indoor"]
                                                                               else ""), 34), fc_col))
        film_lines = [truncate(x, 44) for x in film[:3]]
        note = weather.staff_note(league, team, g)
        if note:
            film_lines = film_lines[:2] + [paint(truncate(note, 44), C.BCYAN)]
        rows = columns(panel("SATURDAY", top, 50, height=4), panel("MONDAY · FILM", film_lines, 49, height=4))
        rows += columns(panel("TUESDAY · INBOX", inbox_lines, 50, height=4),
                        panel("WEDNESDAY · PRACTICE", prac, 49, height=4))
        rows += columns(panel("THURSDAY · PRESS", press, 50, height=3), panel("FRIDAY · INJURIES", inj, 49, height=3))
        for ln in rows:
            print(ln)
        lc = last_credit_line(team)
        if lc:
            print(lc)
        print(rule())
        rl = routine_list()
        dflt = st.get("routine_default")
        print("   " + paint("ROUTINE ", C.BCYAN, C.BOLD) + (paint(routine, C.BGREEN, C.BOLD) if routine else
                                                           paint("none — set it by hand, or pick one:", C.GRAY)))
        items = [key(str(i), truncate(r["name"], 16) + ("★" if k == dflt else ""),
                     C.BGREEN if routine and routine.startswith(r["name"]) else C.BYELLOW)
                 for i, (k, r) in enumerate(rl, 1)] + [key("Y", "routines")]
        cur = "  "
        for it in items:
            if visible_len(cur) + visible_len(it) + 2 > 99:
                print(cur.rstrip())
                cur = "  "
            cur += " " + it + " "
        print(cur.rstrip())
        from ui import footer
        footer(key("Enter", "go to Saturday", C.BGREEN), key("G", "game plan"), key("P", "practice focus"),
               key("D", "depth chart"), key("F", "formation subs"), key("K", "retention"), key("I", "inbox"),
               key("M", "press conference"), key("R", "practice report"), key("O", f"film on {opp.school}"),
               key("T", f"{opp.school} page & schedule"), key("W", "weather"), key("S", "my schedule"),
               key("B", "back", C.GRAY))
        c = ask("This week:").strip().lower()
        if c == "":
            apply_prep(league, team, focus, presser, routine=routine)
            st["practice_focus"] = focus
            settings.save()
            league._suggested_focus = None
            league.__dict__.pop("_hub_state", None)
            return True
        if c == "b":
            return False
        if c.isdigit() and 1 <= int(c) <= len(rl):
            use(rl[int(c) - 1][0])
            continue
        if c == "y":
            k = routines_screen(league, team, g, focus, gplan, league.conference_color(team.conference))
            if k:
                use(k)
            continue
        if c == "r":
            import practice
            practice.screen(league, team)
            continue
        if c == "o":
            import practice
            practice.film(league, opp)
            continue
        if c == "w":
            import weather_screens
            weather_screens.center(league, team)
            continue
        if c in ("t", "s"):
            import screens
            (screens.team_view if c == "t" else screens.schedule_view)(league, opp if c == "t" else team)
            continue
        if c == "d":
            import depth_ui
            depth_ui.manage(league, team)
            continue
        if c == "f":
            import formation_subs
            formation_subs.screen(league, team)
            continue
        if c == "k":
            import retention
            retention.screen(league, team)
            continue
        if c == "g":
            before = {k: gplan.get(k) for k in ("off", "def", "script")} if gplan else None
            gplan = game_plan_screen(league, team, opp, gplan) or gplan
            if gplan:
                sideline.set_plan(team, league.year, wk, gplan["off"], gplan["def"], gplan.get("script"))
                if before != {k: gplan[k] for k in ("off", "def", "script")}:
                    edited()
            continue
        if c == "i":
            people.inbox_screen(league)
            focus = getattr(league, "_suggested_focus", None) or focus
        elif c == "p":
            print()
            for i, k in enumerate(FOCUS_KEYS, 1):
                lb, bl, *_ = FOCUS[k]
                tag = paint("  ← staff", C.BCYAN) if k == sug else ""
                print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(lb, 24)}{paint(bl, C.GRAY)}{tag}")
            p = ask("Focus:").strip()
            if p.isdigit() and 1 <= int(p) <= len(FOCUS_KEYS) and FOCUS_KEYS[int(p) - 1] != focus:
                focus = FOCUS_KEYS[int(p) - 1]
                edited()
        elif c == "m":
            if presser:
                print(paint("   You've already done your media availability this week.", C.GRAY))
                pause()
            else:
                presser = press_conference(league, team, g)
