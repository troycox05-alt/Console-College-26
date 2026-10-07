"""
gameday_league.py — Campus Countdown as the around-the-country show.

Two blocks, each a real conversation rather than a scoreboard crawl:

  AROUND THE COUNTRY: LAST WEEK   the four to six games from last Saturday that
                                  actually mattered. For each one the host sets it
                                  up, and the crew says *why* it happened (read off
                                  the box score: turnovers, the run game, a comeback,
                                  a player who took over, penalties) and *what it
                                  means* (the poll, the league race, the playoff, a
                                  coach's seat, a trophy, a streak).

  AROUND THE COUNTRY: TODAY       the best games on today's board that the pick
                                  segment won't get to: ranked matchups, trophy
                                  games, league-race games, a coach who needs one,
                                  a ranked team on the road. Kickoff time, what's
                                  at stake, where the matchup tilts (offense against
                                  defense, the quarterbacks, the player to watch,
                                  the series), and somebody's lean.

Every line is built from what happened in your world. Nothing here changes a result.
"""
from collections import Counter

import broadcast


def _fbs(g):
    return not getattr(g.home, "fcs", False) and not getattr(g.away, "fcs", False)


def _r(league, t):
    r = league.rankings.rank_of(t)
    return f"No. {r} {t.school}" if r else t.school


def _ranks(g):
    return getattr(g, "ranks", {}) or {}


# ═══ Reading a finished game ═══════════════════════════════════════════════

def read_box(g):
    """What the tape says: a dict of facts about one finished game."""
    box = g.box
    w, l = g.winner, g.loser
    ws, ls = g.score_for(w), g.score_for(l)
    f = {"g": g, "w": w, "l": l, "ws": ws, "ls": ls, "margin": ws - ls, "ot": bool(getattr(box, "ot_round", 0))}
    if box is None:
        return f
    side = {w: Counter(), l: Counter()}
    best = {w: None, l: None}
    from impact import game_impact
    for p, c in box.stats.items():
        t = box.team_of(p)
        if t not in side:
            continue
        side[t].update(c)
        v = game_impact(c)
        if best[t] is None or v > best[t][0]:
            best[t] = (v, p, c)
    f["side"] = side
    f["best"] = best
    give = lambda t: side[t]["pass_int"] + max(0, side[_other(g, t)]["fr"])
    f["to_w"], f["to_l"] = give(w), give(l)                 # turnovers each side committed
    f["rush_w"], f["rush_l"] = side[w]["rush_yds"], side[l]["rush_yds"]
    f["pass_w"], f["pass_l"] = side[w]["pass_yds"], side[l]["pass_yds"]
    f["sacks_w"] = side[w]["sack"]
    ts = getattr(box, "team_stats", {}) or {}
    f["pen_w"] = ts.get(w, {}).get("penalties", 0) if ts else 0
    f["pen_l"] = ts.get(l, {}).get("penalties", 0) if ts else 0
    f["pen_yds_l"] = ts.get(l, {}).get("pen_yds", 0) if ts else 0
    f["top_w"] = ts.get(w, {}).get("top", 0) if ts else 0
    line = getattr(box, "line", {}) or {}
    lw, ll = line.get(w, []), line.get(l, [])
    if len(lw) >= 3 and len(ll) >= 3:
        f["after3"] = (sum(lw[:3]), sum(ll[:3]))
        f["half"] = (sum(lw[:2]), sum(ll[:2]))
        f["q4"] = (lw[3] if len(lw) > 3 else 0, ll[3] if len(ll) > 3 else 0)
    return f


def _other(g, t):
    return g.away if t is g.home else g.home


def _pname(p):
    return f"{p.first_name} {p.last_name}" if hasattr(p, "first_name") else str(p)


def star_phrase(p, c):
    n = _pname(p)
    if c["pass_yds"] >= 250:
        return f"{n} threw for {c['pass_yds']} yards and {c['pass_td']} touchdown{'s' if c['pass_td'] != 1 else ''}"
    if c["rush_yds"] >= 120:
        return f"{n} ran for {c['rush_yds']} yards on {c['rush_att']} carries"
    if c["rec_yds"] >= 110:
        return f"{n} caught {c['rec']} balls for {c['rec_yds']} yards"
    if c["sack"] >= 2:
        return f"{n} had {c['sack']:g} sacks"
    if c["int"] >= 2:
        return f"{n} picked off {c['int']} passes"
    if c["tkl"] >= 11:
        return f"{n} made {c['tkl']} tackles"
    return None


