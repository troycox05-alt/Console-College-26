"""
recap.py — Spectator mode: the week (or the offseason) in one place, and a story kit for an AI writer.

THE RECAP opens on its own after every week you watch or simulate, at every stop of the
offseason (the carousel, awards and the draft, the portal, signing day), and any time from
the dashboard ([C]) — in the preseason it's the preseason desk, after the title game it's
the season in review.

CURATE STORIES ([C] on any Recap) builds a story kit: a writing prompt that knows where we
are (the season, the week, conference championship weekend, a playoff round, the offseason
month), editorial rules a real network follows (cover what's newsworthy, keep the rest as
reference), and every fact you chose. Offseason and in-season news is "since the last
edition": what you already curated isn't repeated, and the very first edition is told to
set the scene. The kit goes on your clipboard and into story_kit.txt.
"""
import os

from ui import (
    WIDTH,
    C,
    ask,
    clear,
    pad,
    paint,
    pause,
    rule,
    section,
    title_bar,
    truncate,
)

HERE = os.path.dirname(os.path.abspath(__file__))
KIT_FILE = os.path.join(HERE, "story_kit.txt")

STYLES = [
    ("espn", "National network (ESPN-style)"),
    ("conf", "Conference podcast"),
    ("team", "Team podcast"),
    ("pate", "Josh Pate-style independent show"),
]

# The offseason, stop by stop (season.OFFSEASON_STAGES): (when, what, stop for a Recap?)
STAGES = {
    "off_carousel": ("December", "the coaching carousel", True),
    "off_awards": ("January to April", "awards, the Hall of Fame and the Pro League Draft", True),
    "off_winter": ("winter", "graduation and player development", False),
    "off_portal": ("winter", "the transfer portal", True),
    "off_signing": ("February", "National Signing Day", True),
    "off_arrivals": ("summer", "the freshmen arrive", False),
    "off_rollover": ("August", "a new season's schedule", False),
}
STAGE_ORDER = list(STAGES)

_LIVE = {}           # the offseason in progress (staged_offseason): ctx, stage — never saved


# ── Small helpers ───────────────────────────────────────────────────────────

def _fbs(league):
    return [t for t in league.teams if not getattr(t, "fcs", False)]


def _p4(t):
    import world
    from season import BIG_CONFERENCES
    return t.conference in BIG_CONFERENCES or t.school == getattr(world, "FLAGSHIP_INDEPENDENT", None)


def _rk(rankings, t):
    r = rankings.rank_of(t) if rankings is not None else None
    return f"#{r} " if r else ""


def _kick(league, g):
    import screens
    return screens._kickoff(g, league.rankings)


def _week_games(league, week=None):
    import media_center
    if week is None:
        return media_center._last_week(league)
    return week, [g for g in league.schedule.get(week, []) if g.played]


def _is_upset(league, g):
    k = _kick(league, g)
    w, l = g.winner, g.loser
    rw, rl = k.rank_of(w), k.rank_of(l)
    return bool((rl and (not rw or rw - rl > 5)) or (l.team_ovr - w.team_ovr) >= 5
                or (getattr(w, "fcs", False) and not getattr(l, "fcs", False)))


def _rivalry(g):
    try:
        import rivalries
        if rivalries.is_rivalry(g.home, g.away):
            return rivalries.rivalry_name(g.home, g.away) or "rivalry game"
    except Exception:                                    # noqa: BLE001
        return None
    return None


def tier(league, g):
    """How a real network would treat this game: 1 = lead it, 2 = cover it, 3 = scoreboard only."""
    import postseason as ps
    k = _kick(league, g)
    w, l = g.winner, g.loser
    rw, rl = k.rank_of(w), k.rank_of(l)
    gt = g.game_type or ""
    margin = abs(g.home_score - g.away_score)
    ot = getattr(g.box, "ot_round", 0) if g.box is not None else 0
    if gt in ps.CFP_TYPES or gt == "Conference Championship":
        return 1
    if rw and rl:
        return 1
    if rl and _is_upset(league, g):
        return 1                                         # a ranked team went down
    if (rw or rl) and (margin <= 7 or ot) and min(r for r in (rw, rl) if r) <= 15:
        return 1                                         # a top-15 team in a one-score game
    if getattr(w, "fcs", False) and _p4(l):
        return 1
    if _rivalry(g) and (_p4(g.home) or _p4(g.away)):
        return 1 if (rw or rl) else 2
    if gt == "Bowl":
        return 2
    if rw or rl:
        return 2
    if _p4(g.home) and _p4(g.away):
        return 2
    if _is_upset(league, g) and (_p4(w) or _p4(l)):
        return 2
    return 3


def _score_line(league, g, records=True):
    import postseason as ps
    k = _kick(league, g)
    w, l = g.winner, g.loser
    at = "vs" if (w is g.home or g.neutral) else "at"
    ot = getattr(g.box, "ot_round", 0) if g.box is not None else 0
    tag = []
    gt = g.game_type or ""
    if gt in ps.CFP_TYPES:
        tag.append(ps.round_name(g))
    elif gt == "Conference Championship" or gt == "Bowl":
        tag.append(getattr(g, "display_name", None) or getattr(g, "bowl_name", None) or gt)
    if ot:
        tag.append("OT" if ot == 1 else f"{ot}OT")
    if _is_upset(league, g):
        tag.append("UPSET")
    riv = _rivalry(g)
    if riv:
        tag.append(riv)
    seed = ""
    if gt in ps.CFP_TYPES:
        sw, sl = ps.seed_of(g, w), ps.seed_of(g, l)
        seed = (f"(seed {sw}) ", f"(seed {sl}) ") if sw and sl else ("", "")
    sw_, sl_ = seed if seed else ("", "")
    return (f"{sw_}{_rk(k, w)}{w.school} {g.score_for(w)}, {at} {sl_}{_rk(k, l)}{l.school} {g.score_for(l)}"
            + (f" (now {w.record} and {l.record})" if records else "") + (f"  [{'; '.join(tag)}]" if tag else ""))


def _season_line(s):
    bits = []
    if s.get("pass_att", 0) >= 20:
        bits.append(f"{s['pass_cmp']}/{s['pass_att']} passing, {s['pass_yds']:,} yds, {s['pass_td']} TD, {s['pass_int']} INT")
    if s.get("rush_att", 0) >= 15:
        bits.append(f"{s['rush_att']} car, {s['rush_yds']:,} rush yds, {s['rush_td']} TD")
    if s.get("rec", 0) >= 5:
        bits.append(f"{s['rec']} rec, {s['rec_yds']:,} yds, {s['rec_td']} TD")
    if s.get("tkl", 0) >= 10 or s.get("sack", 0) or s.get("int", 0):
        d = [f"{s.get('tkl', 0)} tkl"]
        for k, lbl in (("tfl", "TFL"), ("sack", "sacks"), ("int", "INT"), ("pbu", "PBU")):
            if s.get(k):
                d.append(f"{s[k]:g} {lbl}")
        bits.append(", ".join(d))
    if s.get("fg_att", 0):
        bits.append(f"{s['fg_made']}/{s['fg_att']} FG")
    return "; ".join(bits)


def _who(p, t=None, cls=True):
    t = t or getattr(p, "team", None)
    yr = f", {p.class_label}" if cls else ""
    return f"{p.name} ({p.position}{yr}{', ' + t.school if t is not None else ''})"


def _weight(league, text):
    """How big the schools named in a line are (for ordering news)."""
    best = 0
    for t in _fbs(league):
        if t.school in text:
            best = max(best, t.prestige + (30 - (league.rankings.rank_of(t) or 30)))
    return best


# ── Where we are ────────────────────────────────────────────────────────────

def phase(league):
    if _LIVE.get("ctx") is not None:
        return "offseason"
    if league.season_complete:
        return "season_over"
    if league.week == 0:
        return "preseason"
    return "inseason"


