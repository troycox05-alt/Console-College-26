"""
postgame.py — The postgame press conference (Career mode, your games only).

Two or three questions built from the game you just played: the result, the
margin, the swing plays, your quarterback, the injuries, the rival, what's next.
Answers have tones, like the Thursday presser, and a little weight — every
one with an upside and a cost (see podium.py):
  fiery    — the locker room feeds off it next week; plays a bit emotional late;
             some ADs love it, some wince
  humble   — takes the heat off the players (after a loss, the room feels it);
             patient ADs like it; doesn't sell to recruits
  confident— recruits like it; a loss plus swagger can annoy the AD
  measured — steady; no headlines
Plus what each answer does on its own: calling out the officials (a fine, and
a locker room that loves you for it), standing by your staff, crediting a
freshman, owning a blowout. Whatever lifts or drags your team carries into
next week's game.
"""
import random

from ui import C, ask, clear, pad, paint, pause, title_bar
from netplay import moments

TONE_COLOR = {"confident": C.BYELLOW, "measured": C.BWHITE, "fiery": C.BRED, "humble": C.BCYAN}


def _facts(league, team, g):
    opp = g.opponent_of(team)
    box = getattr(g, "box", None)
    ts = box.team_stats.get(team, {}) if box else {}
    os_ = box.team_stats.get(opp, {}) if box else {}
    stats = getattr(box, "stats", {}) if box else {}
    mine = {p: c for p, c in stats.items() if (box.team_of(p) if hasattr(box, "team_of") else None) is team}
    qb = max((p for p in mine if mine[p].get("pass_att", 0)), key=lambda p: mine[p]["pass_att"], default=None)
    star = None
    if mine:
        from impact import game_impact
        star = max(mine, key=lambda p: game_impact(mine[p]))
    hurt = [i for i in getattr(box, "injuries", []) or [] if len(i) >= 7 and i[2] is team and i[5] != "shaken"]
    ranks = getattr(g, "ranks", {}) or {}
    import carousel as cz
    return {"opp": opp, "won": g.winner is team, "pf": g.score_for(team), "pa": g.score_for(opp),
            "margin": g.score_for(team) - g.score_for(opp), "to": ts.get("turnovers", 0),
            "opp_to": os_.get("turnovers", 0), "rush": ts.get("rush_yds", 0), "opp_rush": os_.get("rush_yds", 0),
            "qb": qb, "qbc": mine.get(qb, {}), "star": star, "starc": mine.get(star, {}), "hurt": hurt,
            "rank": ranks.get(team), "opp_rank": ranks.get(opp),
            "rival": cz.PRIMARY_RIVAL.get(team.school) == opp.school or cz.PRIMARY_RIVAL.get(opp.school) == team.school,
            "ot": bool(box and getattr(box, "ot_round", 0)), "post": g.game_type != "Regular Season",
            "record": team.record, "week": g.week}


