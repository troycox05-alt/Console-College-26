"""
personalities.py — Players as people: captains, the locker room, money, and the NFL.

Traits (traits.py) say who a player is. This is what he *does* with it, week to
week and winter to winter, on every roster in the country:

  CAPTAINS      Every August the team votes. Upperclassmen who lead (Captain,
                Team Leader, Mentor, Quiet Professional, Tone Setter, Humble)
                get the votes; divas, hotheads and mercenaries don't. Captains
                steady the room and call the players-only meeting when it's
                going sideways.

  CHEMISTRY     Every locker room has a temperature, 0-100. Winning warms it,
                losing streaks and blowups cool it, captains and a Players'
                Coach hold it together, divas and hotheads pull it apart. It's
                worth up to about a point either way on Saturday.

  INCIDENTS     A few times a season somewhere, something happens: a hothead
                is suspended for violating team rules, a diva vents online after
                a loss, a fight at practice, a players-only meeting. On your
                team, it lands in your inbox and you decide how it's handled.

  NIL RAISES    When the season ends, good starters who are underpaid for what
                they just did want a raise — and the ones with Mercenary or
                Chasing Spotlight in them say "or I'm in the portal." Pay him and
                he stays put. Refuse and he's very likely gone. The AI's athletic
                departments make the same call with the same money.

  LEAVING EARLY Draft-eligible underclassmen weigh the NFL. Where he projects
                matters most, but so does who he is: the Loyal kid and the
                captain with unfinished business come back more often, the kid
                chasing the spotlight goes. On your team, you get to make your
                case (or tell him he's earned it).

Nothing happens to your team without you seeing it in the inbox (career mode);
everything league-wide shows up on the Wire and in the offseason report.
"""
import random

from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

LEADER_TRAITS = {"captain": 3.0, "leader": 2.5, "mentor": 1.5, "quiet_pro": 1.2, "tone_setter": 1.0,
                 "humble": 0.8, "coachable": 0.5, "grinder": 0.8, "vocal": 1.2, "alpha": 1.0,
                 "faith": 0.8, "old_soul": 0.8, "fierce": 0.7}
TROUBLE_TRAITS = {"diva": 3.0, "hothead": 2.5, "headcase": 2.0, "chippy": 1.2, "mercenary": 1.0,
                  "spotlight": 1.0, "stubborn": 0.6, "showman": 0.4, "stat_padder": 1.0, "social": 1.0,
                  "night_owl": 1.2, "eligibility": 1.4, "social_star": 1.0, "brand": 0.5, "intense": 0.5, "loner": 0.4}
GREEDY = {"mercenary": 1.8, "spotlight": 1.5, "diva": 1.4, "impatient": 1.2}
CONTENT = {"loyal": 0.35, "grinder": 0.4, "family_guy": 0.6, "humble": 0.6, "quiet_pro": 0.7, "captain": 0.7}
CHEM_LIFT = 0.9                     # rating points at chemistry 0 or 100


def _career_team(league):
    me = getattr(league, "user_coach", None)
    if getattr(league, "mode", None) != "career" or me is None or me.team is None:
        return None
    if getattr(league, "autosim", False):
        return None
    return me.team


def _mines(league):
    """Every human coach's program (hot seat: all of them)."""
    if getattr(league, "autosim", False) or getattr(league, "mode", None) != "career":
        return []
    import hotseat
    return list(hotseat.humans(league))


def _as(league, team, mines):
    """Run as the coach of `team` when he's one of the humans (so his mail lands in his own inbox)."""
    import contextlib
    import hotseat
    return hotseat.acting_as(league, team) if any(team is m for m in mines) else contextlib.nullcontext()


def news(league, year=None):
    return league.__dict__.setdefault("locker_news", {}).setdefault(year or league.year, [])


def _say(league, text):
    news(league).append((league.week, text))


# ═══ Captains ══════════════════════════════════════════════════════════════

def captain_score(p):
    s = p.overall * 0.35 + p.year * 6 + sum(LEADER_TRAITS.get(t, 0) for t in __import__("traits").tags(p)) * 8
    s -= sum(TROUBLE_TRAITS.get(t, 0) for t in __import__("traits").tags(p)) * 7
    s += getattr(p, "captain_years", 0) * 6
    import morale
    s += (morale.get(p) - 60) * 0.12                 # happy veterans get the votes
    return s


def name_captains(league, team, rng):
    if getattr(team, "captains_year", None) == league.year:
        return team.captains
    pool = [p for p in team.roster if p.year >= 2 and p.overall >= 50] or [p for p in team.roster if p.year >= 1]
    ranked = sorted(pool, key=lambda p: -(captain_score(p) + rng.gauss(0, 4)))
    n = 3 if len(ranked) >= 3 else len(ranked)
    if ranked and rng.random() < 0.35:
        n = min(4, len(ranked))
    team.captains = ranked[:n]
    team.captains_year = league.year
    for p in team.captains:
        p.captain_years = getattr(p, "captain_years", 0) + 1
        p.events[league.year].append("Voted team captain")
    return team.captains


def is_captain(p):
    t = getattr(p, "team", None)
    return t is not None and p in (getattr(t, "captains", None) or [])


# ═══ Chemistry ═════════════════════════════════════════════════════════════

