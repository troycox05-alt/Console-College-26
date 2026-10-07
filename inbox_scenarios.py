"""
inbox_scenarios.py — The rest of the mail: the situations a head coach
actually walks into during a season.

Each of these is a real dilemma — no free answer, and usually no obviously
right one. What each choice does is shown under it in the inbox (see
effects.py). A few of them ride on a later result or a coin you choose to
flip, and the verdict shows up in your inbox afterward.

  CAMP        Team rules — how you run the building (incidents vs. the room)
  IN SEASON   Playing hurt · Saving a package for the big one · The rival
              coach talks · Travel plans · Opening up the playbook · Academics ·
              The podcast · Pro League scouts at practice · A program legend · The
              walk-on · Tampering · In-season lifting · A family emergency ·
              The Golden Helmet push · A high school banquet · A donor with strings ·
              The freshman plan · Bowl eligibility
  DECEMBER    Your DC wants a raise · The bowl practices
"""
from effects import by_ad
from ui import C

HEADLINES = {"default": 0, "brand": 1, "politician": 1, "booster": 1}          # an AD who wants you out front


def _people():
    import people
    return people


def _once(league, tag):
    said = league.__dict__.setdefault("_beats", {}).setdefault(league.year, set())
    if tag in said:
        return False
    said.add(tag)
    return True


def _starters(team):
    return [p for grp in team.starters().values() for p in grp]


def _post(league, *a, **kw):
    return _people().choice(league, *a, **kw)


# ═══ Camp ═══════════════════════════════════════════════════════════════════

def preseason(league, team, rng):
    if not _once(league, "team_rules"):
        return
    ops = "Director of Football Operations"
    _post(league, ops, "Staff", "Team rules for the year",
          "Before the players report: how do you want to run the building? Curfews, phones in meetings, "
          "class checks — whatever you set now is what the older guys will hold the young ones to.",
          [("Strict: curfew, phones in a bin, class checks every morning.",
            {"chem": -3, "notes": [(True, "fewer incidents all year")], "rules": 0.6},
            "The players grumble. Trouble gets a lot harder to find."),
           ("The leadership council writes the rules. I sign off.",
            {"chem": 2, "notes": [(True, "somewhat fewer incidents")], "rules": 0.85},
            "The older guys take ownership. It won't be airtight."),
           ("They're grown men. Two rules: be on time, be a good teammate.",
            {"chem": 4, "notes": [(False, "more incidents all year")], "rules": 1.4},
            "The room loves the trust. Somebody will test it.")],
          color=C.BCYAN, due=(league.year, 1))


# ═══ In season ══════════════════════════════════════════════════════════════

def weekly(league, team, rng):
    """Up to two of these a week, most pressing first."""
    import carousel as cz
    wk = league.week
    if wk < 1 or wk > 13:
        return
    people = _people()
    nxt = people._next_game(league, team)
    posted = 0
    bank = [_hurt_star, _depth_question, _lookahead, _rival_talk, _scheme, _bowl_eligible, _travel, _tampering, _family,
            _heisman, _freshman, _walk_on, _academics, _podcast, _scouts, _legend, _strength, _banquet, _donor]
    for fn in bank:
        if posted >= 2:
            break
        try:
            if fn(league, team, rng, nxt, cz):
                posted += 1
        except (AttributeError, IndexError, KeyError, ValueError, ZeroDivisionError):
            continue                                  # a scenario that doesn't fit this world skips itself


def _depth_question(league, team, rng, nxt, cz):
    if rng.random() > 0.3:
        return False
    import promises
    return promises.depth_question(league, team, rng)


