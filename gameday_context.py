"""
gameday_context.py — What the Campus Countdown crew knows about the season.

The show used to know the featured game very well and the rest of the sport in
passing. This file is the rest of the sport: every week it reads the whole
season and finds the stories people are actually talking about —

  a preseason top-10 team that's 0-2, or has lost two straight
  the team nobody ranked in August that's now in the top ten
  the defending champion (rolling, or reeling)
  winless programs, long losing streaks, long winning streaks
  unbeaten teams and a Group of Five team crashing the playoff conversation
  the Golden Helmet race (a leader, a gap, a new name)
  league races that are tight, and teams that have run away with them
  first-year coaches who've flipped a program, and coaches whose seats are on fire
  a team playing under a postseason ban, a school in its first year in a new league
  an offense on a record pace, a defense nobody can score on
  a locker room coming apart, a star lost for the season, the poll's biggest fall

— and it gives the crew a real conversation about each one: the number that
frames it, a diagnosis read off the season (turnovers, the quarterback, the
defense, close losses, injuries, a new staff, a brutal schedule), someone who
disagrees, and what comes next (including who they play next week).

The same pieces feed the rest of the show: short "context notes" for the
previews and recaps, questions for the one-on-one interview, and signs.
Nothing is told twice in a row unless the story has moved.
"""
import world
import random

from ui import C

POWER = world.POWER


# ═══ Reading a team's season ═══════════════════════════════════════════════

def pre_rank(league, t):
    pr = getattr(league.rankings, "preseason_ranks", None) or {}
    return pr.get(t.school)


def played(league, t):
    return [g for g in league.team_games(t) if g.played]


def streak(league, t):
    kind, n = None, 0
    for g in reversed(played(league, t)):
        k = "W" if g.winner is t else "L"
        if kind is None:
            kind = k
        if k != kind:
            break
        n += 1
    return kind, n


def next_game(league, t):
    for w in sorted(league.schedule):
        if w <= league.week:
            continue
        for g in league.schedule[w]:
            if t in (g.home, g.away) and not g.played:
                return g
    return None


def this_game(league, t, games):
    return next((g for g in games if t in (g.home, g.away) and not g.played), None)


def ppg(t):
    n = max(1, t.wins + t.losses)
    return t.points_for / n, t.points_against / n


def _rank_s(league, t):
    r = league.rankings.rank_of(t)
    return f"No. {r} {t.school}" if r else t.school


def _qb(t):
    import gameday_dossier as gd
    return gd._qb(t)


def diagnose(league, t):
    """Why a team is struggling — the reasons a good analyst would find. [(tag, text)]"""
    out = []
    games = played(league, t)
    if not games:
        return out
    close = [g for g in games if g.loser is t and g.score_for(g.winner) - g.score_for(t) <= 7]
    if len(close) >= 2:
        out.append(("close", f"They've lost {len(close)} one-score games. That's a play here, a play there — "
                             f"and it's also a team that doesn't finish."))
    qb = _qb(t)
    if qb is not None:
        s = qb.season_stats
        if s["pass_att"] >= 60 and s["pass_int"] >= max(5, s["pass_td"]):
            out.append(("qb", f"{qb.name} has thrown {s['pass_int']} interceptions to {s['pass_td']} touchdowns. "
                              f"You can't win like that at quarterback."))
    pf, pa = ppg(t)
    last = [r for r in getattr(t, "historical_records", []) if r[0] == league.year - 1]
    if pa >= 30:
        out.append(("defense", f"They're giving up {pa:.0f} points a game. That's not a scheme problem, that's a "
                               f"tackling-and-effort problem."))
    if pf <= 20 and t.wins + t.losses >= 3:
        out.append(("offense", f"{pf:.0f} points a game. The offense has no identity — they don't know what "
                               f"they are on third-and-5."))
    hurt = [p for p in t.injured() if p in t.players_at(p.position)[:1] and p.position in ("QB", "RB", "WR", "DL", "LB", "CB")]
    if hurt:
        p = hurt[0]
        out.append(("injury", f"They're without {p.name}, their starting {p.position}. People forget how much "
                              f"one guy matters."))
    if getattr(t.coach, "hired_year", None) == league.year:
        out.append(("new_staff", f"New staff, new system. Year one under {t.coach.name} was always going to have "
                                 f"growing pains."))
    ranked_losses = [g for g in games if g.loser is t and (getattr(g, "ranks", {}) or {}).get(g.winner)]
    if len(ranked_losses) >= 2:
        out.append(("schedule", f"To be fair, {len(ranked_losses)} of those losses came against ranked teams. "
                                f"The schedule hasn't done them any favors."))
    if getattr(t, "chemistry", 50) < 38:
        out.append(("room", "And from what I'm hearing, that locker room isn't together. Talent doesn't matter "
                            "if they're not playing for each other."))
    return out


