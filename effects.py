"""
effects.py — What your answers actually do (Career mode).

Every reply in the inbox and every answer at the podium carries a small bundle
of consequences. They're written as a dict, applied here, and described to you
before you choose (the gray line under each option), so a choice is a trade,
not a guess:

  seat        your AD's patience (negative = he likes it; the seat cools)
  chem        locker-room chemistry (worth up to about a point on Saturday)
  lift        this coming Saturday's game-day form
  later_lift  the game after that (a package saved, a plan that pays off late)
  opp_lift    the other locker room's form (bulletin-board material)
  clutch      poise in one-score fourth quarters, next game
  inj         injury-rate multiplier, next game
  season_lift / season_inj   the same, every game for the rest of the season
  hours       recruiting hours: + extra this week, - spent this week
  recruits    interest from the top of your recruiting board
  recruit     interest from the one recruit the message is about (ref)
  state       interest from every recruit on your board from one state
  money       next season's NIL pool (+ a gift, - money spent)
  focus       the staff's suggested practice focus
  unhappy / bought_in / dev / promise / sit / heal   one player (who)
  stay        a coordinator's lean: -1 more likely to stay, +1 more likely to go
  gamble      [(odds, fx, text), (fx, text)] — a coin you choose to flip
  stake       something on the line later (resolved after a game, or in December)

Nothing here runs outside Career mode.
"""
import random

from ui import C, paint


# ═══ The AD's taste ═════════════════════════════════════════════════════════

def by_ad(team, table):
    """Pick a number by AD style: by_ad(team, {"default": 0, "win_now": -2})."""
    style = (getattr(team, "ad", None) or {}).get("style", "default")
    return table.get(style, table.get("default", 0))


# ═══ Boosts that wait for a game ════════════════════════════════════════════

def _boosts(team):
    return team.__dict__.setdefault("_fx_boost", {"next": {}, "later": {}})


def _add(bucket, k, v):
    if k == "inj":
        bucket["inj"] = bucket.get("inj", 1.0) * v
    else:
        bucket[k] = bucket.get(k, 0.0) + v


def _prep_live(league, team):
    """The practice plan for the coming game, if it's already been set this week."""
    wp = getattr(team, "week_prep", None) or {}
    return wp if wp and wp.get("year") == league.year and wp.get("week") == league.week + 1 else None


_SRC = [None]                                             # what apply() is applying right now (for the credit)


def source_label(why):
    """Where a boost came from, for the postgame credit: the Thursday presser, last week's
    postgame podium, or the inbox (and anything else you answered during the week)."""
    if why == "press conference":
        return "press"
    if why == "postgame press conference":
        return "podium"
    return "inbox"


def _credit(bucket, src, kw):
    per = bucket.setdefault("_src", {}).setdefault(src, {})
    for k, v in kw.items():
        if k == "inj":
            per["inj"] = per.get("inj", 1.0) * v
        else:
            per[k] = per.get(k, 0.0) + v


def boost(league, team, when="next", **kw):
    """Add to the next game (or the one after). If the week's plan is already
    locked in, it goes straight onto it."""
    src = source_label(_SRC[0])
    live = _prep_live(league, team) if when == "next" else None
    if live is not None:
        for k, v in kw.items():
            if k == "inj":
                live["injury"] = live.get("injury", 1.0) * v
            else:
                live[k] = live.get(k, 0.0) + v
        _credit(live.setdefault("parts", {}), src, kw)
        return
    b = _boosts(team)[when]
    for k, v in kw.items():
        _add(b, k, v)
    _credit(b, src, kw)


def season_mod(league, team, lift=0.0, inj=1.0):
    s = team.__dict__.get("_fx_season")
    if not s or s.get("year") != league.year:
        s = team._fx_season = {"year": league.year, "lift": 0.0, "inj": 1.0}
    s["lift"] += lift
    s["inj"] *= inj