def _hurt_star(league, team, rng, nxt, cz):
    if nxt is None:
        return False
    from models import STARTING_LINEUP
    first_team = {p for pos, n in STARTING_LINEUP.items() for p in team.players_at(pos)[:n]}
    hurt = [p for p in team.roster if p in first_team and 1 <= getattr(p, "inj_games", 0) <= 2
            and not getattr(p, "suspended", False)]
    asked = league.__dict__.setdefault("_asked_hurt", set())
    hurt = [p for p in hurt if (league.year, id(p)) not in asked]
    if not hurt or rng.random() > 0.8:
        return False
    p = max(hurt, key=lambda x: x.overall)
    asked.add((league.year, id(p)))
    backup = next((q for q in team.available_at(p.position) if q is not p), None)
    opp = nxt.opponent_of(team).school
    big = cz.PRIMARY_RIVAL.get(team.school) == opp or league.rankings.rank_of(nxt.opponent_of(team))
    _post(league, "Head athletic trainer", "Sports medicine", f"{p.name}: can he go?",
          f"{p.first_name} ({p.position}) is listed out {p.inj_games} week{'s' if p.inj_games != 1 else ''}. "
          f"He's telling everybody he can play against {opp}{' — and it is a big one' if big else ''}. "
          "Medically, he'd be about 85%. If he tweaks it again, you lose him for longer. Your call.",
          [("Play him. He knows his body.",
            {"who": p, "play_hurt": True, "chem": 1},
            f"{p.first_name} is on the travel roster. Fingers crossed."),
           ("Sit him. We'll need him in November.",
            {"who": p, "bought_in": True, "notes": [(False, f"{p.first_name} stays out")],
             "also": ({"who": backup, "dev": 1.06} if backup is not None else {})},
            f"{p.first_name} is frustrated. He also knows you've got his back — and his backup gets a week "
            "of first-team reps."),
           ("Let him warm up and decide at the stadium.",
            {"gamble": [(0.5, {"who": p, "play_hurt": True}, f"{p.first_name} looked good in warmups. He's in."),
                        ({"lift": -0.1, "clutch": -0.1}, f"{p.first_name} couldn't cut in warmups. He's out, "
                                                           "and the plan changed an hour before kickoff.")]},
            "A game-day decision, with everything that comes with it.")],
          ref=p, color=C.BRED)
    return True


def _lookahead(league, team, rng, nxt, cz):
    if nxt is None:
        return False
    games = [g for g in league.team_games(team) if not g.played]
    if len(games) < 2 or games[1].week != nxt.week + 1:
        return False
    after = games[1]
    site = 0 if nxt.neutral else (1 if nxt.home is team else -1)
    wp = cz.win_prob(team, nxt.opponent_of(team), site, league)
    big = after.opponent_of(team)
    a_site = 0 if after.neutral else (1 if after.home is team else -1)
    big_wp = cz.win_prob(team, big, a_site, league)
    marquee = league.rankings.rank_of(big) or cz.PRIMARY_RIVAL.get(team.school) == big.school or big_wp <= 0.45
    if wp < 0.72 or not marquee or not _once(league, f"lookahead{nxt.week}"):
        return False
    dc = getattr(team, "dc", None)
    small = nxt.opponent_of(team).school
    _post(league, dc.name if dc else "Staff", "Defensive Coordinator" if dc else "Staff",
          f"{small}, then {big.school}",
          f"We should handle {small}. {big.school} is the one I'm worried about. I've got a pressure package I'd "
          f"love to keep off film until then. If we show it Saturday, {big.school} will have a week to fix it.",
          [("Save it. Vanilla against {0}.".format(small),
            {"lift": -0.25, "later_lift": 0.35},
            f"You'll play {small} with half the playbook. {big.school} won't see it coming."),
           ("Show everything. Win the game in front of you.",
            {"lift": 0.15, "later_lift": -0.1},
            f"Nobody's overlooking {small}. {big.school}'s staff will be taking notes."),
           ("Split the difference: install it, call it twice.",
            {"lift": 0.05, "later_lift": 0.15, "clutch": -0.05},
            "A little of both. A little less of each.")],
          color=C.BCYAN)
    return True


