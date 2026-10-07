"""
december.py — The month after the regular season (Career mode).

The postseason used to arrive a week at a time with no warning. Now each week
of it is built as soon as the week before it is final, so the whole week
before a conference title game, a bowl or a playoff game knows who it's
against — the week hub, the Thursday presser, the practice plan, and the
inbox. And December gets its own mail:

  CHAMPIONSHIP WEEK   how you prepare for the title game
  THE BOWL TRIP       a business trip or a reward trip
  OPT-OUTS            your draft-bound stars asking to skip the bowl — and
                      stars around the country actually skipping theirs
  THE PLAYOFF         every round: lock in, soak it in, or sell it on the trail
  EARLY SIGNING       push your commits to sign now, or let them look around
  THE PORTAL WINDOW   the unhappy players on your roster, before it opens
  NO BOWL             a December with no game: develop, recruit, or rest

Every choice shows what it costs, like the rest of the inbox.
"""
import random

from effects import by_ad
from ui import C

CFP = ("NP First Round", "NP Quarterfinal", "NP Semifinal", "National Championship")


def _once(league, tag):
    said = league.__dict__.setdefault("_beats", {}).setdefault(league.year, set())
    if tag in said:
        return False
    said.add(tag)
    return True


def _post(league, *a, **kw):
    import people
    return people.choice(league, *a, **kw)


def _next(league, team):
    return next((g for g in league.team_games(team) if not g.played), None)


def _starters(team):
    return {p for grp in team.starters().values() for p in grp}


def _eligible(p):
    return p.year == 3 or p.year == 2 or (p.year == 1 and getattr(p, "redshirt", False))


# ═══ Around the country: bowl opt-outs ══════════════════════════════════════

def after_week(league):
    """Once the bowls are set, draft-bound stars on other teams decide whether to play."""
    bowls = [g for g in league.schedule.get(16, []) if g.game_type == "Bowl" and not g.played]
    if not bowls or not _once(league, "ai_optouts"):
        return
    import personalities
    import morale
    board = personalities.projected_spots(league)
    rng = random.Random(f"optout:{league.seed}:{league.year}")
    import hotseat
    mines = hotseat.humans(league) if getattr(league, "mode", None) == "career" else []
    for g in bowls:
        for t in (g.home, g.away):
            if any(t is m for m in mines):
                continue
            outs = 0
            for p in sorted(t.roster, key=lambda x: -x.overall):
                spot = board.get(id(p))
                if spot is None or spot > 100 or not _eligible(p) or outs >= 2:
                    continue
                odds = (0.65 if spot <= 32 else 0.45 if spot <= 64 else 0.2) * (1.25 if morale.get(p) < 45 else 1.0)
                if rng.random() < odds:
                    personalities._suspend(league, p, g.week - league.week, "opted out — preparing for the draft",
                                           event=f"Opted out of the {g.bowl_name}")
                    outs += 1
                    if spot <= 64:
                        personalities._say(league, f"{t.school} {p.position} {p.name} opts out of the "
                                                   f"{g.bowl_name} to prepare for the Pro League Draft.")


# ═══ Your December ══════════════════════════════════════════════════════════

def inbox(league, team, rng):
    """Called from the weekly mail once the regular season is over."""
    if league.week < 13:
        return
    nxt = _next(league, team)
    gt = getattr(nxt, "game_type", None)
    if gt == "Conference Championship":
        _title_game(league, team, nxt)
    elif gt in CFP:
        _playoff(league, team, nxt)
    elif gt == "Bowl":
        _bowl_trip(league, team, nxt)
        _opt_outs(league, team, nxt)
    elif nxt is None and league.week == 13 and team.wins < 6:
        _no_bowl(league, team)
    if 13 <= league.week <= 14:
        _early_signing(league, team, rng)
    if league.week >= 14:
        _portal_window(league, team)


def _title_game(league, team, g):
    if not _once(league, "ccg"):
        return
    opp = g.opponent_of(team).school
    _post(league, f"AD {team.ad['name']}", "Athletic Director", f"{team.conference} Championship",
          f"We're playing for the {team.conference} title against {opp}. Whatever you need this week, ask. "
          "How are you handling it?",
          [("Same week as always. Routine wins championships.", {"clutch": 0.3, "chem": 1},
            "Nothing changes. The players feel the calm."),
           ("Everything we've got: extra film, full pads Tuesday.", {"lift": 0.35, "inj": 1.15, "chem": -1},
            "The most prepared you've ever been. The most beat-up, too."),
           ("Bring every recruit we've got to the game.",
            {"recruits": 3, "lift": -0.15, "seat": by_ad(team, {"default": 0, "brand": -1, "recruiting": -1})},
            "The recruits get a title-game atmosphere. The staff's attention is split.")],
          color=C.BYELLOW)


