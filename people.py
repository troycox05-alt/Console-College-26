"""
people.py — The people who talk to you.

Every week of a career, the people around your program reach out: your
athletic director, your players, the recruits on your board, your
coordinators, the boosters, the trainers, the student section. They say it in
their own voice — an AD sounds like his style — and they're reacting to what
actually happened: the last game, your seat, the depth chart, a recruitment
that's slipping.

Every message that wants an answer gives you real choices, and none of them is
free. Each option shows what it does before you pick it (the colored line
under it: green is what you get, red is what it costs, yellow is a risk or
something riding on a later result). What the choices can touch — see
effects.py — is your AD's patience, the locker room, this Saturday (or the
game after), late-game poise, injuries, recruiting hours and interest, next
year's NIL money, and individual players: who's happy, who's bought in, who
develops faster, who's eyeing the portal.

No answer is an answer too: a message you leave sitting for two weeks closes,
and a few of them (a recruit, a player asking about his role) notice.

More scenarios live in inbox_scenarios.py. Nothing here happens in spectator mode.
"""
import random
from netplay import moments

import effects as fx
from effects import by_ad
from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

KEEP = 40                     # how many messages the inbox holds


# ═══ The inbox ══════════════════════════════════════════════════════════════

def _normalize_message(league, m):
    """Bring inbox entries from older/forked saves up to the current schema.

    Inbox UI should never be able to crash just because a historical message predates
    a field added by a later branch. Keep this deliberately conservative: only fill
    presentation/state defaults and leave the actual message/effects untouched.
    """
    if not isinstance(m, dict):
        return None
    m.setdefault("year", getattr(league, "year", 2026))
    m.setdefault("week", getattr(league, "week", 0))
    m.setdefault("sender", "Staff")
    m.setdefault("role", "Staff")
    m.setdefault("subject", "Message")
    m.setdefault("body", "")
    m.setdefault("replies", [])
    m.setdefault("kind", "note")
    m.setdefault("ref", None)
    m.setdefault("read", False)
    m.setdefault("answered", None)
    m.setdefault("color", None)
    m.setdefault("due", None)
    m.setdefault("silence", None)
    m.setdefault("silence_text", None)
    return m


def inbox(league):
    msgs = league.__dict__.setdefault("inbox", [])
    # Saves have existed through several UI branches. Normalize lazily on access so
    # every old save benefits without needing a one-off migration version gate.
    clean = []
    changed = False
    for m in msgs:
        nm = _normalize_message(league, m)
        if nm is not None:
            clean.append(nm)
        else:
            changed = True
    if changed:
        league.inbox = clean
        msgs = clean
    return msgs


def unread(league):
    return sum(1 for m in inbox(league) if not m.get("read", False))


def waiting(league):
    """Messages that still want an answer."""
    return [m for m in inbox(league) if m.get("replies") and m.get("answered") is None]


def _post(league, sender, role, subject, body, replies=None, kind="note", ref=None, color=None,
          silence=None, silence_text=None, due=None):
    import world_rules
    if not world_rules.enabled(league, "inbox"):
        return None
    msgs = inbox(league)
    msgs.append({"year": league.year, "week": league.week, "sender": sender, "role": role, "subject": subject,
                 "body": body, "replies": replies or [], "kind": kind, "ref": ref, "read": False,
                 "answered": None, "color": color, "due": due or (league.year, league.week + 1),
                 "silence": silence, "silence_text": silence_text})
    del msgs[:-KEEP]
    return msgs[-1]


def choice(league, sender, role, subject, body, options, color=None, ref=None, silence=None,
           silence_text=None, due=None):
    """A message with real choices. options: [(label, effects, what happens)]."""
    replies = [(f"o{i}", label) for i, (label, _, _) in enumerate(options)]
    m = _post(league, sender, role, subject, body, replies, kind="choice", ref=ref, color=color,
              silence=silence, silence_text=silence_text, due=due)
    m["fx"] = {f"o{i}": e for i, (_, e, _) in enumerate(options)}
    m["out"] = {f"o{i}": t for i, (_, _, t) in enumerate(options)}
    return m


def _expire(league):
    """Messages nobody answered in time close. Some of them notice."""
    now = (league.year, league.week)
    for m in inbox(league):
        if not m.get("replies") or m.get("answered") is not None:
            continue
        due = m.get("due")
        if due is None or tuple(due) >= now:
            continue
        m["answered"] = "silence"
        if m.get("silence"):
            fx.apply(league, m["silence"], "an unanswered message")
        if str(m.get("sender", "")).startswith("AD "):
            import ad_trust
            ad_trust.change(league, -4, "left him on read")


def _career(league):
    me = getattr(league, "user_coach", None)
    return getattr(league, "mode", None) == "career" and me is not None and me.team is not None


def _last_game(league, team):
    done = [g for g in league.team_games(team) if g.played]
    return done[-1] if done else None


def _next_game(league, team):
    return next((g for g in league.team_games(team) if not g.played), None)


def _rival(team):
    import carousel as cz
    return cz.PRIMARY_RIVAL.get(team.school)


# ═══ Voices ═════════════════════════════════════════════════════════════════
# How each kind of AD talks. {opp}, {score}, {rec} are filled in.

AD_VOICE = {
    "after_bad_loss": {
        "win_now": ["That can't happen. {score} to {opp} is the kind of result that gets remembered in this building.",
                    "I'll be blunt: {score}. We didn't hire you for weeks like this."],
        "booster": ["My phone has not stopped ringing since {opp}. The donors want to know what happened. So do I.",
                    "{score}. I spent Sunday explaining that one to people who write very large checks."],
        "politician": ["Talk radio is lit up about {opp}. I need something to tell them, Coach.",
                       "The message boards are ugly after {score}. I'm getting it from every direction."],
        "patient": ["Rough one against {opp}. Get the film fixed and keep building — I'm not going anywhere.",
                    "{score} stings. One game doesn't change what we're doing. Clean it up."],
        "default": ["{score} against {opp} wasn't us. What do you need to fix it?",
                    "Tough Saturday. I want to hear your plan for getting back on track."],
    },
    "after_big_win": {
        "booster": ["Coach — the boosters are ecstatic after {opp}. You made a lot of friends Saturday.",
                    "{score}! I've had three donors call just to say thank you."],
        "brand": ["That's the kind of win that gets us on national TV. {opp}, {score}. More of that.",
                  "Everybody in the country saw {score} Saturday. That's what this program is supposed to look like."],
        "big_game": ["THAT is why you're here. Beating {opp} is what I hired you for.",
                     "Ranked win, {score}. Those are the ones people remember."],
        "default": ["Great win over {opp}. The whole building felt it Monday morning.",
                    "{score} — well done, Coach. Enjoy it for a day, then get back to work."],
    },
    "hot_seat": {
        "win_now": ["I'll be honest with you: I need wins, and I need them soon.",
                    "We're {rec}. You know what the expectations are here. I need to see a response."],
        "budget": ["I'd rather not write a buyout check. Help me not have to.",
                   "{rec} isn't where we need to be. I'm being patient — don't make me stop."],
        "default": ["People are asking me questions about the direction of the program. I need answers on the field.",
                    "The heat's real, Coach. {rec}. Let's turn it around."],
    },
    "rival_week": {
        "default": ["It's {opp} week. You know what this game means here. I don't need to say more.",
                    "{opp} this Saturday. Nobody in this state will remember our record if we win this one."],
        "traditionalist": ["{opp} week. This is the game. Win it, and you'll have all the rope you need.",
                           "Beat {opp}. Everything else is secondary this week."],
    },
    "cold_seat": {
        "default": ["Just wanted to say — the program's in a great place. Keep it rolling.",
                    "People around here are excited about football again. That's on you, Coach."],
    },
}


def _voice(team, kind, rng, **kw):
    style = team.ad.get("style", "default")
    pool = AD_VOICE[kind].get(style) or AD_VOICE[kind]["default"]
    return rng.choice(pool).format(**kw)


# Legacy: how the AD took a reply in saves from before choices had effects.
AD_REPLY_EFFECT = {
    "accountable": {"default": -1, "win_now": -2, "politician": -1},
    "process":     {"default": 0, "patient": -2, "analytics": -2, "turnaround": -1, "win_now": 3, "politician": 2,
                    "booster": 2},
    "fire":        {"default": 0, "politician": -2, "booster": -2, "big_game": -1, "patient": 1, "analytics": 1},
    "thanks":      {"default": -1},
    "ask_help":    {"default": 1, "budget": 3, "patient": 0, "recruiting": -1},
}

# The AD's taste, as seat changes (negative = he liked it).
PROCESS = {"default": 0, "patient": -2, "analytics": -2, "turnaround": -1, "recruiting": -1,
           "win_now": 3, "politician": 2, "booster": 2, "big_game": 1}
ASK_SEAT = {"default": 1, "budget": 3, "patient": 0, "recruiting": -1, "booster": 0, "brand": 0}
ASK_MONEY = {"default": 150_000, "budget": 0, "booster": 350_000, "win_now": 200_000, "brand": 250_000,
             "patient": 100_000, "recruiting": 250_000}
SWAGGER = {"default": 0, "politician": -1, "brand": -1, "booster": -1, "big_game": -1, "patient": 1,
           "traditionalist": 1, "budget": 1}
HEADLINES = {"default": 0, "brand": 1, "politician": 1, "booster": 1}          # he wants you out front


def _ask(league, team, money, seat, what):
    """Asking your AD for money. Every ask this season gets you less and costs you more."""
    n = team.__dict__.get("_fx_asks", {}).get(league.year, 0)
    import ad_trust
    import skills
    boost = 1.25 if skills.team_has(team, "booster_circuit") else 1.0          # Booster Circuit (coaching tree)
    m = int(round(by_ad(team, money) / (1 + n) * ad_trust.money_factor(league.user_coach, team) * boost / 5000) * 5000)
    return {"money": m, "seat": by_ad(team, seat) + n, "ask": True, "money_what": what,
            **({"notes": [(False, f"you've asked {n} time{'s' if n != 1 else ''} already this year")]} if n else {})}