def _bank(league, team, g, f, rng):
    qs = []

    def q(pri, text, answers):
        qs.append((pri + rng.random() * 0.5, text, answers))

    o = f["opp"].school
    m = abs(f["margin"])
    if f["won"]:
        if f["opp_rank"] and (not f["rank"] or f["rank"] > f["opp_rank"]):
            q(9, f"Coach, you just beat No. {f['opp_rank']} {o}. What does this win mean?",
              [("confident", "It means we belong. We knew it — now everybody else does.", ("recruits", 2)),
               ("humble", "It means we get to enjoy it tonight. Tomorrow it's back to work.", ("lift", 0.1)),
               ("fiery", "It means nothing if we don't back it up next week.", ("lift", 0.2))])
        if f["rival"]:
            q(8, f"You beat {o}. How long do you let them enjoy this one?",
              [("fiery", "All year. That's what this game is for.", ("lift", 0.15)),
               ("humble", "It's a great rivalry. Tonight belongs to our fans.", ("chem", 1)),
               ("confident", "Get used to it.", [("recruits", 1.5),
                                                  ("fx", {"notes": [(False, "they'll remember it next year")]})])])
        if f["ot"] or m <= 3:
            q(7, "That one came down to the last few plays. What did you see from your team at the end?",
              [("confident", "Guys who expect to win close games. That's a habit now.", ("lift", 0.1)),
               ("measured", "We made one more play than they did. That's football.", None),
               ("humble", "Honestly? We got fortunate. We have to be cleaner than that.", None)])
        if m >= 28:
            q(5, f"A {f['pf']}-{f['pa']} final. Anything you didn't like?",
              [("measured", "We'll find plenty on the film. There always is.", None),
               ("fiery", "The penalties. The finish. We don't play to the scoreboard.", ("lift", 0.1)),
               ("humble", f"{o} competed. That score doesn't tell the whole story.", None)])
    else:
        if m >= 21:
            q(9, f"{f['pa']}-{f['pf']}. What happened out there?",
              [("humble", "That's on me. We weren't ready, and that's my job.",
                [("seat_humble", 0), ("follow", "staff")]),
               ("fiery", "We got embarrassed. That won't happen again. Not with this group.", ("lift", 0.2)),
               ("measured", "They were better today. We'll look at the film and get to work.", None)])
        elif m <= 7:
            q(8, "So close. What's the message in the locker room right now?",
              [("measured", "Close doesn't count. We'll fix the few plays that cost us.", None),
               ("fiery", "I told them to remember this feeling. We're not losing that game again.", ("lift", 0.2)),
               ("confident", "We're a good football team. We'll be fine.", None)])
        if f["rival"]:
            q(8, f"A loss to {o}. How do you face your fan base after this one?",
              [("humble", "I understand the frustration. I feel it too. We'll get it fixed.", ("seat_humble", 0)),
               ("measured", "One game. It stings. Next year's circled already.", None),
               ("fiery", "Nobody hurts more than that locker room. They'll answer.", ("lift", 0.15))])
        if f["opp_rank"] is None and f["rank"]:
            q(7, f"You came in ranked and lost to an unranked {o}. Did your team overlook them?",
              [("humble", "If we did, that's on me. It won't happen twice.", None),
               ("fiery", "Nobody overlooked anybody. We just didn't play well enough.", None),
               ("measured", f"Credit {o}. They played a great game.", None)])
    if f["to"] >= 3:
        q(7, f"{f['to']} turnovers today. How do you fix that?",
          [("measured", "Ball security, every drill, every day this week.", ("lift", 0.05)),
           ("fiery", "Whoever puts it on the ground doesn't play. Simple as that.", ("lift", 0.1)),
           ("humble", "We're coaching it. Clearly not well enough yet.", None)])
    elif f["opp_to"] >= 3 and f["won"]:
        q(5, f"Your defense forced {f['opp_to']} turnovers. Is that something you emphasize?",
          [("confident", "Every single day. That's who we are.", None),
           ("measured", "We practice it. Today it showed up.", None),
           ("humble", "Credit the players. They made the plays.", None)])
    qb, c = f["qb"], f["qbc"]
    if qb is not None and c.get("pass_int", 0) >= 2:
        q(6, f"{qb.name} threw {c['pass_int']} interceptions. Is he still your quarterback?",
          [("confident", f"Absolutely. {qb.first_name} is our guy.", ("qb", 1)),
           ("measured", "We'll evaluate everything, like we do every week.", [("qb", -1), ("follow", "qb_hedge")]),
           ("fiery", "He'll be better. He knows it. I know it.", ("qb", 1))])
    elif qb is not None and c.get("pass_td", 0) >= 3:
        q(5, f"{qb.name} with {c['pass_td']} touchdown passes. Is he playing the best football of his career?",
          [("confident", "He's playing like the best quarterback in this conference.", ("qb", 1)),
           ("measured", "He's playing well. We need him to keep stacking days.", None),
           ("humble", "The guys around him made it easy. Credit the line.", None)])
    star, sc = f["star"], f["starc"]
    if star is not None and star is not qb and (sc.get("rush_yds", 0) >= 120 or sc.get("rec_yds", 0) >= 120
                                                   or sc.get("sack", 0) >= 2):
        q(5, f"Talk about {star.name}'s day.",
          [("confident", f"{star.first_name} is as good as anybody in the country at what he does.", ("recruits", 1)),
           ("humble", f"{star.first_name} works as hard as anyone we've got. Days like this are earned.", None),
           ("measured", "He did his job. That's what we ask.", None)])
    if f["hurt"]:
        p = f["hurt"][0][3]
        q(6, f"Any update on {p.name}?",
          [("measured", "We'll know more tomorrow. I'm not a doctor.", None),
           ("humble", f"We're praying for {p.first_name}. Football comes second.", None),
           ("confident", "Next man up. We've got a deep room.",
            ("fx", {"lift": 0.05, "who": p, "morale": -5,
                    "notes": [(False, f"{p.first_name} hears that he's replaceable")]}))])
    if f["rush"] >= 220:
        q(4, f"{f['rush']} rushing yards. Was that the plan coming in?",
          [("confident", "We felt we could run it on anybody. Today we did.", None),
           ("measured", "We took what they gave us.", None),
           ("humble", "The offensive line deserves the game ball.", ("lift", 0.05))])
    if g.week >= 10:
        returning = sorted((p for p in team.players_at("QB") if getattr(p, "year", 0) < 3), key=lambda p: -p.overall)
        if not returning or returning[0].overall < 72:
            q(6, "You can see the roster math: next year there isn't an obvious answer at quarterback. How aggressive will you be?",
              [("confident", "Aggressive enough to solve it. This program won't drift at quarterback.", ("fx", {"recruits": 0.8, "chem": -1})),
               ("measured", "We'll develop our room, recruit the position and evaluate every transfer who fits.", ("fx", {"clutch": 0.05, "recruits": -0.2})),
               ("humble", "The guys in that room have earned a real chance before I promise their job to somebody else.", ("fx", {"chem": 1, "recruits": -0.5})),
               ("fiery", "Competition starts tomorrow. If somebody wants that job, go take it.", ("fx", {"lift": 0.1, "chem": -1, "recruits": 0.3}))])
    if team.wins in (8, 10, 12) and f["won"]:
        q(5, f"That's win No. {team.wins} this season. Does that milestone change how you view where the program is?",
          [("confident", "It confirms the standard is moving. Now we raise it again.", ("fx", {"recruits": 0.7, "seat": 1})),
           ("measured", "It matters when the season is over. Tonight, it means we won one game.", ("fx", {"clutch": 0.05, "recruits": -0.2})),
           ("humble", "It belongs to the players and staff. My name is just on the door.", ("fx", {"chem": 1, "recruits": -0.4})),
           ("fiery", "We're not hanging a banner for a win total. There are bigger things in front of us.", ("fx", {"lift": 0.1, "seat": 1}))])
    _newer(league, team, g, f, q)
    _procedural_context(league, team, g, f, q)
    q(1, "What's next for this team?",
      [("measured", "Film tomorrow, then the next opponent. That's the whole job.", None),
       ("fiery", "We're going to go get the next one. That's all that matters.", ("lift", 0.05)),
       ("confident", "Keep stacking wins. This team's just getting started." if f["won"] else
        "We'll be fine. This team's better than what you saw today.", None)])
    limit = 4 if f["post"] or f["rival"] else 3
    history = league.__dict__.setdefault("_postgame_topics", {}).setdefault(league.year, {})
    out = []
    for item in sorted(qs, key=lambda x: -x[0]):
        # Text prefix is a stable-enough topic signature for old saves; keep generic questions on a short leash.
        sig = item[1].split("?")[0][:58]
        last = history.get(sig)
        if last is not None and g.week - last <= 2 and item[0] < 8:
            continue
        out.append(item)
        history[sig] = g.week
        if len(out) >= limit:
            break
    return out