def where_label(league):
    ph = phase(league)
    if ph == "offseason":
        yr = _LIVE["ctx"]["report"].year
        when, what, _ = STAGES[_LIVE["stage"]]
        return f"{yr}-{str(yr + 1)[2:]} offseason · {when}: {what}"
    if ph == "season_over":
        return f"{league.year} season over · the title game is in the books"
    if ph == "preseason":
        return f"{league.year} preseason"
    return f"{league.year} season · {league.week_name(league.week)}"


def _context(league, prefs, style, focus):
    import committee
    from season import REGULAR_SEASON_WEEKS
    ph = phase(league)
    wk = league.week
    lines = ["CONTEXT", "======="]
    lines.append("- The format: FBS college football and the 12-team National Playoff (first round on campus, "
                 "quarterfinals and semifinals in bowls, then the national championship game). The Media Poll Top 25 "
                 "runs all season; the committee's Playoff Rankings arrive in November.")
    if ph == "inseason":
        if wk <= REGULAR_SEASON_WEEKS:
            left = REGULAR_SEASON_WEEKS - wk
            stage = ("early season — teams still finding out who they are" if wk <= 4 else
                     "midseason — conference play is deciding things" if wk <= 9 else
                     "the stretch run — every result moves the playoff picture")
            lines.append(f"- Where we are: the {league.year} season, just after Week {wk} of {REGULAR_SEASON_WEEKS} "
                         f"in the regular season ({stage}). {left} regular-season week{'s' if left != 1 else ''} left, "
                         f"then conference championship weekend, then the 12-team National Playoff.")
        else:
            import postseason as ps
            lines.append(f"- Where we are: the {league.year} postseason, just after {ps.week_label(wk)}.")
            nxt = {14: "Next: the committee's final rankings, Selection Day and the 12-team bracket, then the National Playoff "
                       "first round on campus.",
                   15: "Next: bowl season and the National Playoff quarterfinals.",
                   16: "Next: the National Playoff semifinals.",
                   17: "Next: the National Championship.",
                   18: "That was the National Championship. The season is over."}.get(wk)
            if nxt:
                lines.append(f"- {nxt}")
        cm = committee.get(league)
        lines.append("- The committee's Playoff Rankings are out and drive the playoff conversation." if cm.released else
                     "- The playoff committee hasn't released rankings yet; the Media Poll is the only poll.")
    elif ph == "season_over":
        lines.append(f"- Where we are: the {league.year} season just ended with the National Championship. The "
                     f"offseason (carousel, awards, the Pro League Draft, the portal, signing day) is next.")
    elif ph == "offseason":
        yr = _LIVE["ctx"]["report"].year
        when, what, _ = STAGES[_LIVE["stage"]]
        done = STAGE_ORDER[:STAGE_ORDER.index(_LIVE["stage"]) + 1]
        todo = [STAGES[s][1] for s in STAGE_ORDER[STAGE_ORDER.index(_LIVE["stage"]) + 1:] if STAGES[s][2]]
        lines.append(f"- Where we are: the offseason between the {yr} and {yr + 1} seasons — {when}, {what}. "
                     f"Done so far this offseason: {', '.join(STAGES[s][1] for s in done)}."
                     + (f" Still to come: {', '.join(todo)}." if todo else ""))
    else:
        lines.append(f"- Where we are: the {league.year} preseason. The offseason is over: coaches hired, the "
                     f"draft done, the portal closed, the freshmen on campus. Week 1 is next.")
    last = prefs.get("last")
    if not prefs.get("editions"):
        lines.append("- FIRST EDITION: this is the first piece of coverage in this series. Set the scene — the "
                     "landscape, the powers, the storylines, where this moment sits in the season or offseason — "
                     "before the news.")
    elif last:
        lines.append(f"- Previous edition: {last}. Pick up the story from there. The news below is what's new since "
                     f"then; anything repeated (polls, standings) is the current state, for context.")
    if focus:
        lines.append(f"- Focus of this show: {focus}.")
    return "\n".join(lines) + "\n"


EDITORIAL = """
EDITORIAL RULES
===============
- Write it LONG and complete: this is a full feature or a full episode, not a summary.
- Be a real network: lead with what matters (ranked teams, upsets, playoff and conference-race stakes,
  rivalries, records, coaching drama, stars). Items marked LEAD are the stories; ALSO NOTABLE gets
  shorter treatment; REFERENCE is there so you know everything and get every fact right — use it for
  context, and don't spend time on games or names nobody would care about (a mid-major blowout, an
  unranked team beating an FCS team) unless there's a real story in it.
- Every result, record, ranking, stat and name comes from the FACTS. Never invent a score, a stat, an
  injury, a quote attributed to a real person, or a result. Analysis, opinion, stakes and predictions
  are yours to bring.
- Be context aware: what this moment of the season means, what's next, what changed since last time.
"""


def _task(style, focus, ph):
    long_ = "3,000-4,500 words" if ph in ("offseason", "preseason", "season_over") else "2,500-4,000 words"
    if style == "espn":
        return (f"FORMAT: a long-form national feature from a major sports network's college football desk "
                f"(think a big ESPN-style wrap). {long_}. A strong headline and dek, then sections with subheads "
                f"built around the lead stories, then the polls and the playoff picture (or, in the offseason, "
                f"what the moves mean for next year), the stars, recruiting, and what to watch next.")
    if style == "conf":
        return (f"FORMAT: a full episode script of a {focus} conference podcast, two hosts with original names. "
                f"{long_}. Cold open, then segments: every result and storyline in the {focus} with real takes, "
                f"the race (or the offseason winners and losers), the league's place in the national picture, "
                f"the league's best players, recruiting, and predictions. Stay on the {focus}; touch the rest of "
                f"the country only when it matters to the league.")
    if style == "team":
        return (f"FORMAT: a full episode script of a {focus} fan podcast, a host and a co-host with original "
                f"names, homers but honest. {long_}. Center everything on {focus}: their result or offseason, "
                f"grades, the players who stood out, the conference race and playoff path, recruiting and "
                f"portal moves that touch {focus}, the rivals, and what's next. A detailed TEAM DOSSIER follows: "
                f"treat it as the show's standing research packet and use its roster, staff, athletic director, "
                f"schedule and expectations throughout the episode whenever relevant.")
    return (f"FORMAT: a full solo-host episode script in the style of Josh Pate's college football show — "
            f"energetic, conversational, opinion-first: big takes, tangents that come back around, talking "
            f"straight to the audience, ranking things, calling out overreactions and underreactions, closing "
            f"predictions. Write it as an ORIGINAL host inspired by that style; don't present it as Josh Pate "
            f"himself or put words in his mouth. {long_}, with segment headings.")


# ── Sections ────────────────────────────────────────────────────────────────
# Each returns a list of lines. "news" sections are filtered against what earlier editions
# already covered.

def sec_scores(league, kit):
    games = kit["games"]
    played = [g for g in games if g.played and not (getattr(g.home, "fcs", False) and getattr(g.away, "fcs", False))]
    t1, t2, t3 = [], [], []
    for g in sorted(played, key=lambda g: (tier(league, g), -sum(30 - (_kick(league, g).rank_of(t) or 30)
                                                                   for t in (g.home, g.away)))):
        [t1, t2, t3][tier(league, g) - 1].append(_score_line(league, g))
    out = [f"{kit['week_name']}:", "LEAD:"] + (t1 or ["(no headline games)"])
    out += ["", "ALSO NOTABLE:"] + (t2 or ["(none)"])
    out += ["", "REFERENCE — the rest of the scoreboard:"] + (t3 or ["(none)"])
    return out


def _top40(league):
    """The top 40 of the full order — this week's and last week's, so a team that just fell out still counts."""
    r = league.rankings
    return set(r.order[:40]) | set((getattr(r, "last_order", None) or [])[:40])


