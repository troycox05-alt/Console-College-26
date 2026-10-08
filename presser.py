"""
presser.py — Thursday's press conference, built from the week you're actually having.

The room asks about what's real: your first game ever as a head coach, the
blowout loss, the 5-0 start, the quarterback who threw three picks, the
rivalry, the job rumors, the old school you're playing, the seniors' last
home game. Nobody asks about an opponent's 0-0 record in Week 1.

Every question comes with its own three answers, written for that question.
Each answer has a tone, and every tone has an upside and a cost (see
podium.py for the full table):

  confident   recruits like it — but as the underdog it's bulletin-board
              material for the other locker room
  measured    your team stays composed late — but no headlines, and an AD who
              wants noise notices a podium full of nothing
  fiery       your team feeds off it on Saturday — but plays a little
              emotional late; some ADs love it, some wince
  humble      takes the heat off your players — but doesn't sell to recruits;
              patient ADs like it, win-now ADs want fire

Many answers also do something of their own — backing your quarterback,
talking up the class, a shot at the rival, standing by your staff — and a few
draw a follow-up ("So you're guaranteeing it?"). Every answer shows what it
does before you pick it.
"""
import random

from effects import by_ad
from ui import C, ask, clear, pad, paint, pause, title_bar
from netplay import moments

FIERY_AD = {"politician": 1, "booster": 1, "big_game": 1, "patient": -1, "analytics": -1, "budget": -1}
HUMBLE_AD = {"patient": 1, "traditionalist": 1, "politician": -1, "win_now": -1}


# ═══ Reading the week ═══════════════════════════════════════════════════════

def _situation(league, team, g):
    import carousel as cz
    coach = league.user_coach
    opp = g.opponent_of(team)
    played = [x for x in league.team_games(team) if x.played]
    last = played[-1] if played else None
    site = 0 if g.neutral else (1 if g.home is team else -1)
    s = {
        "team": team, "opp": opp, "coach": coach, "g": g, "week": g.week, "last": last,
        "wp": cz.win_prob(team, opp, site, league), "home": g.home is team and not g.neutral,
        "rank": league.rankings.rank_of(team), "opp_rank": league.rankings.rank_of(opp),
        "rival": cz.PRIMARY_RIVAL.get(team.school) == opp.school or cz.PRIMARY_RIVAL.get(opp.school) == team.school,
        "first_game_ever": not coach.history and not played,
        "first_game_here": coach.hired_year == league.year and not played,
        "opp_played": opp.wins + opp.losses > 0,
        "seat": getattr(coach, "seat", 30), "fire_line": cz.fire_line(team),
        "conf_opener": g.conference_game and not any(x.conference_game for x in played),
        "last_home": g.home is team and not g.neutral and not any(
            x.home is team and not x.neutral for x in league.team_games(team)
            if not x.played and x is not g and x.game_type == "Regular Season"),
        "former": next((h["school"] for h in coach.history if h["school"] == opp.school), None),
    }
    streak, kind = 0, None
    for x in reversed(played):
        w = x.winner is team
        if kind is None:
            kind = w
        if w != kind:
            break
        streak += 1
    s["streak"], s["streak_win"] = streak, kind
    if last is not None:
        lo = last.opponent_of(team)
        s["last_won"] = last.winner is team
        s["last_margin"] = last.score_for(team) - last.score_for(lo)
        s["last_opp"] = lo
        lsite = 0 if last.neutral else (1 if last.home is team else -1)
        s["last_wp"] = cz.win_prob(team, lo, lsite, league)
        box = getattr(last, "box", None)
        ts = box.team_stats.get(team, {}) if box else {}
        s["last_to"] = ts.get("turnovers", 0)
        s["last_rush"] = ts.get("rush_yds", 0)
        s["first_win_ever"] = s["last_won"] and sum(h["w"] for h in coach.history) + sum(
            1 for x in played if x.winner is team) == 1
    qb = team.players_at("QB")
    s["qb"] = qb[0] if qb else None
    if s["qb"] is not None:
        st = s["qb"].season_stats
        s["qb_ints"] = st.get("pass_int", 0)
        s["qb_tds"] = st.get("pass_td", 0)
        s["qb_yds"] = st.get("pass_yds", 0)
    hurt = [p for p in team.injured() if p in team.players_at(p.position)[:1]]
    s["star_out"] = max(hurt, key=lambda p: p.overall) if hurt else None
    try:
        cyc = league.recruiting
        s["commits"] = len(cyc.commitments(team))
        s["class_rank"] = cyc.class_rank(team)
    except Exception:
        s["commits"], s["class_rank"] = 0, None
    s["wins"], s["losses"] = team.wins, team.losses
    returning_qbs = sorted((p for p in team.players_at("QB") if getattr(p, "year", 0) < 3), key=lambda p: -p.overall)
    s["next_qb"] = returning_qbs[0] if returning_qbs else None
    s["next_qb_clear"] = bool(returning_qbs and returning_qbs[0].overall >= 72)
    s["career_wins"] = sum(h.get("w", 0) for h in coach.history) + team.wins
    s["opp_coach"] = opp.coach.name if getattr(opp, "coach", None) else None
    return s