def strengths(league, t):
    out = []
    pf, pa = ppg(t)
    qb = _qb(t)
    if qb is not None and qb.season_stats["pass_att"] >= 60:
        s = qb.season_stats
        ypa = s["pass_yds"] / max(1, s["pass_att"])
        if ypa >= 8.5 or s["pass_td"] >= 3 * max(1, s["pass_int"]):
            out.append(("qb", f"{qb.name} is playing at a different level: {s['pass_yds']:,} yards, "
                              f"{s['pass_td']} touchdowns, {s['pass_int']} picks."))
    if pa <= 16 and t.wins + t.losses >= 3:
        out.append(("defense", f"The defense is allowing {pa:.0f} points a game. Everything starts there."))
    if pf >= 38:
        out.append(("offense", f"They're scoring {pf:.0f} a game. You have to be perfect to keep up."))
    close = [g for g in played(league, t) if g.winner is t and g.score_for(t) - g.score_for(g.loser) <= 7]
    if len(close) >= 2:
        out.append(("close", f"They've won {len(close)} one-score games. Some people call that luck. I call it a "
                             f"team that knows how to finish."))
    if getattr(t.coach, "hired_year", None) == league.year:
        out.append(("coach", f"And give {t.coach.name} credit — first year, and they already play like his team."))
    if getattr(t, "chemistry", 50) >= 68:
        out.append(("room", "The locker room is as tight as any in the country. You see it when things go wrong — "
                            "nobody points fingers."))
    return out


def note(league, t):
    """A short context note for previews and recaps, or None."""
    pr = pre_rank(league, t)
    r = league.rankings.rank_of(t)
    kind, n = streak(league, t)
    if pr and pr <= 12 and t.losses >= 2 and t.wins <= t.losses:
        return f"preseason No. {pr} and {t.record}"
    if pr and pr <= 10 and kind == "L" and n >= 2:
        return f"preseason No. {pr}, and losers of {n} straight"
    if not pr and r and r <= 12:
        return f"unranked in August, No. {r} now"
    if t.losses == 0 and t.wins >= 5:
        return f"one of the country's unbeaten teams at {t.record}"
    if t.wins == 0 and t.losses >= 3:
        return f"still looking for a win at {t.record}"
    if kind == "W" and n >= 5:
        return f"winners of {n} straight"
    if kind == "L" and n >= 3:
        return f"losers of {n} straight"
    import dynasty
    if dynasty.banned(league, t):
        return "playing under a CAB postseason ban"
    hist = getattr(t, "conf_history", None)
    if hist and len(hist) > 1 and hist[-1][0] == league.year:
        return f"in its first season in the {t.conference}"
    if getattr(t.coach, "seat", 0) >= 82 and t.losses >= 2:
        return f"playing for {t.coach.name}'s job"
    return None


# ═══ The season's storylines ═══════════════════════════════════════════════