def _ad_sender(team):
    import ad_trust
    coach = team.coach
    if coach is not None and "ad_trust" in coach.__dict__:
        v = ad_trust.get(coach, team)
        return f"AD {team.ad['name']}", f"Athletic Director · trust {v:.0f} ({ad_trust.word(v)})"
    return f"AD {team.ad['name']}", "Athletic Director"


# ═══ Writing the week's messages ════════════════════════════════════════════

@moments.moment("mail")
def weekly(league):
    """Everyone who has something to say this week. Called once per week before your game."""
    if not _career(league):
        return
    key = (league.year, league.week)
    if league.__dict__.get("_people_week") == key:
        return
    league._people_week = key
    team = league.user_coach.team
    rng = random.Random(f"people:{league.seed}:{league.year}:{league.week}")
    import ad_trust
    ad_trust.record(league.user_coach, team, league)          # your AD starts keeping score
    import skills
    skills.milestones(league)                                  # career wins earn skill points
    _expire(league)
    fx.after_game_rolls(league)
    fx.settle(league)
    import inbox_scenarios as more
    if league.week == 0:
        _preseason(league, team, rng)
        _preseason_more(league, team, rng)
        more.preseason(league, team, rng)
        return
    _from_ad(league, team, rng)
    _from_players(league, team, rng)
    _from_recruits(league, team, rng)
    _from_staff(league, team, rng)
    _season_beats(league, team, rng)
    more.weekly(league, team, rng)
    import compliance_events
    compliance_events.inbox(league, team, rng)         # a shortcut, offered
    try:
        import depth_staff
        depth_staff.maybe_suggest(league, team)
    except Exception:
        pass
    import december
    december.inbox(league, team, rng)


def _score(g, team):
    opp = g.opponent_of(team)
    return f"{g.score_for(team)}-{g.score_for(opp)}", opp


def _loss_options(league, team, opp_school=None):
    """What you tell an AD who's unhappy. Every one of these costs something."""
    rival = _rival(team)
    opts = [
        ("That's on me. We'll fix it this week.",
         {"seat": by_ad(team, {"default": -1, "win_now": -2, "politician": -2}), "chem": 1,
          "stake": {"on": "next", "hint": "lose the next one and he remembers you said it",
                    "win": {"seat": -1}, "loss": {"seat": 2},
                    "who": _ad_sender(team)[0], "subject": "You said you'd fix it",
                    "wtext": "You said you'd fix it, and you did. That's what I needed to see.",
                    "ltext": "You told me it was on you and you'd fix it. Then we lost again. I'm writing it down."}},
         "He appreciates a coach who doesn't hide. He also heard you promise a fix."),
        ("Trust the process. We're building something.",
         {"seat": by_ad(team, PROCESS), "chem": 2},
         "The players like that you didn't panic. How your AD took it depends on who he is."),
        ("The roster isn't there yet. I need more support.",
         {**_ask(league, team, ASK_MONEY, ASK_SEAT, "the AD found more for football"), "chem": -2},
         "You asked for help. The players heard you blame the roster."),
        ("Full pads this week. They'll feel it.",
         {"seat": by_ad(team, {"default": -1, "patient": 0, "analytics": 1}), "focus": "physical", "chem": -2},
         "Practice is on the calendar in full pads. The room grumbles; the AD sees a response."),
    ]
    return opts


def _from_ad(league, team, rng):
    import carousel as cz
    coach = league.user_coach
    ad, role = _ad_sender(team)
    last = _last_game(league, team)
    nxt = _next_game(league, team)
    seat = getattr(coach, "seat", 30)
    line = cz.fire_line(team)
    rival = _rival(team)
    if last is not None and last.week == league.week:
        score, opp = _score(last, team)
        won = last.winner is team
        ranked = getattr(last, "ranks", {}).get(opp)
        xp = cz.win_prob(team, opp, 0 if last.neutral else (1 if last.home is team else -1), league)
        if not won and (xp >= 0.6 or rival == opp.school):
            import ad_trust
            choice(league, ad, role, f"About {opp.school}",
                   _voice(team, "after_bad_loss", rng, score=score, opp=opp.school, rec=team.record)
                   + ad_trust.voice(coach, team, bad=True),
                   _loss_options(league, team), color=C.BRED,
                   silence={"seat": 1}, silence_text="He noticed you never called back.")
            return
        if won and (ranked or xp <= 0.4 or rival == opp.school):
            import ad_trust
            choice(league, ad, role, f"{opp.school}!",
                   _voice(team, "after_big_win", rng, score=score, opp=opp.school, rec=team.record)
                   + ad_trust.voice(coach, team, bad=False),
                   [("The players earned it. They get Sunday off.", {"chem": 3, "lift": -0.15},
                     "The room loves it. A day off costs a little prep."),
                    ("We're just getting started.",
                     {"seat": by_ad(team, SWAGGER), "recruits": 1.5,
                      "stake": {"on": "season", "need": "winning", "hint": "a winning season (overall)",
                                "win": {}, "loss": {"seat": 2}, "who": ad, "subject": "Just getting started?",
                                "wtext": "You said we were just getting started. You backed it up.",
                                "ltext": "You told me we were just getting started. The finish didn't match the talk."}},
                     "Recruits love the swagger. Your AD will hold you to it."),
                    ("Use the momentum — can recruiting get a bigger budget?",
                     _ask(league, team, {"default": 120_000, "budget": 40_000, "booster": 250_000, "recruiting": 200_000},
                          {"default": 1, "budget": 2, "booster": -1, "recruiting": -1, "brand": -1},
                          "a bump after a big win"),
                     "You struck while the iron was hot. Some ADs like that more than others."),
                    ("Film Monday like we lost.", {"lift": 0.2, "chem": -1},
                     "Nobody enjoys a Monday like that. They'll be sharp Saturday.")],
                   color=C.BGREEN)
            return
    if nxt is not None and rival == nxt.opponent_of(team).school:
        o = nxt.opponent_of(team).school
        choice(league, ad, role, "Rivalry week",
               _voice(team, "rival_week", rng, opp=o, score="", rec=team.record),
               [("We'll be ready. Circle it.",
                 {"lift": 0.15, "opp_lift": 0.1,
                  "stake": {"on": "vs", "opp": o, "hint": f"the {o} game, both ways",
                            "win": {"seat": -2}, "loss": {"seat": 2}, "who": ad, "subject": f"{o}",
                            "wtext": f"You said you'd be ready for {o}. You were. Enjoy this one.",
                            "ltext": f"You told me you'd be ready for {o}. We weren't."}},
                 "He'll remember what you said either way."),
                ("It's one game. We treat it like any other.",
                 {"chem": 1, "clutch": 0.2, "seat": by_ad(team, {"default": 1, "traditionalist": 2, "politician": 2,
                                                                 "patient": 0, "analytics": -1})},
                 "Your players stay loose. Some ADs hate hearing it's 'any other game.'"),
                ("Open Wednesday's practice to the boosters and recruits.",
                 {"recruits": 2, "money": 60_000, "lift": -0.15, "money_what": "rivalry-week practice donors"},
                 "The Club loves it and so do the recruits. Practice is a little less sharp.")],
               color=C.BYELLOW)
        return
    if seat >= line - 12 and team.losses >= 2 and team.losses >= team.wins - 1 and rng.random() < 0.6:
        opts = _loss_options(league, team)[:2]
        if rival and not any(g.played for g in league.team_games(team) if g.opponent_of(team).school == rival):
            opts.append(("Judge me after the rivalry game.",
                         {"seat": -3, "stake": {"on": "vs", "opp": rival, "hint": f"your job, more or less, on {rival}",
                                                "win": {"seat": -3}, "loss": {"seat": 7}, "who": ad,
                                                "subject": f"After {rival}",
                                                "wtext": f"You asked me to judge you after {rival}. I have. We're good.",
                                                "ltext": f"You asked me to judge you after {rival}. I have."}},
                         "He'll give you until then. Then he'll grade you on it."))
        opts.append(("I'm shaking up the depth chart. Jobs are open.",
                     {"lift": 0.2, "chem": -3, "seat": -1},
                     "Practice gets a jolt. So does the locker room."))
        import ad_trust
        choice(league, ad, role, "We need to talk",
               _voice(team, "hot_seat", rng, rec=team.record, opp="", score="") + ad_trust.voice(coach, team),
               opts, color=C.BRED,
               silence={"seat": 2}, silence_text="You didn't answer your AD on the hot seat. He noticed.")
    elif seat <= 15 and team.wins >= 3 and rng.random() < 0.25:
        coord = getattr(team, "oc", None) or getattr(team, "dc", None)
        choice(league, ad, role, "Keep it rolling",
               _voice(team, "cold_seat", rng, rec=team.record, opp="", score=""),
               [("Appreciate it. The staff deserves the credit.",
                 {"coord": coord, "stay": -1, "chem": 1} if coord else {"chem": 1},
                 "Word gets back to your staff. They like working for you."),
                ("Then let's invest while it's good — more for recruiting.",
                 _ask(league, team, {"default": 150_000, "budget": 50_000, "booster": 250_000},
                      {"default": 1, "budget": 2, "booster": -1, "recruiting": -1}, "invested while it was good"),
                 "He'll find some money. He also noticed you asked."),
                ("We haven't done anything yet. Keep the pressure on.",
                 {"lift": 0.15, "chem": -1, "seat": by_ad(team, {"default": 0, "win_now": -1, "big_game": -1})},
                 "The staff sets a harder tone this week.")],
               color=C.BGREEN)