def steady_phrase(p, c):
    """A quieter good day — a game manager, not a takeover."""
    if c["pass_yds"] >= 150 and c["pass_int"] == 0:
        return f"{_pname(p)} threw for {c['pass_yds']} and didn't turn it over"
    return None


# ═══ Picking the games that matter ═════════════════════════════════════════

def _recap_score(league, g):
    R = _ranks(g)
    rw, rl = R.get(g.winner), R.get(g.loser)
    s = 0.0
    if rl and (not rw or rw > rl + 3):
        s += 60 - rl                                     # upset of a ranked team
    if rw and rl:
        s += 45 - (rw + rl) / 2                          # ranked against ranked
    import rivalries
    if rivalries.is_rivalry(g.home, g.away):
        s += 22
    if rivalries.trophy(g.home, g.away):
        s += 6
    m = g.score_for(g.winner) - g.score_for(g.loser)
    if getattr(g.box, "ot_round", 0):
        s += 18
    elif m <= 3:
        s += 10
    if rw and rw <= 10 and m >= 28:
        s += 8
    c = g.loser.coach
    if c is not None and getattr(c, "seat", 0) >= 75:
        s += 12
    if g.game_type != "Regular Season":
        s += 30
    return s


def recap_games(league, n=5):
    prev = [g for g in league.schedule.get(league.week - 1, []) if g.played and _fbs(g)]
    ranked = sorted(prev, key=lambda g: -_recap_score(league, g))
    return [g for g in ranked if _recap_score(league, g) > 8][:n]


def _preview_score(league, g):
    R = league.rankings
    rh, ra = R.rank_of(g.home), R.rank_of(g.away)
    s = 0.0
    if rh and ra:
        s += 60 - (rh + ra) / 2
    elif rh or ra:
        s += 18 - (rh or ra) / 3
        if ra and not rh:
            s += 6                                        # ranked team on the road
    import rivalries
    if rivalries.is_rivalry(g.home, g.away):
        s += 20
    if rivalries.trophy(g.home, g.away):
        s += 6
    if g.conference_game and g.home.conf_losses + g.away.conf_losses <= 1 and g.home.conf_wins + g.away.conf_wins >= 4:
        s += 14                                           # both near the top of the league
    for t in (g.home, g.away):
        if getattr(t.coach, "seat", 0) >= 78:
            s += 9
        if t.losses == 0 and t.wins >= 4:
            s += 6
    return s


def preview_games(league, show, n=5):
    taken = set(id(g) for g in show.slate)
    cand = [g for g in show.games if _fbs(g) and not g.played and id(g) not in taken]
    cand.sort(key=lambda g: -_preview_score(league, g))
    return [g for g in cand if _preview_score(league, g) >= 10][:n]


# ═══ LAST WEEK ═════════════════════════════════════════════════════════════

def recap_block(show):
    """Four to six games from last week, each one talked through."""
    L = show.league
    games = recap_games(L, n=5 if show.rng.random() < 0.6 else 6)
    if not games:
        return
    for i, g in enumerate(games):
        _recap_one(show, g, i)
    show.say("host", show.vary("rc_close", [
        "That's last week. Today's going to be even better.", "All right — enough looking back.",
        "And that's where the country stands. Let's keep going.", "That's the week that was.",
    ]))