def baseline(team):
    starters = [p for grp in team.starters().values() for p in grp]
    b = 50.0
    for p in starters:
        b += _lead_score(p) * 1.2                     # a freshman "mentor" hasn't anyone to mentor yet
        b -= sum(TROUBLE_TRAITS.get(t, 0) for t in __import__("traits").tags(p)) * 1.5
    for p in getattr(team, "captains", None) or []:
        b += 2.5
    c = team.coach
    if c is not None:
        tr = __import__("traits").tags(c)
        b += 6 * ("players_coach" in tr) + 3 * ("culture" in tr) - 3 * ("burnout" in tr)
        b += __import__("traits").mod(c, "chem", 0.0)
    return max(20.0, min(85.0, b))


def chemistry(team):
    v = getattr(team, "chemistry", None)
    if v is None:
        v = team.chemistry = baseline(team)
    return v


def _nudge(team, d):
    team.chemistry = max(0.0, min(100.0, chemistry(team) + d))


def chemistry_lift(team):
    """Rating points on Saturday."""
    if getattr(team, "fcs", False):
        return 0.0
    import skills
    lift = 1.5 if skills.team_has(team, "run_through_wall") else CHEM_LIFT     # coaching tree
    return (chemistry(team) - 50) / 50 * lift


def chem_word(v):
    return ("tight" if v >= 72 else "together" if v >= 58 else "steady" if v >= 42
            else "tense" if v >= 28 else "fractured")


# ═══ Weekly: results, drift, incidents ═════════════════════════════════════

def weekly(league, games):
    if league.week < 1:
        return
    rng = random.Random(f"locker:{league.seed}:{league.year}:{league.week}")
    played = {}
    for g in games:
        if not g.played:
            continue
        for t in (g.home, g.away):
            played[t] = g
    mines = _mines(league)
    import commissioner
    discipline_on = commissioner.allows(league, "discipline")   # Commissioner Mode: no incidents or suspensions
    for team in league.teams:
        for p in team.roster:
            if getattr(p, "suspended", False) and getattr(p, "inj_games", 0) <= 0:
                p.suspended = False
        g = played.get(team)
        c = chemistry(team)
        if g is not None:
            won = g.winner is team
            margin = abs(g.home_score - g.away_score)
            d = 1.6 if won else -2.2
            if not won and margin >= 28:
                d -= 2.5
            if won and _rival_game(g):
                d += 2.5
            _nudge(team, d)
        # drift back toward what this room is
        team.chemistry = chemistry(team) + (baseline(team) - chemistry(team)) * 0.12
        if league.week > 13 or not discipline_on:
            continue
        with _as(league, team, mines):
            _incident(league, team, g, rng, team if any(team is m for m in mines) else None)


def _rival_game(g):
    import rivalries
    return rivalries.is_rivalry(g.home, g.away)


def _losing_streak(league, team):
    n = 0
    for g in reversed([g for g in league.team_games(team) if g.played]):
        if g.winner is team:
            break
        n += 1
    return n


def _incident(league, team, g, rng, mine):
    trouble = [p for p in team.roster if p.year >= 0 and any(t in TROUBLE_TRAITS for t in __import__("traits").tags(p))
               and getattr(p, "inj_games", 0) <= 0]
    streak = _losing_streak(league, team)
    c = chemistry(team)
    p_event = 0.012 + 0.006 * min(6, len(trouble)) + (0.03 if streak >= 3 else 0.012 if streak == 2 else 0) \
        + (0.02 if c < 35 else 0)
    if team.coach is not None:
        import coach_profile
        p_event *= __import__("traits").mod(team.coach, "trouble", 1.0) * max(0.7, min(1.3, 1 - coach_profile.delta(team.coach, "discipline") / 100))
    if team is mine:
        p_event *= 1.4                                   # your own locker room is louder to you
        rules = getattr(team, "_fx_rules", None)
        if rules and rules[0] == league.year:
            p_event *= rules[1]                          # the team rules you set in camp
    if rng.random() > p_event:
        return
    lost = g is not None and g.winner is not team
    caps = [p for p in (getattr(team, "captains", None) or []) if p in team.roster]
    # A players-only meeting when it's going wrong and somebody's there to call it.
    if streak >= 2 and caps and rng.random() < 0.45:
        cap = max(caps, key=lambda p: captain_score(p))
        _nudge(team, 7)
        _say(league, f"{team.school}: captain {cap.name} calls a players-only meeting after {streak} straight losses.")
        if team is mine:
            import people
            worst = max((p for p in team.roster if any(t in TROUBLE_TRAITS for t in __import__("traits").tags(p))),
                        key=lambda p: _trouble_score(p), default=None)
            opts = [("Good. That's your team as much as mine.", {"chem": 2, "who": cap, "bought_in": True},
                     f"{cap.first_name} walks a little taller."),
                    ("Follow it with a coaches-only film session tomorrow.", {"lift": 0.15, "chem": -1},
                     "The players said their piece. Now the tape says its piece.")]
            if worst is not None and worst is not cap:
                opts.append(("Who isn't bought in? I want names.",
                             {"chem": -2, "gamble": [(0.55, {"who": worst, "bought_in": True, "lift": 0.1},
                                                      f"{cap.first_name} named {worst.first_name}. You sat down with "
                                                      f"{worst.first_name} and it went better than expected."),
                                                     ({"who": worst, "unhappy": True},
                                                      f"{worst.first_name} found out who talked. It's worse now.")]},
                             "The captain doesn't love being asked."))
            people.choice(league, f"{cap.position} {cap.name}", "Team captain", "Players-only meeting",
                          f"Coach, heads up — we had a players-only meeting last night. Everybody said their piece. "
                          f"I think we're better for it.", opts, ref=cap, color=C.BCYAN)
        return
    if not trouble:
        return
    weights = [sum(TROUBLE_TRAITS.get(t, 0) for t in __import__("traits").tags(p)) * (1.5 if p in _starters(team) else 1.0)
               for p in trouble]
    p = rng.choices(trouble, weights=weights)[0]
    kind = None
    if any(t in p.traits for t in ("diva", "spotlight")) and lost and p in _starters(team):
        kind = "rant"
    elif any(t in p.traits for t in ("hothead", "chippy", "headcase")):
        kind = "suspension" if rng.random() < 0.55 else "fight"
    elif "mercenary" in p.traits and p not in _starters(team):
        kind = "sulk"
    else:
        kind = "fight" if rng.random() < 0.5 else "rant" if lost else None
    if kind is None:
        return
    if team is mine:
        _ask_the_coach(league, team, p, kind, g, rng)
        return
    _resolve_ai(league, team, p, kind, g, rng)