def _from_players(league, team, rng):
    from portal import STARTER_DEPTH
    # A buried player who thinks he should be playing.
    cands = []
    for p in team.roster:
        if p.year < 1 or getattr(p, "inj_games", 0) or getattr(p, "promise", None) is not None:
            continue
        room = team.players_at(p.position)
        n = STARTER_DEPTH.get(p.position, 2)
        if p in room[n:n + 2] and room[n - 1].overall - p.overall <= 3:
            weight = 1 + ("mercenary" in p.traits) * 2 + ("impatient" in p.traits) * 2 + (p.hs_stars >= 4)
            cands.append((weight, p))
    asked = league.__dict__.setdefault("_asked_players", set())
    cands = [(w, p) for w, p in cands if id(p) not in asked]
    if cands and rng.random() < 0.45:
        _, p = max(cands, key=lambda x: (x[0], x[1].overall))
        asked.add(id(p))
        starter = team.players_at(p.position)[0]
        body = rng.choice([
            "Coach, can we talk? I've been working every day. I think I'm better than what I'm getting.",
            "I'm not trying to cause problems. I just came here to play, and I'm not playing.",
            "Coach, my family keeps asking why I'm not on the field. I don't have an answer for them."])
        import morale
        mv = morale.get(p)
        choice(league, f"{p.position} {p.name}", f"{p.class_label} · {__import__('scout').ovr_tag(p)} · backup · morale {mv:.0f} "
               f"({morale.word(mv)})", "Playing time", body,
               [("You'll get more snaps. You have my word.",
                 {"who": p, "promise": "made", "also": {"who": starter, "chem": -1}},
                 f"{p.first_name} lights up. He'll stay patient — if he's in the rotation by season's end. "
                 f"Break it and he's very likely in the portal. {starter.first_name} heard about it, too."),
                ("Keep competing. Earn it in practice.",
                 {"chem": 1, "gamble": [(0.65, {}, f"{p.first_name} nods. He doesn't love it, but he respects it."),
                                        ({"who": p, "unhappy": True},
                                         f"{p.first_name} goes quiet. He's not sure he believes you.")]},
                 "The room respects a standard."),
                ("Special teams now, and a real shot in the spring.",
                 {"who": p, "promise": "role", "dev": 1.12, "lift": -0.05},
                 f"{p.first_name} takes the role. Spring ball becomes his audition."),
                ("Honestly? If you want to play somewhere else, I'll help you find it.",
                 {"who": p, "unhappy": True, "recruits": 1, "chem": 1},
                 f"{p.first_name} is stunned, then grateful. He's probably gone in December — and recruits hear "
                 "you tell kids the truth.")],
               ref=p, color=C.BYELLOW, silence={"who": p, "promise": "ignored"},
               silence_text=f"{p.first_name} noticed you never answered.")
    # A leader, after a bad stretch or a big win.
    last = _last_game(league, team)
    if last is not None and last.week == league.week and rng.random() < 0.5:
        leaders = [p for p in team.roster if "leader" in p.traits or "captain" in p.traits]
        if leaders:
            p = max(leaders, key=lambda x: x.overall)
            won = last.winner is team
            streak = 0
            for g in reversed([g for g in league.team_games(team) if g.played]):
                if (g.winner is team) != won:
                    break
                streak += 1
            if not won and streak >= 2:
                choice(league, f"{p.position} {p.name}", "Team captain", "The locker room",
                       rng.choice(["Coach, the guys are still with you. We just need something to go our way.",
                                   "Nobody's quitting in there. I'll make sure of it."]),
                       [("That means a lot. Lead them this week.", {"chem": 2, "who": p, "bought_in": True},
                         f"{p.first_name} takes it personally, in the best way."),
                        ("I need more from the seniors. Starting with you.", {"lift": 0.15, "chem": -1},
                         "He hears it. So do the other seniors."),
                        ("Call a players-only meeting. No coaches.",
                         {"gamble": [(0.6, {"chem": 5}, "It works. Guys cleared the air."),
                                     ({"chem": -3}, "It got loud. Some things were said that can't be unsaid.")]},
                         "They meet Tuesday night.")],
                       ref=p, color=C.BCYAN)
            elif won and streak >= 3:
                choice(league, f"{p.position} {p.name}", "Team captain", "Momentum",
                       rng.choice(["Coach, this team believes right now. Don't let us get comfortable.",
                                   f"{streak} straight. Keep pushing us — we can take it."]),
                       [("Good. Tuesday's going to be a long one.", {"lift": 0.2, "inj": 1.1, "chem": -0.5},
                         "Long practice. Nobody's comfortable."),
                        ("Enjoy it. We'll lighten Tuesday.", {"chem": 2, "inj": 0.9, "lift": -0.1},
                         "Fresh legs, loose room."),
                        ("Nobody says the word 'streak.' Not once.", {"clutch": 0.25, "chem": -1},
                         "A little superstition, a lot of focus. Some guys think it's too much.")],
                       ref=p, color=C.BGREEN)


def _recruit_first(r):
    return r.first_name if hasattr(r, "first_name") else r.name.split()[0]


def _from_recruits(league, team, rng):
    import finance as fi
    cycle = league.recruiting
    board = [r for r in getattr(team, "recruiting_targets", []) if not r.signed]
    if not board:
        return
    posted = 0
    last = _last_game(league, team)
    # A commit who's wavering.
    for r in board:
        if posted >= 2:
            break
        if r.committed_to is team:
            mine = r.interest.get(team, 0)
            rival = max(((t, v) for t, v in r.interest.items() if t is not team), key=lambda x: x[1], default=(None, 0))
            if rival[0] is not None and mine - rival[1] <= 8:
                nm = _recruit_first(r)
                choice(league, f"{r.stars}★ {r.position} {r.name}", f"committed to you · {r.home_state}",
                       f"{rival[0].school} keeps calling",
                       rng.choice([f"Coach, I'm still with you. But {rival[0].school} won't stop calling and my mom "
                                   f"keeps asking about them.",
                                   f"{rival[0].school} came by the house last night. I just want to know I'm a priority."]),
                       [("You're a priority. Nothing's changed.", {"hours": -1, "recruit": 4, "ref": r},
                         f"{nm} appreciated that."),
                        ("I'll be in your living room this week.", {"hours": -4, "recruit": 9, "ref": r},
                         f"The visit goes great. {nm}'s mom made dinner."),
                        ("I'll have one of our players from back home call you.",
                         {"ref": r, "gamble": [(0.75, {"recruit": 4, "ref": r}, f"They talked for an hour. {nm} feels good."),
                                               ({"recruit": -2, "ref": r}, "It came off scripted. He could tell.")]},
                         "It costs you nothing but a favor."),
                        ("If you're looking around, I need to know now.",
                         {"ref": r, "gamble": [(0.55, {"recruit": 12, "ref": r}, f"{nm} recommits, loudly. He's locked in."),
                                               ({"recruit": -15, "ref": r}, f"{nm} didn't love the ultimatum. "
                                                                             f"{rival[0].school} is closer now.")]},
                         "You forced the issue.")],
                       ref=r, color=C.BYELLOW, silence={"recruit": -3, "ref": r},
                       silence_text=f"{nm} never heard back. {rival[0].school} did call.")
                posted += 1
    # A kid who wants to talk money.
    for r in board:
        if posted >= 2:
            break
        if r.committed_to is None and fi.appetite(r) >= 1.2 and not fi.offer_to(cycle, team, r) \
                and team in r.offers and team in r.top_schools(3):
            m = choice(league, f"{r.stars}★ {r.position} {r.name}", f"{r.home_state} · you're in his top 3",
                       "NIL", rng.choice(["Coach, real talk — has there been any conversation about NIL?",
                                          "My family wants to know what NIL looks like at your place before I visit again."]),
                       [("Let's talk numbers. (make a NIL offer)", {"notes": [(True, "his interest ▲▲ if the number's right"), (False, "uses next year's NIL money")]}, ""),
                        ("We don't lead with money. Come see what we're building.",
                         {"recruit": -3, "ref": r, "recruits": 0.5},
                         "He's not thrilled. The rest of your board likes hearing it."),
                        ("Let's talk after your official visit.",
                         {"recruit": -1, "ref": r, "notes": [(True, "keeps your NIL pool untouched for now")]},
                         "He'll wait. For now.")],
                       ref=r, color=C.BGREEN, silence={"recruit": -2, "ref": r})
            m["nil_key"] = "o0"
            posted += 1
    # A kid reacting to Saturday.
    if last is not None and last.week == league.week and posted < 2:
        watchers = [r for r in board if r.committed_to in (None, team) and r.interest.get(team, 0) >= 25]
        if watchers:
            r = rng.choice(watchers)
            won = last.winner is team
            score, opp = _score(last, team)
            nm = _recruit_first(r)
            body = (rng.choice([f"Watched you guys beat {opp.school} Saturday. That atmosphere was crazy.",
                                f"{score}! My whole family was watching. That's the kind of team I want to be on."])
                    if won else
                    rng.choice([f"Tough one against {opp.school}. You guys will bounce back.",
                                f"Saw the {opp.school} game. What happened in the second half?"]))
            same = [p for p in team.roster if p.position == r.position and p.year >= 1]
            host = max(same, key=lambda p: p.overall, default=None)
            opts = [("Appreciate you watching. We want you here.", {"hours": -1, "recruit": 2, "ref": r},
                     f"{nm} appreciated that."),
                    ("Come to our next home game as my guest.", {"hours": -3, "recruit": 5, "ref": r},
                     f"{nm}'s coming. Sideline passes for the family.")]
            if host is not None:
                opts.append((f"I'll have {host.name} reach out — he plays your spot.",
                             {"ref": r, "gamble": [(0.7, {"recruit": 3, "ref": r}, f"{host.first_name} sold it."),
                                                   ({"recruit": -1, "ref": r},
                                                    f"{host.first_name} was honest about the depth chart. Maybe too honest.")]},
                             "Players recruit players."))
            if not won:
                opts.append(("Honestly? We got outcoached. It won't happen twice.",
                             {"recruit": 3, "ref": r, "seat": by_ad(team, {"default": 0, "politician": 1}),
                              "notes": [(False, "he may repeat it publicly")]},
                             f"{nm} respects the honesty. He posted about it, too."))
            choice(league, f"{r.stars}★ {r.position} {r.name}", f"{r.home_state} · recruit", "Saturday", body,
                   opts, ref=r, color=C.BGREEN if won else C.GRAY)