def _set_up(show, g, f):
    L = show.league
    R = _ranks(g)
    w, l = f["w"], f["l"]
    rw, rl = R.get(w), R.get(l)
    W = f"No. {rw} {w.school}" if rw else w.school
    Lz = f"No. {rl} {l.school}" if rl else l.school
    s = f"{f['ws']}-{f['ls']}"
    where = "at home" if (g.home is w and not g.neutral) else "on the road" if not g.neutral else "on a neutral field"
    import rivalries
    riv = rivalries.rivalry_name(g.home, g.away)
    tro = rivalries.trophy(g.home, g.away)
    if g.game_type == "Conference Championship":
        return f"{W} won the {g.bowl_name}, {s} over {Lz}."
    if rl and (not rw or rw > rl + 3) and (riv or tro):
        return show.vary("rc_up_riv", [
            "{W} knocked off {L} in {riv}, {s}.", "Rivalry upset: {W} over {L}, {s}.",
            "{L} came in ranked and left with a loss to its rival — {W}, {s}.",
        ], W=W, L=Lz, s=s, riv=riv or f"the game for {tro}")
    if rl and (not rw or rw > rl + 3):
        return show.vary("rc_up", [
            "{W} knocked off {L} {where}, {s}.", "Upset: {W} over {L}, {s}.",
            "{L} went down — {W} got them {where}, {s}.", "{W} {s} over {L}. Nobody had that.",
        ], W=W, L=Lz, where=where, s=s)
    if f.get("ot"):
        return show.vary("rc_ot", ["{W} outlasted {L} in overtime, {s}.",
                                   "It took overtime, but {W} got past {L}, {s}."], W=W, L=Lz, s=s)
    if tro:
        return f"{W} beat {Lz} {s} in the game for {tro}."
    if riv:
        return f"{riv[0].upper() + riv[1:]}: {W} {s} over {Lz}."
    if rw and rl:
        return show.vary("rc_rr", ["{W} over {L}, {s}, in a ranked matchup.",
                                   "Ranked on ranked: {W} {ws}, {L} {ls}."],
                         W=W, L=Lz, s=s, ws=f["ws"], ls=f["ls"])
    return show.vary("rc_plain", ["{W} beat {L}, {s}.", "{W} {s} over {L}.",
                                  "{W} took care of {L}, {s}."], W=W, L=Lz, s=s)


def why_lines(show, f):
    """Why it happened — each a (speaker, text), best first."""
    g, w, l = f["g"], f["w"], f["l"]
    out = []
    if "side" not in f:
        return out
    tw, tl = f["to_w"], f["to_l"]
    if tl - tw >= 3:
        out.append(("defender", show.vary("why_to", [
            f"Turnovers. {l.school} gave it away {tl} times. You don't beat anybody doing that.",
            f"{w.school} was plus-{tl - tw} in turnovers. That's the whole ballgame right there.",
            f"{tl} turnovers. {l.school} beat themselves, and {w.school} was happy to let them.",
        ])))
    if "after3" in f:
        a_w, a_l = f["after3"]
        if a_w < a_l:
            q4w = f["q4"][0]
            out.append(("film", show.vary("why_comeback", [
                f"{w.school} was down {a_l}-{a_w} going into the fourth and scored {q4w} in the quarter. "
                f"That's a team that doesn't flinch.",
                f"Trailing {a_l}-{a_w} after three. They came back. That tells you about the locker room.",
                f"Down going to the fourth, and they found a way. Those wins count double in December.",
            ])))
        elif f["half"][0] - f["half"][1] >= 21:
            out.append(("coach", show.vary("why_fast", [
                f"It was over at halftime — {f['half'][0]}-{f['half'][1]}. {w.school} came out and punched first.",
                f"{f['half'][0]}-{f['half'][1]} at the half. {l.school} wasn't ready to play, and that's on the staff.",
            ])))
    if f["rush_w"] >= 230 and f["rush_w"] > f["rush_l"] + 100:
        out.append(("coach", show.vary("why_run", [
            f"{w.school} ran for {f['rush_w']} yards. When you can line up and run it like that, you control everything.",
            f"{f['rush_w']} rushing yards. That's not a scheme, that's a line of scrimmage getting whipped.",
            f"They ran it {f['side'][w]['rush_att']} times for {f['rush_w']}. {l.school} knew it was coming and couldn't stop it.",
        ])))
    if f["sacks_w"] >= 4:
        out.append(("defender", show.vary("why_sacks", [
            f"{f['sacks_w']:g} sacks. {w.school} lived in the backfield.",
            f"The pass rush won that game. {f['sacks_w']:g} sacks, and the quarterback never got comfortable.",
        ])))
    if f["pen_l"] >= 10:
        out.append(("coach", show.vary("why_pen", [
            f"{l.school} had {f['pen_l']} penalties for {f['pen_yds_l']} yards. That's undisciplined, and it cost them.",
            f"{f['pen_l']} flags. You can't win on the road like that. You can't win anywhere like that.",
        ])))
    best = f["best"].get(w)
    if best and not star_phrase(best[1], best[2]) and steady_phrase(best[1], best[2]):
        out.append(("film", show.vary("why_steady", [
            f"{steady_phrase(best[1], best[2])}. Sometimes the quarterback's job is just not to lose it.",
            f"Quiet day for the offense, but {steady_phrase(best[1], best[2])}. That's winning football.",
        ])))
    if best:
        phrase = star_phrase(best[1], best[2])
        if phrase:
            out.append(("film", show.vary("why_star", [
                f"{phrase}. He was the best player on the field and it wasn't close.",
                f"The difference was {_pname(best[1])}: {phrase[len(_pname(best[1])) + 1:]}.",
                f"{phrase}. Go back and watch it — he took that game over.",
                f"{phrase}. That's what a star does in a game like that.",
            ])))
    lbest = f["best"].get(l)
    if lbest and f["margin"] <= 8:
        phrase = star_phrase(lbest[1], lbest[2])
        if phrase:
            out.append(("boom", f"And don't sleep on {l.school} — {phrase}. Heck of a day in a loss."))
    if f["pass_w"] >= 380:
        out.append(("film", f"{f['pass_w']} yards through the air. {l.school}'s secondary had no answers."))
    return out