def _starters(team):
    return {p for grp in team.starters().values() for p in grp}


def _suspend(league, p, games, why, event=None):
    p.inj_games = max(getattr(p, "inj_games", 0), games)
    p.inj_desc = why
    p.inj_week = league.week
    p.suspended = True
    p.events[league.year].append(event or f"Suspended {games} game{'s' if games != 1 else ''} ({why})")


def _resolve_ai(league, team, p, kind, g, rng):
    who = f"{team.school} {p.position} {p.name}"
    if kind == "suspension":
        n = rng.choices((1, 2, 3), weights=(6, 3, 1))[0]
        _suspend(league, p, n, "suspended — violation of team rules")
        _nudge(team, -2)
        _say(league, f"{who} suspended {n} game{'s' if n != 1 else ''} for a violation of team rules.")
    elif kind == "fight":
        _nudge(team, -3)
        _say(league, f"{who} gets into it with a teammate at practice. The staff says it's handled.")
    elif kind == "rant":
        _nudge(team, -5)
        if p.position in ("QB", "RB", "WR", "TE"):
            _say(league, f"{who} vents on social media after the loss: \"Get me the ball.\"")
        else:
            _say(league, f"{who} calls out teammates' effort on social media after the loss.")
    elif kind == "sulk":
        _nudge(team, -2)
        p.__dict__["disgruntled"] = league.year
        _say(league, f"{who}, unhappy with his role, skips a team meeting.")


# ── your team: you decide ────────────────────────────────────────────────────

def _ask_the_coach(league, team, p, kind, g, rng):
    import people
    tag = f"{p.class_label} · {__import__('scout').ovr_tag(p)}" + (" · starter" if p in _starters(team) else "")
    if kind == "suspension":
        body = rng.choice([f"Coach, {p.first_name} broke curfew again and got into it with a staffer on the way in. "
                           f"It's the second time this month. How do you want to handle it?",
                           f"{p.first_name} missed a mandatory study hall and then mouthed off in position meeting. "
                           f"The other guys are watching what you do here."])
        people._post(league, "Director of Football Operations", "Staff", f"Discipline: {p.name}", body,
                     [("pers_suspend", "Sit him one game. Rules are rules."),
                      ("pers_internal", "Handle it internally. He plays Saturday."),
                      ("pers_dismiss", "Dismiss him from the team.")],
                     kind="pers_discipline", ref=p, color=C.BRED, silence={"chem": -3},
                     silence_text="Nobody did anything. The seniors noticed.")
    elif kind == "fight":
        body = (f"{p.first_name} and a teammate went at it during team period today. Coaches broke it up. "
                f"The room's split on who started it.")
        people._post(league, "Strength coach", "Staff", f"Practice fight: {p.name}", body,
                     [("pers_extra", "Extra conditioning for both. Move on."),
                      ("pers_talk", "Get them in my office. Together."),
                      ("pers_ignore", "It's football. Happens.")],
                     kind="pers_fight", ref=p, color=C.BYELLOW, silence={"chem": -2})
    elif kind == "rant":
        if p.position in ("QB", "RB", "WR", "TE"):
            body = (f"Coach, you're going to see it — {p.first_name} posted after the game that he 'can't win "
                    f"games from the sideline' and needs the ball. It's everywhere.")
        else:
            body = (f"Coach, you're going to see it — {p.first_name} posted after the game that 'some guys in "
                    f"that locker room didn't show up today.' His teammates saw it too.")
        people._post(league, "Sports information director", "Staff", f"{p.name} went public", body,
                     [("pers_touches", "Promise him more touches.") if p.position in ("QB", "RB", "WR", "TE")
                      else ("pers_back", "Back him publicly: we need more from everybody."),
                      ("pers_earn", "Tell him to earn it — and keep it in-house."),
                      ("pers_bench", "Bench him the first series Saturday.")],
                     kind="pers_rant", ref=p, color=C.BYELLOW, silence={"chem": -3},
                     silence_text="Saying nothing said something.")
    elif kind == "sulk":
        body = (f"{p.first_name} skipped the team meeting this morning. Word is he's unhappy with his role and "
                f"talking to people about the portal.")
        people._post(league, "Position coach", "Staff", f"{p.name} is checked out", body,
                     [("pers_meet", "I'll sit down with him."),
                      ("pers_promise", "Tell him a bigger role is coming."),
                      ("pers_let", "Let him go if he wants to go.")],
                     kind="pers_sulk", ref=p, color=C.BYELLOW, silence={"who": p, "unhappy": True},
                     silence_text="He took the silence as your answer.")