def _preseason(league, team, rng):
    """Fall camp: the AD sets the tone, a captain checks in."""
    coach = league.user_coach
    ad, role = _ad_sender(team)
    first = coach.hired_year == league.year
    style = team.ad.get("style", "default")
    opener = {"win_now": "I'll keep it simple: we're here to win now.",
              "patient": "Build it the right way. I'm not grading you on September.",
              "booster": "The donors are excited. Let's give them something to be excited about.",
              "budget": "We're doing this within our means. Spend smart.",
              "brand": "I want us on TV, ranked, and relevant.",
              "politician": "The fans are fired up. Let's keep them that way."}.get(style, "Let's have a year.")
    gl = [g.spoken for g in getattr(team, "goals", [])]
    wants = ("I want us to " + ", ".join(gl[:-1]) + (", and " if len(gl) > 2 else " and ") + gl[-1]) if len(gl) > 1 \
        else (f"I want us to {gl[0]}" if gl else "")
    import carousel as cz
    grace = cz.AD_STYLES.get(style, ("", "", {}))[2].get("grace", 2)
    when = (f" I'll hold you to that starting in year {grace + 1} — until then, show me we're headed there."
            if first else "")
    body = (f"{'Welcome aboard, Coach. ' if first else ''}{opener} " + (f"{wants}.{when}" if wants else ""))
    young = sorted((p for p in team.roster if p.year <= 1), key=lambda p: -p.potential)[:3]
    opts = [("We'll meet every one of those.",
             {"seat": -2, "stake": {"on": "season", "need": "winning", "hint": "a winning season (overall)",
                                    "win": {"seat": -2}, "loss": {"seat": 3}, "who": ad, "subject": "What you promised",
                                    "wtext": "You told me in August you'd deliver. You did.",
                                    "ltext": "You told me in August you'd meet every goal. We're not close."}},
             "He likes the certainty. He'll remember it in December."),
            ("We're going to surprise some people.",
             {"recruits": 1.5, "seat": by_ad(team, SWAGGER),
              "stake": {"on": "season", "need": "bowl", "hint": "a bowl game",
                        "win": {"recruits": 1}, "loss": {"seat": 2}, "who": ad, "subject": "The surprise",
                        "wtext": "You said we'd surprise people. We're going bowling.",
                        "ltext": "You said we'd surprise people. We didn't."}},
             "Recruits eat it up. The bar is a bowl game now."),
            (("Year one is about the foundation. Judge the arrow, not the record." if first else
              "The roster's young. I'm playing the long game with it."),
             {"seat": by_ad(team, {"default": 1, "patient": -2, "turnaround": -1, "analytics": -2, "recruiting": -1,
                                   "win_now": 3, "politician": 2, "booster": 2}), "chem": 1,
              "also": [{"who": y, "dev": 1.1} for y in young]},
             "Your young players will get real reps. Some ADs hear that as an excuse.")]
    choice(league, ad, role, f"{league.year}: what I expect", body, opts, color=C.BCYAN,
           due=(league.year, 2))
    import personalities as pz
    # The same leaders the locker room lists (veterans first), so the inbox and the room agree.
    leaders = [p for p in pz.leaders(team) if p.year >= 2] or \
        sorted((p for p in team.roster if p.year >= 2), key=lambda p: (-pz.captain_score(p), -p.overall))
    if leaders:
        p = leaders[0]
        chem_now = pz.chemistry(team)
        tense = chem_now < 42
        tag = "captain" if p in (getattr(team, "captains", None) or []) else "one of your leaders"
        choice(league, f"{p.position} {p.name}", f"{p.class_label} · {tag}", "Camp",
               rng.choice(["Coach, camp's been good, but not everybody's bought in yet. Some guys are waiting to see "
                           "if this is for real. Winning early would help.",
                           "We've got some guys to win over. I'm working on it. The young ones are listening."])
               if tense else
               rng.choice(["Coach, camp's been good. Most of the guys are with us — a few are still waiting to see.",
                           "We've been working. The room's getting there. A good start would lock it in.",
                           "Legs are heavy, and not everybody's all the way in yet. We'll be ready for Week 1."])
               if chem_now < 55 else
               rng.choice(["Coach, camp's been good. The young guys are learning fast.",
                           "We've been working. Everybody's bought in. Let's go get it.",
                           "Legs are heavy, but the room's together. We'll be ready for Week 1."]),
               [("Two more hard days, then we taper.", {"lift": 0.3, "inj": 1.15, "chem": -2},
                 "They'll be sharp for the opener — and sore."),
                ("Give them a day off. They've earned it.", {"chem": 4 if tense else 3, "lift": -0.15},
                 "The room exhales."),
                ("You and the leaders run Thursday's practice.",
                 {"gamble": [(0.6, {"chem": 5 if tense else 4, "who": p, "bought_in": True},
                              "It was the best practice of camp. The players own this team now."),
                             ({"chem": -1, "lift": -0.2}, "It got sloppy. Good intentions, bad practice.")]},
                 "A risk, and a statement.")],
               ref=p, color=C.BGREEN, due=(league.year, 1))


# ═══ More mail: camp, the opener, the long middle, and the end ══════════════

def _leader(team, pos=None):
    pool = [p for p in team.roster if p.year >= 2 and (pos is None or p.position == pos)]
    return max(pool, key=lambda p: p.overall, default=None)