def meaning_lines(show, g, f):
    """What it means — poll, league, playoff, seat, trophy, streak."""
    L = show.league
    w, l = f["w"], f["l"]
    R = _ranks(g)
    out = []
    import gameday_context as gx
    pr = gx.pre_rank(L, l)
    if pr and pr <= 12 and l.wins <= l.losses:
        kind, n = gx.streak(L, l)
        out.append(("host", show.vary("mean_flop", [
            f"And that's preseason No. {pr} {l.school} falling to {l.record}.",
            f"{l.school} started this year at No. {pr}. They're {l.record} now." + (f" {n} straight losses." if kind == "L" and n >= 2 else ""),
            f"Preseason No. {pr}. {l.record}. Somebody explain {l.school} to me.",
        ])))
    wp = gx.pre_rank(L, w)
    if not wp and L.rankings.rank_of(w) and L.rankings.rank_of(w) <= 15 and w.wins >= 5:
        out.append(("boom", f"Nobody ranked {w.school} in August! They're {w.record}! I LOVE this sport!"))
    rw, rl = R.get(w), R.get(l)
    now_w, now_l = L.rankings.rank_of(w), L.rankings.rank_of(l)
    if rl and not now_l:
        out.append(("host", f"{l.school} fell out of the poll entirely."))
    elif rl and now_l and now_l - rl >= 5:
        out.append(("host", f"{l.school} dropped from {rl} to {now_l}."))
    if now_w and not rw:
        out.append(("host", f"{w.school} jumps into the poll at No. {now_w} this week."))
    elif now_w and rw - now_w >= 4:
        out.append(("host", f"{w.school} climbs from {rw} to {now_w}."))
    if g.conference_game and g.game_type == "Regular Season":
        lead = L.standings(w.conference)
        if lead and lead[0] is w and w.conf_losses == 0 and w.conf_wins >= 3:
            out.append(("coach", show.vary("mean_conf", [
                f"{w.school} is {w.conf_wins}-0 in the {w.conference}. Everybody else is chasing them now.",
                f"That puts {w.school} in the driver's seat in the {w.conference}.",
                f"Unbeaten in league play. {w.school} controls its own path to the {w.conference} title game.",
            ])))
        elif l.conf_losses >= 2 and (l.conf_wins + l.conf_losses) <= 6 and rl:
            out.append(("coach", f"Two league losses for {l.school}. That's probably it for the {l.conference} race."))
    if rl and rl <= 12 and l.losses == 1 and L.week >= 5:
        out.append(("film", show.vary("mean_cfp_first", [
            f"First loss for {l.school}. In a twelve-team playoff that's survivable — but now there's no margin.",
            f"{l.school} can absorb one. Two, and they're sweating Selection Day.",
        ])))
    elif rl and l.losses >= 2 and L.week >= 7 and rl <= 15:
        out.append(("film", f"That's loss number {l.losses} for {l.school}. The playoff math is getting ugly."))
    if w.losses == 0 and w.wins >= 6:
        out.append(("boom", f"{w.school} is {w.record}! UNDEFEATED! Somebody stop them!"))
    c = l.coach
    if c is not None and getattr(c, "seat", 0) >= 75 and l.losses >= 2 and not getattr(c, "user", False):
        out.append(("defender", show.vary("mean_seat", [
            f"And the pressure on {c.name} keeps going up. {l.school} is {l.record}.",
            f"That one's going to be talked about in {l.school}'s AD office this week. {c.name} needed it.",
            f"{c.name} is running out of Saturdays. That's the reality at {l.school}.",
        ])))
    import rivalries
    tro = rivalries.trophy(g.home, g.away)
    s = rivalries.series(L, g.home, g.away)
    if tro and s.n:
        who, n = s.streak
        if n >= 3 and who == w.school:
            out.append(("host", f"{w.school} keeps {tro} — that's {n} straight in the series."))
        elif n == 1 and s.n >= 2:
            out.append(("host", f"And {w.school} takes {tro} back."))
    if g.game_type == "Conference Championship":
        out.append(("coach", f"{w.school} is your {w.conference} champion. That's an automatic bid if they're high enough."))
    return out