# How each call lands with the player it's about (morale points).
MOOD = {"pers_suspend": -10, "pers_internal": 4, "pers_extra": -3, "pers_talk": 5, "pers_touches": 12,
        "pers_back": -4, "pers_earn": -5, "pers_bench": -12, "pers_meet": 12, "pers_promise": 10, "pers_let": -12,
        "pers_ok": 4, "nil_pay": 15, "nil_refuse": -18, "draft_stay": 3, "draft_go": 8, "draft_neutral": 2}
MOOD_WHY = {"pers_suspend": "suspended", "pers_bench": "benched a series", "pers_let": "told he could leave",
            "pers_meet": "you sat down with him", "pers_promise": "promised a bigger role",
            "pers_touches": "promised more touches", "nil_pay": "got his NIL raise", "nil_refuse": "raise refused",
            "pers_earn": "told to earn it", "draft_go": "you backed his NFL dream"}


DISCIPLINE = ("pers_suspend", "pers_bench", "pers_extra", "pers_earn", "pers_dismiss", "pers_back")


def answer(league, m, choice):
    """Your reply to a locker-room message. Returns what happened. Players' Coach and
    Hard Nosed (coaching tree) scale what a discipline call does for the room."""
    team = league.user_coach.team
    import skills
    f = 0.5 if skills.team_has(team, "players_coach") else 1.5 if skills.team_has(team, "hard_nosed") else 1.0
    if choice in DISCIPLINE and f != 1.0:
        before = chemistry(team)
        out = _answer(league, m, choice)
        after = chemistry(team)
        if after > before:
            team.chemistry = max(0.0, min(100.0, before + (after - before) * f))
        return out
    return _answer(league, m, choice)


def _answer(league, m, choice):
    """Your reply to a locker-room message. Returns what happened."""
    team = league.user_coach.team
    p = m.get("ref")
    rng = random.Random(f"ans:{league.seed}:{league.year}:{league.week}:{choice}")
    mood = MOOD.get(choice)
    if mood and p is not None and hasattr(p, "traits"):
        import morale
        morale.nudge(p, mood, MOOD_WHY.get(choice, "how you handled it"), league)
    if choice == "pers_ok":
        _nudge(team, 2)
        return "The room responds to that."
    if choice == "pers_suspend":
        _suspend(league, p, 1, "suspended — violation of team rules")
        _nudge(team, 3)
        _say(league, f"{team.school} suspends {p.position} {p.name} one game for a violation of team rules.")
        return f"{p.first_name} sits Saturday. The locker room noticed you meant it."
    if choice == "pers_internal":
        if rng.random() < 0.4:
            _nudge(team, -4)
            return "He plays. A few of the seniors think that's a double standard."
        return "Handled quietly. He plays Saturday."
    if choice == "pers_dismiss":
        if p in team.roster:
            team.roster.remove(p)
            p.team = None
            p.nil = 0
            import finance
            _nudge(team, 1 if "diva" in p.traits or "hothead" in p.traits else -3)
            _say(league, f"{team.school} dismisses {p.position} {p.name} from the program.")
            return f"{p.name} is off the team. His scholarship and NIL are gone with him."
        return "He's already gone."
    if choice == "pers_extra":
        _nudge(team, 1)
        return "Nobody fights at 6 a.m. after 40 up-downs."
    if choice == "pers_talk":
        _nudge(team, 3 if rng.random() < 0.7 else -1)
        return "They shake on it. Mostly."
    if choice == "pers_ignore":
        _nudge(team, -2)
        return "It lingers."
    if choice == "pers_touches":
        p.__dict__["promised_touches"] = league.year
        _nudge(team, -1)
        return f"{p.first_name} is happy. A couple of the other receivers aren't."
    if choice == "pers_back":
        if rng.random() < 0.5:
            _nudge(team, 4)
            return "It lands as a wake-up call. Practice is sharp all week."
        _nudge(team, -4)
        return "A few of the guys he called out took it personally."
    if choice == "pers_earn":
        _nudge(team, 2 if "captain" not in p.traits else 1)
        if rng.random() < 0.35:
            p.__dict__["disgruntled"] = league.year
            return f"{p.first_name} doesn't love it. He's quiet in meetings."
        return "Message received."
    if choice == "pers_bench":
        _nudge(team, 3)
        p.__dict__["disgruntled"] = league.year
        return f"{p.first_name} sits a series. The room gets the message; he's steaming."
    if choice == "pers_meet":
        p.__dict__.pop("disgruntled", None)
        p.promise = getattr(p, "promise", None) or "earn"
        return "You talk for an hour. He's back at practice tomorrow."
    if choice == "pers_promise":
        p.__dict__.pop("disgruntled", None)
        p.promise = "made"
        _nudge(team, -1)
        return (f"{p.first_name} is back in the building. Now you owe him snaps — break it and he's gone. "
                "A couple of guys wonder why skipping a meeting got rewarded.")
    if choice == "pers_let":
        p.__dict__["disgruntled"] = league.year
        return "Noted. He'll probably be in the portal in December."
    if choice in ("nil_pay", "nil_counter", "nil_refuse"):
        return _answer_nil(league, team, m, choice)
    if choice in ("draft_stay", "draft_go", "draft_neutral"):
        return _answer_draft(league, team, m, choice)
    return ""