def storylines(league, show):
    L, wk = league, league.week
    out = []
    feat = {show.h, show.a}

    def add(kind, weight, key, **data):
        out.append({"kind": kind, "weight": weight, "key": key, **data})

    teams = [t for t in L.teams]
    for t in teams:
        pr = pre_rank(L, t)
        r = L.rankings.rank_of(t)
        kind, n = streak(L, t)
        g = t.wins + t.losses
        if g == 0:
            continue
        # preseason contenders in trouble
        if pr and pr <= 12:
            if t.wins == 0 and t.losses >= 2:
                add("flop", 120 - pr * 3 + t.losses * 6, f"flop:{t.school}:{t.record}", team=t, pr=pr)
            elif kind == "L" and n >= 2 and g <= 6:
                add("flop", 95 - pr * 3 + n * 6, f"flop:{t.school}:{t.record}", team=t, pr=pr)
            elif t.losses >= 3 and t.losses > t.wins - 2:
                add("flop", 80 - pr * 2 + t.losses * 4, f"flop:{t.school}:{t.record}", team=t, pr=pr)
        # the team nobody saw coming
        if not pr and r and r <= 12 and g >= 4:
            add("surprise", 70 + (13 - r) * 3, f"surprise:{t.school}:{r // 4}", team=t, r=r)
        elif pr and pr >= 20 and r and r <= 6 and g >= 5:
            add("surprise", 62 + (7 - r) * 3, f"surprise:{t.school}:{r // 3}", team=t, r=r, pr=pr)
        # winless
        if t.wins == 0 and t.losses >= 5:
            add("winless", 40 + t.losses * 3 + (t.prestige - 50) * 0.8, f"winless:{t.school}:{t.losses // 2}", team=t)
        # long streaks
        if kind == "W" and n >= 7 and t.losses >= 1:
            add("hot", 45 + n * 3, f"hot:{t.school}:{n // 3}", team=t, n=n)
        if kind == "L" and n >= 4 and t.prestige >= 70 and t.wins >= 1:
            add("skid", 50 + n * 5 + (t.prestige - 70), f"skid:{t.school}:{n}", team=t, n=n)
        # sanctions
        import dynasty
        if dynasty.banned(L, t) and t.wins >= 5 and t.losses <= 2:
            add("banned", 58, f"banned:{t.school}:{t.wins // 3}", team=t)
        # first year in a new league
        hist = getattr(t, "conf_history", None)
        if hist and len(hist) > 1 and hist[-1][0] == L.year and wk >= 3 and t.conf_wins + t.conf_losses >= 1:
            add("newleague", 42 + (15 if t.conf_losses == 0 and t.conf_wins >= 2 else 0),
                f"newleague:{t.school}:{t.conf_wins}-{t.conf_losses}", team=t)
        # the chair
        c = t.coach
        if c is not None and getattr(c, "seat", 0) >= 85 and t.losses >= 3 and wk >= 5 and not getattr(c, "is_user", False):
            add("seat", 44 + (c.seat - 85) + (t.prestige - 60) * 0.4, f"seat:{t.school}:{t.record}", team=t)
        if c is not None and getattr(c, "hired_year", None) == L.year and wk >= 4:
            last = t.last_season
            if last and last[0] <= last[1] and t.wins >= t.losses + 3:
                add("turnaround", 55 + (t.wins - t.losses) * 3, f"turnaround:{t.school}:{t.wins // 3}",
                    team=t, last=last)
        # offense / defense on a pace
        pf, pa = ppg(t)
        if g >= 5 and pf >= 45:
            add("offense", 40 + (pf - 45) * 2, f"offense:{t.school}:{wk // 3}", team=t, pf=pf)
        if g >= 5 and pa <= 11:
            add("defense", 40 + (11 - pa) * 3, f"defense:{t.school}:{wk // 3}", team=t, pa=pa)
    # the defending champion
    champ = L.champion_of(L.year - 1)
    if champ is not None:
        ct = next((t for t in teams if t.school == champ.champion), None)
        if ct is not None and ct.wins + ct.losses >= 2 and (wk <= 4 or wk % 3 == 0):
            state = "rolling" if ct.losses == 0 else "reeling" if ct.losses >= 2 else "wobbling"
            add("champ", 48 + (20 if state == "reeling" else 8 if state == "rolling" else 5),
                f"champ:{ct.record}", team=ct, state=state)
    # unbeaten Group of Five
    g5 = [t for t in teams if t.conference not in POWER and t.school != world.FLAGSHIP_INDEPENDENT and t.losses == 0 and t.wins >= 6]
    if g5 and wk >= 7:
        t = max(g5, key=lambda x: (x.wins, -(L.rankings.rank_of(x) or 99)))
        add("g5", 58 + t.wins * 2, f"g5:{t.school}:{t.wins}", team=t)
    # Golden Helmet race
    h = L.rankings.heisman
    if h and len(h) >= 2 and wk >= 4:
        lead, second = h[0], h[1]
        prev = [x[0] if isinstance(x, (tuple, list)) else x for x in (getattr(L.rankings, "last_heisman", []) or [])[:1]]
        new_leader = prev and prev[0] is not lead[0]
        add("heisman", 46 + (18 if new_leader else 0) + (8 if wk >= 9 else 0), f"heisman:{lead[0].name}:{wk // 2}",
            p=lead[0], p2=second[0], new=bool(new_leader))
    # league races
    for conf in POWER:
        st = [t for t in L.standings(conf) if t.conf_wins + t.conf_losses >= 3]
        unb = [t for t in st if t.conf_losses == 0]
        if len(unb) >= 3 and wk >= 7:
            add("race", 44 + len(unb) * 4, f"race:{conf}:{len(unb)}", conf=conf, teams=unb)
    # the poll's free fall
    if wk >= 2:
        falls = []
        for t in teams:
            pr_, now = L.rankings.previous_rank(t), L.rankings.rank_of(t)
            if pr_ and pr_ <= 10 and (not now or now - pr_ >= 9):
                falls.append((pr_, t, now))
        if falls:
            pr_, t, now = min(falls, key=lambda x: x[0])
            add("fall", 52 + (11 - pr_) * 2, f"fall:{t.school}:{wk}", team=t, was=pr_, now=now)
    # a star lost for the season
    for t in teams:
        r = L.rankings.rank_of(t)
        if not r or r > 20:
            continue
        for p in t.injured():
            if p.position == "QB" and getattr(p, "inj_games", 0) >= 99 and getattr(p, "inj_week", -9) >= wk - 1 \
                    and p in t.players_at("QB")[:1] + [p]:
                add("star_out", 60 + (21 - r), f"starout:{p.name}", team=t, p=p)
                break
    # a locker room coming apart (from personalities)
    try:
        import personalities as pers
        for w, text in pers.news(L)[-60:]:
            if w == wk and ("players-only meeting" in text or "suspended 3" in text or "calls out teammates" in text):
                school = text.split(" ")[0]
                t = next((x for x in teams if text.startswith(x.school)), None)
                if t is not None and (L.rankings.rank_of(t) or t.prestige >= 75):
                    add("locker", 40, f"locker:{text[:40]}", team=t, text=text)
                    break
    except Exception:
        pass
    # memory: skip what we told last week unless it moved
    told = _told(show)
    fresh = []
    for s in out:
        if s["key"] in told:
            continue
        if any(x in feat for x in (s.get("team"),)) and s["kind"] not in ("heisman", "champ"):
            s["weight"] -= 25                      # the featured teams get their own segment
        fresh.append(s)
    fresh.sort(key=lambda s: -s["weight"])
    # at most one story per team, and not three of one kind
    seen, kinds, picked = set(), {}, []
    for s in fresh:
        t = s.get("team")
        if t is not None and t.school in seen:
            continue
        if kinds.get(s["kind"], 0) >= (2 if s["kind"] in ("flop", "surprise") else 1):
            continue
        picked.append(s)
        if t is not None:
            seen.add(t.school)
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    return picked