def _preseason_more(league, team, rng):
    """August: the coordinators' camp reports, media day, the boosters, the circled game.
    Posted media day first so the inbox (newest on top) reads the staff's notes before it."""
    oc, dc = getattr(team, "oc", None), getattr(team, "dc", None)
    qbs = sorted(team.players_at("QB"), key=lambda p: -p.overall)[:2]
    battle = len(qbs) == 2 and qbs[0].overall - qbs[1].overall <= 5
    qb_topic = (f"the {qbs[0].last_name}-{qbs[1].last_name} quarterback battle" if battle else
                f"{qbs[0].name}'s {'senior year' if qbs[0].year >= 3 else 'year'} at quarterback" if qbs else
                "the quarterback room")
    due = (league.year, 1)
    # the young star the cameras want: the best freshman or sophomore with some buzz
    young = max((p for p in team.roster if p.year <= 1 and p.hs_stars >= 3), key=lambda p: (p.hs_stars, p.overall),
                default=None)
    choice(league, f"{team.school} Communications", "Sports Information", "Media day schedule",
           f"Media day is Tuesday. Local TV, the beat writers, and the conference network. They'll ask about "
           f"{'the new era' if league.user_coach.hired_year == league.year else 'last year'}, {qb_topic}, "
           "and the opener. How much of the building do you want in front of the cameras?",
           [("Full access: me, both coordinators, and our best players.",
             {"recruits": 2, "lift": -0.1, "seat": -by_ad(team, HEADLINES)},
             "Great coverage. A long day away from the game plan."),
            ("Thirty minutes at the podium and out. We're game-planning.",
             {"lift": 0.15, "recruits": -0.5, "seat": by_ad(team, HEADLINES)},
             "The staff gets the afternoon back. The coverage is thin."),
            ("Just me and the seniors. It's their year.",
             {"chem": 2, "recruits": 0.3, "seat": by_ad(team, {"default": 0, "brand": 1}),
              **({"who": young, "morale": -5} if young is not None else {})},
             "The seniors love it." + (f" {young.first_name} {young.last_name}, the {young.hs_stars}-star "
                                       f"{young.class_label.lower().replace('rs-', 'redshirt ')} the cameras wanted, "
                                       "stays in the film room — and noticed." if young is not None else ""))],
           color=C.GRAY, due=due)
    if dc is not None:
        import finance as f_
        k = f_.contract(dc)
        new_here = k is not None and k.get("start", 0) >= league.year
        front = [p for p in team.roster if p.position in ("DL", "LB")]
        best = max(front, key=lambda p: p.overall, default=None)
        corners = sorted((p for p in team.roster if p.position == "CB"), key=lambda p: -p.overall)
        thin = len(corners) < 3 or corners[2].overall < corners[0].overall - 10
        worry = "Depth at corner is my worry." if thin else "The back end is further along than I expected."
        faster = "We're faster than the tape I watched from last year." if new_here else "We're faster than last year."
        body = rng.choice([f"{faster} {best.name if best else 'The front'} has been unblockable in team periods. {worry}",
                           (f"Tackling's been good. Communication on the back end still isn't where I want it. {worry}"
                            if thin else f"Tackling's been good, and the communication on the back end is sharp. {worry}"),
                           f"I like this group's edge. {best.first_name if best else 'The front'} and the linebackers "
                           f"are setting the tone every morning. {worry}"])
        if thin:
            young_cb = [p for p in corners if p.year <= 1][:2]
            import playbook as _pb
            import staff as _sf
            _calls = _pb.DEFENSE_SCHEMES.get(_sf.play_caller(team, "def").defense_scheme, {})
            from career import MAN_CALLS as _MAN
            dc_zone = sum(v for k, v in _calls.items() if k not in _MAN) / (sum(_calls.values()) or 1) >= 0.8
            opts = [("Corners go to the top of the recruiting board.",
                     {"priority": "CB", "recruits": -0.5, "notes": [(False, "other positions slide on your board")]},
                     "Corners are flagged as a staff priority. The rest of the board slides a little."),
                    ("Live press reps every day for the young corners.",
                     {"inj": 1.15, "also": {"who": young_cb[0], "dev": 1.15} if young_cb else {},
                      },
                     "They'll get beat in practice so they don't get beat in November."),
                    (("Keep it simple — one coverage, no checks. Hide them." if dc_zone else
                      "Play more zone early. Hide them."), {"clutch": -0.1, "lift": 0.1},
                     "Safer on the back end, softer on third down.")]
        else:
            opts = [("Tackle live one more week.", {"lift": 0.25, "inj": 1.15},
                     "They'll be ready to hit somebody else."),
                    ("Back off contact. Save their legs.", {"inj": 0.85, "lift": -0.1, "heal": 2},
                     "Fresh legs for the opener. A little rust."),
                    ("Install the pressure package now.", {"lift": 0.1, "clutch": -0.15},
                     "More pressure, more busts until they learn it.")]
        choice(league, dc.name, "Defensive Coordinator", "Defense after camp", body, opts, color=C.BCYAN, due=due)
    if oc is not None and len(qbs) == 2:
        a, b = qbs
        close = a.overall - b.overall <= 3
        if close:
            body = (f"{a.name} and {b.name} are neck and neck. I lean {a.first_name} — steadier with the ball. "
                    "Your call on whether we name him now or let it play out into the week.")
            opts = [(f"Name {a.first_name}. Let's go.",
                     {"chem": 2, "who": a, "bought_in": True,
                      "gamble": [(0.55, {}, f"{b.first_name} took it like a pro."),
                                 ({"who": b, "unhappy": True}, f"{b.first_name} took it hard. He's quiet.")]},
                     "The room settles. Everybody knows whose team it is."),
                    ("Keep it open through the week.", {"lift": -0.15, "who": b, "bought_in": True, "clutch": -0.1},
                     "Both of them stay hungry. The offense doesn't settle."),
                    ("Rotate them in the opener, series by series.",
                     {"lift": -0.25, "also": {"who": a, "unhappy": True},
                      "gamble": [(0.5, {"who": b, "bought_in": True, "chem": 1}, "The rotation keeps both engaged."),
                                 ({"chem": -2}, "The room splits into camps.")]},
                     "Nobody's happy, nobody's gone. Yet.")]
        else:
            body = (f"{a.name} has separated. {b.first_name}'s handling it — for now. I'd name {a.first_name} today "
                    "and let the room settle.")
            opts = [(f"Name {a.first_name} today.",
                     {"chem": 2, "gamble": [(0.7, {}, f"{b.first_name} handled it."),
                                            ({"who": b, "unhappy": True}, f"{b.first_name} is hurt more than he lets on.")]},
                     "The room settles."),
                    (f"No announcement. {b.first_name} keeps competing.",
                     {"who": b, "bought_in": True, "lift": -0.1},
                     f"{b.first_name} is all in. The offense takes a little longer to settle."),
                    (f"Name {a.first_name}, and build {b.first_name} a package.",
                     {"chem": 1, "who": b, "promise": "role", "lift": -0.05},
                     "A few snaps a game for the backup. Install time is install time.")]
        choice(league, oc.name, "Offensive Coordinator", "QB room after camp", body, opts, ref=a, color=C.BCYAN,
               due=due)
    rival = _rival(team)
    booster = f"{rng.choice(['Frank', 'Dale', 'Carol', 'Walt', 'Linda', 'Ray'])} {rng.choice(['Whitfield', 'Harlan', 'Beaumont', 'Pruitt', 'Kessler', 'Maddox'])}"
    opts = [("I'll be at the Club's kickoff dinner.",
             {"money": by_ad(team, {"default": 100_000, "booster": 175_000, "budget": 60_000}), "lift": -0.1,
              "money_what": "Champions Club kickoff dinner"},
             "You shook every hand in the room. A night away from game-week prep.")]
    if rival:
        opts.append((f"Tell them to have the checkbooks ready for {rival}.",
                     {"stake": {"on": "vs", "opp": rival, "hint": f"the {rival} game",
                                "win": {"money": 250_000, "money_what": f"the Club, after {rival}"},
                                "loss": {"seat": by_ad(team, {"default": 1, "booster": 3, "politician": 2})},
                                "who": booster, "subject": f"After {rival}",
                                "wtext": f"Coach — you said checkbooks. The Club heard you. Beat {rival} and here we are.",
                                "ltext": f"Coach, the Club remembers what you said about {rival}. So does the AD."}},
                     "The Club loved it. They'll love it more if you win."))
    opts.append(("Keep a little distance. The team comes first.",
                 {"lift": 0.1, "chem": 1, "seat": by_ad(team, {"default": 0, "booster": 2, "big_game": 1})},
                 "Your players notice where your time goes. The Club notices too."))
    choice(league, booster, "Booster · Champions Club", "Welcome to the season",
           (f"Coach — the Club's sold out for the year. Everybody's got one date circled: {rival}. "
            "Beat them and the checkbooks open." if rival else
            "Coach — the Club's sold out for the year. Win at home and you'll never pay for dinner in this town."),
           opts, color=C.BYELLOW, due=due)


def _season_beats(league, team, rng):
    """In-season mail that isn't about one game: the opener's aftermath, midseason,
    streaks, the poll, rivalry week, the bye."""
    coach = league.user_coach
    wk = league.week
    last = _last_game(league, team)
    nxt = _next_game(league, team)
    said = league.__dict__.setdefault("_beats", {}).setdefault(league.year, set())

    def once(tag):
        if tag in said:
            return False
        said.add(tag)
        return True

    if wk == 1 and last is not None and last.week == 1 and once("week1"):
        won = last.winner is team
        choice(league, f"Mrs. {rng.choice(['Johnson', 'Alvarez', 'Nguyen', 'Brooks', 'Patel'])}", "A player's mom",
               "First game",
               ("My son called me from the locker room. He said you told them you were proud of them. "
                "Thank you for taking care of our boys." if won else
                "My son called me after. He was down, but he said you told them it was one game. "
                "They believe in you. So do we."),
               [("Call her back personally.", {"hours": -1, "recruits": 1.5},
                 "Moms talk to moms. Recruits' families hear about it."),
                ("Invite the families to Tuesday's practice.", {"chem": 2, "lift": -0.1},
                 "The players love it. Practice is a little less focused."),
                ("Start a family section at every home game.",
                 {"money": -40_000, "chem": 2, "recruits": 1, "money_what": "family section tickets"},
                 "It costs real money. It's the kind of thing people remember.")],
               color=C.BMAGENTA)
        cap = _leader(team)
        if cap is not None:
            if won:
                opts = [("Hard film Monday. Nobody's satisfied.", {"lift": 0.2, "chem": -1},
                         "Long film session. Sharp week."),
                        ("Enjoy it tonight. Back to work Monday.", {"chem": 2, "lift": -0.05},
                         "The room's loose."),
                        ("You run film with the leadership group.",
                         {"gamble": [(0.65, {"chem": 3, "clutch": 0.1, "who": cap, "bought_in": True},
                                      "They were harder on each other than you would've been."),
                                     ({"lift": -0.15}, "It turned into a highlight session.")]},
                         "Their team, their film room.")]
            else:
                opts = [("Film Monday. Every snap, every mistake.", {"lift": 0.25, "chem": -2},
                         "Nobody enjoyed it. Everybody learned from it."),
                        ("Burn the tape. New week.", {"chem": 2, "clutch": -0.1},
                         "Fresh start. Some of those mistakes will come back."),
                        ("You tell me what went wrong.",
                         {"gamble": [(0.6, {"chem": 3, "lift": 0.1, "who": cap, "bought_in": True},
                                      f"{cap.first_name} nailed it. You fixed it together."),
                                     ({"chem": -2}, "He named names. It got around.")]},
                         "Players see things coaches don't.")]
            choice(league, f"{cap.position} {cap.name}", f"{cap.class_label} · captain", "Week 1 in the books",
                   ("One down. Guys are hungry for more — nobody's satisfied with that film." if won else
                    "We know. We'll fix it. The room's together — I promise you that."),
                   opts, ref=cap, color=C.BGREEN)
    if wk >= 1 and once("captains"):
        _captain_vote(league, team)
    if wk == 6 and once("midseason"):
        exp = ""
        try:
            import carousel as cz
            xw, n = cz.expectation(league, team, coach)
            exp = f" The numbers had us at about {xw:.0f} win{'s' if round(xw) != 1 else ''} by now; we're at {team.wins}."
        except Exception:
            pass
        ad, role = _ad_sender(team)
        choice(league, ad, role, "Halfway point",
               f"Six games in. You're {team.record}.{exp} Let's talk about the stretch run — "
               "I want to know what you need.",
               [("We'll get to a bowl. That's on me.",
                 {"seat": -2, "stake": {"on": "season", "need": "bowl", "hint": "a bowl game",
                                        "win": {"seat": -1}, "loss": {"seat": 3}, "who": ad,
                                        "subject": "The bowl you promised",
                                        "wtext": "You said we'd get to a bowl. We did.",
                                        "ltext": "You told me at midseason we'd get to a bowl."}},
                 "He'll hold you to six."),
                ("We're building. The second half will show it.", {"seat": by_ad(team, PROCESS), "chem": 1},
                 "Depends who you're talking to."),
                ("More support for the staff would help.",
                 _ask(league, team, ASK_MONEY, ASK_SEAT, "midseason ask"),
                 "He heard the ask."),
                ("I'm shifting staff time to next year's class.",
                 {"recruits": 2.5, "season_lift": -0.05,
                  "seat": by_ad(team, {"default": 1, "recruiting": -2, "analytics": -1, "win_now": 3})},
                 "The class gets more attention. Every Saturday gets a little less.")],
               color=C.BCYAN)
    streak = 0
    for g in reversed([x for x in league.team_games(team) if x.played]):
        if g.winner is team:
            break
        streak += 1
    if streak == 3 and once(f"skid{wk}"):
        cap = _leader(team)
        if cap is not None:
            trouble = [p for p in team.roster if any(t in ("diva", "hothead", "mercenary", "headcase") for t in p.traits)]
            culprit = max(trouble, key=lambda p: p.overall, default=None)
            opts = [("I'll address the whole team first thing. Hard truths.",
                     {"gamble": [(0.6, {"chem": 4, "lift": 0.1}, "It landed. They practiced angry."),
                                 ({"chem": -3}, "Some of them tuned you out.")]},
                     "You said what needed saying."),
                    ("You lead it. They'll follow you.", {"chem": 2, "who": cap, "bought_in": True},
                     f"{cap.first_name} takes the room."),
                    ("Cancel Tuesday. Take them bowling.", {"chem": 5, "lift": -0.25},
                     "Nobody talked football. Everybody laughed. You lost a practice.")]
            if culprit is not None:
                opts.append((f"Anybody not bought in sits. Starting with {culprit.first_name}.",
                             {"lift": 0.3, "chem": -2, "who": culprit, "unhappy": True},
                             f"Message sent. {culprit.first_name} got it loud and clear."))
            choice(league, f"{cap.position} {cap.name}", f"{cap.class_label} · captain", "The locker room",
                   "Three straight is weighing on guys. Some of the young ones are checking out. "
                   "Can you talk to the team before Tuesday's practice?", opts, ref=cap, color=C.BGREEN)
    rank = league.rankings.rank_of(team)
    if rank and once("first_ranked"):
        caps = [p for p in (getattr(team, "captains", None) or []) if p in team.roster]
        choice(league, f"{team.school} Communications", "Sports Information", f"No. {rank} in the media poll",
               f"We're ranked No. {rank}. National media requests tripled overnight. The student section wants "
               "to know if you'll come to their tailgate Friday.",
               [("I'll stop by. Tell them to be loud Saturday.", {"recruits": 1.5, "chem": 1, "lift": -0.1},
                 "The students went nuts. Friday's walkthrough was a little rushed."),
                ("No distractions this week.", {"lift": 0.15, "seat": by_ad(team, HEADLINES)},
                 "Locked in. The SID is disappointed."),
                ("Send the captains instead.",
                 {"chem": 1.5, "recruits": 0.5, "who": caps[0], "bought_in": True} if caps else {"chem": 1.5, "recruits": 0.5},
                 "The captains loved it.")],
               color=C.GRAY)
    if nxt is not None:
        import carousel as cz
        opp = nxt.opponent_of(team)
        home = nxt.home is team and not nxt.neutral
        if (cz.PRIMARY_RIVAL.get(team.school) == opp.school or cz.PRIMARY_RIVAL.get(opp.school) == team.school) \
                and once("rivalry"):
            choice(league, f"{team.school} Student Section", "Student government", f"{opp.school} week",
                   f"We're painting the whole student section. Anything you want the players to see when they walk out "
                   f"against {opp.school}?",
                   [("Just be loud from the first snap.", {"lift": 0.15 if home else 0.05},
                     "Simple. It'll help" + (" — a lot, at home." if home else ", a little, on the road.")),
                    (f"Put last year's {opp.school} score on the wall.", {"lift": 0.25, "opp_lift": 0.2},
                     "Everybody's fired up. Everybody."),
                    ("Put the seniors' names on the banner.", {"chem": 2.5},
                     "The seniors saw it before practice. A few of them teared up.")],
                   color=C.BMAGENTA)
        if nxt.week - league.week >= 2 and wk <= 12 and once(f"bye{wk}"):
            dc = getattr(team, "dc", None)
            young = sorted((p for p in team.roster if p.year == 0), key=lambda p: -p.potential)[:1]
            choice(league, dc.name if dc else "Staff", "Staff", "Bye week plan",
                   f"Bye week. How do you want to use it before {opp.school}?",
                   [("Vets get Monday and Tuesday off. The young guys work.",
                     {"heal": 2, "chem": 1, "lift": -0.1, "also": {"who": young[0], "dev": 1.1} if young else {}},
                     "Bodies heal. The freshmen get real reps."),
                    ("Everybody practices. We need it.", {"lift": 0.3, "inj": 1.1, "chem": -1},
                     "Two extra padded practices. Nobody's thrilled."),
                    ("Whole staff on the road Thursday and Friday.", {"hours": 12, "lift": -0.1},
                     "A dozen living rooms in two days.")],
                   color=C.BCYAN)