# ═══ Season's end: NIL raises and the draft decision ═══════════════════════

def market_value(p):
    import finance
    return finance.transfer_market(p)


def _raise_room(league, team):
    import finance
    return finance.nil_pool(league, team) - finance.roster_nil(team, returning=True)


def season_end(league):
    """After the title game: stars ask for raises, draft-eligible juniors think about leaving."""
    key = league.year
    if league.__dict__.get("_season_end_done") == key:
        return
    league._season_end_done = key
    rng = random.Random(f"nil_raise:{league.seed}:{league.year}")
    import morale
    morale.promises(league)                          # kept promises lift; broken ones cost more
    import promises
    import hotseat
    hotseat.each_seat(league, lambda: promises.grade(league))   # and the ones you made on the recruiting trail
    mines = _mines(league)
    board = projected_spots(league)
    for team in league.teams:
        starters = _starters(team)
        asks = 0
        for p in sorted(team.roster, key=lambda p: -p.overall):
            if asks >= 2:
                break
            p.__dict__.pop("nil_demand", None)
            if p.year >= 3 or p not in starters or p.walk_on:
                continue
            spot = board.get(id(p))
            if spot is not None and spot <= 40:
                continue                                   # he's thinking about Sundays, not NIL
            mkt = market_value(p)
            have = getattr(p, "nil", 0) or 0
            if have >= mkt * 0.65 or mkt < 60_000:
                continue
            greed = 1.0
            for t in __import__("traits").tags(p):
                greed *= GREEDY.get(t, 1.0) * CONTENT.get(t, 1.0)
            greed *= __import__("traits").mod(p, "nil", 1.0)
            odds = min(0.8, 0.22 * greed * (1.3 if p.season_stats and sum(p.season_stats.values()) > 0 else 1.0))
            if rng.random() > odds:
                continue
            ask_amt = int(round(mkt * rng.uniform(0.8, 1.15) / 5000) * 5000)
            import morale
            threat = (any(t in p.traits for t in ("mercenary", "spotlight", "diva", "impatient"))
                      or morale.get(p) < 40 or rng.random() < 0.35)
            p.nil_demand = {"year": league.year, "ask": ask_amt, "was": have, "threat": threat, "status": "open"}
            asks += 1
            if any(team is m for m in mines):
                with _as(league, team, mines):
                    _post_nil(league, team, p)
    for mine in mines:
        with _as(league, mine, mines):
            for p in mine.roster:
                spot = board.get(id(p))
                eligible = p.year == 2 or (p.year == 1 and p.redshirt)
                if eligible and spot is not None and spot <= 160:
                    _post_draft(league, mine, p, spot)


def _post_nil(league, team, p):
    import people
    from finance import money
    d = p.nil_demand
    agent = "His agent" if d["threat"] else "He"
    body = (f"{agent} says {p.first_name} is worth {money(d['ask'])} a year after the season he just had "
            f"(he's on {money(d['was'])} now). ")
    body += ("If it's not there, he's putting his name in the portal." if d["threat"]
             else "He wants to stay. He also wants to be paid like a starter.")
    body += f" Room left in next year's NIL pool: {money(_raise_room(league, team))}."
    people._post(league, f"{p.position} {p.name}", f"{p.class_label} · {__import__('scout').ovr_tag(p)} · starter", "NIL raise",
                 body, [("nil_pay", f"Pay him {money(d['ask'])}."),
                        ("nil_counter", f"Counter at {money((d['ask'] + d['was']) // 2)}."),
                        ("nil_refuse", "No. He's under contract.")], kind="pers_nil", ref=p, color=C.BGREEN)


def _answer_nil(league, team, m, choice):
    from finance import money
    p = m["ref"]
    d = getattr(p, "nil_demand", None)
    if not d or d["status"] != "open":
        return "That's already settled."
    room = _raise_room(league, team)
    if choice == "nil_pay":
        cost = d["ask"] - d["was"]
        if cost > room:
            try:
                import budget_fix
                if budget_fix.cover(league, team, cost, f"{p.name}'s NIL raise: {money(d['ask'])}/yr",
                                    free_fn=lambda: _raise_room(league, team)):
                    room = _raise_room(league, team)
            except Exception:
                pass
        if cost > room:
            m["answered"] = None
            return f"You don't have {money(cost)} of room. Counter, refuse, or free up money first."
        p.nil = d["ask"]
        d["status"] = "paid"
        _say(league, f"{team.school} gives {p.position} {p.name} an NIL raise to {money(d['ask'])}.")
        return f"Done. {p.first_name} is staying."
    if choice == "nil_counter":
        amt = (d["ask"] + d["was"]) // 2
        if amt - d["was"] > room:
            try:
                import budget_fix
                if budget_fix.cover(league, team, amt - d["was"], f"a counter for {p.name}: {money(amt)}/yr",
                                    free_fn=lambda: _raise_room(league, team)):
                    room = _raise_room(league, team)
            except Exception:
                pass
        if amt - d["was"] > room:
            m["answered"] = None
            return f"You don't even have room for {money(amt)}."
        took = random.Random(f"ctr:{league.seed}:{p.last_name}").random() < (0.35 if d["threat"] else 0.7)
        if took:
            p.nil = amt
            d["status"] = "paid"
            import morale
            morale.nudge(p, 5, "took a counter on his NIL raise", league)
            return f"He takes {money(amt)}. Close enough."
        d["status"] = "refused"
        import morale
        morale.nudge(p, -12, "NIL counter fell through", league)
        return f"He turned it down. {'Expect him in the portal.' if d['threat'] else 'He is not happy.'}"
    d["status"] = "refused"
    return "He hears you. " + ("His agent is already making calls." if d["threat"] else "He's sulking.")