def _told(show):
    import gameday_show as gs
    st = gs._state(show.league)
    return st.setdefault("context_told", {}).setdefault(show.league.year, set())


def remember(show, s):
    _told(show).add(s["key"])


# ═══ Telling them ══════════════════════════════════════════════════════════

def _next_line(show, t):
    L = show.league
    g = this_game(L, t, show.games) or next_game(L, t)
    if g is None:
        return None
    o = g.opponent_of(t)
    when = "today" if g in show.games else "next"
    where = "at home" if g.home is t and not g.neutral else "on the road" if not g.neutral else "on a neutral field"
    ro = L.rankings.rank_of(o)
    return show.vary("ctx_next", [
        f"And it doesn't get easier: {'No. ' + str(ro) + ' ' if ro else ''}{o.school} {where} {when}.",
        f"{'Today' if when == 'today' else 'Next up'}: {o.school}, {where}. {'That’s a ranked team.' if ro else 'That’s a game they have to have.'}",
        f"They get {o.school} {when}. We'll find out what they're made of.",
    ]) if (ro or t.losses >= 2) else show.vary("ctx_next2", [
        f"{o.school} is {'today' if when == 'today' else 'up next'}.",
        f"Next for them: {o.school}, {where}.",
    ])


def tell(show, s):
    k = s["kind"]
    L = show.league
    fn = globals().get(f"_tell_{k}")
    if fn is None:
        return
    fn(show, s)
    remember(show, s)


def _tell_flop(show, s):
    t, pr = s["team"], s["pr"]
    kind, n = streak(show.league, t)
    losses = [g for g in played(show.league, t) if g.loser is t]
    lg = losses[-1]
    opp = lg.winner
    rec = t.record
    if t.wins == 0:
        open_ = show.vary("flop0", [
            f"We have to talk about {t.school}. Preseason No. {pr}. They're {rec}.",
            f"Preseason No. {pr} {t.school} is {rec}. Nobody saw that coming — nobody.",
            f"{t.school} started the year at No. {pr}. They haven't won a game yet.",
            f"Let's talk about the biggest shock of the season so far: {t.school}, preseason No. {pr}, is {rec}.",
        ])
    else:
        open_ = show.vary("flopn", [
            f"{t.school} came into the year at No. {pr}. They've now lost {n} straight and they're {rec}.",
            f"Preseason No. {pr} {t.school} is {rec}" + (f", losers of {n} in a row." if kind == "L" and n >= 2 else "."),
            f"Remember when {t.school} was a top-{pr if pr > 5 else 5} team? That was August. They're {rec}.",
        ])
    show.say("host", open_)
    show.say("host", f"Last week: {opp.school} {lg.score_for(opp)}, {t.school} {lg.score_for(t)}.")
    why = diagnose(show.league, t)
    if why:
        a = show.rng.choice(("film", "coach", "defender"))
        show.say(a, why[0][1])
        if len(why) > 1:
            b = show.rng.choice([x for x in ("film", "coach", "defender") if x != a])
            if why[1][0] == "schedule":
                show.say(b, why[1][1])                     # the defense of them, not a pile-on
            else:
                show.say(b, show.rng.choice(("And it's not just that. ", "It's more than that. ", "Add this: ")) + why[1][1])
    else:
        show.say("film", show.rng.choice((
            "Here's the thing — on paper, nothing's wrong. The talent is there. That's what makes it worse.",
            "I went back and watched all of it. It's not one thing. It's a hundred little things.")))
    show.say("boom", show.vary("flop_boom", [
        f"{t.school} fans, I'm sorry. I'm sincerely sorry.", f"I had {t.school} in my preseason top five. I'd like that deleted.",
        f"Somebody check on {t.school}. Seriously.", "That's the beauty of this sport. Nobody's safe. NOBODY.",
    ]))
    if t.losses <= 2 and show.league.week <= 6:
        show.say("coach", show.vary("flop_hope", [
            f"It's not over. Twelve teams make the playoff now. Win out and {t.school} is in the conversation.",
            "Don't bury them yet. I've had teams start slow. What matters is what you do in November.",
            "The good news is it's early. The bad news is there's no margin left.",
        ]))
    else:
        show.say("coach", show.vary("flop_done", [
            f"The playoff's gone. Now it's about pride — and finding out who in that building still wants to play.",
            f"At this point, {t.school} is playing for a bowl game and for next year.",
            f"Somebody's going to pay for this season in that building. That's the reality.",
        ]))
    nl = _next_line(show, t)
    if nl:
        show.say("host", nl)