# ═══ The question bank ══════════════════════════════════════════════════════
# Each entry: (priority, question, [(tone, answer, extra), ...]). Higher priority
# gets asked first; two questions a week, never two of the same kind.

def _bank(s, rng):
    t, o, c = s["team"], s["opp"], s["coach"]
    qs = []

    def q(kind, pri, text, answers):
        qs.append((pri + rng.random() * 0.5, kind, text, answers))

    # ── firsts ──
    if s["first_game_ever"]:
        q("first", 10, f"Coach, this is your first game as a head coach — anywhere. What's going through your mind?",
          [("confident", "I've been ready for this for a long time. So have these players.", None),
           ("humble", "Honestly? Gratitude. A lot of people got me here. Now I owe them a good team.", None),
           ("fiery", "I'm not here to soak it in. I'm here to win the game.", None)])
        q("first", 9, f"What will {t.school} fans see from your team on Saturday that they haven't seen before?",
          [("confident", "A team that plays fast, plays hard, and expects to win.", None),
           ("measured", "Effort, discipline, and a group that takes care of the football. The rest we'll earn.", None),
           ("fiery", "Toughness. Nobody's going to out-hit us. Nobody.", None)])
    elif s["first_game_here"]:
        q("first", 9, f"First game on the {t.school} sideline. Different feeling from your last stop?",
          [("confident", "Same job, bigger stage. We're built for it.", None),
           ("humble", "Every place is special. This one's home now — I want to earn that.", None),
           ("measured", "It's a football game. We'll prepare like it's any other one.", None)])
    if s.get("first_win_ever"):
        q("firstwin", 8, "You got your first win as a head coach last week. Where's the game ball going?",
          [("humble", "To the players. I just held the headset.", ("lift", 0.1)),
           ("confident", "Mounted on my wall — right next to where the next ninety are going.", None),
           ("measured", "We enjoyed it for a night. It's a new week.", None)])

    # ── week 1 (no opponent records yet) ──
    if s["week"] == 1 and not s["first_game_ever"]:
        q("opener", 6, "Season opener. What did fall camp tell you about this team?",
          [("confident", "That we're deeper than people think. You'll see it Saturday.", None),
           ("measured", "That we've got work to do, and a group willing to do it.", None),
           ("fiery", "That these guys are tired of hitting each other. They want someone else.", ("lift", 0.1))])
        if s["rank"]:
            q("expect", 6, f"You open the year ranked No. {s['rank']}. Does that number mean anything to you?",
              [("measured", "Preseason polls are guesses. We'll find out who we are.", None),
               ("confident", "It means people have noticed. Now let's prove them right.", None),
               ("humble", "It means our players did a lot of good things last year. None of it counts now.", None)])
    if s["week"] == 1 and s["qb"] is not None:
        q("qb", 5, f"{s['qb'].name} is your starter. What won him the job?",
          [("confident", f"He's the best player in that room, and it wasn't close.", ("qb", 1)),
           ("measured", "Consistency. He did the boring things right every day.", None),
           ("humble", "He earned it, but nothing's locked in. Everybody competes every week.", ("qb", -1))])

    # ── last week ──
    if s["last"] is not None:
        lo = s["last_opp"].school
        m = s["last_margin"]
        if s["last_won"] and s["last_wp"] <= 0.35:
            q("upset", 8, f"Nobody gave you a chance against {lo}. What did you see that we didn't?",
              [("confident", "We saw a team we could beat. We just didn't say it out loud.", None),
               ("humble", "The players believed before anybody else did. That's all them.", ("lift", 0.1)),
               ("fiery", "Keep not giving us a chance. It works.", ("lift", 0.15))])
        elif not s["last_won"] and m <= -21:
            q("blowout", 8, f"You lost by {-m} to {lo}. What happened?",
              [("humble", "I didn't have them ready. That's on me, and I'll fix it.", ("lift", 0.15)),
               ("measured", "They were better than us on Saturday. We'll watch the tape and get better.", None),
               ("fiery", "What happened is unacceptable, and everybody in that building knows it.", ("lift", 0.2))])
        elif not s["last_won"] and m >= -3:
            q("close_l", 7, f"A {-m if m else 'one'}-point loss to {lo}. What's the one play you want back?",
              [("humble", "Too many to name one. Close losses are a coaching problem first.", None),
               ("measured", "We'll look at all of them. Close games come down to details.", None),
               ("fiery", "I'm not going to relive it up here. We'll fix it in the building.", None)])
        elif not s["last_won"] and s["last_wp"] >= 0.65:
            q("bad_l", 7, f"You were supposed to beat {lo}. Where does this team go from here?",
              [("humble", "Back to work. I have to coach better and so do our players.", None),
               ("confident", "Nobody in our locker room is panicking. We're a good football team.", None),
               ("fiery", "We go take it out on the next team. That's where we go.", ("lift", 0.1))])
        elif not s["last_won"]:
            q("loss", 5, rng.choice([f"What went wrong against {lo}?",
                                     f"Where did the {lo} game get away from you?",
                                     f"A {-m}-point loss to {lo}. What's the fix?"]),
              [("humble", "We didn't coach it well enough. I'll own that.", None),
               ("measured", "Some execution, some things they did well. It's all fixable.", None),
               ("fiery", "We beat ourselves. That's what makes me mad.", ("lift", 0.1))])
        elif s["last_won"] and m >= 28:
            q("rout", 5, f"A {m}-point win over {lo}. Anything you didn't like?",
              [("measured", "Plenty. We'll find it on film. We always do.", None),
               ("confident", "Not much. That's what we're supposed to look like.", None),
               ("fiery", "The penalties. I don't care what the score is.", ("lift", 0.05))])
        elif s["last_won"]:
            q("win", 3, rng.choice([f"What did the win over {lo} tell you about this team?",
                                    f"Good win over {lo}. Who stood out on the tape?",
                                    f"You handled {lo}. What's the next step for this group?"]),
              [("confident", "That we can win different ways. That's what good teams do.", None),
               ("measured", "That we're improving. We're not a finished product.", None),
               ("humble", "That our players are resilient. I'm proud of them.", None)])
        if s.get("last_to", 0) >= 3:
            q("turnovers", 8, f"{s['last_to']} turnovers last week. How do you fix that in four days?",
              [("measured", "Ball security drills every period. Ball security in the walkthrough. Every day.", None),
               ("fiery", "Whoever puts it on the ground watches from the sideline. Simple.", ("lift", 0.1)),
               ("humble", "It starts with me — our plan put them in bad spots.", None)])

    # ── streaks and records ──
    if s["last"] is not None and not s["last_won"] and s["losses"] == 1 and s["wins"] >= 4:
        q("loss", 8, f"First loss of the season after a {s['wins']}-0 start. How does this team respond?",
          [("confident", "The same way we did all year. One game doesn't change who we are.", None),
           ("humble", "We found out we're not as good as we thought. That's useful, if we listen.", None),
           ("fiery", "Angry. I hope they're angry. I am.", ("lift", 0.15))])
    if s["streak"] >= 3 and s["streak_win"]:
        q("streak_w", 6, rng.choice([f"That's {s['streak']} straight wins. Is this team for real?",
                                     f"{s['streak']} in a row now. What's changed?",
                                     f"You've won {s['streak']} straight. Are you worried about getting comfortable?"]),
          [("confident", "You're asking the wrong question. Ask the teams we've played.", None),
           ("measured", "We'll know in November. Right now we're playing well.", None),
           ("humble", "We haven't done anything yet. Talk to me in December.", None)])
    if s["streak"] >= 3 and s["streak_win"] is False:
        q("streak_l", 8, f"That's {s['streak']} straight losses. Is the locker room still with you?",
          [("confident", "Absolutely. Come to practice and see it.", None),
           ("humble", "I have to earn that every day, and I will.", ("lift", 0.1)),
           ("fiery", "Anybody who's not with us can find the door. The ones who are will turn this around.",
            ("lift", 0.2))])
    if s["wins"] == 5 and s["week"] <= 12:
        q("bowl", 6, "One more win and you're bowl eligible. Do you talk about that with the team?",
          [("measured", "We talk about this week. The rest takes care of itself.", None),
           ("confident", "We're not thinking about eligible. We're thinking about a lot more than that.", None),
           ("humble", "For this program it would mean a lot. The seniors deserve it.", None)])
    if s["losses"] == 0 and s["wins"] >= 5:
        q("unbeaten", 7, rng.choice([f"{s['wins']}-0. At what point do you let yourself think about the playoff?",
                                     f"Still unbeaten at {s['wins']}-0. Does the pressure build every week?",
                                     f"{s['wins']}-0 and people are starting to talk. Do your players hear it?"]),
          [("measured", "When somebody hands us a bracket. Not before.", None),
           ("confident", "We think about it every day. We'd be lying if we said we didn't.", None),
           ("humble", "We haven't played our best game yet. That's what I'm thinking about.", None)])

    # ── this opponent ──
    if s["rival"]:
        q("rival", 9, f"It's {o.school} week. What does this game mean to you personally?",
          [("fiery", f"Everything. You don't come here and not understand what {o.school} means.", ("lift", 0.15)),
           ("measured", "It's the one people remember. We'll treat it that way.", None),
           ("confident", "It means we get to prove what everybody in this state already knows.",
            [("jab", 1), ("follow", "guarantee")])])
    if s["former"]:
        q("former", 9, f"You coached at {s['former']}. What's it like game-planning against your old program?",
          [("humble", "I've got a lot of respect for the people over there. That doesn't change Saturday.", None),
           ("confident", "I know where some of the bodies are buried. We'll leave it at that.",
            [("jab", 1), ("seat", 1)]),
           ("measured", "It's a new staff, a new scheme. It's just another opponent.", None)])
    if s["opp_rank"] and s["week"] > 1 or (s["opp_rank"] and s["opp_rank"] <= 10):
        where = f"No. {s['opp_rank']} {o.school} comes to town" if s["home"] else \
            f"You go on the road to No. {s['opp_rank']} {o.school}"
        q("ranked", 7, f"{where}. What's the challenge?",
          [("confident", "They're good. So are we. Saturday settles it.", ("follow", "guarantee")),
           ("measured", f"They're ranked for a reason. We'll have to play our best game.", None),
           ("fiery", "Rankings don't block and tackle. Line it up.", ("lift", 0.1))])
    if s["wp"] <= 0.3 and not s["opp_rank"]:
        q("underdog", 6, f"The oddsmakers don't like your chances against {o.school}. Neither do most people.",
          [("confident", "Good. Keep that energy until kickoff.", ("follow", "guarantee")),
           ("humble", "They've earned that respect. We're going to go earn ours.", None),
           ("fiery", "I'll put our guys against anybody's. Anybody's.", ("lift", 0.1))])
    if s["wp"] >= 0.8:
        q("favorite", 3, f"You're a heavy favorite against {o.school}. How do you avoid a letdown?",
          [("measured", "You respect the opponent. Every week. That's how.", None),
           ("confident", "We don't do letdowns here.", None),
           ("humble", f"{o.school} has good players. If we're not ready, we'll lose. Simple.", None)])
    if s["conf_opener"]:
        q("conf", 6, f"Conference play starts with {o.school}. Does the season start over now?",
          [("measured", "The non-conference games counted. These count twice.", None),
           ("confident", "Our goal's in this league. Now we go get it.", None),
           ("fiery", "This is what we practiced for since January.", None)])
    if s["opp_played"] and s["week"] > 1 and not s["rival"]:
        q("opp", 2, rng.choice([f"{o.school} comes in {o.record}. What stands out on film?",
                                f"What worries you most about {o.school}?",
                                f"What's the key to beating {o.school} ({o.record}) this week?"]),
          [("measured", "They're well-coached and they don't beat themselves.", None),
           ("confident", "They're good, but we like our matchups.", None),
           ("humble", f"{s['opp_coach'] or 'Their staff'} does a great job. We'll have our hands full.", None)])

    # ── people ──
    if s["qb"] is not None and s.get("qb_ints", 0) >= 6 and s["week"] > 3:
        q("qb_ints", 8, f"{s['qb'].name} has thrown {s['qb_ints']} interceptions. Is he still your guy?",
          [("confident", "Yes. And it's not close. He's our quarterback.", ("qb", 1)),
           ("measured", "He's our starter this week. We'll keep evaluating everybody.",
            [("qb", -1), ("follow", "qb_hedge")]),
           ("fiery", "Some of those are on the receivers and some are on me. Put it on me.", ("qb", 1))])
    elif s["qb"] is not None and s["week"] > 3 and (s.get("qb_tds", 0) >= 20 or (s.get("qb_tds", 0) >= 14 and s["rank"])):
        q("qb_good", 5, f"{s['qb'].name} has {s['qb_tds']} touchdown passes. Golden Helmet talk — fair?",
          [("confident", "Put his tape next to anybody's.", ("qb", 1)),
           ("humble", "He'd tell you it's the guys around him. He'd be right.", None),
           ("measured", "Individual awards take care of themselves when you win.", None)])
    if s["star_out"] is not None:
        p = s["star_out"]
        q("injury", 7, f"{p.name} is out. How does that change what you do?",
          [("measured", "Next man up is a cliche because it's true. We've prepared for it.", None),
           ("confident", "It doesn't. The guy behind him has been waiting for this.", ("lift", 0.05)),
           ("humble", f"You don't replace a {p.position} like {p.first_name}. We'll adjust.", None)])

    # ── the job ──
    if s["seat"] >= s["fire_line"] - 15 and s["losses"] >= 2:
        q("seat", 8, "There's a lot of talk about your job security. Your response?",
          [("measured", "My focus is on this team and this week. That's all I control.", None),
           ("fiery", "Talk is cheap. Watch us play Saturday.",
            [("lift", 0.15), ("fx", {"stake": {"on": "next", "hint": "you told them to watch Saturday",
                                               "win": {"seat": -2}, "loss": {"seat": 2},
                                               "who": f"AD {t.ad['name']}", "subject": "Watch us play Saturday",
                                               "wtext": "You told them to watch Saturday. They watched. Good.",
                                               "ltext": "You told the whole state to watch Saturday. They did."}})]),
           ("humble", "I understand the standard here. I'm the one who has to meet it.", [("seat", -1), ("chem", 1)])])
    if s["last_home"] and s["week"] >= 11:
        q("senior", 7, "Last home game for your seniors. What do they mean to this program?",
          [("humble", "Everything. They stuck with this place through a lot. I want to send them out right.",
            ("lift", 0.15)),
           ("measured", "They've given us a lot. We'll honor them by playing well.", None),
           ("fiery", "They deserve to walk off that field winners. That's the only acceptable ending.",
            ("lift", 0.15))])
    if s["commits"] >= 8 and s["week"] >= 3:
        q("recruit", 4, f"You've got {s['commits']} commitments already. What's the pitch working on the trail?",
          [("confident", "Kids see what we're building and they want in. It's that simple.", ("recruits", 2)),
           ("measured", "Development and honesty. We tell them the truth.", ("recruits", 1)),
           ("humble", "Our players do the recruiting. Recruits trust other 18-year-olds.", ("recruits", 1))])
    # ── the everyday stuff: always something to ask ──
    young = sorted((p for p in t.roster if p.year == 0), key=lambda p: -p.overall)
    if young and s["week"] <= 6:
        p = young[0]
        q("young", 1.5, f"Any young players standing out in practice?",
          [("confident", f"{p.name}. Remember that name.", ("recruits", 1)),
           ("measured", "A few. They'll get their chances when they're ready.", None),
           ("humble", f"{p.first_name} has been impressive, but the older guys are teaching him a lot.", None)])
    q("health", 1, rng.choice([f"How's the health of the team heading into {o.school}?",
                               "Anybody banged up after last week?"]),
      [("measured", "About what you'd expect this time of year. We'll know more Thursday.", None),
       ("confident", "We're as healthy as we've been. No excuses.", None),
       ("humble", "Guys are playing through a lot. I'm proud of how they've handled it.", None)])
    q("matchup", 1, rng.choice([f"What's the key matchup against {o.school}?" if s["week"] > 1 else
                                f"What's the key to Saturday against {o.school}?",
                                "Where does this game get won?"]),
      [("measured", "Up front. It always is. Whoever controls the line of scrimmage.", None),
       ("confident", "Our playmakers against theirs. We like ours.", None),
       ("fiery", "Whoever wants it more. And we're going to want it more.", ("lift", 0.05))])
    q("crowd" if s["home"] else "road", 1,
      "Home crowd this week. How much does it matter?" if s["home"] else
      f"You're on the road at {o.school}. How do you handle the noise?",
      [("confident", "It's worth a touchdown. Our fans know it." if s["home"] else
        "We like playing on the road. It's us against everybody.", None),
       ("measured", "It helps, but it doesn't block anybody." if s["home"] else
        "Silent counts all week. We've prepared for it.", None),
       ("humble", "We need them. We'll give them something to cheer about." if s["home"] else
        "It's a great environment. We'll have to play our best.", None)])
    q("message", 1, "What's your message to the fan base this week?",
      [("confident", "Buy a ticket. You're going to want to see this team.", ("recruits", 1)),
       ("humble", "Thank you. We feel it. We'll keep working to deserve it.", None),
       ("fiery", "Be loud. Be early. We'll handle the rest.", ("lift", 0.05))])
    if s["last"] is not None and s.get("last_rush", 99) < 90:
        q("run_game", 3, f"Only {s['last_rush']} rushing yards last week. Is the run game broken?",
          [("measured", "It's a work in progress. We'll find what works.", None),
           ("fiery", "We're going to run it until they stop it. They didn't stop it — we did.", ("lift", 0.05)),
           ("confident", "Not broken. We've got a plan for this week.", None)])
    _more(s, q)
    _procedural_context(s, q)
    if s["week"] >= 10 and not s.get("next_qb_clear"):
        q("next_qb", 7, "Next season you don't have a clear answer behind center. How do you plan to address this?",
          [("confident", "We'll find the answer. Whether he's in our room or somewhere else, we'll get it right.",
            ("fx", {"recruits": 0.8, "chem": -1})),
           ("measured", "We'll evaluate the room, recruit the position and use the portal if it makes sense.",
            ("fx", {"clutch": 0.05, "recruits": -0.2})),
           ("humble", "The young quarterbacks here deserve the first opportunity to earn it.",
            ("fx", {"chem": 1, "recruits": -0.5})),
           ("fiery", "It's an open competition. Nobody gets handed the keys around here.",
            ("fx", {"lift": 0.1, "chem": -1, "recruits": 0.3}))])
    if s.get("class_rank") and s["class_rank"] <= 10 and s["week"] >= 8:
        q("class_context", 5, f"Your recruiting class is No. {s['class_rank']} right now. How much does that validate what you're building?",
          [("confident", "It tells you players see where this is going. We expect to finish even stronger.", ("fx", {"recruits": 0.8, "seat": 1})),
           ("measured", "Rankings are nice. Fit matters more, and we still have work to do.", ("fx", {"clutch": 0.05, "recruits": -0.2})),
           ("humble", "Credit our staff and our players. They're the ones recruits believe in.", ("fx", {"chem": 1, "recruits": -0.4})),
           ("fiery", "We're not trying to win signing-day headlines. We're trying to build a championship roster.", ("fx", {"lift": 0.08, "recruits": 0.4, "seat": 1}))])
    if s["week"] == 13:
        q("grade", 4, f"Last game of the regular season. How would you grade the year?",
          [("measured", "Incomplete. There's still a game to play.", None),
           ("humble", "Not good enough. That starts with me.", None) if s["wins"] < s["losses"] else
           ("humble", "Proud of these kids. They've given everything.", None),
           ("confident", "We'll finish it the right way, and then you can grade it.", None)])
    return qs