def take(league, team):
    """What's waiting for this game: {"lift", "opp_lift", "clutch", "inj"}. Called when
    the week's plan is set; the game-after bucket moves up."""
    b = _boosts(team)
    out = dict(b["next"])
    out["_src"] = {k: dict(v) for k, v in (out.get("_src") or {}).items()}
    b["next"], b["later"] = b["later"], {}
    s = team.__dict__.get("_fx_season")
    if s and s.get("year") == league.year:
        out["lift"] = out.get("lift", 0.0) + s["lift"]
        out["inj"] = out.get("inj", 1.0) * s["inj"]
        if s["lift"] or s["inj"] != 1.0:
            out["_src"]["season"] = {"lift": s["lift"], "inj": s["inj"]}
    return out


def pending_lift(team):
    """For the week screen: what's already banked for Saturday."""
    b = _boosts(team)["next"]
    return b.get("lift", 0.0), b.get("opp_lift", 0.0)


# ═══ Applying a bundle ══════════════════════════════════════════════════════

_QUIET_TRUST = False                                      # set while a stake is settled (it has its own trust line)


def _seat_why(d, why):
    """What people say moved the seat: 'the AD liked your press conference'."""
    if not why or why.startswith(("the AD", "your AD")):
        return why
    if why[0].isupper() or ":" in why:
        what = f"your reply to “{why}”"
    elif why.startswith(("a ", "an ", "the ", "your ", "how ", "what ")):
        what = why
    else:
        what = f"your {why}"
    return f"the AD {'liked' if d < 0 else 'didn’t like'} {what}"


def _seat(league, coach, d, why):
    if not d:
        return
    coach.__dict__.setdefault("seat_events", []).append((league.week, d, _seat_why(d, why)))
    log = coach.__dict__.setdefault("seat_log", [])           # survives the week-1 reset of seat_events
    log.append((league.year, league.week, d, _seat_why(d, why)))
    del log[:-20]
    coach.seat = int(max(0, min(100, coach.seat + d)))
    if not _QUIET_TRUST:
        import ad_trust
        ad_trust.change(league, -d * 1.5, why)             # he remembers what you said, not just the heat


def board(team, n=10):
    return [r for r in getattr(team, "recruiting_targets", []) if not r.signed][:n]


def _bump_recruit(team, r, v):
    r.interest[team] = max(0, min(100, r.interest.get(team, 0) + v))