REACTIONS = {
    "boom": ["LOVE IT!", "What a game that was.", "I was screaming at my TV. My neighbors called somebody.",
             "That's college football, baby!", "Put that one in the time capsule."],
    "coach": ["That's how you win on the road.", "They'll learn more from that than from any win.",
              "Somebody's watching that tape very unhappy this week.", "Execution. That's all it ever is."],
    "defender": ["Defense travels.", "Credit that defensive staff.", "They played harder. Simple as that."],
    "film": ["Watch the tape and it's even clearer.", "The numbers back that up, too.",
             "That's a matchup problem they'll see again."],
}


def _recap_one(show, g, i):
    f = read_box(g)
    lead = _set_up(show, g, f)
    if i and show.rng.random() < 0.5 and ":" not in lead[:30]:
        lead = show.rng.choice(("Also last week — ", "Then there's this one. ", "Meanwhile, ")) + lead
    show.say("host", lead)
    whys = why_lines(show, f)
    means = meaning_lines(show, g, f)
    said = set()
    if whys:
        who, text = whys[0]
        show.say(who, text)
        said.add(who)
        if len(whys) > 1 and show.rng.random() < 0.55:
            alt = next(((w2, t2) for w2, t2 in whys[1:] if w2 not in said), None)
            if alt:
                show.say(alt[0], alt[1])
                said.add(alt[0])
    elif show.rng.random() < 0.6:
        k = show.rng.choice(("coach", "film", "defender"))
        show.say(k, show.rng.choice(REACTIONS[k]))
    if means:
        who, text = means[0] if means[0][0] not in said or len(means) == 1 else \
            next(((a, b) for a, b in means if a not in said), means[0])
        show.say(who, text)
        if len(means) > 1 and show.rng.random() < 0.4:
            show.say(means[1][0], means[1][1])
    if show.rng.random() < 0.25:
        k = show.rng.choice([x for x in ("boom", "coach", "defender", "film") if x not in said] or ["boom"])
        show.say(k, show.rng.choice(REACTIONS[k]))


# ═══ TODAY ═════════════════════════════════════════════════════════════════

def _unit_edge(a, b):
    """(team, text) — the biggest offense-versus-defense mismatch in the game."""
    d1 = a.offense_ovr - b.defense_ovr
    d2 = b.offense_ovr - a.defense_ovr
    if max(d1, d2) < 4:
        return None
    off, dfn, d = (a, b, d1) if d1 >= d2 else (b, a, d2)
    return off, dfn, d