def _tell_surprise(show, s):
    t, r = s["team"], s["r"]
    pr = s.get("pr")
    open_ = (f"Nobody ranked {t.school} in August. They're {t.record} and No. {r}." if not pr
             else f"{t.school} started at No. {pr}. They're {t.record} and up to No. {r}.")
    show.say("host", show.vary("sur_open", [open_, f"The story nobody predicted: {t.school}, {t.record}, No. {r} in the country.",
                                            f"How about {t.school}? {t.record}. No. {r}. I did not have that on my bingo card."]))
    good = strengths(show.league, t)
    if good:
        show.say(show.rng.choice(("film", "defender")), good[0][1])
        if len(good) > 1 and show.rng.random() < 0.6:
            show.say("coach", good[1][1])
    show.say("boom", show.vary("sur_boom", [f"I'm ALL IN on {t.school}. Book my flight.",
                                             f"{t.school} is the most fun team in the country. Don't @ me.",
                                             "This is why you play the games! This is why!"]))
    show.say(show.rng.choice(("coach", "film")), show.vary("sur_doubt", [
        f"I'll believe it when they beat somebody in November. Their schedule's been kind.",
        f"Real test is still coming. But they've earned the number.",
        f"They're not a fluke. I've seen the tape. They're good.",
    ]))
    nl = _next_line(show, t)
    if nl:
        show.say("host", nl)


def _tell_winless(show, s):
    t = s["team"]
    show.say("host", show.vary("wl_open", [f"{t.school} is {t.record}.", f"Still no wins for {t.school} — {t.record}.",
                                           f"It's been a long year at {t.school}: {t.record}."]))
    why = diagnose(show.league, t)
    show.say("coach", why[0][1] if why else "It's hard to watch. You feel for the players.")
    show.say("defender", show.vary("wl_take", [f"Somebody's going to get that first win against them and it's going to feel like a loss.",
                                                "One win changes a locker room. They need one bad.",
                                                f"{t.coach.name} has to find something — anything — to build on."]))


def _tell_hot(show, s):
    t, n = s["team"], s["n"]
    show.say("host", show.vary("hot_open", [f"{t.school} has won {n} straight.", f"Nobody's hotter than {t.school}: {n} in a row.",
                                            f"{n} straight wins for {t.school}. They lost early and haven't lost since."]))
    good = strengths(show.league, t)
    show.say("film", good[0][1] if good else "They're playing their best football right now, and that's what you want in November.")
    show.say("boom", "Nobody wants to see them in December. NOBODY.")


def _tell_skid(show, s):
    t, n = s["team"], s["n"]
    show.say("host", show.vary("skid_open", [f"{t.school} has lost {n} straight.", f"{n} losses in a row for {t.school}. They're {t.record}.",
                                             f"Something's broken at {t.school}. {n} straight losses."]))
    why = diagnose(show.league, t)
    if why:
        show.say("film", why[0][1])
    show.say("coach", f"Losing is contagious. When it starts, everybody starts playing not to make the mistake. "
                      f"That's when you make more of them.")
    nl = _next_line(show, t)
    if nl:
        show.say("host", nl)


def _tell_banned(show, s):
    t = s["team"]
    sanc = getattr(t, "sanctions", {}) or {}
    show.say("host", f"{t.school} is {t.record} — and it doesn't matter. They're banned from the postseason "
                     f"this year{(' for ' + sanc['why']) if sanc.get('why') else ''}.")
    show.say("coach", "Those kids didn't do anything wrong, and they're playing like it. That says everything about that locker room.")
    show.say("boom", f"If {t.school} runs the table, I'm giving them a trophy myself. I'll make it out of tinfoil.")


def _tell_newleague(show, s):
    t = s["team"]
    hist = t.conf_history
    old = hist[-2][1]
    show.say("host", f"First year in the {t.conference} for {t.school}, after {league_years(hist)} in the {old}. "
                     f"They're {t.conf_wins}-{t.conf_losses} in league play.")
    if t.conf_losses == 0:
        show.say("film", "So much for an adjustment period. They look like they've been there for years.")
    else:
        show.say("coach", f"Every week in the {t.conference} is a different animal. The travel, the size up front. "
                          f"There's a price to moving up.")


def league_years(hist):
    if len(hist) >= 2:
        return f"{hist[-1][0] - hist[-2][0]} years"
    return "years"


def _tell_seat(show, s):
    t = s["team"]
    c = t.coach
    yrs = show.league.year - (c.hired_year or show.league.year) + 1
    show.say("host", show.vary("seat_open", [
        f"The seat is scorching at {t.school}. {c.name} is {t.record} in year {yrs}.",
        f"Let's talk about {c.name}. {t.school} is {t.record}, and the noise is getting loud.",
        f"{t.school}: {t.record}. It's year {yrs} for {c.name}, and people want answers.",
    ]))
    why = diagnose(show.league, t)
    if why:
        show.say("film", why[0][1])
    show.say("coach", show.vary("seat_coach", [
        "I've been there. You stop sleeping. You stop reading anything. And the players can feel it.",
        "When the AD starts saying 'we support him' in public, you've got about three weeks.",
        "Coaches don't get fired for losing. They get fired for losing the building. That's what I'd be watching.",
    ]))
    show.say("defender", show.vary("seat_def", [f"The players have to play for him. That's the only way out.",
                                                 f"If they lose {(_next_opp(show, t) or 'this week')}, it's over. I think everybody knows it."]))


def _next_opp(show, t):
    g = this_game(show.league, t, show.games) or next_game(show.league, t)
    return g.opponent_of(t).school if g else None