def apply(league, fx, why="", rng=None):
    """Apply a bundle. Returns a list of short lines describing what happened
    (the gamble's result, the recruiting-hour bill...). Returns None if a cost
    can't be paid (and nothing happens)."""
    if not fx:
        return []
    coach = league.user_coach
    team = coach.team
    rng = rng or random.Random(f"fx:{league.seed}:{league.year}:{league.week}:{why}:{sorted(fx)}")
    out = []
    cost = fx.get("hours", 0)
    import skills
    if fx.get("meeting") and skills.team_has(team, "open_door"):
        cost = 0                                                     # Open Door: your office is always open
    if cost < 0:
        cyc = league.recruiting
        if cyc.remaining_hours(team) < -cost:
            return None
        cyc.hours_used[team] += -cost
    elif cost > 0:
        league.recruiting.hours_used[team] -= cost          # extra hours this week
    if fx.get("seat"):
        _seat(league, coach, fx["seat"], why or "how you handled it")
    if fx.get("chem"):
        import personalities
        personalities._nudge(team, fx["chem"])
    nxt = {k: fx[k] for k in ("lift", "opp_lift", "clutch", "inj") if fx.get(k)}
    _SRC[0] = why
    try:
        if nxt:
            boost(league, team, "next", **nxt)
        if fx.get("later_lift"):
            boost(league, team, "later", lift=fx["later_lift"])
    finally:
        _SRC[0] = None
    if fx.get("season_lift") or fx.get("season_inj"):
        season_mod(league, team, fx.get("season_lift", 0.0), fx.get("season_inj", 1.0))
    if fx.get("recruits"):
        for r in board(team):
            _bump_recruit(team, r, fx["recruits"])
    if fx.get("recruit") and fx.get("ref") is not None:
        _bump_recruit(team, fx["ref"], fx["recruit"])
    if fx.get("promise_recruit") and fx.get("ref") is not None:
        r = fx["ref"]
        r.player.promised = {"kind": fx["promise_recruit"], "school": team.school, "year": league.year}
        k = (team, r)
        league.recruiting.relationship[k] = min(100, league.recruiting.relationship[k] + 6)
    if fx.get("state"):
        st, v = fx["state"]
        for r in getattr(team, "recruiting_targets", []):
            if not r.signed and r.home_state == st:
                _bump_recruit(team, r, v)
    if fx.get("top"):
        for r in board(team, fx["top"][0]):
            _bump_recruit(team, r, fx["top"][1])
    if fx.get("ask"):
        asks = team.__dict__.setdefault("_fx_asks", {})
        asks[league.year] = asks.get(league.year, 0) + 1
        import ad_trust
        ad_trust.change(league, -2 * asks[league.year], "asked him for money")
    if fx.get("money"):
        team.__dict__.setdefault("income", []).append(
            {"what": fx.get("money_what") or why or "inbox", "amount": int(fx["money"]), "year": league.year + 1})
    if fx.get("cp"):
        import compliance
        out.extend(compliance.apply_fx(league, team, fx["cp"], fx.get("ref"), fx.get("who")) or [])
    if fx.get("rules"):
        team._fx_rules = (league.year, fx["rules"])       # how often trouble finds your locker room
    if fx.get("focus"):
        league._suggested_focus = fx["focus"]
    if fx.get("priority"):
        team.priority_pos = fx["priority"]
    if fx.get("depth_swap"):
        pos, promote, demote = fx["depth_swap"]
        order = list(team.players_at(pos))
        if promote in order and demote in order:
            import morale, traits
            order.remove(promote); order.insert(order.index(demote), promote)
            team.__dict__.setdefault("depth_order", {})[pos] = order
            morale.nudge(promote, 4 * traits.mod(promote, "role", 1.0), "promoted by the staff", league)
            morale.nudge(demote, -6 * traits.mod(demote, "role", 1.0), "demoted by the staff", league)
    p = fx.get("who")
    if p is not None:
        import morale
        why = fx.get("why_mood") or why or "a decision you made"
        if fx.get("unhappy"):
            p.__dict__["disgruntled"] = league.year
            morale.nudge(p, -15, why, league)
        if fx.get("bought_in"):
            p.__dict__.pop("disgruntled", None)
            p.__dict__["bond"] = league.year
            morale.nudge(p, 15, why, league)
        if fx.get("morale"):
            morale.nudge(p, fx["morale"], why, league)
        if fx.get("dev"):
            p.__dict__["dev_boost"] = max(getattr(p, "dev_boost", 1.0), fx["dev"])
        if fx.get("promise"):
            p.promise = fx["promise"]
            morale.nudge(p, {"made": 8, "role": 5, "ignored": -8}.get(fx["promise"], 0), why, league)
        if fx.get("sit"):
            import personalities
            personalities._suspend(league, p, fx["sit"], fx.get("sit_why", "held out"), event=fx.get("sit_event"))
        if fx.get("add_captain"):
            caps = team.__dict__.setdefault("captains", [])
            if p not in caps:
                caps.append(p)
                p.events[league.year].append("Named a captain by the head coach")
        if fx.get("drop_captain"):
            caps = getattr(team, "captains", None) or []
            if p in caps:
                caps.remove(p)
                p.events[league.year].append("Lost his captaincy")
        if fx.get("play_hurt"):
            p.inj_games = 0
            p.__dict__["playing_hurt"] = (league.year, league.week)
    if fx.get("team_morale"):
        import morale
        for q in team.roster:
            morale.nudge(q, fx["team_morale"], fx.get("why_mood") or why or "the team", league)
    if fx.get("heal"):
        for q in team.roster:
            if 1 <= getattr(q, "inj_games", 0) <= fx["heal"] and not getattr(q, "suspended", False):
                q.inj_games -= 1
    c = fx.get("coord")
    if c is not None and fx.get("stay"):
        c.__dict__["stay_lean"] = (league.year, fx["stay"])
    if fx.get("flip"):
        n, v = fx["flip"]
        import skills
        if skills.team_has(team, "flip_artist"):
            v *= 1.5                                                 # Flip Artist (coaching tree)
        pool = sorted((r for r in getattr(team, "recruiting_targets", [])
                       if not r.signed and r.committed_to is not None and r.committed_to is not team),
                      key=lambda r: -r.interest.get(team, 0))[:n]
        for r in pool:
            _bump_recruit(team, r, v)
    if fx.get("stake"):
        stake(league, fx["stake"])
    also = fx.get("also")
    for extra in (also if isinstance(also, list) else [also] if also else []):
        apply(league, extra, why, rng)
    if fx.get("gamble"):
        (odds, good, gtxt), (bad, btxt) = fx["gamble"]
        if rng.random() < odds:
            apply(league, good, why, rng)
            out.append(gtxt)
        else:
            apply(league, bad, why, rng)
            out.append(btxt)
    return out