def _procedural_context(s, q):
    """Questions that exist because of where the program is in the season, not a random quote bank."""
    t, o = s["team"], s["opp"]
    played = s["wins"] + s["losses"]
    qb = s.get("qb")
    if s["week"] >= 5 and s["streak"] >= 3 and s["streak_win"]:
        q("expectations", 6, f"You've won {s['streak']} straight. Has the conversation inside the building changed?",
          [("confident", "It should. Winning changes expectations, and we're not hiding from that.", ("fx", {"recruits": .7, "opp_lift": .15})),
           ("measured", "The standard hasn't changed. The evidence that we can meet it has.", ("fx", {"clutch": .08, "recruits": -.2})),
           ("humble", "The record gives us credibility. It doesn't give us a single point Saturday.", ("fx", {"chem": 1, "recruits": -.35})),
           ("fiery", "Good. Now people expect us to win. Our players earned that pressure.", ("fx", {"lift": .12, "clutch": -.04, "opp_lift": .1}))])
    if s["week"] >= 5 and s["streak"] >= 2 and s["streak_win"] is False:
        q("response", 7, f"Two straight losses have changed the mood around the program. What has to change first?",
          [("humble", "Me. The head coach sets the week, and I have to set a better one.", ("fx", {"chem": 1, "recruits": -.35})),
           ("measured", "Our details. Bad stretches get worse when you start chasing magic fixes.", ("fx", {"clutch": .1, "lift": -.04})),
           ("fiery", "Our edge. We have been too comfortable, and that ends now.", ("fx", {"lift": .15, "chem": -1})),
           ("confident", "Nothing is broken. Win Saturday and the conversation changes again.", ("fx", {"recruits": .5, "seat": 1}))])
    if s["rank"] and s["rank"] <= 12 and s["week"] >= 7:
        q("stakes", 5, f"At No. {s['rank']}, every result is starting to carry national consequences. Do you talk about that with the team?",
          [("confident", "Absolutely. They came here to play meaningful games. This is what meaningful feels like.", ("fx", {"recruits": .8, "opp_lift": .15})),
           ("measured", "We acknowledge it once, then get back to the opponent in front of us.", ("fx", {"clutch": .08, "recruits": -.2})),
           ("humble", "The ranking is borrowed. We have to earn it again every Saturday.", ("fx", {"chem": 1, "recruits": -.4})),
           ("fiery", "Pressure is a privilege. I want them feeling every ounce of it.", ("fx", {"lift": .12, "clutch": -.05}))])
    if qb is not None and getattr(qb, "year", 0) >= 3 and s["week"] >= 8:
        q("qb_legacy", 5, f"You're getting late in the year with {qb.name}. How much are you thinking about what this offense looks like after him?",
          [("confident", "We've planned for it. Good programs don't let one graduation reset the position.", ("fx", {"recruits": .7, "chem": -1})),
           ("measured", f"Enough to prepare, not enough to steal a week from {qb.first_name} and this team.", ("fx", {"clutch": .06, "recruits": -.2})),
           ("humble", f"Right now I want {qb.first_name} to finish his story the right way. The next chapter can wait.", ("fx", {"chem": 1, "recruits": -.4})),
           ("fiery", "The next quarterback is watching how this one leads. Competition never waits for January.", ("fx", {"lift": .08, "chem": -1, "recruits": .25}))])
    young = [p for p in t.roster if getattr(p, "year", 9) == 0 and getattr(p, "overall", 0) >= 70]
    if len(young) >= 3 and s["week"] >= 6:
        q("youth", 4, f"You have {len(young)} freshmen already forcing their way into the conversation. Is the timetable changing?",
          [("confident", "Talent changes timetables. If they're ready, we're not making them wait.", ("fx", {"recruits": .8, "chem": -1})),
           ("measured", "Their role grows when their consistency does. That's the deal.", ("fx", {"clutch": .05, "recruits": -.15})),
           ("humble", "The veterans are teaching them how to be college players. That matters more than hype.", ("fx", {"chem": 1, "recruits": -.35})),
           ("fiery", "I don't care what year is next to your name. Take the job and it's yours.", ("fx", {"lift": .1, "chem": -1, "recruits": .35}))])
    if s["rival"] and s["week"] >= 8:
        q("rival_weight", 8, f"This is {o.school}. At this point in the season, can a rivalry game redefine the whole year?",
          [("confident", "Yes. Big games are supposed to define programs. We intend to define this one.", [("recruits", .8), ("follow", "guarantee")]),
           ("measured", "It can shape the year. It can't erase everything that came before it.", ("fx", {"clutch": .08, "recruits": -.2})),
           ("humble", "It means more to a lot of people than one Saturday usually does. We respect that.", ("fx", {"chem": 1, "recruits": -.35})),
           ("fiery", "If you need me to explain what this game means, you haven't been in our building this week.", ("fx", {"lift": .15, "opp_lift": .2}))])
    if played >= 8 and s["wins"] == s["losses"]:
        q("identity", 4, f"At {t.record}, do you know what kind of team you have yet?",
          [("confident", "Yes. A better team than the record says, and we have time to prove it.", ("fx", {"recruits": .45, "seat": 1})),
           ("measured", "We're inconsistent. Naming it honestly is the first step toward fixing it.", ("fx", {"clutch": .08, "recruits": -.2})),
           ("humble", "We're still becoming one. I have to give them a clearer identity.", ("fx", {"chem": 1, "recruits": -.35})),
           ("fiery", "We're a team that's about to find out who actually wants to finish.", ("fx", {"lift": .12, "chem": -1}))])