def _tell_turnaround(show, s):
    t, last = s["team"], s["last"]
    show.say("host", f"Last year {t.school} went {last[0]}-{last[1]}. Year one under {t.coach.name}: {t.record}.")
    good = strengths(show.league, t)
    show.say("coach", show.vary("ta_coach", [f"That's coaching. Same kind of players, completely different team.",
                                             f"He changed the culture in one offseason. That's rare.",
                                             f"You know what that tells me? The talent was there. It needed a plan."]))
    if good:
        show.say("film", good[0][1])
    show.say("boom", f"Give {t.coach.name.split()[-1]} a statue. Right now. Bronze.")


def _tell_offense(show, s):
    t, pf = s["team"], s["pf"]
    qb = _qb(t)
    show.say("host", f"{t.school} is averaging {pf:.0f} points a game.")
    if qb is not None:
        st = qb.season_stats
        n = max(1, t.wins + t.losses)
        pace = st["pass_yds"] / n * 13
        show.say("film", f"{qb.name}: {st['pass_yds']:,} yards and {st['pass_td']} touchdowns. "
                         f"That's a {pace:,.0f}-yard pace." + (" That's record-book stuff." if pace >= 5200 else ""))
    show.say("defender", "As a defender, you hate playing them. You do everything right and it's still a touchdown.")


def _tell_defense(show, s):
    t, pa = s["team"], s["pa"]
    show.say("host", f"{t.school} is giving up {pa:.0f} points a game.")
    import gameday_dossier as gd
    d = gd._defender(t)
    if d is not None:
        show.say("defender", f"Watch {d.name}. {gd._stat_words(d)}. He's the one they build the whole plan around.")
    show.say("coach", "Defense travels. Defense wins in December. That's not a cliché — it's the whole sport.")


def _tell_champ(show, s):
    t, state = s["team"], s["state"]
    if state == "rolling":
        show.say("host", f"The defending champs, {t.school}, are {t.record} and haven't lost.")
        show.say("coach", "Repeating is the hardest thing in this sport. Everybody's best game is against you. Every week.")
        show.say("boom", "They look BORED out there. Like it's a scrimmage.")
    elif state == "reeling":
        show.say("host", f"The defending national champions are {t.record}. {t.school} has already lost {t.losses}.")
        why = diagnose(show.league, t)
        show.say("film", why[0][1] if why else "They lost a lot to the draft. That's the price of winning it all.")
        show.say("defender", "Hangover's real. Everybody tells you it's not. It's real.")
    else:
        show.say("host", f"Defending champion {t.school}: {t.record}. One loss, but not the same team.")
        show.say("coach", "They're finding out who they are without last year's guys. That takes time.")


def _tell_g5(show, s):
    t = s["team"]
    r = show.league.rankings.rank_of(t)
    show.say("host", f"{t.school} of the {t.conference} is {t.record}" + (f" and No. {r}." if r else "."))
    show.say("film", f"The highest-ranked conference champion outside the Power leagues gets a playoff spot. "
                     f"Right now, that's {t.school}'s to lose.")
    show.say("boom", f"I want {t.school} in the playoff so bad. I want chaos. I want them to go on the road in the playoff and win.")
    show.say("coach", "Respect the record. Be honest about the schedule. Both things can be true.")


def _tell_heisman(show, s):
    p, p2 = s["p"], s["p2"]
    L = show.league
    blurb = lambda x: _statline(x)
    if s.get("new"):
        show.say("host", f"New name at the top of the Golden Helmet race: {p.name} of {p.team.school}. {blurb(p)}.")
    else:
        show.say("host", f"Golden Helmet race: {p.name}, {p.team.school}, still in front — {blurb(p)}.")
    show.say("film", f"The one I'm watching is {p2.name} at {p2.team.school}: {blurb(p2)}. One big night and it's a race.")
    show.say(show.rng.choice(("coach", "defender")), show.vary("heis_take2", [
        "It's a quarterback's award unless somebody does something ridiculous. Somebody might.",
        "Watch the November games. Voters remember November.",
        "Stats get you invited to New York. Winning gets you the trophy.",
    ]))


def _statline(p):
    s = p.season_stats
    if s["pass_yds"] >= 300:
        return f"{s['pass_yds']:,} passing yards, {s['pass_td']} touchdowns"
    if s["rush_yds"] >= 200:
        return f"{s['rush_yds']:,} rushing yards, {s['rush_td']} touchdowns"
    if s["rec_yds"] >= 200:
        return f"{s['rec_yds']:,} receiving yards, {s['rec_td']} touchdowns"
    return f"{s['tkl']} tackles, {s['sack']:g} sacks, {s['int']} interceptions"


def _tell_race(show, s):
    conf, teams = s["conf"], s["teams"]
    names = ", ".join(t.school for t in teams[:4])
    show.say("host", f"The {conf} race: {len(teams)} teams without a league loss — {names}.")
    show.say("coach", "Somebody's going to lose a game they shouldn't. Somebody always does. That's how these races get decided.")
    show.say("film", f"If I'm picking one, it's {max(teams, key=lambda t: t.team_ovr).school}. Deepest roster of the group.")