def _playoff(league, team, g):
    gt = g.game_type
    if not _once(league, f"cfp:{gt}"):
        return
    opp = g.opponent_of(team).school
    round_name = {"NP First Round": "a home playoff game", "NP Quarterfinal": f"the {g.bowl_name}",
                  "NP Semifinal": f"the semifinal at the {g.bowl_name}",
                  "National Championship": "the national championship"}[gt]
    title = gt == "National Championship"
    _post(league, f"{team.school} Communications", "Sports Information",
          "National title week" if title else f"Playoff: {opp}",
          f"It's {round_name} against {opp}. Media requests have gone through the roof — national TV, "
          "every podcast, a documentary crew. How much of it do we let in?",
          [("Lock it down. Nobody talks but me.", {"lift": 0.35, "chem": -1, "recruits": -0.5},
            "Total focus. The players are a little tightly wound."),
           ("Let them soak it in. This is why they came here.", {"chem": 3, "lift": 0.1, "team_morale": 4,
                                                                  "clutch": -0.1},
            "They'll never forget this week. They may be a little loose."),
           ("Let the cameras in. Sell the program.", {"recruits": 3.5, "lift": -0.15,
                                                       "seat": by_ad(team, {"default": 0, "brand": -2, "booster": -1})},
            "Recruits everywhere see your locker room. The week is louder than it should be.")],
          color=C.BMAGENTA)


def _bowl_trip(league, team, g):
    if not _once(league, "bowl_trip"):
        return
    _post(league, "Director of Football Operations", "Staff", f"The {g.bowl_name}",
          f"We're headed to the {g.bowl_name} ({g.venue}) against {g.opponent_of(team).school}. The bowl has "
          "events every night — the players will want to do all of them. Business trip or reward trip?",
          [("Business trip. Curfew every night. We came to win.", {"lift": 0.35, "team_morale": -3, "chem": -1},
            "They'll be ready. They'll also remember the curfew."),
           ("Reward trip. They earned every minute of it.", {"team_morale": 5, "chem": 3, "lift": -0.25},
            "Best week of the year for the players. The game plan got the leftovers."),
           ("Split it, and use the bowl practices on the young guys.",
            {"also": [{"who": p, "dev": 1.1} for p in sorted((q for q in team.roster if q.year <= 1),
                                                             key=lambda q: -q.potential)[:4]],
             "lift": -0.1, "team_morale": 1},
            "The freshmen get 15 extra practices. The vets get a little bored.")],
          color=C.BGREEN)