def _rival_talk(league, team, rng, nxt, cz):
    if nxt is None:
        return False
    opp = nxt.opponent_of(team)
    if not (cz.PRIMARY_RIVAL.get(team.school) == opp.school or cz.PRIMARY_RIVAL.get(opp.school) == team.school):
        return False
    if rng.random() > 0.65 or not _once(league, "rival_talk"):
        return False
    coach = opp.coach.name if getattr(opp, "coach", None) else f"{opp.school}'s coach"
    line = rng.choice([f"'We don't really think of them as a rival. We think about the conference.'",
                       f"'Their best player would be our third-stringer.'",
                       f"'We've got more respect for their band than their defense.'",
                       f"'It's a big game for them. For us, it's Saturday.'"])
    _post(league, f"{team.school} Communications", "Sports Information", f"{coach} said what?",
          f"Heads up: {coach} was asked about us on his radio show last night. His words: {line} "
          "It's all over social. The beat writers want your reaction by noon.",
          [("Fire back. \"We'll see him Saturday.\"",
            {"lift": 0.2, "opp_lift": 0.2, "recruits": 1,
             "seat": by_ad(team, {"default": 0, "politician": -1, "booster": -1, "traditionalist": 1})},
            "The fan base loves it. So does theirs."),
           ("Take the high road. \"Great program, great coach.\"",
            {"opp_lift": -0.1, "chem": -1,
             "seat": by_ad(team, {"default": 0, "patient": -1, "traditionalist": -1, "politician": 1, "booster": 1})},
            "Mature. Some of your players wanted you to say something."),
           ("No comment. Print it and put it in every locker.",
            {"lift": 0.25, "gamble": [(0.75, {}, "It stayed in the building."),
                                      ({"opp_lift": 0.2}, "Somebody posted a picture of the locker room. It leaked.")]},
            "Private fuel. If it stays private.")],
          color=C.BYELLOW)
    return True


def _scheme(league, team, rng, nxt, cz):
    if nxt is None or rng.random() > 0.3:
        return False
    opp = nxt.opponent_of(team)
    site = 0 if nxt.neutral else (1 if nxt.home is team else -1)
    wp = cz.win_prob(team, opp, site, league)
    if not (league.rankings.rank_of(opp) or wp < 0.4) or not _once(league, f"scheme{nxt.week}"):
        return False
    if len([t for t in league.__dict__.get("_beats", {}).get(league.year, set()) if t.startswith("scheme")]) > 3:
        return False
    oc = getattr(team, "oc", None)
    if oc is None:
        return False
    _post(league, oc.name, "Offensive Coordinator", f"Plan for {opp.school}",
          f"Honest take: if we play it straight, {opp.school} is better than us. I want to open it up — "
          "fourth-down tries, trick plays, tempo. It might steal us the game. It might also get ugly.",
          [("Open it up. Let's go steal one.", {"lift": 0.35, "clutch": -0.3, "coord": oc, "stay": -1},
            "Aggressive plan. Great if it works, loose if it's close late."),
           ("Stay conservative. Keep it close, win it late.", {"clutch": 0.4, "lift": -0.1, "coord": oc, "stay": 1},
            "Shorten the game. Your OC wanted the keys."),
           ("One trick play a quarter. That's it.", {"lift": 0.15, "clutch": 0.05},
            "A little spice. Nobody gets everything they wanted.")],
          color=C.BCYAN)
    return True


def _bowl_eligible(league, team, rng, nxt, cz):
    if team.wins != 6 or not _once(league, "bowl_eligible"):
        return False
    young = sorted((p for p in team.roster if p.year <= 1), key=lambda p: -p.potential)[:3]
    _post(league, f"AD {team.ad['name']}", "Athletic Director", "Six wins",
          f"That's six. We're going bowling. The extra bowl practices are yours — how do you want to use them?",
          [("The young guys get the extra reps.",
            {"also": [{"who": p, "dev": 1.12} for p in young], "chem": 1, "lift": -0.1},
            "Your freshmen will look different in the spring. The veterans are a little bored."),
           ("It's about the vets. We're chasing a better bowl.", {"season_lift": 0.08, "chem": 1},
            "Every rep goes to the guys who play Saturdays."),
           ("Split the staff: half coach, half recruit.", {"hours": 8, "season_lift": -0.03},
            "Living rooms now, a little less coaching the rest of the way.")],
          color=C.BGREEN)
    return True