def resolve_demands(league, rng):
    """Before the portal opens: every open demand gets an answer (the AI's, or silence from you)."""
    import finance
    mines = _mines(league)
    for team in league.teams:
        style = team.ad.get("style", "patient") if isinstance(getattr(team, "ad", None), dict) else "patient"
        spend = finance.AD_CONTRACT.get(style, {}).get("nil", 1.0)
        for p in team.roster:
            d = getattr(p, "nil_demand", None)
            if not d or d["year"] != league.year or d["status"] != "open":
                continue
            if any(team is m for m in mines):
                d["status"] = "refused"                    # you never answered
                continue
            room = _raise_room(league, team)
            cost = d["ask"] - d["was"]
            rank = sorted(team.players_at(p.position), key=lambda x: -x.overall).index(p) \
                if p in team.players_at(p.position) else 3
            want = (0.55 + (0.25 if p.position == "QB" else 0) - rank * 0.1) * spend
            if cost <= room * 0.5 and rng.random() < want:
                p.nil = d["ask"]
                d["status"] = "paid"
                if p.overall >= 78:
                    _say(league, f"{team.school} pays up: {p.position} {p.name} gets an NIL raise to "
                                 f"{finance.money(d['ask'])}.")
            else:
                d["status"] = "refused"
                if d["threat"] and p.overall >= 76:
                    _say(league, f"NIL talks break down between {team.school} and {p.position} {p.name}.")


def portal_odds(team, player, odds):
    """portal.entry_odds calls this last: money, promises and moods."""
    d = getattr(player, "nil_demand", None)
    if d and d.get("status") == "refused":
        odds = max(odds, 0.55 if d.get("threat") else 0.18)
    elif d and d.get("status") == "paid":
        odds *= 0.3
    if getattr(player, "disgruntled", None) is not None:
        odds = max(odds * 1.8, 0.2)
    if is_captain(player):
        odds *= 0.5
    import morale
    odds *= morale.portal_factor(player)             # how he feels about the place
    import skills
    if skills.team_has(team, "players_coach"):
        odds *= 0.8                                  # Players' Coach (coaching tree)
    return odds


def portal_reason(player):
    d = getattr(player, "nil_demand", None)
    if d and d.get("status") == "refused":
        return "NIL talks broke down"
    if getattr(player, "disgruntled", None) is not None:
        return "unhappy with his role"
    return None


# ── the draft decision ───────────────────────────────────────────────────────

def projected_spots(league):
    """Where every draft-eligible player projects right now: id(player) -> board spot."""
    import draft
    rng = random.Random(f"proj:{league.seed}:{league.year}")
    board = []
    for t in league.teams:
        for p in t.roster:
            if p.year == 3 or p.year == 2 or (p.year == 1 and p.redshirt):
                p.team = p.team or t
                board.append((draft.draft_grade(league, p, rng), p))
    board.sort(key=lambda x: -x[0])
    return {id(p): i for i, (_, p) in enumerate(board, 1)}