def _opt_outs(league, team, g):
    import personalities
    import morale
    board = personalities.projected_spots(league)
    starters = _starters(team)
    asked = league.__dict__.setdefault("_asked_optout", set())
    cands = [p for p in team.roster if p in starters and _eligible(p) and id(p) not in asked
             and board.get(id(p)) is not None and board[id(p)] <= 120]
    for p in sorted(cands, key=lambda x: board[id(x)])[:2]:
        asked.add(id(p))
        spot = board[id(p)]
        rnd = min(7, (spot - 1) // 32 + 1)
        mv = morale.get(p)
        stay_odds = max(0.15, min(0.85, mv / 100 + (0.1 if "loyal" in p.traits or "captain" in p.traits else 0)))
        n = max(1, g.week - league.week)
        _post(league, f"{p.position} {p.name}", f"{p.class_label} · {__import__('scout').ovr_tag(p)} · projected round {rnd} · "
                                                f"morale {mv:.0f}",
              "The bowl game",
              f"Coach, I've been going back and forth. My agent — well, my family's advisor — says I should sit "
              f"out the {g.bowl_name} and protect my draft stock. I don't want to let the guys down. What do you think?",
              [("It's your future. We support you, no questions.",
                {"who": p, "sit": n, "sit_why": "opted out — preparing for the draft", "morale": 10, "recruits": 1,
                 "lift": -0.15, "sit_hint": "he sits out the bowl", "sit_event": f"Opted out of the {g.bowl_name}"},
                f"{p.first_name} is grateful. Recruits hear you put players first. The bowl team is thinner."),
               ("Play one more for the seniors. Finish it together.",
                {"gamble": [(stay_odds, {"chem": 3, "who": p, "morale": 2},
                             f"{p.first_name} is in. The locker room erupted when he told them."),
                            ({"who": p, "sit": n, "sit_why": "opted out — preparing for the draft", "morale": -10,
                              "sit_hint": "he sits out the bowl", "sit_event": f"Opted out of the {g.bowl_name}"},
                             f"{p.first_name} opted out anyway. It's awkward now.")]},
                "You asked. He'll decide."),
               ("Play the first half, then you're done.",
                {"lift": 0.1, "who": p, "morale": -2, "notes": [(False, "he's exposed to injury for a half")]},
                "A compromise nobody loves and everybody accepts.")],
              ref=p, color=C.BMAGENTA)


def _no_bowl(league, team):
    if not _once(league, "no_bowl"):
        return
    young = sorted((p for p in team.roster if p.year <= 1), key=lambda p: -p.potential)[:5]
    _post(league, f"AD {team.ad['name']}", "Athletic Director", "No bowl this year",
          f"{team.record}. No postseason. That's a long December. What do you want to do with it?",
          [("Practice anyway. The young guys get the reps.",
            {"also": [{"who": p, "dev": 1.12} for p in young], "team_morale": -3,
             "seat": by_ad(team, {"default": -1, "patient": -2})},
            "Nobody wants to practice in December for nothing. The freshmen will be better for it."),
           ("Every coach on the road until signing day.", {"hours": 15, "top": (8, 3)},
            "Your staff lives in hotels for three weeks."),
           ("Send them home. Heal up, reset, come back hungry.", {"team_morale": 6, "chem": 3, "heal": 3,
                                                                  "seat": by_ad(team, {"default": 1, "patient": 0})},
            "The room needed it. Some people upstairs think you're taking it easy.")],
          color=C.BCYAN)


def _early_signing(league, team, rng):
    try:
        commits = list(league.recruiting.commitments(team))
    except Exception:
        return
    if not commits or not _once(league, "early_signing"):
        return
    commits = [r for r in commits if not getattr(r, "signed", False)]
    shaky = sorted(commits, key=lambda r: r.interest.get(team, 0))[:3]
    _post(league, "Recruiting Office", "Director of Recruiting", "Early signing period",
          f"Early signing period opens this week. We have {len(commits)} commitment{'s' if len(commits) != 1 else ''}. "
          + (f"The shakiest: {', '.join(r.name for r in shaky)}. " if shaky else "")
          + "Do we push everybody to sign now, or let them take their official visits?",
          [("Push every commit to sign now.",
            {"hours": -3, "gamble": [(0.8, {"quiet": True, "notes": [(True, "every commit locks in")],
                                            "also": [{"recruit": 10, "ref": r} for r in commits]},
                                      "Most of them signed on day one. The class is locked."),
                                     ({"quiet": True, "notes": [(False, f"{shaky[0].name if shaky else 'one kid'} balks")],
                                       "also": [{"recruit": 6, "ref": r} for r in commits[:-1]] +
                                               [{"recruit": -12, "ref": r} for r in shaky[:1]]},
                                      f"Most signed. {shaky[0].name if shaky else 'One kid'} felt pressured and "
                                      "is looking around.")]},
            "Pressure closes classes. Sometimes it opens doors, too."),
           ("Let them take their visits. They'll come back.",
            {"recruits": 1, "also": [{"quiet": True, "notes": [(False, "your shakiest commits drift")]}]
                                    + [{"recruit": -3, "ref": r, "quiet": True} for r in shaky]},
            "Kids and families respect it. Rival staffs will be in those living rooms."),
           ("Hold two spots for flips from other schools.",
            {"flip": (3, 6), "notes": [(True, "3 kids committed elsewhere warm up")],
             "also": [{"quiet": True, "notes": [(False, "your own commits notice")]}]
                     + [{"recruit": -2, "ref": r, "quiet": True} for r in shaky[:2]]},
            "Your own commits noticed you're still shopping.")],
          color=C.BYELLOW)


def _portal_window(league, team):
    import morale
    unhappy = sorted((p for p in team.roster if morale.get(p) < 40 and p.year <= 2), key=lambda p: -p.overall)[:3]
    if not unhappy or not _once(league, "portal_window"):
        return
    best = unhappy[0]
    names = ", ".join(f"{p.position} {p.name} ({morale.get(p):.0f})" for p in unhappy)
    _post(league, "Director of Player Personnel", "Staff", "Before the portal opens",
          f"The transfer portal opens after the postseason. These guys are unhappy enough to go: {names}. "
          "If we're going to change any minds, it's now.",
          [("I'll meet with every one of them.",
            {"hours": -2 * len(unhappy), "meeting": True, "notes": [(True, "each one's morale ▲▲")],
             "also": [{"who": p, "morale": 14, "quiet": True, "why_mood": "you met with him"} for p in unhappy]},
            "A long week of meetings. Some of them just wanted to be asked."),
           (f"Focus on {best.first_name}. Promise him a bigger role.",
            {"who": best, "promise": "made", "morale": 12, "why_mood": "promised a bigger role"},
            f"{best.first_name} is listening. The others noticed who got the meeting."),
           ("Let them go. Their NIL money goes to next year's class.",
            {"recruits": 1.5, "chem": 1, "notes": [(False, "they're very likely gone")],
             "also": [{"who": p, "morale": -8, "quiet": True, "why_mood": "told he could go"} for p in unhappy]},
            "The staff turns its attention to who's coming, not who's leaving.")],
          color=C.BYELLOW)