def _captain_vote(league, team):
    """The team voted in August. You can take the vote, add a captain, or overrule it."""
    import morale
    import personalities as pz
    caps = [p for p in (getattr(team, "captains", None) or []) if p in team.roster]
    if not caps:
        return
    starters = {p for grp in team.starters().values() for p in grp}
    pool = sorted((p for p in team.roster if p not in caps and p.year >= 1 and p in starters),
                  key=lambda p: -(pz.captain_score(p) + morale.get(p) * 0.2))
    pick = pool[0] if pool else None
    weak = min(caps, key=lambda p: (not any(t in morale.WILD for t in p.traits), morale.get(p)))
    names = ", ".join(f"{p.position} {p.name} ({morale.get(p):.0f})" for p in caps)
    opts = [("Good vote. They're your captains.",
             {"chem": 2, "also": [{"who": p, "morale": 4, "quiet": True, "why_mood": "you backed the captains vote"} for p in caps],
              "notes": [(True, "the captains' morale ▲")]},
             "The room likes that you trusted them.")]
    if pick is not None:
        opts.append((f"Add a fourth captain: {pick.position} {pick.name}.",
                     {"who": pick, "morale": 12, "add_captain": True, "chem": -1, "why_mood": "named a captain",
                      "notes": [(True, "a leader with a say in the room pulls it his way")]},
                     f"{pick.first_name} is a captain. A few guys wonder why the vote wasn't enough."))
        if weak is not None and (any(t in morale.WILD for t in weak.traits) or morale.get(weak) < 50):
            opts.append((f"Overrule it: {weak.last_name} out, {pick.last_name} in.",
                         {"who": pick, "morale": 12, "add_captain": True, "chem": -4, "why_mood": "named a captain",
                          "also": {"who": weak, "morale": -20, "drop_captain": True, "why_mood": "stripped of the C"}},
                         f"You overruled the players. {weak.first_name} took it hard; {pick.first_name} "
                         "has the C now."))
    choice(league, "Director of Football Operations", "Staff", "The captains vote",
           f"The team voted: {names}. Captains pull the whole locker room toward their own mood — "
           "a happy captain lifts it, an unhappy one drags it. Your call on whether the vote stands.",
           opts, color=C.BCYAN)


def season_end(league):
    """After the last game: the AD's year-end review, the seniors, the staff, signing day."""
    if not _career(league):
        return
    key = league.year
    if league.__dict__.get("_people_end") == key:
        return
    league._people_end = key
    team = league.user_coach.team
    rng = random.Random(f"people-end:{league.seed}:{league.year}")
    fx.settle(league, season_over=True)
    import skills
    skills.season_review(league)                         # the season's skill points
    import ad_trust
    ad_trust.new_season(league)                          # last year's goodwill fades toward neutral
    import carousel as cz
    met = []
    for g in getattr(team, "goals", []):
        try:
            st, _ = cz.goal_status(team, league.user_coach, g, league.year)
            met.append(f"{g.short}: {'met' if st == 'met' else 'missed' if st == 'failed' else 'still open'}")
            import ad_trust
            if st == "met":
                ad_trust.change(league, 8, f"met a goal: {g.short.lower()}")
            elif st == "failed":
                ad_trust.change(league, -6, f"missed a goal: {g.short.lower()}")
        except Exception:
            pass
    seat = getattr(league.user_coach, "seat", 30)
    tone = ("You've got my full support going into next year." if seat < 40 else
            "We need to see real progress next season." if seat < 65 else
            "I'll be honest with you: next year has to be different.")
    ad, role = _ad_sender(team)
    oc, dc = getattr(team, "oc", None), getattr(team, "dc", None)
    worst = None
    try:
        import staff
        worst = min((c for c in (oc, dc) if c is not None),
                    key=lambda c: staff.resume_score(c), default=None)
    except Exception:
        worst = None
    opts = [("Understood. The work starts now.", {"seat": -1, "chem": -1},
             "He likes it. Your players are about to find out what 'now' means."),
            ("We're closer than the record says.", {"seat": by_ad(team, PROCESS), "recruits": 1},
             "Recruits like the optimism. Your AD grades it by his own taste."),
            ("I'll need more resources to get there.",
             _ask(league, team, ASK_MONEY, ASK_SEAT, "year-end ask"),
             "He heard you.")]
    if worst is not None and seat >= 40:
        opts.append((f"I'm going to look hard at my staff.",
                     {"seat": -2, "coord": worst, "stay": 1, "chem": -1},
                     f"He likes accountability. {worst.name} heard about it by lunch."))
    choice(league, ad, role, f"{league.year} in review",
           f"The season's over at {team.record}. " + ("Goals: " + "; ".join(met) + ". " if met else "") + tone,
           opts, color=C.BCYAN)
    seniors = sorted((p for p in team.roster if p.year >= 3), key=lambda p: -p.overall)[:1]
    for p in seniors:
        young = sorted((q for q in team.roster if q.position == p.position and q.year <= 1),
                       key=lambda q: -q.potential)
        opts = [("Stay on as a graduate assistant.", {"money": -40_000, "chem": 2, "recruits": 1,
                                                      "money_what": f"GA spot for {p.name}"},
                 "He said yes before you finished the sentence."),
                ("Host our official visits this winter.", {"recruits": 2},
                 "Recruits will hear it from somebody who lived it.")]
        if young:
            opts.append((f"Spend a week with {young[0].first_name} before you go.",
                         {"who": young[0], "dev": 1.15, "chem": 1},
                         f"{young[0].first_name} gets a masterclass at his position."))
        choice(league, f"{p.position} {p.name}", f"{p.class_label} · senior", "Thank you, Coach",
               rng.choice(["I came here a kid. I'm leaving a man. Thank you for everything.",
                           "Whatever's next for me, I'll always be one of yours. Thank you.",
                           "Four years went fast. Take care of the young guys for me."]),
               opts, ref=p, color=C.BGREEN)
    try:
        n, r = len(league.recruiting.commitments(team)), league.recruiting.class_rank(team)
    except Exception:
        n, r = 0, None
    choice(league, "Recruiting Office", "Director of Recruiting", "Signing day is coming",
           f"We're at {n} commit{'s' if n != 1 else ''}" + (f", ranked No. {r} nationally" if r else "")
           + ". The dead period ends soon — this is when classes are won or lost. Who do you want on the road?",
           [("Everybody. Every staffer, every living room.", {"hours": 12, "chem": -1.5},
             "Your players won't see a coach for two weeks."),
            ("Focus on our top five targets.", {"top": (5, 6)},
             "Five kids get everything you've got."),
            ("Go flip some commits.", {"flip": (4, 5), "seat": by_ad(team, {"default": 0, "traditionalist": 1}),
                                       "notes": [(True, "4 kids committed elsewhere warm up")]},
             "Other schools' commits are fair game until they sign.")],
           color=C.BYELLOW)
    if oc is not None:
        import staff
        if staff.buzz_score(oc) >= 7:
            choice(league, oc.name, "Offensive Coordinator", "A heads-up",
                   "A couple of schools have called about their head job. I wanted you to hear it from me first. "
                   "Nothing's decided — I love it here.",
                   [("Go get what you've earned.", {"coord": oc, "stay": 1, "chem": 1, "recruits": 1},
                     "He's grateful. Recruits hear your assistants become head coaches."),
                    ("We'd hate to lose you — I'll get you a raise.",
                     {"coord": oc, "stay": -1, "money": -150_000, "money_what": f"raise for {oc.name}"},
                     "He's moved. The money comes out of next year's pool."),
                    ("Hear them out, but talk to me before you decide.",
                     {"gamble": [(0.5, {"coord": oc, "stay": -1}, "He appreciated the respect."),
                                 ({"coord": oc, "stay": 1}, "He took it as permission.")]},
                     "Honest, and a little risky.")],
                   color=C.BCYAN)
    import inbox_scenarios as more
    more.season_end(league, team, rng)