def _procedural_context(league, team, g, f, q):
    """Postgame questions driven by consequences: standings, roster arc, milestones and what comes next."""
    o = f["opp"].school
    qb = f.get("qb")
    if f["won"] and f["rank"] and f["rank"] <= 12 and f["week"] >= 8:
        q(6.5, f"You leave this week {team.record} and ranked No. {f['rank']}. Has the goal changed from having a good year to chasing something bigger?",
          [("confident", "The goal was always bigger. Now everybody else can see the path too.", ("fx", {"recruits": .8, "seat": 1})),
           ("measured", "The path only exists if we handle next week. That's where this gets dangerous.", ("fx", {"clutch": .08, "recruits": -.2})),
           ("humble", "We earned another meaningful week. That's enough to be grateful for tonight.", ("fx", {"chem": 1, "recruits": -.4})),
           ("fiery", "We're done pretending the ceiling is low. Go chase the whole thing.", ("fx", {"lift": .12, "clutch": -.05}))])
    if not f["won"] and f["rank"] and f["rank"] <= 15 and f["week"] >= 7:
        q(7.5, f"You came in No. {f['rank']} and now the margin for error is almost gone. How do you keep one loss from becoming two?",
          [("humble", "By making sure I don't ask players to carry the disappointment for me.", ("fx", {"chem": 1, "recruits": -.4})),
           ("measured", "Separate consequence from correction. The stakes changed; Tuesday's work didn't.", ("fx", {"clutch": .1, "recruits": -.2})),
           ("fiery", "Good teams get angry. Great teams make that anger useful next Saturday.", ("fx", {"lift": .15, "clutch": -.05})),
           ("confident", "We're still the same team people were afraid to play this morning.", ("fx", {"recruits": .55, "seat": 1}))])
    if qb is not None and getattr(qb, "year", 0) >= 3 and f["week"] >= 10:
        q(5.8, f"We're getting close to the end for {qb.name}. How do you balance chasing this season with preparing the quarterback room for next year?",
          [("confident", "By doing both. Contenders don't get to use transition as an excuse.", ("fx", {"recruits": .7, "chem": -1})),
           ("measured", "This season gets the meeting room. The future gets our evaluation time.", ("fx", {"clutch": .06, "recruits": -.2})),
           ("humble", f"{qb.first_name} earned the right for this stretch to be about this team, not his replacement.", ("fx", {"chem": 1, "recruits": -.4})),
           ("fiery", "Everybody behind him should be preparing like the job opens tomorrow.", ("fx", {"lift": .08, "chem": -1, "recruits": .3}))])
    if f["rival"]:
        if f["won"]:
            q(7.8, f"You beat {o}, but rivalry wins have a way of becoming promises about the future. What does tonight obligate this program to do next?",
              [("confident", "Make this the expectation, not the exception.", ("fx", {"recruits": .8, "opp_lift": .15})),
               ("measured", "Recruit, develop and come back prepared to earn it again. Nothing carries over.", ("fx", {"clutch": .08, "recruits": -.2})),
               ("humble", "Respect how hard this was to earn. Rivalries punish people who get comfortable.", ("fx", {"chem": 1, "recruits": -.35})),
               ("fiery", "Make them live with it for a year, then go do it again.", ("fx", {"lift": .14, "opp_lift": .25}))])
        else:
            q(8.2, f"Losing to {o} follows a program for 365 days. What changes because of this?",
              [("humble", "I carry it first. The players will get correction, not blame.", ("fx", {"chem": 1, "recruits": -.45})),
               ("measured", "We document why we lost and build next year's plan from facts, not emotion.", ("fx", {"clutch": .1, "recruits": -.2})),
               ("fiery", "Everything about how we prepare for them. I want this feeling remembered.", ("fx", {"lift": .15, "chem": -1})),
               ("confident", "The result changes. The direction of this program doesn't.", ("fx", {"recruits": .5, "seat": 1}))])
    if f["post"]:
        q(8.5, f"This wasn't a normal Saturday; it was {g.game_type}. What did you learn about your program under postseason pressure?",
          [("confident", "That we belong in games with consequences, and we expect to be back in them.", ("fx", {"recruits": .8, "seat": 1})),
           ("measured", "That pressure exposes details. Some held up; some become our offseason list.", ("fx", {"clutch": .1, "recruits": -.2})),
           ("humble", "How much work it takes just to get here. I won't let us take that for granted.", ("fx", {"chem": 1, "recruits": -.4})),
           ("fiery", "That this stage should feel normal here. If it doesn't yet, we're going to make it normal.", ("fx", {"lift": .12, "clutch": -.04}))])
    if f["won"] and team.wins in (9, 11, 13):
        q(5.5, f"Win No. {team.wins} puts this team in rare territory for a season. When do you let yourself appreciate that?",
          [("confident", "Tonight. Then we start asking what record this group can break next.", ("fx", {"recruits": .65, "seat": 1})),
           ("measured", "After the last game. Milestones are markers, not finish lines.", ("fx", {"clutch": .06, "recruits": -.2})),
           ("humble", "When the seniors are gone and we understand what they actually built.", ("fx", {"chem": 1, "recruits": -.35})),
           ("fiery", "Appreciate it on the bus. Tomorrow we go hunt the next one.", ("fx", {"lift": .1, "clutch": -.04}))])