def _more(s, q):
    """More of the week's real storylines."""
    t, o = s["team"], s["opp"]
    if s["week"] == 1 and not s["first_game_ever"] and not s["first_game_here"]:
        q("opener", 6, "Season opener this week. What are you still trying to figure out about this team?",
          [("measured", "Who we are when it gets hard. You only learn that in a game.", None),
           ("confident", "Not much. We know who we are. Now we go show it.", ("lift", 0.05)),
           ("humble", "Plenty. Young team in spots. We'll learn a lot on Saturday.", None)])
    if s["opp_rank"] and s["rank"] and s["opp_rank"] < s["rank"]:
        q("ranked_opp", 6, f"No. {s['opp_rank']} {o} is ranked ahead of you. Do you feel disrespected?",
          [("fiery", "Rankings don't play. We'll settle it on the field.", ("lift", 0.15)),
           ("measured", "It's early. Polls sort themselves out.", None),
           ("humble", f"They've earned it. We haven't yet.", None)])
    if s.get("star_out") is not None:
        p = s["star_out"]
        q("injury", 7, f"How does your team replace {p.name}?",
          [("confident", "Next man up. We recruit for this.", ("lift", 0.05)),
           ("measured", "By committee. Nobody has to be him — everybody has to do a little more.", None),
           ("humble", f"You don't replace {p.first_name}. We'll adjust.", None)])
    if s.get("qb_ints", 0) >= 5 and s["week"] >= 4:
        q("qb_ints", 6, f"{s['qb'].name} has {s['qb_ints']} interceptions. Is there a quarterback competition?",
          [("confident", f"No. {s['qb'].first_name} is our guy. Period.", ("qb", 1)),
           ("measured", "Everybody competes every day. That includes quarterbacks.",
            [("qb", -1), ("follow", "qb_hedge")]),
           ("fiery", "He'll clean it up. He knows it better than anybody.", ("qb", 1))])
    if s.get("commits", 0) >= 12 and s.get("class_rank") and s["class_rank"] <= 15:
        q("class", 3, f"Your recruiting class is ranked No. {s['class_rank']}. Does winning on Saturday help close it?",
          [("confident", "Winning helps everything. And we plan on winning.", ("recruits", 1)),
           ("measured", "It helps. Relationships close classes.", None),
           ("humble", "These kids are choosing people, not a scoreboard.", ("recruits", 1))])
    if s["last_home"]:
        q("senior", 6, "Senior day this week. What has this class meant to you?",
          [("humble", "Everything. They believed before there was much to believe in.", ("lift", 0.1)),
           ("measured", "They set the standard. We want to send them out right.", ("lift", 0.05)),
           ("fiery", "They deserve a win, and they're going to get one.", ("lift", 0.1))])
    _newer(s, q)
    if s["opp_coach"] and s.get("opp_played") and o.losses >= o.wins + 2:
        q("trap", 3, f"{o} is {o.record}. Is this a trap game?",
          [("measured", "Their film doesn't look like their record. We'll be ready.", None),
           ("fiery", "There's no such thing. Not in our building.", ("lift", 0.05)),
           ("confident", "We just have to play our game.", ("opp", 0))])