FOCUS_FROM_FILM = {"turnovers": "ball security", "third": "situational football", "run_d": "physical",
                   "pass_d": "coverage", "run_o": "physical", "rest": "rest"}


def film_notes(league, team, g):
    """What the film says about a game: (note, suggested practice focus)."""
    if g is None or not getattr(g, "box", None):
        return []
    sim = g.box
    opp = g.opponent_of(team)
    ts, os_ = sim.team_stats.get(team, {}), sim.team_stats.get(opp, {})
    notes = []
    if ts.get("turnovers", 0) >= 2:
        notes.append((f"{ts['turnovers']} turnovers. That's the game — or close to it.", "ball"))
    if ts.get("third_att", 0) >= 8 and ts.get("third_conv", 0) / ts["third_att"] < 0.35:
        notes.append((f"{ts['third_conv']} of {ts['third_att']} on third down. We can't stay on the field.", "situational"))
    if os_.get("rush_yds", 0) >= 200:
        notes.append((f"They ran for {os_['rush_yds']}. We got pushed around up front.", "physical"))
    if ts.get("rush_yds", 0) < 80:
        notes.append((f"Only {ts.get('rush_yds', 0)} rushing yards. We were one-dimensional.", "physical"))
    if os_.get("pass_yds", 0) >= 320:
        notes.append((f"{os_['pass_yds']} passing yards allowed. Our coverage has to be better.", "gameplan"))
    if not notes:
        won = g.winner is team
        notes.append(("Clean game. Nothing jumps off the tape." if won else
                       "No one thing lost it — a little bit of everything.", "balanced"))
    return notes


def _from_staff(league, team, rng):
    last = _last_game(league, team)
    if last is None or last.week != league.week:
        return
    notes = film_notes(league, team, last)
    if not notes:
        return
    note, focus = notes[0]
    if focus == "balanced":
        return                                            # nothing worth a message
    oc = getattr(team, "oc", None)
    dc = getattr(team, "dc", None)
    defensive = focus in ("physical",) and "They ran" in note or "coverage" in note
    who = dc if defensive and dc is not None else oc if oc is not None else dc
    if who is None:
        return
    role = "Defensive Coordinator" if who is dc else "Offensive Coordinator"
    import week as wk
    label = wk.FOCUS.get(focus, wk.FOCUS["balanced"])[0]
    opts = [(f"Agreed — {label.lower()} all week.",
             {"focus": focus, "notes": [wk.FOCUS[focus][1]], "coord": who, "stay": -1},
             f"It's on the practice plan. {who.name.split()[-1]} likes being heard.")]
    if focus != "rest":
        opts.append(("Rest them. Legs matter more right now.", {"focus": "rest", "notes": [wk.FOCUS["rest"][1]]},
                     "Rest week. The problem on film is still there."))
    if focus != "gameplan":
        opts.append(("Scheme around it instead.", {"focus": "gameplan", "notes": [wk.FOCUS["gameplan"][1]],
                                                   "coord": who, "stay": 1 if rng.random() < 0.5 else 0},
                     "Game-plan week. Your coordinator thinks you're dodging the problem."))
    choice(league, who.name, role, "Film review", f"{note} I'd spend this week on it: {label.lower()}.",
           opts, ref=focus, color=C.BCYAN)


# ═══ Answering ══════════════════════════════════════════════════════════════

# What the older, hand-coded replies do — shown as the colored line before you pick.
LEGACY_HINTS = {
    "pers_suspend": [(False, "he misses a game"), (True, "locker room ▲"), (False, "his morale ▼")],
    "pers_internal": [(True, "he plays Saturday"), (None, "40%: seniors call it a double standard")],
    "pers_dismiss": [(False, "he's gone for good"), (None, "room ▲ if he was trouble, ▼ if not")],
    "pers_extra": [(True, "locker room ▲ a little")],
    "pers_talk": [(None, "70%: room ▲ / else ▼")],
    "pers_ignore": [(False, "locker room ▼"), (True, "no one sits")],
    "pers_touches": [(True, "he's happy"), (False, "locker room ▼")],
    "pers_back": [(None, "50%: wake-up call ▲ / else the room takes it personally ▼")],
    "pers_earn": [(True, "locker room ▲"), (None, "35%: he's unhappy (portal risk)")],
    "pers_bench": [(True, "locker room ▲"), (False, "his morale ▼▼ (portal risk)")],
    "pers_meet": [(True, "he's back · his morale ▲▲"), (False, "costs you an afternoon")],
    "pers_let": [(False, "he's probably gone in December"), (True, "no special treatment")],
    "pers_promise": [(True, "his morale ▲"), (False, "break it and he's gone"), (False, "locker room ▼")],
    "nil_pay": [(True, "he stays · his morale ▲▲"), (False, "full raise out of next year's pool")],
    "nil_counter": [(None, "he might take half"), (False, "if not, he may walk")],
    "nil_refuse": [(True, "keeps your NIL pool"), (False, "his morale ▼▼ · portal risk ▲")],
    "draft_stay": [(True, "better odds he returns"), (None, "he may resent it if he stays and slips")],
    "draft_go": [(True, "locker room ▲ · recruits ▲"), (False, "he's likely gone")],
    "draft_neutral": [(None, "his call, his odds")],
}


def _hint_line(parts):
    bits = [paint(t, C.BGREEN if g is True else C.BRED if g is False else C.BYELLOW) for g, t in parts]
    return paint(" · ", C.GRAY).join(bits)


@moments.moment("answer")
def answer(league, m, choice_key):
    """Apply your reply. Returns a line describing what happened."""
    team = league.user_coach.team
    coach = league.user_coach
    kind = m["kind"]
    if kind == "choice":
        if m.get("nil_key") == choice_key:
            import finance_screens
            res = finance_screens.nil_prompt(league, team, m["ref"])
            if res:
                m["answered"] = choice_key
                return res[1]
            return "No offer made."
        e = m.get("fx", {}).get(choice_key, {})
        got = fx.apply(league, e, m.get("subject", ""))
        if got is None:
            return "You don't have the recruiting hours left this week. Pick another answer, or come back next week."
        m["answered"] = choice_key
        label = next((lab for k, lab in m.get("replies", []) if k == choice_key), "")
        league.__dict__.setdefault("week_calls", []).append(
            (league.year, league.week, m.get("subject", ""), label, fx._parts(e)))
        del league.week_calls[:-40]
        return " ".join([m.get("out", {}).get(choice_key, "")] + got).strip()
    m["answered"] = choice_key
    # ── replies from before choices carried effects (older saves) ──
    import carousel as cz  # noqa: F401
    if kind == "ad":
        eff = AD_REPLY_EFFECT.get(choice_key, {"default": 0})
        d = eff.get(team.ad.get("style"), eff["default"])
        if d:
            coach.__dict__.setdefault("seat_events", []).append((league.week, d, "how you talk to your AD"))
            coach.seat = int(max(0, min(100, coach.seat + d)))
        return ("He liked that." if d < 0 else "That didn't land well." if d > 0 else "He nods. Noted.")
    if kind == "player":
        p = m["ref"]
        if choice_key == "promise":
            p.promise = "made"
            return (f"{p.first_name} lights up. He'll stay patient — if he's in the rotation by the end of the "
                    f"season. Break it and he's very likely in the portal.")
        if choice_key == "earn":
            return f"{p.first_name} nods. He doesn't love it, but he respects it."
        p.promise = "ignored"
        return f"{p.first_name} noticed you didn't answer."
    if kind == "leader":
        return "He'll carry that into the locker room."
    if kind == "recruit":
        r = m["ref"]
        cycle = league.recruiting
        if choice_key in ("reassure", "thanks_r"):
            if cycle.remaining_hours(team) < 1:
                m["answered"] = None
                return "You're out of recruiting hours this week — the reply will have to wait."
            cycle.hours_used[team] += 1
            bump = 4.0 if choice_key == "reassure" else 2.0
            r.interest[team] = min(100, r.interest.get(team, 0) + bump)
            return f"{_recruit_first(r)} appreciated that. (+interest)"
        if choice_key == "nil":
            import finance_screens
            res = finance_screens.nil_prompt(league, team, r)
            if res:
                return res[1]
            m["answered"] = None
            return "No offer made."
        return "You'll get back to him."
    if kind.startswith("pers_"):
        import personalities
        return personalities.answer(league, m, choice_key)
    if kind == "staff_note":
        if choice_key == "name_qb":
            import personalities
            personalities._nudge(team, 1.5)
            return "The room settles. Everybody knows whose team it is. (chemistry up)"
        if choice_key == "recruit_cb":
            team.priority_pos = "CB"
            return "Corners are flagged as a staff priority — they'll rise in your Suggested list."
        return "Noted."
    if kind == "staff":
        if choice_key == "use_focus":
            league._suggested_focus = m["ref"]
            return "It's on the practice plan."
        return "Noted."
    return ""