def _qb_line(t):
    import gameday_dossier as gd
    qb = gd._qb(t)
    if qb is None:
        return None, None
    s = qb.season_stats
    if s["pass_att"] >= 40:
        pl = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
        return qb, (f"{s['pass_yds']:,} yards, {pl(s['pass_td'], 'touchdown')}, {pl(s['pass_int'], 'pick')}")
    return qb, None


def preview_block(show):
    """Four or five more games on today's board, each with the crew's read."""
    L = show.league
    games = preview_games(L, show, n=5 if show.rng.random() < 0.6 else 4)
    if not games:
        return
    for i, g in enumerate(games):
        _preview_one(show, g, i)


def _preview_one(show, g, i):
    L = show.league
    show.__dict__.setdefault("discussed", []).append(g)     # the picks table will carry these picks
    a, h = g.away, g.home
    at = "vs" if g.neutral else "at"
    when = broadcast.at_time(g)                          # "at noon", "at 7:30 tonight"
    import rivalries
    tro = rivalries.trophy(h, a)
    riv = rivalries.rivalry_name(h, a)
    both_new = a.wins + a.losses == 0 and h.wins + h.losses == 0
    setup = (f"{_r(L, a)} {at} {_r(L, h)}, {when}." if both_new else
             f"{_r(L, a)} ({a.record}) {at} {_r(L, h)} ({h.record}), {when}.")
    if tro:
        setup = f"{tro[0].upper() + tro[1:]} is on the line {when}: {_r(L, a)} {at} {_r(L, h)}."
    elif riv:
        setup = f"{riv[0].upper() + riv[1:]}, {when}: {_r(L, a)} {at} {_r(L, h)}."
    if i and show.rng.random() < 0.4:
        setup = show.rng.choice(("Also today — ", "Keep an eye on this one. ", "Next up: ")) + setup
    show.say("host", setup)
    lines = _stakes(show, g) + _matchup(show, g)
    show.rng.shuffle(lines)
    lines.sort(key=lambda x: -x[2])
    used = set()
    shapes = show.__dict__.setdefault("said_shapes", set())      # nothing said twice in one show
    n = 0
    for who, text, _w in lines:
        if who in used or n >= 2 or _shape(text, g) in shapes:
            continue
        show.say(who, text)
        shapes.add(_shape(text, g))
        used.add(who)
        n += 1
    # a lean
    from gameday_show import pick
    k = show.rng.choice([x for x in ("film", "coach", "defender", "boom") if x not in used] or ["boom"])
    team, conf, why = pick(L, k, g)
    show.table[(k, g)] = team
    other = g.away if team is g.home else g.home
    lean = show.vary(f"lean:{k}", [
        f"I'll take {team.school}.", f"{team.school}. Not overthinking it.",
        f"Give me {team.school}{' — and it won’t be close' if conf > 0.75 else ''}.",
        f"{team.school} finds a way.", f"I like {team.school} there.",
        f"{team.school}, but {other.school} makes it uncomfortable.",
    ] if k != "boom" else [
        f"{team.school.upper()}! Book it!", f"I'm taking {team.school} and I'm not apologizing.",
        f"{team.school}! {'Upset special!' if (L.rankings.rank_of(other) and not L.rankings.rank_of(team)) else 'Easy money!'}",
    ])
    show.say(k, lean)
    # sometimes somebody on the desk disagrees
    if show.rng.random() < 0.35:
        for k2 in show.rng.sample(["film", "coach", "defender", "boom", "host"], 5):
            if k2 == k:
                continue
            t2, c2, why2 = pick(L, k2, g)
            show.table[(k2, g)] = t2
            if t2 is not team:
                show.say(k2, show.vary(f"disagree:{k2}", [
                    f"I'm going the other way. {t2.school}.", f"Hard disagree. {t2.school} wins that game.",
                    f"No chance. {t2.school}, and I'll say it with my chest.",
                    f"You're wrong, and I'll bring it up next week. {t2.school}.",
                ]))
                show.say(k, show.rng.choice(("We'll see.", "Put it on tape.", "Loser buys lunch.", "Noted. Incorrectly.")))
                break