def sec_boxes(league, kit):
    """Full box scores for every game a top-40 team played."""
    import re

    from commentary import box_score_lines
    top = _top40(league)
    pos = {t: i for i, t in enumerate(league.rankings.order, 1)}
    games = [g for g in kit["games"] if g.played and g.box is not None and (g.home in top or g.away in top)]
    games.sort(key=lambda g: (tier(league, g), min(pos.get(g.home, 999), pos.get(g.away, 999))))
    out = []
    for g in games:
        try:
            lines = [re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", ln).rstrip() for ln in box_score_lines(g.box)]
        except Exception:                                # noqa: BLE001, S112
            continue
        tags = []
        for t in (g.away, g.home):
            if t in top and not league.rankings.rank_of(t):
                tags.append(f"{t.school} is just outside the Top 25")
        out.append(f"=== {_score_line(league, g, records=False)} ===" + (f"  ({'; '.join(tags)})" if tags else ""))
        out += [ln for ln in lines if ln.strip()]
        out.append("")
    return out


def sec_earlier(league, kit):
    """Headline games from weeks between the last edition and this one."""
    prefs = kit["prefs"]
    lw = prefs.get("last_week")
    if prefs.get("last_year") != league.year or lw is None or kit["week"] is None or kit["week"] - lw <= 1:
        return []
    out = []
    for w in range(lw + 1, kit["week"]):
        gs = [g for g in league.schedule.get(w, []) if g.played and tier(league, g) == 1]
        if gs:
            out.append(f"{league.week_name(w)}:")
            out += [_score_line(league, g) for g in gs]
    return out


def sec_headlines(league, kit):
    import dashboard
    team = getattr(league, "follow_team", None) or (league.rankings.top() or _fbs(league))[0]
    items = [text for _col, text in dashboard.headlines(league, team, n=20)]
    yr = league.carousel.get(league.year, []) if isinstance(getattr(league, "carousel", None), dict) else []
    items += [text for kind, text in yr if kind in ("fired", "hired", "retired", "poached")]
    items = sorted(dict.fromkeys(items), key=lambda t: -_weight(league, t))
    return [f"- {t}" for t in items]


def sec_hotseat(league, kit):
    import carousel as cz
    cs = [c for c in cz.all_coaches(league) if c.team is not None and not cz.is_interim(c)]
    hot = sorted(cs, key=lambda c: -c.seat)[:12]
    return [f"  {c.name}, {c.team.school} ({c.team.record}) — {cz.seat_label(c.seat)}" for c in hot]


def _rec_news(league, weeks):
    cyc = league.recruiting
    meta = cyc.__dict__.get("news_meta", {})
    items = [t for w, _k, t in getattr(cyc, "news", []) if weeks is None or w in weeks]
    return sorted(items, key=lambda t: -((meta.get(t) or (0, None, 0))[2] or 0))


def sec_recruiting(league, kit):
    cyc = league.recruiting
    meta = cyc.__dict__.get("news_meta", {})
    news = [t for t in _rec_news(league, None) if ((meta.get(t) or (0, None, 0))[2] or 0) >= 4][:30]
    out = [f"- {t}" for t in news]
    return out


def sec_classes(league, kit):
    cyc = league.recruiting
    out = []
    try:
        ranked = sorted(_fbs(league), key=lambda t: cyc.class_rank(t) or 999)[:20]
        for t in ranked:
            r = cyc.class_rank(t)
            if not r:
                continue
            commits = cyc._class_of(t)
            five = sum(1 for x in commits if getattr(x, "stars", 0) == 5)
            four = sum(1 for x in commits if getattr(x, "stars", 0) == 4)
            out.append(f"  {r:>2}. {t.school} — {len(commits)} commits ({five} five-star, {four} four-star)")
    except Exception:                                    # noqa: BLE001, S110
        pass
    return out


def sec_standings(league, kit):
    from league import CONFERENCES
    out = []
    for short, full, _col in CONFERENCES:
        teams = league.standings(short)
        if not teams:
            continue
        out.append(f"{full}:")
        for i, t in enumerate(teams, 1):
            conf = f"{t.conf_wins}-{t.conf_losses} conf, " if short != "Independent" else ""
            out.append(f"  {i:>2}. {_rk(league.rankings, t)}{t.school} — {conf}{t.record} overall")
    return out


def sec_ap(league, kit):
    r = league.rankings
    out = []
    for i, t in enumerate(r.top(), 1):
        prev = r.previous_rank(t)
        move = "new" if not prev else ("—" if prev == i else (f"up {prev - i}" if prev > i else f"down {i - prev}"))
        rec = "" if league.week == 0 else f" ({t.record})"
        import team_momentum
        form = f", form: {team_momentum.line(t)}" if league.week and t.wins + t.losses else ""
        out.append(f"  {i:>2}. {t.school}{rec} — {move if league.week else 'preseason'}{form}")
    return out


def sec_cfp(league, kit):
    import committee
    cm = committee.get(league)
    if not cm.released:
        return []
    out = []
    for i, t in enumerate(cm.order[:25], 1):
        prev = cm.previous_rank(t)
        move = "" if not prev or prev == i else (f" (up {prev - i})" if prev > i else f" (down {i - prev})")
        out.append(f"  {i:>2}. {t.school} ({t.record}){move}")
    return out


def sec_heisman(league, kit):
    r = league.rankings
    return [f"  {i:>2}. {p.name}, {p.position}, {p.team.school if p.team else '—'} — {blurb}"
            for i, (p, _score, blurb) in enumerate(r.heisman[:12], 1)]


def sec_potg(league, kit):
    import impact
    import media_center as mc
    games = kit["games"]
    out = ["Player of the game (headline games first):"]
    for g in sorted([g for g in games if g.played and g.box is not None], key=lambda g: tier(league, g)):
        if tier(league, g) == 3:
            continue
        try:
            p, t, side = impact.player_of_the_game(g.box)
        except Exception:                                # noqa: BLE001, S112
            continue
        if p is None:
            continue
        out.append(f"  {g.winner.school} {g.score_for(g.winner)}-{g.score_for(g.loser)} {g.loser.school}: "
                   f"{_who(p, t)} — {mc._line(p, g.box.stats[p], side)}")
    aw = mc.week_awards(league, games)
    out += ["", "National players of the week:"]
    for key, label, side in (("off", "Offense", "off"), ("def", "Defense", "def"), ("fr", "Freshman", None),
                             ("st", "Special teams", "st")):
        p, _v, c, t = aw[key]
        if p is not None:
            out.append(f"  {label}: {_who(p, t)} — {mc._line(p, c, side or 'off')}")
    return out


def sec_notable(league, kit, limit=260):
    import media_center as mc
    seen, rows = set(), []
    per = max(12, limit // len(mc.CATEGORIES) + 12)
    for _name, _key, value, _detail in mc.CATEGORIES:
        ranked = []
        for t in _fbs(league):
            for p in t.roster:
                v = value(p, p.season_stats)
                if v:
                    ranked.append((v, p, t))
        ranked.sort(key=lambda x: -x[0])
        for _v, p, t in ranked[:per]:
            if id(p) not in seen:
                seen.add(id(p))
                rows.append((p, t))
    hz = {id(p) for p, _s, _b in league.rankings.heisman}
    rows.sort(key=lambda x: (id(x[0]) not in hz, league.rankings.rank_of(x[1]) or 99))
    out = []
    for p, t in rows[:limit]:
        line = _season_line(p.season_stats)
        if line:
            out.append(f"  {p.name} ({p.position}, {p.class_label}, {_rk(league.rankings, t)}{t.school} {t.record}): {line}")
    return out


def sec_final(league, kit):
    """The season in review: champion, the bracket, conference champions, the big bowls."""
    import postseason as ps
    yr = kit["season"]
    out = []
    ch = league.champion_of(yr)
    if ch:
        out.append(f"NATIONAL CHAMPION: {ch.champion} ({ch.record}), def. {ch.runner_up} {ch.score}-{ch.opp_score}"
                   f"{' (' + ch.note + ')' if ch.note else ''} at {ch.site}. Head coach {ch.coach}.")
    for wk in (15, 16, 17, 18):
        gs = [g for g in league.schedule.get(wk, []) if g.played and g.game_type in ps.CFP_TYPES]
        if gs:
            out.append(f"{ps.round_name(gs[0])}:")
            out += ["  " + _score_line(league, g, records=False) for g in gs]
    ccg = [g for g in league.schedule.get(14, []) if g.played and g.game_type == "Conference Championship"]
    if ccg:
        out.append("Conference championship games:")
        out += ["  " + _score_line(league, g, records=False) for g in ccg]
    bowls = [g for g in league.schedule.get(16, []) + league.schedule.get(15, []) + league.schedule.get(17, [])
             if g.played and g.game_type == "Bowl"]
    if bowls:
        bowls.sort(key=lambda g: tier(league, g))
        out.append("Bowls (biggest first):")
        out += ["  " + _score_line(league, g, records=False) for g in bowls[:20]]
    return out


def sec_carousel(league, kit):
    yr = kit["season"]
    items = [text for kind, text in (league.carousel.get(yr, []) if isinstance(league.carousel, dict) else [])
             if kind in ("fired", "hired", "retired", "poached", "vote")]
    items += [text for y, _k, text in getattr(league, "ad_moves", []) if y == yr]
    items = sorted(dict.fromkeys(items), key=lambda t: -_weight(league, t))
    return [f"- {t}" for t in items]


def sec_awards(league, kit):
    aw = (getattr(league, "awards", {}) or {}).get(kit["season"])
    if not aw:
        return []
    out = []
    if aw.get("heisman"):
        p, t, line = aw["heisman"]
        out.append(f"Golden Helmet winner: {_who(p, t, cls=False)} — {line}")
    for name, p, t, line in aw.get("positional", []):
        out.append(f"{name}: {_who(p, t, cls=False)} — {line}")
    if aw.get("freshman"):
        p, t, line = aw["freshman"]
        out.append(f"Freshman of the Year: {_who(p, t, cls=False)} — {line}")
    if aw.get("coach"):
        name, t, rec = aw["coach"]
        out.append(f"Coach of the Year: {name}, {t.school} ({rec})")
    if aw.get("first"):
        out.append("First-team All-Americans: " + "; ".join(f"{grp} {p.name} ({t.school})" for grp, p, t in aw["first"]))
    if aw.get("second"):
        out.append("Second-team All-Americans (reference): " + "; ".join(f"{grp} {p.name} ({t.school})"
                                                                      for grp, p, t in aw["second"]))
    return out


def sec_draft(league, kit):
    picks = (getattr(league, "drafts", {}) or {}).get(kit["season"])
    if not picks:
        return []
    out = [f"{len(picks)} players drafted, {sum(1 for x in picks if x.get('early'))} underclassmen."]
    out.append("Round 1:")
    for x in picks[:32]:
        out.append(f"  {x['overall_pick']:>2}. {x['nfl']} — {x['name']}, {x['pos']}, {x['school']}"
                   f"{' (early entry)' if x.get('early') else ''}")
    by = {}
    for x in picks:
        by[x["school"]] = by.get(x["school"], 0) + 1
    top = sorted(by.items(), key=lambda kv: -kv[1])[:12]
    out.append("Most players drafted: " + ", ".join(f"{s} {n}" for s, n in top))
    return out


def sec_portal(league, kit):
    rep = None
    if _LIVE.get("ctx") is not None:
        rep = getattr(_LIVE["ctx"]["report"], "portal", None)
    rep = rep or getattr(league, "last_portal", None)
    if rep is None or not getattr(rep, "moves", None):
        return []
    yr = kit["season"]

    def value(m):
        e, _t = m
        p = e.player
        st = p.yearly_stats.get(yr) or {}
        prod = st.get("pass_yds", 0) / 30 + st.get("rush_yds", 0) / 12 + st.get("rec_yds", 0) / 12 \
            + st.get("tkl", 0) * 1.2 + st.get("sack", 0) * 6 + st.get("int", 0) * 8
        return p.hs_stars * 20 + prod + (25 if (e.depth or 9) <= 1 else 0)
    moves = sorted(rep.moves, key=lambda m: -value(m))
    out = [f"{len(rep.moves)} players moved in the transfer portal; {len(getattr(rep, 'unsigned', []))} are still unsigned."]
    for e, new in moves[:45]:
        p = e.player
        st = _season_line(p.yearly_stats.get(yr) or {})
        role = "starter" if (e.depth or 9) <= 1 else "backup"
        out.append(f"  {p.name}, {p.position} — {e.origin.school} to {new.school} (former {p.hs_stars}-star, {role}"
                   f"{'; ' + st if st else ''}; {e.reason})")
    net = {}
    for e, new in rep.moves:
        net[new.school] = net.get(new.school, 0) + p_val(e)
        net[e.origin.school] = net.get(e.origin.school, 0) - p_val(e)
    gain = sorted(net.items(), key=lambda kv: -kv[1])
    out.append("Biggest portal winners: " + ", ".join(s for s, _v in gain[:8]))
    out.append("Biggest portal losses: " + ", ".join(s for s, _v in gain[-8:][::-1]))
    return out


def p_val(e):
    return e.player.hs_stars + (2 if (e.depth or 9) <= 1 else 0)


def sec_signing(league, kit):
    rep = None
    if _LIVE.get("ctx") is not None:
        rep = getattr(_LIVE["ctx"]["report"], "recruiting", None)
    if rep is not None:
        return _signing_lines(rep)
    cap = league.__dict__.get("recap_capture") or {}
    return list(cap.get("signing", [])) if cap.get("year") == kit["season"] else []


def _signing_lines(rep):
    ranks = sorted(rep.ranks.items(), key=lambda kv: kv[1])[:25]
    out = ["National Signing Day — final class rankings:"]
    for t, r in ranks:
        cls = rep.classes.get(t, [])
        out.append(f"  {r:>2}. {t.school} — {len(cls)} signees ({sum(1 for x in cls if x.stars == 5)} five-star, "
                   f"{sum(1 for x in cls if x.stars == 4)} four-star)")
    top = sorted((x for cls in rep.classes.values() for x in cls), key=lambda x: x.national_rank or 9999)[:30]
    out.append("The top recruits and where they signed:")
    for x in top:
        dest = next((t.school for t, cls in rep.classes.items() if x in cls), "?")
        out.append(f"  No. {x.national_rank} {x.player.name}, {x.stars}-star {x.position} — {dest}")
    for x, a, b in list(getattr(rep, "flips", []))[:12]:
        out.append(f"  FLIP: {x.player.name} ({x.stars}-star {x.position}) from "
                   f"{getattr(a, 'school', a)} to {getattr(b, 'school', b)}")
    return out


def sec_new_coaches(league, kit):
    out = []
    for t in sorted(_fbs(league), key=lambda t: -t.prestige):
        c = t.coach
        if c is not None and c.hired_year == league.year:
            prev = c.history[-1]["school"] if c.history else (getattr(c, "origin", "") or "first head job")
            out.append(f"  {t.school}: {c.name} (from {prev})")
    return out


def sec_games_of_year(league, kit):
    r = league.rankings
    games = [g for w in range(1, 14) for g in league.schedule.get(w, [])]
    scored = []
    for g in games:
        a, b = r.rank_of(g.home), r.rank_of(g.away)
        v = (30 - a if a else 0) + (30 - b if b else 0) + (12 if _rivalry(g) and (a or b) else 0)
        if a and b:
            v += 20
        if v >= 25:
            scored.append((v, g))
    scored.sort(key=lambda x: -x[0])
    out = []
    for _v, g in scored[:20]:
        riv = _rivalry(g)
        out.append(f"  Week {g.week}: {_rk(r, g.away)}{g.away.school} at {_rk(r, g.home)}{g.home.school}"
                   + (f" [{riv}]" if riv else ""))
    return out


def sec_outlook(league, kit):
    from league import CONFERENCES
    r = league.rankings
    out = []
    for short, full, _c in CONFERENCES:
        teams = league.conference_teams(short)
        if not teams or short == "Independent":
            continue
        top = sorted(teams, key=lambda t: (r.rank_of(t) or 99, -t.prestige))[:4]
        out.append(f"{full} contenders: " + ", ".join(f"{_rk(r, t)}{t.school}" for t in top))
    return out


def sec_returning(league, kit):
    aw = (getattr(league, "awards", {}) or {}).get(league.year - 1) or {}
    out = []
    for grp, p, t in aw.get("first", []) + aw.get("second", []):
        if p.team is not None and p in p.team.roster:
            moved = f" (transferred from {t.school})" if p.team is not t else ""
            out.append(f"  {grp} {p.name}, {p.team.school}{moved} — All-American last season; "
                       f"{_season_line(p.yearly_stats.get(league.year - 1) or {})}")
    return out


# key: (label, function, on by default, phases it belongs to, filter against earlier editions?)
SECTIONS = {
    "earlier":   ("Headline games since the last edition", sec_earlier, True, {"inseason"}, False),
    "scores":    ("Game scores (lead / notable / reference)", sec_scores, True, {"inseason"}, False),
    "boxes":     ("Full box scores: every game with a top-40 team", sec_boxes, True, {"inseason"}, False),
    "headlines": ("Headlines & notes (upsets, injuries, records, coaches)", sec_headlines, True,
                  {"inseason", "season_over"}, True),
    "hotseat":   ("Hot seat watch", sec_hotseat, True, {"inseason"}, False),
    "final":     ("The season in review (champion, bracket, CCGs, bowls)", sec_final, True, {"season_over", "offseason"}, True),
    "carousel":  ("Coaching carousel & AD moves", sec_carousel, True, {"offseason", "preseason", "season_over"}, True),
    "awards":    ("Awards & All-Americans", sec_awards, True, {"offseason", "preseason"}, True),
    "draft":     ("The Pro League Draft", sec_draft, True, {"offseason", "preseason"}, True),
    "portal":    ("The transfer portal", sec_portal, True, {"offseason", "preseason"}, True),
    "signing":   ("Signing day & class rankings", sec_signing, True, {"offseason", "preseason"}, True),
    "recruiting": ("Recruiting news (4- and 5-stars)", sec_recruiting, True, {"inseason", "season_over"}, True),
    "classes":   ("Recruiting class rankings (in progress)", sec_classes, True, {"inseason", "season_over"}, False),
    "standings": ("Conference standings", sec_standings, True, {"inseason", "season_over"}, False),
    "ap":        ("Media Poll Top 25", sec_ap, True, {"inseason", "season_over", "preseason"}, False),
    "cfp":       ("Playoff Rankings (when released)", sec_cfp, True, {"inseason"}, False),
    "heisman":   ("Golden Helmet watch", sec_heisman, True, {"inseason", "season_over", "preseason"}, False),
    "potg":      ("Players of the game & of the week", sec_potg, True, {"inseason"}, False),
    "new_coaches": ("New head coaches", sec_new_coaches, True, {"preseason"}, False),
    "outlook":   ("Conference contenders", sec_outlook, True, {"preseason"}, False),
    "games":     ("Games of the year (the schedule's biggest)", sec_games_of_year, True, {"preseason"}, False),
    "returning": ("Returning All-Americans", sec_returning, True, {"preseason"}, False),
    "notable":   ("Notable stats (about 250 players)", sec_notable, False, {"inseason", "season_over"}, False),
}


def _kit_state(league, prefs, games=None):
    ph = phase(league)
    wk, wgames = _week_games(league) if ph in ("inseason", "season_over") else (None, [])
    if ph == "season_over":
        wk, wgames = _week_games(league, 18)
    season = _LIVE["ctx"]["report"].year if ph == "offseason" else (league.year - 1 if ph == "preseason"
                                                                     else league.year)
    return {"phase": ph, "week": wk, "games": games if games is not None else wgames, "prefs": prefs,
            "season": season, "week_name": league.week_name(wk) if wk else ""}


def available(league, prefs, games=None):
    kit = _kit_state(league, prefs, games)
    return [k for k, v in SECTIONS.items() if kit["phase"] in v[3]], kit


def _key(k, line):
    """What makes a news line the same story next time: not records or class years that move."""
    import re
    return f"{k}|" + re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", line)).strip()


def _seen(league):
    s = league.__dict__.get("recap_seen")
    if not isinstance(s, set):
        s = league.__dict__["recap_seen"] = set()
    return s


STAFF_LEVELS = [
    ("off", "Off"),
    ("hc", "Head coaches"),
    ("coords", "Head coaches + coordinators"),
    ("full", "Head coaches + coordinators + position coaches"),
]


def _staff_teams(league, fact_lines, style, focus):
    """Teams worth including in the AI reference: teams that actually appear in this kit."""
    joined = "\n".join(fact_lines)
    teams = [t for t in league.teams if t.school and t.school in joined]
    if focus and style == "team":
        teams += [t for t in league.teams if t.school == focus]
    elif focus and style == "conf":
        teams += list(league.conference_teams(focus))
    seen, out = set(), []
    for t in teams:
        if t.school not in seen:
            seen.add(t.school)
            out.append(t)
    return sorted(out, key=lambda t: t.school)


def _staff_lines(league, fact_lines, style, focus, level):
    if level == "off":
        return []
    import poscoach
    out = []
    for t in _staff_teams(league, fact_lines, style, focus):
        hc = getattr(t, "coach", None)
        bits = [f"HC {hc.name}" if hc is not None else "HC —"]
        if level in ("coords", "full"):
            oc, dc = getattr(t, "oc", None), getattr(t, "dc", None)
            bits += [f"OC {oc.name}" if oc is not None else "OC —",
                     f"DC {dc.name}" if dc is not None else "DC —"]
        out.append(f"- {t.school}: " + "; ".join(bits))
        if level == "full":
            room = t.__dict__.get("pos_coaches", {})
            pcs = []
            for g in poscoach.GROUPS:
                c = room.get(g)
                if c is not None:
                    pcs.append(f"{g} {c.name}")
            if pcs:
                out.append("  Position coaches: " + "; ".join(pcs))
    return out




def _team_by_school(league, school):
    return next((t for t in league.teams if t.school == school), None)


def _team_schedule_lines(league, team):
    """A writer-friendly full schedule: every played result plus every known future game."""
    out = []
    for g in league.team_games(team):
        opp = g.opponent_of(team)
        where = "vs" if g.neutral or g.home is team else "at"
        rank = None
        try:
            rank = (getattr(g, "ranks", None) or {}).get(opp) if g.played else league.rankings.rank_of(opp)
        except Exception:                                    # noqa: BLE001
            rank = None
        opp_name = f"#{rank} {opp.school}" if rank else opp.school
        label = league.week_name(g.week) if getattr(g, "week", None) else ""
        tags = []
        if getattr(g, "conference_game", False) and getattr(g, "game_type", "") == "Regular Season":
            tags.append("conference")
        if getattr(g, "game_type", "") and g.game_type != "Regular Season":
            tags.append(str(g.game_type))
        if getattr(g, "showcase", None):
            tags.append(str(g.showcase))
        riv = _rivalry(g)
        if riv:
            tags.append(riv)
        suffix = f" [{'; '.join(tags)}]" if tags else ""
        if g.played:
            result = "W" if g.winner is team else "L"
            ot = getattr(getattr(g, "box", None), "ot_round", 0)
            ot_txt = " OT" if ot == 1 else (f" {ot}OT" if ot else "")
            out.append(f"- {label}: {result} {team.school} {g.score_for(team)}-{g.score_for(opp)} {where} {opp_name}{ot_txt}{suffix}")
        else:
            out.append(f"- {label}: {where} {opp_name}{suffix}")
    return out or ["- No schedule is available yet."]


def _team_roster_lines(league, team):
    """Full public/context roster without leaking hidden Coach Career ratings."""
    import finance
    from injuries import status_text
    from models import POSITIONS

    out = []
    captains = set(getattr(team, "captains", None) or [])
    for pos in POSITIONS:
        room = list(team.players_at(pos))
        if not room:
            continue
        out.append(f"{pos}:")
        for i, p in enumerate(room, 1):
            bits = [f"#{p.number} {p.name}", p.class_label, f"{p.height_str}, {p.weight} lb", f"depth {i}"]
            if p in captains:
                bits.append("captain")
            tr = getattr(p, "transfer_from", None) or getattr(p, "prev_school", None)
            if tr:
                bits.append(f"transfer from {tr}")
            if getattr(p, "inj_games", 0) > 0:
                try:
                    bits.append(status_text(p))
                except Exception:                          # noqa: BLE001
                    bits.append("injured")
            nil = finance.player_nil(p)
            if nil:
                bits.append(f"NIL {finance.money(nil)}/yr")
            stats = _season_line(getattr(p, "season_stats", {}) or {})
            if stats:
                bits.append(stats)
            out.append("- " + " · ".join(bits))
    return out


def _team_staff_lines(team):
    import poscoach
    out = []
    hc = getattr(team, "coach", None)
    oc = getattr(team, "oc", None)
    dc = getattr(team, "dc", None)
    if hc is not None:
        bits = [f"Head coach: {hc.name}"]
        if getattr(hc, "offense_scheme", None):
            bits.append(f"offense {hc.offense_scheme}")
        if getattr(hc, "defense_scheme", None):
            bits.append(f"defense {hc.defense_scheme}")
        hired = getattr(hc, "hired_year", None)
        if hired:
            bits.append(f"hired {hired}")
        out.append("- " + " · ".join(bits))
    if oc is not None:
        bits = [f"Offensive coordinator: {oc.name}"]
        if getattr(oc, "offense_scheme", None):
            bits.append(str(oc.offense_scheme))
        out.append("- " + " · ".join(bits))
    if dc is not None:
        bits = [f"Defensive coordinator: {dc.name}"]
        if getattr(dc, "defense_scheme", None):
            bits.append(str(dc.defense_scheme))
        out.append("- " + " · ".join(bits))
    room = team.__dict__.get("pos_coaches", {})
    for grp in poscoach.GROUPS:
        c = room.get(grp)
        if c is not None:
            out.append(f"- {grp} coach: {c.name}")
    return out or ["- Staff information unavailable."]


def _team_dossier(league, focus):
    """Deep reference packet automatically attached to a team-focused podcast."""
    team = _team_by_school(league, focus)
    if team is None:
        return []
    import carousel
    import preseason_board

    lines = [f"TEAM DOSSIER — {team.full_name.upper()}", "=" * (15 + len(team.full_name)), ""]
    rank = league.rankings.rank_of(team) if getattr(league, "rankings", None) is not None else None
    lines += ["PROGRAM SNAPSHOT"]
    lines.append(f"- School: {team.full_name}; conference: {team.conference_label}; home: {team.stadium} ({team.capacity:,})")
    lines.append(f"- Current record: {team.record}; conference: {team.conf_record}; current poll: {'#' + str(rank) if rank else 'unranked'}")
    if getattr(team, "last_season", None):
        lines.append(f"- Last season: {team.last_season[0]}-{team.last_season[1]}")
    lines.append(f"- Program prestige: {round(team.prestige)}")
    if team.wins + team.losses:
        g = team.wins + team.losses
        lines.append(f"- Scoring: {team.points_for / g:.1f} points/game; {team.points_against / g:.1f} allowed/game")

    lines += ["", "EXPECTATIONS & ATHLETIC DIRECTOR"]
    try:
        proj = preseason_board.build(league, team)
        lines.append(f"- Preseason projection: {proj['projected_wins']:.1f} wins; conference #{proj['conference_rank']} of {proj['conference_size']}; "
                     f"poll {'#' + str(proj['poll_rank']) if proj['poll_rank'] else 'unranked'}")
    except Exception:                                      # noqa: BLE001
        pass
    ad = getattr(team, "ad", None) or {}
    if ad:
        style = ad.get("style", "")
        style_name = carousel.AD_STYLES.get(style, (style or "unknown",))[0]
        lines.append(f"- Athletic director: {ad.get('name', '—')} · style: {style_name}")
    goals = getattr(team, "goals", None) or []
    if goals:
        lines.append("- Program goals: " + "; ".join(getattr(g, "label", getattr(g, "short", str(g))) for g in goals))
    coach = getattr(team, "coach", None)
    if coach is not None and team.wins + team.losses:
        try:
            xw, n = carousel.expectation(league, team, coach)
            if n:
                lines.append(f"- AD expectation through games played: {xw:.1f} expected wins over {n} games; actual {team.wins}-{team.losses}")
        except Exception:                                  # noqa: BLE001
            pass

    lines += ["", "COACHING STAFF"] + _team_staff_lines(team)
    lines += ["", "FULL SCHEDULE & RESULTS"] + _team_schedule_lines(league, team)
    lines += ["", "FULL ROSTER"] + _team_roster_lines(league, team)

    # Recruiting/portal context that already belongs to this team, when available.
    targets = list(getattr(team, "recruiting_targets", None) or [])
    if targets:
        lines += ["", "ACTIVE RECRUITING BOARD"]
        for r in targets:
            pos = getattr(r, "position", "")
            stars = getattr(r, "stars", None)
            bits = [getattr(r, "name", "Recruit"), pos]
            if stars is not None:
                bits.append(f"{stars}-star")
            home = getattr(r, "home_state", None) or getattr(r, "state", None)
            if home:
                bits.append(str(home))
            lines.append("- " + " · ".join(str(x) for x in bits if x))

    lines += ["", "USE OF THIS DOSSIER",
              "- This is the authoritative background packet for the team-focused show. Use it throughout the episode for names, depth-chart context, schedule arcs, expectations, staff/AD context and player production.",
              "- Do not recite the roster mechanically. Pull in the relevant players and staff naturally when discussing games, injuries, development, recruiting, scheme, jobs and what comes next.",
              "- Do not invent facts that are absent from this dossier or the selected FACTS sections."]
    return lines


def build_kit(league, keys, style, focus=None, games=None, prefs=None):
    """(kit text, the news lines it covered)."""
    prefs = prefs if prefs is not None else _prefs(league)
    _keys, kit = available(league, prefs, games)
    seen = _seen(league)
    names = set()
    if focus and style == "team":
        names = {focus}
    elif focus and style == "conf":
        names = {t.school for t in league.conference_teams(focus)}
    intro = (f"You are writing college football coverage for {where_label(league)}. Read the CONTEXT and the "
             f"EDITORIAL RULES, then write it from the FACTS.\n\n")
    parts = [intro, _context(league, prefs, style, focus),
             EDITORIAL, "\n" + _task(style, focus, kit["phase"]) + "\n"]
    if style == "team" and focus:
        dossier = _team_dossier(league, focus)
        if dossier:
            parts.append("\n" + "\n".join(dossier) + "\n")
    parts.append("\nFACTS\n=====\n")
    covered, before, fact_lines = [], [], []
    for k in keys:
        label, fn, _on, _phases, news = SECTIONS[k]
        try:
            lines = fn(league, kit)
        except Exception as e:                           # noqa: BLE001 — one broken section never sinks the kit
            lines = [f"(couldn't build this section: {e})"]
        if news:
            fresh = [ln for ln in lines if _key(k, ln) not in seen]
            covered += [_key(k, ln) for ln in fresh]
            if lines and not fresh:
                before.append(label)                     # all of it was in an earlier edition
            lines = fresh
        if not lines:
            continue
        if names:
            mine = [ln for ln in lines if any(n in ln for n in names)]
            if mine and len(mine) < len(lines):
                lines = [f"{focus.upper()} FIRST:"] + mine + ["", "Elsewhere:"] + [ln for ln in lines if ln not in mine]
        fact_lines += lines
        parts.append(f"\n## {label}\n" + "\n".join(lines) + "\n")
    staff_level = prefs.get("staff", "off")
    staff_lines = _staff_lines(league, fact_lines, style, focus, staff_level)
    if staff_lines:
        parts.append("\n## COACHING STAFFS\n" + "\n".join(staff_lines) +
                     "\nREFERENCE: use these names when coaching context matters; do not force every assistant into the story.\n")
    if before:
        parts.append("\n## Already covered in earlier editions\n" + ", ".join(before) + " — nothing new there since "
                     "the last edition. Don't re-report it; refer back to it as background where it matters.\n")
    import universe
    return universe.translate("".join(parts)), covered          # your universe's names: Heisman, CFP, SEC...


# ── Screens ─────────────────────────────────────────────────────────────────

def _prefs(league):
    p = league.__dict__.setdefault("recap_prefs", {})
    p.setdefault("style", "espn")
    p.setdefault("off", [k for k, v in SECTIONS.items() if not v[2]])   # sections you've switched off
    p.setdefault("editions", 0)
    p.setdefault("staff", "off")
    p.pop("keys", None)                                                  # (v49.1's list, before phases)
    return p


def _pick_conference(league):
    from league import CONFERENCES
    confs = [s for s, _f, _c in CONFERENCES if s != "Independent"]
    print()
    for i, c in enumerate(confs, 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {c}")
    c = ask("Which conference?").strip()
    if c.isdigit() and 1 <= int(c) <= len(confs):
        return confs[int(c) - 1]
    m = [x for x in confs if x.lower().startswith(c.lower())] if c else []
    return m[0] if m else None


def _pick_team(league):
    default = getattr(league, "follow_team", None)
    q = ask(f"Which team? (Enter = {default.school if default else 'none'})").strip()
    if not q:
        return default.school if default else None
    found = league.search(q)
    return found[0].school if found else None


def curate(league, games=None):
    prefs = _prefs(league)
    msg = ""
    session_covered = set()
    session_kit = None
    copied_any = False
    while True:
        keys, kit = available(league, prefs, games)
        clear()
        print(title_bar("CURATE STORIES", sub=where_label(league).upper()))
        first = "  This is your first edition: the writer will set the scene." if not prefs.get("editions") else \
            f"  Last edition: {prefs.get('last', '—')}. News already covered won't repeat."
        print(paint("   Toggle sections by number, pick a show by letter, Enter copies the story kit." + first + "\n", C.GRAY))
        print(section("WHAT GOES IN", C.BCYAN))
        for i, k in enumerate(keys, 1):
            on = k not in prefs["off"]
            box = paint("[x]", C.BGREEN, C.BOLD) if on else paint("[ ]", C.GRAY)
            print(f"   {paint(f'{i:>2}', C.BYELLOW, C.BOLD)}  {box} {SECTIONS[k][0]}")
        print()
        print(section("COACHING STAFF REFERENCE", C.BCYAN))
        staff_labels = dict(STAFF_LEVELS)
        print(f"   {paint('S', C.BYELLOW, C.BOLD)}  {staff_labels.get(prefs.get('staff', 'off'), 'Off')}")
        print(paint("      Included only for teams that appear in this story kit.", C.GRAY))
        print()
        print(section("THE SHOW", C.BCYAN))
        for letter, (k, label) in zip("EKTJ", STYLES):
            dot = paint("(●)", C.BGREEN, C.BOLD) if k == prefs["style"] else paint("( )", C.GRAY)
            print(f"   {paint(letter, C.BYELLOW, C.BOLD)}  {dot} {label}")
        print(rule())
        if msg:
            print(paint(f"   {msg}", C.BYELLOW))
        c = ask("Toggle #, S = staff depth, pick a show (E/K/T/J), Enter = copy again, B = back:").strip().lower()
        if c in ("b", "back"):
            if copied_any:
                seen = _seen(league)
                seen.update(session_covered)
                if len(seen) > 20000:                    # keep the save small: forget the oldest half
                    league.__dict__["recap_seen"] = set(list(seen)[-10000:])
                prefs["editions"] = prefs.get("editions", 0) + 1
                prefs["last"] = where_label(league)
                prefs["last_year"] = league.year
                if session_kit is not None:
                    prefs["last_week"] = session_kit["week"] if session_kit["phase"] == "inseason" else None
            return
        if c.isdigit() and 1 <= int(c) <= len(keys):
            k = keys[int(c) - 1]
            if k in prefs["off"]:
                prefs["off"].remove(k)
            else:
                prefs["off"].append(k)
            msg = ""
            continue
        if c == "s":
            vals = [k for k, _label in STAFF_LEVELS]
            cur = prefs.get("staff", "off")
            prefs["staff"] = vals[(vals.index(cur) + 1) % len(vals)] if cur in vals else "off"
            msg = ""
            continue
        if len(c) == 1 and c in "ektj":
            prefs["style"] = STYLES["ektj".index(c)][0]
            msg = ""
            continue
        if c == "":
            chosen = [k for k in keys if k not in prefs["off"]]
            if not chosen:
                msg = "Pick at least one section."
                continue
            focus = None
            if prefs["style"] == "conf":
                focus = _pick_conference(league)
                if not focus:
                    msg = "Pick a conference for the conference podcast."
                    continue
            elif prefs["style"] == "team":
                focus = _pick_team(league)
                if not focus:
                    msg = "Pick a team for the team podcast."
                    continue
            covered = _copy(league, prefs, chosen, focus, games, kit)
            session_covered.update(covered)
            session_kit = kit
            copied_any = True
            msg = "Story kit copied. Change anything and press Enter for another; B leaves Curate Stories."
            continue
        msg = "Numbers toggle sections; S changes staff depth; E, K, T or J picks the show; Enter copies."


def _copy(league, prefs, keys, focus, games, kit):
    import screen_copy
    print(paint("\n   Building your story kit…", C.GRAY), flush=True)
    text, covered = build_kit(league, keys, prefs["style"], focus, games, prefs)
    clip = screen_copy.copy(text)
    try:
        with open(KIT_FILE, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass
    words = len(text.split())
    if clip:
        print(paint(f"\n   ✓ Copied to your clipboard — {words:,} words. Paste it into Claude and ask for the story.",
                    C.BGREEN, C.BOLD))
    else:
        print(paint("\n   No clipboard tool found on this computer.", C.BYELLOW))
    print(paint(f"   Also saved to {os.path.basename(KIT_FILE)} in the game folder.", C.GRAY))
    pause()
    return covered


def _two(left, right, w=48):
    rows = max(len(left), len(right))
    left += [""] * (rows - len(left))
    right += [""] * (rows - len(right))
    return [pad(truncate(a, w - 2), w) + truncate(b, WIDTH - w - 4) for a, b in zip(left, right)]


def _footer(extra=""):
    print(rule())
    print(f"   {paint('[C]', C.BYELLOW, C.BOLD)} Curate stories   {extra}{paint('[Enter]', C.GRAY)} continue")


def _hub_lines(league, title, blocks):
    clear()
    print(title_bar(title, sub=where_label(league).upper()))
    for head, lines in blocks:
        if not lines:
            continue
        print(section(head, C.BCYAN))
        for ln in lines:
            print("   " + truncate(ln.strip(), WIDTH - 4))
        print()


def screen(league, games=None):
    """The Recap hub, for wherever we are."""
    ph = phase(league)
    if ph == "preseason":
        return _preseason_hub(league)
    if ph == "season_over":
        return _final_hub(league)
    if ph == "offseason":
        return _stage_hub(league)
    wk, wgames = _week_games(league)
    games = games if games is not None else wgames
    if not wk:
        clear()
        print(title_bar("RECAP"))
        print(paint("\n   No games yet. The Recap opens on its own after every week you watch or sim.", C.GRAY))
        pause()
        return
    kit = {"games": games, "week": wk, "week_name": league.week_name(wk), "prefs": _prefs(league)}
    while True:
        clear()
        print(title_bar(f"RECAP · {league.week_name(wk).upper()}", sub=str(league.year)))
        lead = [_score_line(league, g) for g in sorted(games, key=lambda g: tier(league, g)) if g.played
                and tier(league, g) == 1]
        notable = [_score_line(league, g) for g in games if g.played and tier(league, g) == 2]
        print(section("THE HEADLINE GAMES", C.BYELLOW))
        for ln in (lead or ["(a quiet week at the top)"])[:10]:
            print("   " + truncate(ln, WIDTH - 4))
        if notable:
            print(paint(f"   + {len(notable)} more worth a look ([S] for every score)", C.GRAY))
        r = league.rankings
        top = [f"{i:>2}. {t.school} ({t.record})" for i, t in enumerate(r.top()[:10], 1)]
        hz = [f"{i:>2}. {p.name}, {p.position}, {truncate(p.team.school, 14)}" for i, (p, _s, _b) in
              enumerate(r.heisman[:5], 1)] or ["(no votes yet)"]
        print()
        print(paint(pad("   MEDIA TOP 10", 48), C.BCYAN, C.BOLD) + paint("GOLDEN HELMET WATCH", C.BCYAN, C.BOLD))
        for ln in _two(["   " + x for x in top], hz):
            print(ln)
        import media_center as mc
        aw = mc.week_awards(league, games)
        pw = []
        for key, label, side in (("off", "OFF", "off"), ("def", "DEF", "def"), ("fr", "FR", None)):
            p, _v, c, t = aw[key]
            if p is not None:
                pw.append(f"{label}  {p.name} ({t.school}) — {mc._line(p, c, side or 'off')}")
        if pw:
            print()
            print(section("PLAYERS OF THE WEEK", C.BCYAN))
            for ln in pw:
                print("   " + truncate(ln, WIDTH - 4))
        try:
            import committee
            cm = committee.get(league)
            if cm.released:
                print(paint("   Playoff Rankings top 4: " + ", ".join(f"{i}. {t.school}" for i, t in
                                                                         enumerate(cm.order[:4], 1)), C.BGREEN))
        except Exception:                                # noqa: BLE001, S110
            pass
        notes = [ln[2:] for ln in sec_headlines(league, kit)][:4]
        rec = _rec_news(league, (league.week,))[:3]
        if notes or rec:
            print()
            print(section("AROUND THE SPORT", C.BCYAN))
            for ln in notes:
                print("   ● " + truncate(ln, WIDTH - 6))
            for ln in rec:
                print(paint("   ✎ " + truncate(ln, WIDTH - 6), C.GRAY))
        _footer(f"{paint('[S]', C.BYELLOW, C.BOLD)} All scores   {paint('[T]', C.BYELLOW, C.BOLD)} Standings   "
                f"{paint('[R]', C.BYELLOW, C.BOLD)} Recruiting   ")
        c = ask("Select:").strip().lower()
        if c in ("", "b", "q"):
            return
        if c == "c":
            curate(league, games)
        elif c == "s":
            _page("ALL SCORES", sec_scores(league, kit))
        elif c == "t":
            _page("CONFERENCE STANDINGS", sec_standings(league, kit))
        elif c == "r":
            _page("RECRUITING", sec_recruiting(league, kit) + [""] + sec_classes(league, kit))


def _loop(league, title, blocks_fn, pages=()):
    while True:
        _hub_lines(league, title, blocks_fn())
        extra = "".join(f"{paint('[' + k.upper() + ']', C.BYELLOW, C.BOLD)} {lbl}   " for k, lbl, _f in pages)
        _footer(extra)
        c = ask("Select:").strip().lower()
        if c in ("", "b", "q"):
            return
        if c == "c":
            curate(league)
        for k, lbl, f in pages:
            if c == k:
                _page(lbl.upper(), f())


def _preseason_hub(league):
    prefs = _prefs(league)
    kit = _kit_state(league, prefs)
    r = league.rankings

    def blocks():
        return [("PRESEASON MEDIA TOP 10", [f"{i:>2}. {t.school}" for i, t in enumerate(r.top()[:10], 1)]),
                ("GOLDEN HELMET WATCH LIST", sec_heisman(league, kit)[:5]),
                ("NEW HEAD COACHES", sec_new_coaches(league, kit)[:8]),
                ("GAMES OF THE YEAR", sec_games_of_year(league, kit)[:6])]
    _loop(league, f"PRESEASON DESK · {league.year}", blocks,
          pages=(("p", "Preseason poll", lambda: sec_ap(league, kit)),
                 ("g", "Games of the year", lambda: sec_games_of_year(league, kit)),
                 ("o", "Conference contenders", lambda: sec_outlook(league, kit))))


def _final_hub(league):
    prefs = _prefs(league)
    kit = _kit_state(league, prefs)

    def blocks():
        return [("THE SEASON IN REVIEW", sec_final(league, kit)[:12]),
                ("FINAL MEDIA TOP 10", [f"{i:>2}. {t.school} ({t.record})" for i, t in
                                        enumerate(league.rankings.top()[:10], 1)])]
    _loop(league, f"SEASON IN REVIEW · {league.year}", blocks,
          pages=(("f", "Season in review", lambda: sec_final(league, kit)),))


def _stage_hub(league):
    prefs = _prefs(league)
    kit = _kit_state(league, prefs)
    stage = _LIVE["stage"]
    when, what, _ = STAGES[stage]
    fn = {"off_carousel": sec_carousel, "off_awards": lambda lg, k: sec_awards(lg, k) + [""] + sec_draft(lg, k),
          "off_portal": sec_portal, "off_signing": sec_signing}.get(stage, sec_carousel)

    def blocks():
        return [(f"{when.upper()} · {what.upper()}", fn(league, kit)[:16])]
    _loop(league, f"OFFSEASON · {when.upper()}", blocks, pages=(("a", "All of it", lambda: fn(league, kit)),))


def _page(title, lines):
    per = 34
    lines = lines or ["(nothing yet)"]
    for i in range(0, len(lines), per):
        clear()
        print(title_bar(f"RECAP · {title}"))
        for ln in lines[i:i + per]:
            print("   " + truncate(ln, WIDTH - 4))
        if i + per < len(lines):
            if ask("Enter = more, B = back:").strip().lower() == "b":
                return
        else:
            pause()


# ── Hooks ───────────────────────────────────────────────────────────────────

def after_week(league, games=None):
    """Spectator mode: open the Recap after a week."""
    if getattr(league, "mode", None) != "spectator" or getattr(league, "autosim", False):
        return
    screen(league, games)


def staged_offseason(league):
    """Spectator mode: the offseason one stop at a time, with a Recap (and Curate) at each.
    Same stages, same order, same dice as league.advance_offseason()."""
    from season import OFFSEASON_STAGES, offseason_begin
    ctx = offseason_begin(league)
    try:
        for stage in OFFSEASON_STAGES:
            _LIVE["ctx"], _LIVE["stage"] = ctx, stage.__name__
            stage(league, league.rng, ctx)
            info = STAGES.get(stage.__name__)
            if info and info[2]:
                clear()
                screen(league)
    finally:
        _LIVE.clear()
    return league.after_offseason(ctx["report"])


def capture(league, report):
    """After any offseason: keep the signing-day story as text (the cycle itself is replaced)."""
    rep = getattr(report, "recruiting", None)
    if rep is None:
        return
    lines = _signing_lines(rep)
    league.__dict__["recap_capture"] = {"year": report.year, "signing": lines}