def _option_hint(m, k):
    if m.get("kind") == "choice":
        e = m.get("fx", {}).get(k)
        # an inbox answer's "Saturday" is this week's game (the one-week lift), and says so
        return fx.hint(e).replace("every Saturday", "EVERY_SAT").replace("Saturday", "this Saturday") \
            .replace("EVERY_SAT", "every Saturday") if e is not None else ""
    if k in LEGACY_HINTS:
        return _hint_line(LEGACY_HINTS[k])
    return ""


def sender_label(m, short=False):
    """'Linda Maddox (Booster)' — every sender with a role; short: 'Maddox (Booster)'."""
    role = (m.get("role") or "").split("·")[0].strip()
    who = m["sender"]
    role = {"Offensive Coordinator": "OC", "Defensive Coordinator": "DC",
            "Sports Information": "SID", "Athletic Director": "AD"}.get(role, role)
    parts = who.split()
    if short and who.startswith("Director of Football Operations"):
        return "Football Ops"
    if short and len(parts) == 2 and not parts[0].isupper():   # 'Linda Maddox' → 'Maddox' (not 'AD Tillman')
        who = parts[-1]
    if any(ch.islower() for ch in role) or role in ("OC", "DC", "SID"):
        if role.split()[0].lower() not in who.lower() and not who.lower().startswith("ad "):
            who = f"{who} ({role})"
    return who


def inbox_screen(league):
    """Read and answer your messages: who needs you first, then the rest — with a face on the next one."""
    import guide
    guide.tip(league, "inbox")
    import faces_ui
    from ui import ACCENT
    while True:
        clear()
        allm = list(reversed(inbox(league)))
        todo = [m for m in allm if m.get("replies") and m.get("answered") is None]
        ids = {id(m) for m in todo}
        rest = [m for m in allm if id(m) not in ids]
        msgs = (todo[:14] + rest)[:24]
        shown_todo = min(len(todo), 14)
        print(title_bar(f"INBOX  ·  {unread(league)} unread  ·  {len(todo)} waiting on you"))
        if not msgs:
            print(paint("\n   Nothing yet. People reach out once the season gets going.", C.GRAY))
            pause()
            return
        if todo:
            for ln in faces_ui.next_up(league, todo[0], len(todo)):
                print(ln)

        def row(i, m):
            dot = paint("●", ACCENT) if not m.get("read", False) else " "
            need = paint("  REPLY", C.BMAGENTA, C.BOLD) if m.get("replies") and m.get("answered") is None else ""
            if m.get("answered") == "silence":
                need = paint("  missed", C.GRAY)
            elif m.get("answered") is not None:                  # what you said, so you can scan back
                said = next((lab for k, lab in m.get("replies", []) if k == m["answered"]), None)
                if said:
                    need = paint("  → " + truncate(said, 18), C.GRAY)
            when = ("camp" if m["week"] == 0 else f"wk {m['week']}") if m["year"] == league.year else str(m["year"])
            kind, kcol = faces_ui.who_kind(m)
            print(f"   {dot} {paint(f'{i:>2}', ACCENT)}  {paint(pad(kind, 12), kcol)}"
                  f"{pad(paint(truncate(sender_label(m), 29), m.get('color') or C.BWHITE, C.BOLD), 30)}"
                  f"{pad(truncate(m['subject'], 24), 25)}{paint(pad(when, 6), C.GRAY)}{need}")
        if shown_todo:
            print(section(f"NEEDS YOUR REPLY ({len(todo)})", C.BMAGENTA))
            for i, m in enumerate(msgs[:shown_todo], 1):
                row(i, m)
        if len(msgs) > shown_todo:
            print(section("EARLIER", C.GRAY))
            for i, m in enumerate(msgs[shown_todo:], shown_todo + 1):
                row(i, m)
        print(rule())
        import webview
        if webview.on():
            try:
                def wrow(i, m):
                    said = next((lab for k, lab in m.get("replies", []) if k == m.get("answered")), "") \
                        if m.get("answered") not in (None, "silence") else ""
                    return {"i": i, "unread": not m.get("read", False), "kind": faces_ui.who_kind(m)[0],
                            "from": webview.plain(sender_label(m)), "subject": m["subject"],
                            "when": ("camp" if m["week"] == 0 else f"wk {m['week']}") if m["year"] == league.year else str(m["year"]),
                            "reply": bool(m.get("replies") and m.get("answered") is None),
                            "missed": m.get("answered") == "silence", "said": said}
                webview.emit("inbox", {"unread": unread(league), "waiting": len(todo),
                                       "todo": [wrow(i, m) for i, m in enumerate(msgs[:shown_todo], 1)],
                                       "rest": [wrow(i, m) for i, m in enumerate(msgs[shown_todo:], shown_todo + 1)]})
            except Exception:
                pass
        c = ask("Open # (Enter = back, A = open the next one that needs a reply):").strip().lower()
        if c == "":
            return
        if c == "a":
            # Work the queue: answer one and the next opens, until you leave one for later.
            while True:
                todo = [m for m in inbox(league)[::-1] if m.get("replies") and m.get("answered") is None]
                if not todo or not read_message(league, todo[0], queue=len(todo) - 1):
                    break
        elif c.isdigit() and 1 <= int(c) <= len(msgs):
            read_message(league, msgs[int(c) - 1])


def _wv_message(league, m, opts, queue):
    import webview
    if not webview.on():
        return
    try:
        said = next((lab for k, lab in m.get("replies", []) if k == m.get("answered")), "") \
            if m.get("answered") not in (None, "silence") else ""
        due = m.get("due")
        webview.emit("message", {"subject": m["subject"], "from": webview.plain(m.get("sender", "")),
                                 "role": webview.plain(m.get("role", "")), "body": webview.plain(m.get("body", "")),
                                 "options": [{"key": o["key"], "label": webview.plain(o["label"]), "hint": webview.plain(o["hint"])}
                                             for o in opts],
                                 "said": said, "missed": m.get("answered") == "silence",
                                 "missedText": webview.plain(m.get("silence_text") or "The moment passed."),
                                 "last": bool(due and tuple(due) == (league.year, league.week)), "queue": queue or 0})
    except Exception:
        pass


@moments.moment("read")
def read_message(league, m, queue=None):
    """Show a message (and take a reply). Returns True if you answered it."""
    import textwrap
    while True:
        clear()
        m["read"] = True
        print(title_bar(truncate(m["subject"].upper(), 60)))
        import faces_ui
        hdr = faces_ui.message_header(league, m)
        if hdr:                                              # his face, who he is, and what he wrote
            print()
            for ln in hdr:
                print(ln)
        else:
            print(f"\n   {paint(m['sender'], m.get('color') or C.BWHITE, C.BOLD)}   {paint(m['role'], C.GRAY)}")
            print()
            for ln in textwrap.wrap(m["body"], 88):
                print("   " + paint(ln, C.BWHITE))
        print()
        if not (m["replies"] and m["answered"] is None):
            _wv_message(league, m, [], None)
            if m.get("answered") == "silence":
                print(paint("   You never answered. " + (m.get("silence_text") or "The moment passed."), C.GRAY))
            elif m["answered"] is not None:
                said = next((label for k, label in m["replies"] if k == m["answered"]), "")
                if said:
                    print(paint(f"   You replied: {said}", C.GRAY))
            pause()
            return False
        hints = fx.show_hints()
        wv_opts = []
        for i, (k, label) in enumerate(m["replies"], 1):
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {label}")
            h = _option_hint(m, k) if hints else ""
            if h:
                print("       " + h)
            wv_opts.append({"key": str(i), "label": label, "hint": h})
        _wv_message(league, m, wv_opts, queue)
        due = m.get("due")
        if due and tuple(due) == (league.year, league.week):
            print(paint("\n   Last chance to answer this one.", C.BRED))
        if queue:
            print(paint(f"\n   {queue} more waiting after this one.", C.GRAY))
        c = ask("Reply (Enter = later):").strip()
        if not (c.isdigit() and 1 <= int(c) <= len(m["replies"])):
            return False
        out = answer(league, m, m["replies"][int(c) - 1][0])
        if out:
            for ln in textwrap.wrap(out, 88):
                print(paint("   " + ln, C.BCYAN))
            pause()
        if m["answered"] is not None:
            return True