def _stakes(show, g):
    """(speaker, text, weight)"""
    L = show.league
    a, h = g.away, g.home
    out = []
    import gameday_context as gx
    for t in (a, h):
        n = gx.note(L, t)
        if n:
            o = h if t is a else a
            out.append(("host", show.vary("pv_note", [
                f"Context matters here: {t.school} is {n}.",
                f"Remember, {t.school} is {n}. That changes how this one feels.",
                f"{t.school} comes in {n}. {o.school} knows exactly what that means.",
            ]), 6))
            why = gx.diagnose(L, t) if t.losses >= t.wins - 1 else gx.strengths(L, t)
            if why:
                out.append((show.rng.choice(("film", "coach", "defender")), why[0][1], 5))
            break
    # a look ahead: the trap game
    for t in (a, h):
        o = h if t is a else a
        nxt = gx.next_game(L, t)
        if nxt is not None and nxt is not g and L.rankings.rank_of(t) and L.rankings.rank_of(nxt.opponent_of(t)) \
                and not L.rankings.rank_of(o):
            out.append(("coach", f"Here's what worries me for {t.school}: {nxt.opponent_of(t).school} is next week. "
                                 f"Twenty-year-olds look ahead. They always do.", 4))
            break
    ra, rh = L.rankings.rank_of(a), L.rankings.rank_of(h)
    if ra and rh:
        out.append(("host", f"Winner of this one stays in the playoff conversation. The loser has some explaining to do.", 3))
    if g.conference_game:
        for t in (h, a):
            if t.conf_losses == 0 and t.conf_wins >= 3:
                o = a if t is h else h
                big = o.conf_losses <= 1
                out.append(("coach", show.vary("pv_conf", [
                    f"{t.school} is {t.conf_wins}-0 in the {t.conference}. {o.school} is the next team with a chance to change that.",
                    f"This is a {t.conference} race game. {t.school} is unbeaten in league play" + (f", and {o.school} is right behind them." if big else "."),
                    f"{t.school} hasn't lost in the {t.conference}. A loss here and the whole league race opens up.",
                    f"{o.school} {'can grab a share of first' if big else 'can play spoiler'} with a win. {t.school} is {t.conf_wins}-0 in the league.",
                ]), 4 if big else 2))
                break
    for t in (h, a):
        c = t.coach
        if c is not None and getattr(c, "seat", 0) >= 78 and t.losses >= 2:
            out.append(("defender", show.vary("pv_seat", [
                f"{c.name} needs this one. {t.school} is {t.record}, and everybody in that building knows it.",
                f"This is a big one for {c.name}. You can feel the temperature on that seat from here.",
                f"If {t.school} drops this one, {c.name}'s week gets a lot longer.",
            ]), 5))
            break
    for t in (h, a):
        if t.losses == 0 and t.wins >= 5:
            o = a if t is h else h
            out.append(("boom", show.vary("pv_unb", [
                f"{t.school} is {t.record}! {o.school}'s whole season is sitting right there in front of them!",
                f"Undefeated {t.school} walks in and {o.school} gets to ruin somebody's perfect season. That's a PARTY.",
                f"{t.record}, {t.school}. Every week somebody's Super Bowl. Today it's {o.school}'s.",
                f"You want chaos? Unbeaten {t.school} is on the board. I smell chaos.",
            ]), 3))
            break
    if ra and not rh and not g.neutral:
        out.append(("film", show.vary("pv_trap", [
            f"This is a trap. No. {ra} {a.school} on the road, noon body clocks, a home crowd with nothing to lose."
            if broadcast.time_words(g) == "noon" else
            f"Ranked team on the road against a team that's going to empty the playbook. I'd be nervous if I'm {a.school}.",
            f"Don't sleep on {h.school} at home. {a.school} has to bring it.",
            f"{h.school} has nothing to lose and a home crowd. That's the most dangerous team in football.",
            (f"Road games against teams that are {h.record} are where ranked teams go to die. Focus, {a.school}."
             if h.wins + h.losses else
             f"Road openers against teams with nothing to lose are where ranked teams go to die. Focus, {a.school}."),
            f"{a.school} should win. 'Should' does a lot of work in this sport.",
        ]), 3))
    import rivalries
    s = rivalries.series(L, a, h)
    if s.n:
        who, n = s.streak
        m = s.last
        if n >= 3:
            other = s.b if who == s.a else s.a
            out.append(("coach", f"{who} has won {n} straight in this series. At some point {other} has to take it personally.", 4))
        elif league_year_diff(L, m) <= 2:
            text = f"Last time these two met, {m.winner} won {m.wscore}-{m.lscore}"
            text += f" — {m.star}." if m.star else "."
            if m.wscore - m.lscore <= 3:
                text += f" {m.loser} has been thinking about that one."
            out.append(("film", text, 3))
    return out