def _travel(league, team, rng, nxt, cz):
    if nxt is None or nxt.neutral or nxt.home is team or rng.random() > 0.35:
        return False
    trips = league.__dict__.setdefault("_trips", {}).setdefault(league.year, [])
    if len(trips) >= 3 or (trips and league.week - trips[-1] < 3):
        return False
    trips.append(league.week)
    opp = nxt.opponent_of(team)
    far = team.home_state != opp.home_state
    _post(league, "Director of Football Operations", "Staff", f"Travel to {opp.school}",
          f"Travel plan for {opp.school}. " + ("It's a long trip. " if far else "It's a short trip. ")
          + "Standard is a Friday afternoon flight. We can go early and settle in, or save some money.",
          [("Fly Thursday night. Walk through their stadium Friday.",
            {"money": -60_000, "lift": 0.2 if far else 0.1, "money_what": f"early travel to {opp.school}"},
            "Rested, settled, and a little lighter in the budget."),
           ("Standard Friday trip.", {"clutch": 0.05, "chem": 0.5},
            "Routine is a weapon too. Nothing fancy."),
           ("Bus it and bank the savings." if not far else "Fly in Saturday morning and bank a hotel night.",
            {"money": 40_000, "lift": -0.2, "money_what": "travel savings"},
            "The money goes back into next year's pool. The legs feel it.")],
          color=C.GRAY)
    return True


def _tampering(league, team, rng, nxt, cz):
    if league.week < 5 or rng.random() > 0.1:
        return False
    starters = _starters(team)
    pool = [p for p in team.roster if p in starters and p.year <= 2 and p.overall >= 70]
    if not pool or not _once(league, "tampering"):
        return False
    p = max(pool, key=lambda x: x.overall)
    thief = rng.choice([t for t in league.teams if t is not team and t.prestige >= team.prestige
                        and not getattr(t, "fcs", False)] or [t for t in league.teams if t is not team])
    import finance
    amt = int(round(max(60_000, finance.transfer_market(p) * 0.35) / 5000) * 5000)
    _post(league, "Position coach", "Staff", f"Somebody's in {p.first_name}'s ear",
          f"We're hearing that people connected to {thief.school}'s collective have been in contact with "
          f"{p.name}'s family. Nothing we can prove. He hasn't said a word to us.",
          [(f"Get ahead of it: bump his NIL now. (~{finance.money(amt)})",
            {"who": p, "bought_in": True, "money": -amt, "money_what": f"NIL bump for {p.name}"},
            f"{p.first_name}'s family appreciates it. So will every agent who hears you pay under pressure."),
           ("Talk to him. No money, just the truth about his future here.",
            {"gamble": [(0.6, {"who": p, "bought_in": True, "chem": 1}, f"{p.first_name}: 'I'm not going anywhere, Coach.'"),
                        ({"who": p, "unhappy": True}, f"{p.first_name} was polite. He's still listening to them.")]},
            "Cheap, and personal."),
           (f"Report {thief.school} to the conference.",
            {"chem": 1, "recruits": -1, "who": p,
             "seat": by_ad(team, {"default": 0, "traditionalist": -1, "politician": -1, "budget": -1}),
             "notes": [(None, f"{thief.school} will remember it")]},
            f"The conference will look into it. {p.first_name} is caught in the middle.")],
          ref=p, color=C.BYELLOW)
    return True