def _tell_fall(show, s):
    t, was, now = s["team"], s["was"], s["now"]
    show.say("host", f"{t.school} was No. {was} last week. " + (f"They're No. {now} now." if now else "They're out of the poll entirely."))
    show.say("defender", show.vary("fall_take", ["That's what one bad Saturday costs you.",
                                                 "The voters don't forgive a loss like that.",
                                                 "They deserved to fall. You saw the game."]))


def _tell_star_out(show, s):
    t, p = s["team"], s["p"]
    r = show.league.rankings.rank_of(t)
    backups = [q for q in t.players_at("QB") if q is not p]
    b = backups[0] if backups else None
    show.say("host", f"Brutal news out of {t.school}: quarterback {p.name} is out for the season. {p.inj_desc or ''}".strip())
    if b is not None:
        show.say("film", f"It's {b.name} now. {b.class_label.lower().replace('rs-', 'redshirt ')}, and he's never "
                         f"carried a season. That changes the whole playbook.")
    show.say("coach", f"You find out about your program when the starter goes down. Next man up is a slogan until it isn't.")
    if r and r <= 12:
        show.say("boom", f"That's the playoff picture moving, right there. {t.school} just got a lot harder to pick.")


def _tell_locker(show, s):
    t, text = s["team"], s["text"]
    show.say("host", f"Off the field: {text}")
    show.say("coach", show.vary("lock_take", [
        "That's either the thing that saves their season or the thing that ends it. No in-between.",
        "Players-only meetings are great when the right players are running them.",
        "When it comes out publicly, it's been going on a lot longer than you think.",
    ]))


# ═══ The segment ═══════════════════════════════════════════════════════════

def segment(show):
    """THE STATE OF THE SEASON — the three or four stories everybody's talking about."""
    L = show.league
    if L.week < 2 or L.week > 13:
        return
    stories = storylines(L, show)
    if not stories:
        return
    if not show.segment("STATE OF THE SEASON"):
        return
    n = 4 if (len(stories) >= 4 and show.rng.random() < 0.55) else min(3, len(stories))
    for i, s in enumerate(stories[:n]):
        if i:
            show.say("host", show.rng.choice(("Next —", "Meanwhile.", "Also:", "Let's keep moving.", "And then there's this.",
                                               "Another one people are talking about:")))
        tell(show, s)


# ═══ For the interview ═════════════════════════════════════════════════════