# ═══ Stakes: something on the line later ════════════════════════════════════
# {"on": "next" | "vs" | "season", "opp": school, "made": (year, week),
#  "win": fx, "loss": fx, "wtext": str, "ltext": str, "who": sender, "subject": str,
#  "need": "winning" | "bowl" | int wins   (season stakes only)}

def stake(league, st):
    st = dict(st)
    st["made"] = (league.year, league.week)
    book = league.__dict__.setdefault("_fx_stakes", [])
    if st["on"] == "season":                          # say the same thing twice, it's still one promise
        book[:] = [x for x in book if not (x["on"] == "season" and x.get("subject") == st.get("subject"))]
    book.append(st)


def _result(league, team, st):
    """True/False once the stake is decided, None while it's still open."""
    year, wk = st["made"]
    if league.year != year:
        return "drop"
    games = [g for g in league.team_games(team) if g.played and g.week > wk]
    if st["on"] == "next":
        return (games[0].winner is team) if games else None
    if st["on"] == "vs":
        g = next((g for g in games if g.opponent_of(team).school == st["opp"]), None)
        return (g.winner is team) if g else None
    return None                                       # season stakes are settled in December


def settle(league, season_over=False):
    """Check every open stake. Posts the verdicts to the inbox."""
    import people
    coach = getattr(league, "user_coach", None)
    team = getattr(coach, "team", None)
    if team is None:
        return
    keep = []
    for st in league.__dict__.get("_fx_stakes", []):
        if st["on"] == "season":
            if not season_over or st["made"][0] != league.year:
                if st["made"][0] == league.year:
                    keep.append(st)
                continue
            need = st.get("need", "winning")
            if need == "winning":
                won = team.wins > team.losses
            elif need == "bowl":
                won = team.wins >= 6
            else:
                won = team.wins >= int(need)
        else:
            won = _result(league, team, st)
            if won == "drop":
                continue
            if won is None:
                if season_over:
                    continue                          # the game never came
                keep.append(st)
                continue
        fx = st["win"] if won else st["loss"]
        global _QUIET_TRUST
        _QUIET_TRUST = str(st.get("who", "")).startswith("AD ")
        try:
            apply(league, fx, st.get("why", "a promise you made"))
        finally:
            _QUIET_TRUST = False
        if str(st.get("who", "")).startswith("AD "):
            import ad_trust
            ad_trust.change(league, 6 if won else -7, "kept your word" if won else "broke your word")
        people._post(league, st.get("who", "Staff"), "Follow-up", st.get("subject", "How it played out"),
                     st["wtext"] if won else st["ltext"], kind="result",
                     color=C.BGREEN if won else C.BRED)
    league._fx_stakes = keep