def _night(g):
    k = getattr(g, "kick", None)
    return k is not None and k >= 17 * 60


def _shape(text, g):
    """A line with the teams and numbers taken out — two lines with the same shape
    are the same line, whoever they're about."""
    t = text
    for x in (g.home, g.away):
        t = t.replace(x.school, "#").replace(x.nickname, "#")
    import re
    return re.sub(r"\d+", "N", t)


def league_year_diff(L, m):
    return L.year - m.year


def _matchup(show, g):
    L = show.league
    a, h = g.away, g.home
    out = []
    e = _unit_edge(a, h)
    if e:
        off, dfn, d = e
        out.append(("film", show.vary("pv_edge", [
            f"Here's the matchup: {off.school}'s offense against a {dfn.school} defense that just isn't at that level. "
            f"If {dfn.school} can't get off the field on third down, it's a long "
            f"{'night' if _night(g) else 'afternoon'}.",
            f"{off.school} has the better offense than {dfn.school} has defense — by a lot. {dfn.school} has to shorten the game.",
            f"Talent-wise, {off.school}'s offense should be able to move it on {dfn.school}. The question is whether they beat themselves.",
        ]), 4 if d >= 8 else 2))
    qa, la = _qb_line(a)
    qh, lh = _qb_line(h)
    if qa and qh and la and lh:
        better = qa if qa.overall >= qh.overall else qh
        bt = a if better is qa else h
        out.append(("film", show.vary("pv_qbs", [
            f"Quarterbacks: {qa.name} ({la}) against {qh.name} ({lh}). I trust {better.name} a little more in a tight one.",
            f"{better.name} is the best player on the field. {bt.school} goes as he goes.",
        ]), 3))
    import gameday_dossier as gd
    for t in (a, h):
        star = gd._star(t)
        if star is not None and star.position not in ("QB",):
            s = star.season_stats
            if s["rush_yds"] >= 500:
                out.append(("coach", f"{star.name} — {s['rush_yds']:,} rushing yards. {('Load the box' if t is a else 'Stop the run')} "
                                     f"or you're not beating {t.school}.", 2))
            elif s["rec_yds"] >= 500:
                out.append(("film", f"{t.school}'s {star.name} has {s['rec_yds']:,} receiving yards. Where he lines up, "
                                    f"the safety better follow.", 2))
            elif s["sack"] >= 5:
                out.append(("defender", f"{star.name} has {s['sack']:g} sacks for {t.school}. The tackle across from "
                                        f"him is going to have a long day.", 3))
            elif s["int"] >= 3:
                out.append(("defender", f"{star.name} already has {s['int']} picks. Throw at him at your own risk.", 2))
            break
    pa = a.points_for / max(1, a.wins + a.losses)
    ph = h.points_for / max(1, h.wins + h.losses)
    if min(a.wins + a.losses, h.wins + h.losses) >= 2 and pa >= 38 and ph >= 38:
        out.append(("boom", f"{a.school} scores {pa:.0f} a game. {h.school} scores {ph:.0f}. Take the over and get snacks!", 3))
    pda = a.points_against / max(1, a.wins + a.losses)
    pdh = h.points_against / max(1, h.wins + h.losses)
    if min(a.wins + a.losses, h.wins + h.losses) >= 2 and pda <= 16 and pdh <= 16:   # a real sample, not 0 and 0
        out.append(("defender", f"Two defenses giving up {pda:.0f} and {pdh:.0f} a game. Every yard in this one is going to cost something.", 3))
    return out