def _newer(s, q):
    """The locker room, suspensions, the job market, the money, the staff."""
    import personalities as pz
    t, o = s["team"], s["opp"]
    if pz.chemistry(t) < 40 and s["week"] >= 2:
        trouble = max((p for p in t.roster if any(x in pz.TROUBLE_TRAITS for x in p.traits)),
                      key=lambda p: p.overall, default=None)
        q("chem", 7, "There are reports of friction in your locker room. Is that true?",
          [("confident", "Not true. Come watch practice.", [("recruits", 0.5), ("chem", -1)]),
           ("humble", "Every team has growing pains. We're working through ours.", ("chem", 2)),
           ("fiery", "Whoever's talking to you should come talk to me.",
            [("chem", -2), ("fx", {"who": trouble, "unhappy": True} if trouble else {})])])
    sus = [p for p in t.roster if getattr(p, "suspended", False)]
    if sus:
        p = max(sus, key=lambda x: x.overall)
        q("suspension", 8, f"Why is {p.name} suspended?",
          [("measured", "It's a team matter. It stays in the building.", ("chem", 1)),
           ("fiery", "He broke a rule. Rules apply to everybody here.",
            [("chem", 2), ("fx", {"who": p, "unhappy": True})]),
           ("humble", f"{p.first_name}'s a good kid who made a mistake. We'll get him back.",
            [("chem", -1), ("fx", {"who": p, "bought_in": True})])])
    if s["seat"] <= 20 and s["wins"] >= 6 and s["week"] >= 9:
        q("job", 7, "Your name keeps coming up for bigger jobs. Are you staying?",
          [("confident", "I'm not going anywhere. Put it in print.", ("recruits", 2)),
           ("measured", "I don't talk about other jobs during the season.",
            [("recruits", -1), ("seat", by_ad(t, {"default": 0, "booster": 1, "politician": 1}))]),
           ("humble", "I'm flattered. My focus is this team.", ("chem", 1))])
    if s["week"] >= 4 and s["week"] % 4 == 0:
        q("nil", 3, "Is NIL making it harder to keep a roster together?",
          [("confident", "Players stay where they get developed. They stay here.", ("recruits", 1)),
           ("measured", "It's the landscape. Everybody's adapting.", None),
           ("humble", "Honestly? Yes. We have to do better, and that starts with me.",
            ("fx", {"recruits": -0.5, "money": by_ad(t, {"default": 50_000, "booster": 150_000, "budget": 0}),
                    "money_what": "the AD heard you at the podium", "ask": True}))])
    oc = getattr(t, "oc", None)
    if oc is not None and s["week"] >= 6:
        try:
            import staff
            buzz = staff.buzz_score(oc)
        except Exception:
            buzz = 0
        if buzz >= 7:
            q("oc_buzz", 5, f"{oc.name} is getting head-coach buzz. Can you keep him?",
              [("confident", "He's here because he wants to be here.", ("fx", {"coord": oc, "stay": -1})),
               ("humble", "If he gets his chance, I'll be the first one to congratulate him.",
                ("fx", {"coord": oc, "stay": 1, "recruits": 1, "chem": 1})),
               ("measured", "He's focused on this week. So am I.", None)])