def after_game_rolls(league):
    """Things that happen after a game you took a risk on: a player who played hurt."""
    coach = getattr(league, "user_coach", None)
    team = getattr(coach, "team", None)
    if team is None:
        return
    import people
    for p in team.roster:
        ph = p.__dict__.get("playing_hurt")
        if not ph or ph[0] != league.year or ph[1] >= league.week:
            continue
        p.__dict__.pop("playing_hurt", None)
        rng = random.Random(f"hurt:{league.seed}:{league.year}:{league.week}:{p.last_name}")
        if rng.random() < 0.35:
            n = rng.randint(2, 4)
            p.inj_games = max(getattr(p, "inj_games", 0), n)
            p.inj_desc = "aggravated the injury he played through"
            p.inj_week = league.week
            people._post(league, "Head athletic trainer", "Sports medicine", f"{p.name} aggravated it",
                         f"{p.first_name} made it through Saturday, but he aggravated it. He's out {n} weeks now. "
                         "That's the risk we talked about.", kind="result", color=C.BRED)
        else:
            people._post(league, "Head athletic trainer", "Sports medicine", f"{p.name} came through fine",
                         f"{p.first_name} got through it. Sore, but no setback. He'll be full go this week.",
                         kind="result", color=C.BGREEN)


# ═══ Describing a bundle (the gray line under each option) ══════════════════

UP, DOWN = "▲", "▼"


def _money_word(x):
    x = abs(int(x))
    return f"${x / 1_000_000:.1f}M" if x >= 1_000_000 else f"${x // 1000}K"


def _parts(fx):
    """[(good?, text)] — what the player will see before choosing."""
    if not fx or fx.get("quiet"):
        return [(g, t) for g, t in _notes(fx)] if fx else []
    return _collapse(_raw_parts(fx))


def _notes(fx):
    return [t if isinstance(t, tuple) else (None, t) for t in fx.get("notes", [])]


def _collapse(parts):
    """'Eli develops faster · Zion develops faster' → 'Eli, Zion develop faster'; repeats become ×N."""
    out, devs, seen = [], [], {}
    for g, t in parts:
        if t.endswith(" develops faster"):
            devs.append(t[:-len(" develops faster")])
            continue
        if (g, t) in seen:
            seen[(g, t)] += 1
            continue
        seen[(g, t)] = 1
        out.append((g, t))
    out = [(g, f"{t} ×{seen[(g, t)]}" if seen[(g, t)] > 1 else t) for g, t in out]
    if devs:
        names = devs[0] if len(devs) == 1 else ", ".join(devs[:-1]) + " and " + devs[-1]
        out.append((True, f"{names} develop{'s' if len(devs) == 1 else ''} faster"))
    return out