def _round_of(spot):
    return min(7, (spot - 1) // 32 + 1)


def _post_draft(league, team, p, spot):
    import people
    rnd = _round_of(spot)
    lean = declare_odds(p, spot, _base_odds(spot))
    lean_word = "leaning toward declaring" if lean >= 0.65 else "torn" if lean >= 0.35 else "leaning toward coming back"
    body = (f"{p.first_name}'s family wants to sit down about the NFL. Scouts have him as a round-{rnd} pick "
            f"(around No. {spot} on the board). He's {lean_word}. What do you tell him?")
    people._post(league, f"{p.position} {p.name}", f"{p.class_label} · {__import__('scout').ovr_tag(p)}", "The NFL decision",
                 body, [("draft_stay", "Make the case for one more year here."),
                        ("draft_go", "You've earned it. Go get paid."),
                        ("draft_neutral", "It's your call. We support you either way.")],
                 kind="pers_draft", ref=p, color=C.BMAGENTA)


def _answer_draft(league, team, m, choice):
    p = m["ref"]
    p.draft_pitch = {"stay": "stay", "go": "go", "neutral": None}[choice.split("_")[1]]
    if choice == "draft_stay":
        return f"{p.first_name} listens. He'll decide before the draft."
    if choice == "draft_go":
        _nudge(team, 2)
        for r in [r for r in getattr(team, "recruiting_targets", []) if not r.signed][:10]:
            r.interest[team] = min(100, r.interest.get(team, 0) + 1.0)
        return "He's grateful. Recruits hear about coaches who do that."
    return "He appreciates it. It's his call, and he knows it."


def _base_odds(spot):
    return (0.9 if spot <= 80 else 0.6 if spot <= 160 else 0.35 if spot <= 260 else 0.2 if spot <= 400
            else 0.06 if spot <= 520 else 0.0)


def declare_odds(p, spot, base):
    """Where he projects, then who he is."""
    if base <= 0:
        return 0.0
    f = 1.0
    tr = set(p.traits)
    if tr & {"spotlight", "mercenary", "diva"}:
        f *= 1.2
    if tr & {"loyal", "family_guy", "grinder"}:
        f *= 0.75
    if is_captain(p) or "captain" in tr:
        f *= 0.85                                   # unfinished business
    if (getattr(p, "nil", 0) or 0) >= 400_000 and spot > 48:
        f *= 0.7                                    # the money's good here too
    import morale
    mood = morale.get(p)
    f *= 1.2 if mood < 36 else 0.88 if mood >= 75 else 1.0     # an unhappy kid is out the door
    pitch = getattr(p, "draft_pitch", None)
    odds = base * f
    if pitch == "stay":
        odds *= 0.5 if spot > 32 else 0.8
    elif pitch == "go":
        odds = max(odds, 0.97)
    return max(0.0, min(0.98, odds))


def after_draft(league, declared, board_spots):
    """Headlines for the ones who surprised people by coming back."""
    left = {id(p) for p, _t in declared}
    for t in league.teams:
        for p in t.roster:
            spot = board_spots.get(id(p))
            eligible = p.year == 2 or (p.year == 1 and p.redshirt)
            if eligible and spot is not None and spot <= 64 and id(p) not in left:
                _say(league, f"{t.school} {p.position} {p.name} passes on the NFL Draft and returns for "
                             f"another season.")
                p.events[league.year].append("Returned to school instead of declaring for the draft")
        for p in list(t.roster):
            p.__dict__.pop("draft_pitch", None)


# ═══ Screens ══════════════════════════════════════════════════════════════

def _lead_score(p):
    tags = __import__("traits").tags(p)
    return sum(v for t, v in LEADER_TRAITS.items() if t in tags and not (t == "mentor" and p.year < 2))


def _trouble_score(p):
    tags = __import__("traits").tags(p)
    return sum(v for t, v in TROUBLE_TRAITS.items() if t in tags) + __import__("traits").mod(p, "trouble", 0.0)


def leaders(team):
    """The room's real leaders: at least one true leadership tag (a captain type, a
    mentor, a quiet pro, a tone setter — not just a hard worker), more lead than trouble.
    Starters first. The same list the locker room shows and the inbox writes from."""
    starters = {p for grp in team.starters().values() for p in grp}
    lead = [p for p in team.roster if _lead_score(p) >= 1.0 and _lead_score(p) > _trouble_score(p)]
    return sorted(lead, key=lambda p: (p not in starters, -captain_score(p)))


def _worth(v, tail=" on Saturday"):
    if abs(v) < 0.05:
        return f"(no effect on Saturday{tail.replace(' on Saturday', '').replace(' rating points', '')})"
    return f"(worth {v:+.1f}{tail})"


def locker_room(league, team):
    """Team page: captains, the room, the personalities — and why it feels the way it does."""
    clear()
    print(title_bar(f"{team.school.upper()} · LOCKER ROOM"))
    v = chemistry(team)
    print()
    print(f"   {paint('Chemistry', C.GRAY):<22} {v:5.1f}  {paint(chem_word(v).upper(), C.BGREEN if v >= 58 else C.BYELLOW if v >= 42 else C.BRED, C.BOLD)}"
          f"   {paint(_worth(chemistry_lift(team), f' rating points on Saturday · this roster settles around {baseline(team):.0f}'), C.GRAY)}")
    caps = [p for p in getattr(team, "captains", None) or [] if p in team.roster]
    if caps:
        print(f"   {paint('Captains', C.GRAY):<22} " + ", ".join(f"{p.position} {p.name}" for p in caps))
    # Why: only the starting lineup sets where a room settles.
    starters = {p for grp in team.starters().values() for p in grp}
    ups = sorted(((p, _lead_score(p) * 1.2) for p in starters if _lead_score(p)), key=lambda x: -x[1])
    downs = sorted(((p, _trouble_score(p) * 1.5) for p in starters if _trouble_score(p)), key=lambda x: -x[1])
    from traits import labels
    def who(lst):
        return ", ".join(f"{p.last_name} ({' · '.join(labels(p))})" for p, _ in lst[:4]) or "nobody"
    import textwrap
    for tag, lst, col in (("Pulled up by", ups, C.BGREEN), ("Dragged down by", downs, C.BRED)):
        total = sum(x for _, x in lst)
        for i, ln in enumerate(textwrap.wrap(f"{who(lst)}  ({'+' if col == C.BGREEN else '-'}{total:.0f})", 72)):
            print(f"   {paint(pad(tag if i == 0 else '', 22), C.GRAY)} {paint(ln, col)}")
    print(paint("   Only starters set where the room settles. Wins nudge it up, blowout losses knock it down, a rivalry\n"
                "   win helps most, and captains and leaders in the lineup raise the floor.", C.GRAY))
    import morale
    st_avg = morale.avg(starters)
    print(f"   {paint('Starters’ morale', C.GRAY):<22} {st_avg:5.1f}  {paint(morale.word(st_avg).upper(), morale.color(st_avg), C.BOLD)}"
          f"   {paint(_worth(morale.team_lift(team, list(starters))), C.GRAY)}")
    print()
    low = sorted(team.roster, key=morale.get)[:6]
    sliding = any(morale.get(p) < 45 for p in low)
    print(section("MORALE — WHO'S SLIDING" if sliding else "MORALE — LOWEST IN THE ROOM (nobody's in trouble)",
                  C.BYELLOW))
    for p in low:
        v = morale.get(p)
        why = p.__dict__.get("mood_log", [])
        reason = why[-1][2] if why else ("buried on the depth chart" if p not in starters and morale.expects_to_play(p)
                                         else "wants more from his team" if p in starters and v < 58
                                         else "no one thing — just flat")
        role = "starter" if p in starters else "backup"
        print(f"   {p.position:<3} {pad(truncate(p.name, 22), 23)}{pad(paint(p.class_label, C.GRAY), 7)}"
              f"{pad(paint(role, C.GRAY), 9)} {paint(f'{v:3.0f} {pad(morale.word(v), 10)}', morale.color(v))}"
              f"{paint(truncate(reason, 40), C.GRAY)}")
    forces = morale.contagion(team, starters)
    if forces["captains"] is not None:
        ca = forces["captains"]
        print(paint(f"   Captains' mood {ca:.0f} ({morale.word(ca)}) — "
                    + ("pulling the room up." if ca >= 62 else "dragging the room down." if ca < 48 else
                       "holding the room steady."), morale.color(ca)))
    for p, amt in sorted(forces["drag"], key=lambda x: x[1])[:3]:
        print(paint(f"   Dragging down the {p.position}s: {p.name} ({morale.get(p):.0f}, "
                    f"{' · '.join(t for t in p.traits if t in morale.WILD)})", C.BRED))
    for p, amt in sorted(forces["lift"], key=lambda x: -x[1])[:3]:
        print(paint(f"   Lifting the {p.position}s: {p.name} ({morale.get(p):.0f})", C.BGREEN))
    high = sorted(team.roster, key=lambda p: -morale.get(p))[:3]
    print(paint("   Happiest: " + ", ".join(f"{p.last_name} ({morale.get(p):.0f})" for p in high), C.BGREEN))
    print(paint("   Under 40, a player is shopping; under 25 he's very likely in the portal. Playing time, wins,\n"
                "   money, the room and your promises move it.", C.GRAY))
    print()
    lead = leaders(team)
    trouble = [p for p in team.roster if _trouble_score(p) and _trouble_score(p) >= _lead_score(p)]
    seen = set()
    print(section("THE LEADERS", C.BGREEN))
    for p in lead[:8]:
        seen.update(p.traits)
        role = paint(" starter", C.GRAY) if p in starters else paint(" backup", C.GRAY)
        mixed = paint("  (also a wild card)", C.BYELLOW) if _trouble_score(p) else ""
        print(f"   {p.position:<3} {pad(truncate(p.name, 22), 23)}{pad(paint(p.class_label, C.GRAY), 7)}{pad(role, 9)} "
              f"{paint(' · '.join(labels(p)), C.BGREEN)}{mixed}")
    print()
    print(section("THE WILD CARDS", C.BRED))
    for p in sorted(trouble, key=lambda p: -p.overall)[:8]:
        seen.update(p.traits)
        mood = []
        d = getattr(p, "nil_demand", None)
        if d and d.get("year") == league.year:
            mood.append(f"NIL: {d['status']}")
        if getattr(p, "disgruntled", None) == league.year:
            mood.append("unhappy")
        if getattr(p, "suspended", False):
            mood.append("suspended")
        role = paint(" starter", C.GRAY) if p in starters else paint(" backup", C.GRAY)
        print(f"   {p.position:<3} {pad(truncate(p.name, 22), 23)}{pad(paint(p.class_label, C.GRAY), 7)}{pad(role, 9)} "
              f"{paint(' · '.join(labels(p)), C.BYELLOW)}" + (paint("   " + ", ".join(mood), C.BRED) if mood else ""))
    from traits import PLAYER_TRAITS
    legend = [(PLAYER_TRAITS[t][0], PLAYER_TRAITS[t][1]) for t in sorted(seen) if t in PLAYER_TRAITS]
    if legend:
        print()
        print(section("WHAT THE TAGS MEAN", C.GRAY))
        for n, b in legend:                            # one per line: the name never runs into its meaning
            print(f"   {paint(pad(n, 20), C.BWHITE)}{paint(truncate(b, 74), C.GRAY)}")
    schools = sorted((t.school for t in league.teams), key=len, reverse=True)
    def owner(text):
        return next((s for s in schools if text.startswith(s + " ") or text.startswith(s + ":")), None)
    items = [t for w, t in news(league) if owner(t) == team.school
             or f" between {team.school} and " in t]
    if items:
        print()
        print(section("THIS SEASON", C.BCYAN))
        for t in items[-8:]:
            print(f"   {truncate(t, 110)}")
    pause()