def _family(league, team, rng, nxt, cz):
    if nxt is None or rng.random() > 0.05 or not _once(league, "family"):
        return False
    starters = [p for p in _starters(team) if not getattr(p, "inj_games", 0)]
    if not starters:
        return False
    p = rng.choice(starters)
    _post(league, f"{p.position} {p.name}", f"{p.class_label} · starter", "Family",
          f"Coach, my grandmother's in the hospital back home. It's bad. My mom wants me there. "
          f"I don't want to let the guys down for {nxt.opponent_of(team).school}.",
          [("Go home. Be with your family. Football will be here.",
            {"who": p, "sit": 1, "sit_why": "away — family", "also": {"who": p, "bought_in": True}, "chem": 3},
            f"{p.first_name} flies out tonight. The whole team signed a card."),
           ("Go now; we'll fly you back Friday night. Your call Saturday.",
            {"money": -15_000, "who": p, "bought_in": True, "lift": -0.1, "money_what": "a player's travel home"},
            f"{p.first_name} goes home and comes back. He's not all there, but he's there."),
           ("The team needs you Saturday. Go right after the game.",
            {"lift": 0.1, "chem": -3, "gamble": [(0.6, {}, f"{p.first_name} played. He's quiet about it."),
                                                 ({"who": p, "unhappy": True},
                                                  f"{p.first_name} played. He won't forget you asked.")]},
            "You kept a starter. The locker room heard what you asked.")],
          ref=p, color=C.BMAGENTA)
    return True


def _heisman(league, team, rng, nxt, cz):
    if not (6 <= league.week <= 11):
        return False
    rank = league.rankings.rank_of(team)
    if not rank and team.wins < 6:
        return False
    def score(p):
        s = p.season_stats
        return s.get("pass_td", 0) * 4 + s.get("rush_yds", 0) / 12 + s.get("rec_yds", 0) / 14 + s.get("rush_td", 0) * 5 \
            + s.get("rec_td", 0) * 5 + s.get("sack", 0) * 6
    star = max(team.roster, key=score, default=None)
    if star is None or score(star) < 90 or not _once(league, "heisman"):
        return False
    _post(league, f"{team.school} Communications", "Sports Information", f"The {star.last_name} campaign",
          f"{star.name}'s numbers are real. We could run a Golden Helmet push: a website, a highlight package to every "
          "voter, national radio every week. It's a statement about the program — and about one guy.",
          [("All in. Make him a household name.",
            {"recruits": 2.5, "chem": -2, "who": star, "bought_in": True, "money": -50_000,
             "money_what": f"{star.name} Golden Helmet campaign"},
            "Recruits see the spotlight. Some of his teammates see who's in it."),
           ("Low-key. Let his tape do it.", {"recruits": 0.5, "chem": 1},
            "Quiet confidence. Less noise, less buzz."),
           ("Team first. Push the offensive line for an award instead.",
            {"chem": 3, "who": star, "unhappy": True, "recruits": -0.5},
            f"The linemen are thrilled. {star.first_name} smiled for the cameras and stewed in private.")],
          ref=star, color=C.BYELLOW)
    return True


def _freshman(league, team, rng, nxt, cz):
    if not (3 <= league.week <= 5) or rng.random() > 0.5:
        return False
    fr = sorted((p for p in team.roster if p.year == 0 and p.hs_stars >= 3), key=lambda p: -p.potential)
    if not fr or not _once(league, "freshman_plan"):
        return False
    p = fr[0]
    starting = p in _starters(team)
    who = getattr(team, "oc" if p.position in ("QB", "RB", "WR", "TE", "OL") else "dc", None)
    _post(league, who.name if who else "Staff", "Coordinator", f"Plan for {p.first_name}",
          f"{p.name} ({p.hs_stars}★ {p.position}) is {'already starting' if starting else 'pushing for snaps'}. "
          "The question is what's best for him — and for us. He's got more upside than anybody in the room.",
          [("Throw him in. He learns by playing.",
            {"who": p, "bought_in": True, "season_lift": -0.03 if not starting else 0.02, "clutch": -0.05},
            f"{p.first_name} is thrilled. Freshman mistakes are part of the deal."),
           ("Scout team and development. His time is next year.",
            {"who": p, "dev": 1.22, "gamble": [(0.7, {}, f"{p.first_name} gets it."),
                                                ({"who": p, "unhappy": True},
                                                 f"{p.first_name}'s family expected him to play.")]},
            "He'll be a different player in the spring."),
           ("Special teams and one package. Earn more.",
            {"who": p, "dev": 1.1, "lift": 0.03},
            "A little of both.")],
          ref=p, color=C.BCYAN)
    return True