def _raw_parts(fx):
    if not fx:
        return []
    out = []

    def add(good, text):
        out.append((good, text))

    s = fx.get("seat", 0)
    if s:
        add(s < 0, f"AD {'likes it' if s < 0 else 'won’t like it'}" + (" a lot" if abs(s) >= 3 else ""))
    v = fx.get("chem", 0)
    if v:
        add(v > 0, f"locker room {UP if v > 0 else DOWN}" + (UP if v >= 4 else DOWN if v <= -4 else ""))
    v = fx.get("lift", 0)
    if v:
        add(v > 0, f"Saturday {UP if v > 0 else DOWN}" + (UP if v >= 0.3 else DOWN if v <= -0.3 else ""))
    v = fx.get("later_lift", 0)
    if v:
        add(v > 0, f"the game after {UP if v > 0 else DOWN}")
    v = fx.get("opp_lift", 0)
    if v:
        add(v < 0, "fires up the other locker room" if v > 0 else "quiets the other locker room")
    v = fx.get("clutch", 0)
    if v:
        add(v > 0, f"late-game poise {UP if v > 0 else DOWN}")
    v = fx.get("inj", 1.0)
    if v != 1.0:
        add(v < 1, f"injury risk {UP if v > 1 else DOWN}")
    v = fx.get("season_lift", 0)
    if v:
        add(v > 0, f"every Saturday {UP if v > 0 else DOWN}")
    v = fx.get("season_inj", 1.0)
    if v != 1.0:
        add(v < 1, f"injuries all year {UP if v > 1 else DOWN}")
    v = fx.get("hours", 0)
    if v:
        add(v > 0, f"+{v} recruiting hrs" if v > 0 else f"costs {-v} recruiting hr{'s' if v != -1 else ''}")
    v = fx.get("recruits", 0)
    if v:
        add(v > 0, f"recruits {UP if v > 0 else DOWN}" + (UP if v >= 2.5 else ""))
    v = fx.get("recruit", 0)
    if v:
        add(v > 0, f"his interest {UP if v > 0 else DOWN}" + (UP if v >= 6 else DOWN if v <= -6 else ""))
    if fx.get("state"):
        add(fx["state"][1] > 0, f"{fx['state'][0]} recruits {UP if fx['state'][1] > 0 else DOWN}")
    if fx.get("top"):
        add(True, f"top {fx['top'][0]} targets {UP}")
    v = fx.get("money", 0)
    if v:
        add(v > 0, (f"+{_money_word(v)} to next year’s NIL pool" if v > 0 else f"{_money_word(v)} out of next year’s pool"))
    if fx.get("depth_swap"):
        pos, promote, demote = fx["depth_swap"]
        add(True, f"{promote.last_name} moves ahead of {demote.last_name} at {pos}")
    p = fx.get("who")
    nm = p.first_name if p is not None and hasattr(p, "first_name") else "he"
    if fx.get("unhappy"):
        add(False, f"{nm} unhappy (portal risk)")
    v = fx.get("morale", 0)
    if v:
        add(v > 0, f"{nm}'s morale {UP if v > 0 else DOWN}" + (UP if v >= 12 else DOWN if v <= -12 else ""))
    if fx.get("bought_in"):
        last_year = p is not None and getattr(p, "year", 0) >= 3        # a senior (FR=0 … SR=3)
        add(True, f"{nm} fully bought in" if last_year else f"{nm} bought in (stays)")
    if fx.get("dev"):
        add(True, f"{nm} develops faster")
    if fx.get("sit"):
        add(False, fx.get("sit_hint") or f"{nm} misses {fx['sit']} game{'s' if fx['sit'] != 1 else ''}")
    v = fx.get("team_morale", 0)
    if v:
        add(v > 0, f"whole roster's morale {UP if v > 0 else DOWN}" + (UP if v >= 5 else ""))
    if fx.get("add_captain"):
        add(True, f"{nm} becomes a captain")
    if fx.get("drop_captain"):
        add(False, f"{nm} loses the C")
    if fx.get("play_hurt"):
        add(True, f"{nm} plays Saturday")
        add(False, "re-injury risk")
    if fx.get("promise") == "made":
        add(True, "he stays patient")
        add(False, "break it and he’s gone")
    if fx.get("promise") == "role":
        add(True, "portal risk down a little")
    if fx.get("heal"):
        add(True, "short injuries heal faster")
    if fx.get("focus"):
        import week
        add(True, f"practice: {week.FOCUS[fx['focus']][0].lower()}")
    if fx.get("priority"):
        add(True, f"{fx['priority']}s up your board")
    c = fx.get("coord")
    if c is not None and fx.get("stay"):
        nm = c.name.split()[-1]
        add(fx["stay"] < 0, f"{nm} more likely to {'stay' if fx['stay'] < 0 else 'leave'}")
    if fx.get("stake"):
        add(None, "on the line: " + fx["stake"].get("hint", "later"))
    if fx.get("gamble"):
        (odds, good, _), (bad, _) = fx["gamble"]
        g = ", ".join(t for _, t in _parts(good)) or "it works"
        b = ", ".join(t for _, t in _parts(bad)) or "nothing"
        add(None, f"{int(odds * 100)}%: {g} / else: {b}")
    also = fx.get("also")
    for a in (also if isinstance(also, list) else [also] if also else []):
        out.extend(_notes(a) if a.get("quiet") else _raw_parts(a))
    for t in fx.get("notes", []):
        if isinstance(t, tuple):
            add(*t)
        else:
            add(None, t)
    return out


def hint(fx):
    """One gray line: the upside in green, the cost in red, the gambles in yellow."""
    bits = []
    for good, text in _parts(fx):
        col = C.BGREEN if good is True else C.BRED if good is False else C.BYELLOW
        bits.append(paint(text, col))
    return paint(" · ", C.GRAY).join(bits) if bits else paint("no real effect", C.GRAY)


def show_hints():
    import settings
    return settings.load().get("reply_hints", True)