def questions(league, team, g, n=3):
    """Three questions for this week — the most pressing ones, and nothing the
    room already asked in the last few weeks."""
    rng = random.Random(f"presser:{league.seed}:{league.year}:{league.week}:{team.school}")
    s = _situation(league, team, g)
    asked = league.__dict__.setdefault("_presser_asked", {}).setdefault(league.year, {})
    cooldown = {"unbeaten": 3, "streak_w": 3, "streak_l": 3, "seat": 3, "win": 2, "opp": 2}
    qs = sorted(_bank(s, rng), key=lambda x: -x[0])
    out, kinds = [], set()
    for pri, kind, text, answers in qs:
        if kind in kinds:
            continue
        last = asked.get(kind)
        if last is not None and s["week"] - last < cooldown.get(kind, 2 if pri < 5 else 1) + 1:
            continue
        kinds.add(kind)
        out.append((kind, text, answers))
        if len(out) == n:
            break
    for kind, _, _ in out:
        asked[kind] = s["week"]
    return [(text, answers) for _, text, answers in out], s


# ═══ The podium ═════════════════════════════════════════════════════════════

TONE_COLOR = {"confident": C.BYELLOW, "measured": C.BWHITE, "fiery": C.BRED, "humble": C.BCYAN}


@moments.moment("presser")
def press_conference(league, team, g):
    """Two questions from the real week. Returns the week's presser effects (the
    effects themselves are already banked for Saturday — see podium.py)."""
    import podium
    qs, s = questions(league, team, g)
    eff = {"lift": league.__dict__.pop("_postgame_lift", 0.0), "opp_lift": 0.0}   # an older save's podium
    clear()
    print(title_bar("THURSDAY  ·  PRESS CONFERENCE"))
    print(paint("\n   Cameras up. Every answer has an upside and a cost — read the line under it.", C.GRAY))
    import webview
    webview.emit("presser", {"title": "Thursday · Press conference",
                             "intro": "Cameras up. Every answer has an upside and a cost — read the line under it."})
    ctx = {"league": league, "team": team, "opp": s["opp"], "qb": s["qb"], "underdog": s["wp"] < 0.45,
           "won": None}
    said, total = podium.run(league, qs, "thu", ctx)
    print()
    print(podium.summary(total))
    import webview
    webview.emit("sum", {"text": webview.plain(podium.summary(total))}, add=True)
    pause()
    eff["said"] = said
    return eff


def _seat(league, coach, d, why):
    import effects
    effects._seat(league, coach, d, why)