def _walk_on(league, team, rng, nxt, cz):
    if not (3 <= league.week <= 10) or rng.random() > 0.15:
        return False
    wo = [p for p in team.roster if getattr(p, "walk_on", False) and p in team.players_at(p.position)[:3]]
    if not wo or not _once(league, "walk_on"):
        return False
    p = max(wo, key=lambda x: x.overall)
    _post(league, "Strength coach", "Staff", f"{p.name} — walk-on",
          f"{p.name} walked on, paid his own way, and he's in our two-deep at {p.position}. The guys would run through "
          "a wall for him. A lot of programs put a kid like that on scholarship — in front of the team.",
          [("Put him on scholarship. Tell him in front of everybody.",
            {"money": -30_000, "chem": 4, "recruits": 0.5, "who": p, "bought_in": True,
             "money_what": f"scholarship for walk-on {p.name}"},
            "The video of the moment went everywhere. The locker room went crazy."),
           ("At the end of the year, if he keeps it up.",
            {"lift": 0.05, "gamble": [(0.7, {}, f"{p.first_name} is still grinding."),
                                      ({"chem": -1}, "A couple of the older guys think he's earned it already.")]},
            "Something to play for. Not everybody sees it that way."),
           ("We don't have room in the budget this year.", {"money": 0, "chem": -2,
                                                            "notes": [(True, "keeps the money in the NIL pool")]},
            "Word gets around.")],
          ref=p, color=C.BGREEN)
    return True


def _academics(league, team, rng, nxt, cz):
    if not (3 <= league.week <= 10) or rng.random() > 0.1:
        return False
    starters = [p for p in _starters(team) if not getattr(p, "inj_games", 0)]
    if not starters or not _once(league, "academics"):
        return False
    p = rng.choice(starters)
    _post(league, "Academic advisor", "Academic Services", f"{p.name}'s grades",
          f"{p.first_name} is failing two classes. If midterms go badly, he's ineligible for the rest of the "
          "season. He needs hours in the learning center — hours that come out of football.",
          [("Tutoring before practice every day. He misses film.",
            {"lift": -0.1, "who": p, "notes": [(True, "he stays eligible")]},
            f"{p.first_name} grumbles and goes. He'll be a step slow on the game plan."),
           ("Sit him this week. Grades first — and everybody sees it.",
            {"who": p, "sit": 1, "sit_why": "held out — academics", "chem": 2,
             "seat": by_ad(team, {"default": 0, "traditionalist": -1, "patient": -1})},
            "The message lands with the whole roster."),
           ("He'll handle it. Keep him on schedule.",
            {"gamble": [(0.65, {}, f"{p.first_name} passed his midterms. Barely."),
                        ({"who": p, "sit": 3, "sit_why": "academically ineligible", "chem": -1},
                         f"{p.first_name} failed his midterms. He's ineligible for three games.")]},
            "Nothing changes, for now.")],
          ref=p, color=C.BYELLOW)
    return True


def _podcast(league, team, rng, nxt, cz):
    if not (2 <= league.week <= 11) or rng.random() > 0.12 or not _once(league, "podcast"):
        return False
    oc = getattr(team, "oc", None)
    _post(league, f"{team.school} Communications", "Sports Information", "The big podcast wants you",
          "The biggest college football podcast in the country wants an hour with you Wednesday. National exposure, "
          "the recruits all listen to it. It's also an hour on Wednesday, and they'll ask about everything.",
          [("Do it. Wednesday night after practice.",
            {"recruits": 2, "lift": -0.1, "seat": -by_ad(team, HEADLINES)},
            "Great hour. Your Thursday walkthrough was a little rushed."),
           ("Pass. We're in season.", {"lift": 0.05, "seat": by_ad(team, HEADLINES)},
            "Focus stays on the game."),
           (f"Send {oc.name.split()[-1]} instead." if oc else "Send a coordinator instead.",
            ({"recruits": 1, "coord": oc, "stay": 1} if oc else {"recruits": 1}),
            "Good for your coordinator's profile. Maybe too good.")],
          color=C.GRAY)
    return True