def interview_topics(show, p, team, opp):
    """Questions only this player, this week, gets asked. [(question, [(answer, follow-up q, follow-up a)])]"""
    L = show.league
    out = []
    pr = pre_rank(L, team)
    kind, n = streak(L, team)
    if pr and pr <= 12 and team.losses >= 2 and team.wins <= team.losses:
        out.append((f"You started the year ranked No. {pr}. You're {team.record}. What's the mood in that locker room?",
                    [("Honestly? Angry. Not at each other. At ourselves.", "Angry is good?", "Angry means we care. Quiet would be bad."),
                     ("It's been humbling. Nobody gave us anything because of a preseason number.", "Did the number hurt?",
                      "Maybe. Maybe we read our own clippings. We don't anymore."),
                     ("We know what everybody's saying. We don't need anybody to remind us.", None, None)]))
    if kind == "L" and n >= 3:
        out.append((f"{n} straight losses. How do you stop the bleeding?",
                    [("One play. Then the next one. You can't win four games this week. You can win one.", None, None),
                     ("We stopped having fun. We got it back this week in practice. You'll see it.", "How?",
                      "Music back on in the locker room. Little things.")]))
    if team.losses == 0 and team.wins >= 5:
        out.append((f"You're {team.record}. Does anybody in your locker room talk about the zero?",
                    [("Nobody says it. It's like a no-hitter.", "Like a no-hitter?", "You don't say it out loud. You'll jinx it."),
                     ("Coach won't let us. He says the zero means nothing if we lose today.", None, None),
                     ("We talk about it constantly. We're not robots.", "(laughs) Constantly?", "It's on the group chat every night.")]))
    if kind == "W" and n >= 5:
        out.append((f"{n} straight wins. What changed?",
                    [("We started trusting each other. That sounds soft. It's the whole thing.", None, None),
                     ("The defense. They've carried us. We owe them.", None, None)]))
    s = p.season_stats
    if L.rankings.heisman and any(x[0] is p for x in L.rankings.heisman[:5]):
        out.append(("Your name is on every Golden Helmet list in the country. Do you look?",
                    [("My mom sends me screenshots. I tell her to stop. She doesn't.", None, None),
                     ("No. If we win, all of that takes care of itself.", "You really don't look?", "...Maybe once. On a Sunday."),
                     ("It's an honor. But my line should get a piece of that trophy.", "Which piece?", "The whole bottom half.")]))
    prev = getattr(p, "prev_school", None)
    if prev:
        ps = prev if isinstance(prev, str) else getattr(prev, "school", str(prev))
        if opp is not None and ps == opp.school:
            out.append((f"You started your career at {ps}. Today you play them. Be honest — is this one different?",
                        [("I'd be lying if I said no. I still have friends over there. For three hours, I don't.", None, None),
                         ("It's just another game.", "Really?", "No. I've had it circled since the schedule came out.")]))
        else:
            out.append((f"You transferred in from {ps}. What made you pick {team.school}?",
                        [("They told me the truth. Everybody else told me what I wanted to hear.", None, None),
                         (f"Coach {team.coach.name.split()[-1]} called me the first minute the portal opened. First minute.",
                          None, None)]))
    try:
        import personalities as pers
        if pers.is_captain(p):
            out.append((f"You're a team captain. What does that mean to you?",
                        [("It means when it goes bad, I'm the first one who has to say something.", None, None),
                         ("My teammates voted. That's the only vote I care about.", "More than the polls?", "Way more than the polls.")]))
        if getattr(team, "chemistry", 50) < 38:
            out.append(("There's been talk about your locker room. Is there anything to it?",
                        [("Every team has stuff. Ours just got out. We handled it.", None, None),
                         ("We had a real conversation. It needed to happen.", "Did it help?", "Ask me after today.")]))
    except Exception:
        pass
    c = team.coach
    if c is not None and getattr(c, "seat", 0) >= 82 and team.losses >= 2:
        out.append((f"Everyone's talking about Coach {c.name.split()[-1]}'s job. Do the players feel that?",
                    [("We feel it. We're the ones who can fix it.", None, None),
                     ("He recruited me into his living room. I'm not letting him go out like this.", None, None)]))
    if c is not None and getattr(c, "hired_year", None) == L.year:
        out.append((f"What's been the biggest change since Coach {c.name.split()[-1]} took over?",
                    [("Practice is harder. Way harder. And shorter. Nobody understands how both are true.", None, None),
                     ("Accountability. You're late once, the whole room runs.", "Were you ever late?", "Once. Never again.")]))
    if p.year >= 1 and p.position in ("QB", "RB", "WR", "DL", "CB", "LB", "OL", "S", "TE"):
        try:
            import personalities as pers
            spots = getattr(L, "_proj_cache", None)
            if spots is None or spots[0] != (L.year, L.week):
                spots = L._proj_cache = ((L.year, L.week), pers.projected_spots(L))
            spot = spots[1].get(id(p))
            if spot and spot <= 64 and p.year < 3:
                out.append(("There are Pro League scouts in the building today. Do you think about next year at all?",
                            [("Not today. Today's about us.", "And tomorrow?", "Tomorrow I'll let my family think about it."),
                             ("I'd be lying if I said I didn't. But I owe these guys everything I've got first.", None, None)]))
        except Exception:
            pass
    import rivalries
    if opp is not None:
        sr = rivalries.series(L, team, opp)
        who, sn = sr.streak
        if sr.n and who == opp.school and sn >= 2:
            out.append((f"{opp.school} has beaten you {sn} straight. Does that sit with you?",
                        [("Every day. It's the first thing I see on my phone in the morning. I made it my lock screen.",
                          "Your lock screen?", "The score. From last year. So I don't forget."),
                         ("We don't talk about it. We just have a picture of the scoreboard in the weight room.", None, None)]))
        if sr.trophy:
            held = sr.holder
            out.append((f"{sr.trophy[0].upper() + sr.trophy[1:]} is on the line. What does it mean to you?",
                        [(("It's ours. It's staying ours." if held == team.school else
                           "It's been sitting in their building too long."), None, None),
                         ("The older guys told me about it before I ever played a snap here. Now I get it.", None, None)]))
    hist = getattr(team, "conf_history", None)
    if hist and len(hist) > 1 and hist[-1][0] == L.year:
        out.append((f"First year in the {team.conference}. What's the biggest difference?",
                    [("The size. Every week the guy across from you looks like a grown man.", None, None),
                     ("The travel. I've been on more planes this fall than my whole life.", "Where's the best place so far?",
                      "Wherever we won.")]))
    return out


def context_signs(show):
    """Signs the crowd made about what's going on in the sport. [(sign, reply scene)]"""
    L = show.league
    out = []
    for t in L.teams:
        pr = pre_rank(L, t)
        if pr and pr <= 10 and t.wins == 0 and t.losses >= 2 and t not in (show.h, show.a):
            out.append((f"{t.school.upper()} IS {t.record} AND SO IS MY FANTASY TEAM",
                        [("boom", "That's two tragedies in one sign."), ("crowd", "(laughter)")]))
            out.append((f"PRESEASON NO. {pr}? MORE LIKE PRESEASON NO. {pr + 40}",
                        [("film", "Math checks out, unfortunately."), ("crowd", "(laughter)")]))
        if getattr(t.coach, "seat", 0) >= 88 and t.losses >= 3 and t not in (show.h, show.a):
            out.append((f"{t.coach.name.split()[-1].upper()}'S SEAT IS HOTTER THAN THIS TAILGATE",
                        [("coach", "That's cruel. Accurate, but cruel."), ("crowd", "(laughter)")]))
    h = L.rankings.heisman
    if h and h[0][0].team in (show.h, show.a):
        p = h[0][0]
        out.append((f"{p.last_name.upper()} FOR HEISMAN (I ALREADY BOUGHT THE POSE T-SHIRT)",
                    [("film", "Commit to the bit. Respect."), ("crowd", "(cheering)")]))
    return out