def _newer(league, team, g, f, q):
    """The officials, a freshman's day, bowl eligibility, a leaky defense, the seat."""
    from effects import by_ad
    o = f["opp"].school
    m = f["margin"]
    if not f["won"] and m >= -7:
        q(8, "Any thoughts on the officiating today?",
          [("fiery", "I'll be sending some clips to the conference. Some of those calls...",
            ("fx", {"money": -25_000, "money_what": "conference fine", "chem": 2, "lift": 0.1,
                    "seat": by_ad(team, {"default": 0, "traditionalist": 1, "budget": 1, "politician": -1,
                                         "booster": -1})})),
           ("measured", "We had our chances. That's not why we lost.", ("clutch", 0.1)),
           ("humble", "The officials have a hard job. We have to be better than that.",
            [("chem", -1), ("seat", by_ad(team, {"default": 0, "patient": -1, "traditionalist": -1}))])])
    star, sc = f["star"], f["starc"]
    if star is not None and star.year == 0 and (sc.get("rush_yds", 0) >= 90 or sc.get("rec_yds", 0) >= 90
                                                or sc.get("pass_td", 0) >= 2 or sc.get("sack", 0) >= 2):
        q(6, f"A freshman, {star.name}, had a big day. Is this his arrival?",
          [("confident", "Remember the name. You'll be saying it for three more years.",
            ("fx", {"recruits": 1.5, "gamble": [(0.7, {}, f"{star.first_name} handled the attention."),
                                                ({"who": star, "unhappy": True},
                                                 f"{star.first_name} read every word of it. The vets noticed.")]})),
           ("humble", "He's got a long way to go. The older guys got him ready.",
            ("fx", {"who": star, "dev": 1.1, "chem": 1})),
           ("measured", "He did his job. We'll need him to keep doing it.", None)])
    if f["won"] and team.wins == 6 and g.game_type == "Regular Season":
        q(7, "Six wins. You're bowl eligible. What does that mean to this group?",
          [("humble", "For these seniors? Everything. They've earned it.", ("chem", 2)),
           ("fiery", "Six isn't the goal. It's the floor.", ("lift", 0.1)),
           ("confident", "We're not done. Not close.", [("recruits", 1),
            ("fx", {"stake": {"on": "season", "need": 8, "hint": "eight wins",
                              "win": {"recruits": 1.5}, "loss": {"seat": 1},
                              "who": f"{team.school} Communications", "subject": "'Not close'",
                              "wtext": "You said you weren't done at six. You weren't. Recruits noticed.",
                              "ltext": "You said you weren't done at six. The season ended short of what you said."}})])])
    if f["pa"] >= 38:
        dc = getattr(team, "dc", None)
        q(6, f"You gave up {f['pa']} points. Is the defense a concern?",
          [("confident", "No. We'll be fine.", ("fx", {"coord": dc, "stay": -1} if dc else {})),
           ("fiery", "It's unacceptable. Everybody on that side of the ball is on notice.",
            ("fx", {"lift": 0.15, "chem": -1, **({"coord": dc, "stay": 1} if dc else {})})),
           ("humble", "I'll be more involved with the defense this week. That's on me.",
            ("fx", {"clutch": 0.1, "chem": 1, **({"coord": dc, "stay": 1} if dc else {})}))])
    import halftime
    ht = halftime.second_half(g, team)
    if ht:
        call, (a1, b1), (a2, b2) = ht
        swing = (a2 - b2) - (a1 - b1)
        oc, dc = getattr(team, "oc", None), getattr(team, "dc", None)
        coords = [c for c in (oc, dc) if c is not None]
        if swing >= 10 and a2 > b2:
            q(7, f"You won the second half {a2}-{b2}. What changed at halftime?",
              [("humble", "Credit the coordinators. They saw it before I did.",
                ("fx", {"also": [{"coord": c, "stay": -1} for c in coords], "chem": 1})),
               ("confident", f"We made the right calls. '{call['adjust']}' — and the players executed it.",
                ("recruits", 1.5)),
               ("fiery", "I told them what I thought of the first half. They listened.", ("lift", 0.15))])
        elif swing <= -10 and a2 < b2:
            q(7, f"They won the second half {b2}-{a2}. Did your halftime adjustments backfire?",
              [("humble", "I made the wrong call at the half. That's on me.", [("seat", -1), ("chem", 1)]),
               ("measured", "They adjusted better than we did. We'll learn from it.", None),
               ("fiery", "The plan was fine. The execution wasn't.", [("lift", 0.1), ("chem", -2)])])
    import sideline
    sideline.podium_questions(g, team, q)             # the call that decided it
    import carousel as cz
    coach = league.user_coach
    if not f["won"] and getattr(coach, "seat", 30) >= cz.fire_line(team) - 15:
        q(8, "Do you feel like your job is in jeopardy?",
          [("measured", "I feel like we have a game next week. That's where my head is.", None),
           ("fiery", "No. And anybody who wants to write that can come to practice.",
            [("lift", 0.15), ("seat", by_ad(team, {"default": 0, "politician": -1, "patient": 1}))]),
           ("humble", "That's not my call. My job is to get this fixed.", [("seat", -1), ("chem", 1)])])