def _scouts(league, team, rng, nxt, cz):
    if not (3 <= league.week <= 10) or rng.random() > 0.12:
        return False
    pros = [p for p in team.roster if p.year >= 2 and p.overall >= 78]
    if not pros or not _once(league, "scouts"):
        return False
    p = max(pros, key=lambda x: x.overall)
    _post(league, "Director of Player Personnel", "Staff", "Pro League scouts want in",
          f"Six Pro League teams want to watch practice this week, mostly for {p.name}. Open practices mean cameras, "
          "distractions, and guys playing for the scouts instead of the scheme.",
          [("Open the doors. That's what we sell.", {"recruits": 1.5, "chem": 1, "lift": -0.15},
            "Recruits hear about the Pro League crowd. Practice is a little showy."),
           ("Closed. They can watch the game film.", {"lift": 0.1, "who": p, "unhappy": True},
            f"Locked in. {p.first_name}'s agent is not happy."),
           ("One open day — Tuesday — then we lock it down.", {"recruits": 0.5, "who": p, "bought_in": True,
                                                               "lift": -0.05},
            "Everybody gets a little.")],
          ref=p, color=C.GRAY)
    return True


def _legend(league, team, rng, nxt, cz):
    if not (2 <= league.week <= 12) or rng.random() > 0.08 or not _once(league, "legend"):
        return False
    name = f"{rng.choice(['Marcus', 'Tommy', 'Dwayne', 'Rick', 'Andre', 'Bo'])} {rng.choice(['Hollis', 'Carver', 'Stamps', 'Reddick', 'Oakes', 'Tillman'])}"
    _post(league, name, "Program legend", "Can I talk to the team?",
          f"Coach — {name} here, class of '9{rng.randint(0, 9)}. I'm in town this week. I'd love to talk to the team "
          "Thursday. I've got some things I think they need to hear. I don't sugarcoat.",
          [("Absolutely. Thursday's yours.",
            {"gamble": [(0.7, {"chem": 4, "lift": 0.15}, f"{name.split()[0]} had them on their feet."),
                        ({"chem": -2, "seat": by_ad(team, {"default": 1, "politician": 2})},
                         f"{name.split()[0]} spent half of it criticizing the staff. It got out.")]},
            "Legends are legends for a reason. Some of them have opinions."),
           ("Make him an honorary captain for the coin toss instead.",
            {"chem": 1, "recruits": 0.5},
            "The crowd loved it. No speech required."),
           ("Not during a game week. After the season.",
            {"lift": 0.05, "seat": by_ad(team, {"default": 0, "traditionalist": 1, "booster": 1})},
            "He said he understood. His friends at the Club heard about it.")],
          color=C.BMAGENTA)
    return True


def _strength(league, team, rng, nxt, cz):
    if not (3 <= league.week <= 6) or rng.random() > 0.3 or not _once(league, "strength"):
        return False
    _post(league, "Strength coach", "Staff", "In-season lifting",
          "We're a few weeks in. I can keep the lifting heavy through November — we'll be sturdier late, but a "
          "little heavy-legged on Saturdays. Or I can pull it back and keep them fresh.",
          [("Keep it heavy. Build for November.", {"season_inj": 0.9, "season_lift": -0.05},
            "Fewer injuries the rest of the way. A little slower every Saturday."),
           ("Pull it back. Fresh legs every Saturday.", {"season_lift": 0.1, "season_inj": 1.08},
            "Faster on Saturdays. More guys banged up by November."),
           ("Let the captains and trainers decide week to week.",
            {"chem": 2, "gamble": [(0.5, {"season_inj": 0.95}, "They found the balance."),
                                   ({"season_lift": -0.03}, "They erred toward rest. Too much, some weeks.")]},
            "The players like having a say.")],
          color=C.BCYAN)
    return True


def _banquet(league, team, rng, nxt, cz):
    if not (2 <= league.week <= 12) or rng.random() > 0.1:
        return False
    from collections import Counter
    states = Counter(r.home_state for r in getattr(team, "recruiting_targets", []) if not r.signed)
    if not states or not _once(league, "banquet"):
        return False
    st, n = states.most_common(1)[0]
    _post(league, f"HS coach {rng.choice(['Dale', 'Jerry', 'Mike', 'Tony', 'Curtis'])} {rng.choice(['Pruitt', 'Voss', 'Delgado', 'Boone', 'Whitaker'])}",
          f"High school coach · {st}", "Our banquet",
          f"Coach, we'd be honored to have you speak at our coaches' association banquet Thursday. Every head coach "
          f"in {st} will be there. It's a long night, and it's in the middle of your game week.",
          [("I'll be there.", {"hours": -4, "state": (st, 4), "lift": -0.1},
            f"You worked the room. Every high school coach in {st} has your cell number now."),
           ("Send my recruiting coordinator.", {"hours": -1, "state": (st, 1.5)},
            "A good showing. Not the same as the head coach."),
           ("Record a video message. Game week.", {"state": (st, 0.5), "lift": 0.05,
                                                   "notes": [(False, f"{st} coaches notice you weren't there")]},
            "They played it before dinner. It was fine.")],
          color=C.BYELLOW)
    return True


def _donor(league, team, rng, nxt, cz):
    if not (3 <= league.week <= 11) or rng.random() > 0.08 or not _once(league, "donor"):
        return False
    import finance
    donor = f"{rng.choice(['Harold', 'Patricia', 'Glenn', 'Diane', 'Russell'])} {rng.choice(['Ashworth', 'Kingsley', 'Van Horn', 'Prescott', 'Lyle'])}"
    gift = by_ad(team, {"default": 250_000, "booster": 400_000, "budget": 150_000})
    _post(league, donor, "Major donor", "A gift, and a favor",
          f"Coach, I'd like to put {finance.money(gift)} into the NIL collective for next year. I'd also love for my "
          "grandson — he's a walk-on — to travel with the team and dress for home games. He's worked hard.",
          [("Thank you. He'll travel with us.",
            {"money": gift, "chem": -2, "money_what": f"gift from {donor}"},
            "The money's real. So is the look on your walk-ons' faces who didn't make the travel roster."),
           ("We'd love the gift. The travel roster is earned.",
            {"money": gift // 3, "seat": by_ad(team, {"default": 0, "booster": 2, "politician": 1}), "chem": 1,
             "money_what": f"a smaller gift from {donor}"},
            "He gave — less. The players heard you held the line."),
           ("How about sideline passes for your whole family instead?",
            {"money": gift // 2, "hours": -2, "money_what": f"gift from {donor}"},
            "A compromise. You'll spend a Saturday morning hosting him.")],
          color=C.BGREEN)
    return True


# ═══ December ═══════════════════════════════════════════════════════════════

def season_end(league, team, rng):
    dc = getattr(team, "dc", None)
    if dc is not None:
        try:
            import staff
            good = staff.resume_score(dc) >= 5
        except Exception:
            good = False
        if good:
            _post(league, dc.name, "Defensive Coordinator", "My contract",
                  "Coach, I'll be straight with you: I've got an offer to be a coordinator at a bigger place, "
                  "with a raise. I'd rather stay. I'd like you to make it make sense.",
                  [("Match it. You're worth it.",
                    {"coord": dc, "stay": -1, "money": -175_000, "money_what": f"raise for {dc.name}"},
                    "He's staying. That money isn't going to recruits."),
                   ("Meet me halfway.",
                    {"money": -85_000, "money_what": f"raise for {dc.name}",
                     "gamble": [(0.55, {"coord": dc, "stay": -1}, "He took it."),
                                ({"coord": dc, "stay": 1}, "He appreciated it. He's still thinking about the other job.")]},
                    "A fair offer. Maybe not enough."),
                   ("I can't. Go if you have to — I'll promote from within.",
                    {"coord": dc, "stay": 1, "chem": 1, "notes": [(True, "keeps the money for NIL")]},
                    "Your position coaches noticed there might be a door opening.")],
                  color=C.BCYAN)