@moments.moment("postgame")
def run(league, g):
    import world_rules
    if not world_rules.enabled(league, "media"):
        return
    """Call after your game. Career mode only; quiet for anyone else."""
    if getattr(league, "mode", None) != "career" or getattr(league, "user_coach", None) is None:
        return
    team = league.user_coach.team
    if team is None or team not in (g.home, g.away) or not g.played:
        return
    import week
    week.week_report(league, g, team)                 # what the week's decisions bought
    import sideline
    sideline.headset_log(g, team)                     # your calls, what each was worth, the grade
    rng = random.Random(f"postgame:{league.seed}:{league.year}:{g.week}")
    f = _facts(league, team, g)
    qs = _bank(league, team, g, f, rng)
    import podium
    clear()
    print(title_bar(f"POSTGAME  ·  {team.school.upper()} {f['pf']}, {f['opp'].school.upper()} {f['pa']}"))
    print(paint("\n   The podium. The locker room, the AD and the recruits are listening — read the line under each answer.",
                C.GRAY))
    import halftime
    ht = halftime.second_half(g, team)
    if ht:
        call, (a1, b1), (a2, b2) = ht
        col = C.BGREEN if a2 > b2 else C.BRED if a2 < b2 else C.BWHITE
        print(paint(f"   Your halftime call: {call['adjust']}", C.GRAY)
              + paint(f"   First half {a1}-{b1} · second half {a2}-{b2}", col))
    ctx = {"league": league, "team": team, "opp": f["opp"], "qb": f["qb"], "won": f["won"], "underdog": False}
    import webview
    webview.emit("presser", {"title": f"Postgame · {team.school} {f['pf']}, {f['opp'].school} {f['pa']}",
                             "intro": "The podium. The locker room, the AD and the recruits are listening.",
                             "half": (f"Your halftime call: {ht[0]['adjust']} · first half {ht[1][0]}-{ht[1][1]}, "
                                      f"second half {ht[2][0]}-{ht[2][1]}") if ht else ""})
    said, total = podium.run(league, [(text, answers) for _, text, answers in qs], "post", ctx)
    print()
    print(podium.summary(total))
    webview.emit("sum", {"text": webview.plain(podium.summary(total))}, add=True)
    pause()
