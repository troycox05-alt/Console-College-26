"""
dashboard.py — The hub. A text version of a modern dynasty dashboard: a
scoreboard header, a tab strip, and a grid of live panels — next game, team
ratings, your coach, the polls, your conference, recruiting, headlines —
with every screen in the game one keystroke away.

Tabs (type the number):
  1 HOME        next game, team, coach, polls, standings, recruiting, news
  2 SCHEDULE    your schedule, scores around the country, standings
  3 TEAM        roster, team page, leaders, budget
  4 RECRUITING  recruiting hub, recruit finder, board, class, portal
  5 RANKINGS    Media Top 25, NP rankings, the committee, Golden Helmet, champions, toughest places to play
  6 COACH       your career, development, staff, the carousel
  7 MEDIA       media center, recruiting news
  8 SYSTEM      save, load, export to sheets, settings, quit
Anywhere: [A] advance (play the next week), [M] sim several weeks, [V] save, [Q] quit.
"""
import committee as cm
import finance as fi
from ui import (heat_meter, rating_color, short_school, C, WIDTH, ask, bar, chip, clear, columns, command_bar, key, meter, on, bg, pad, paint,
                panel, pause, rating, tabs, truncate, visible_len)

TABS = ["HOME", "SCHEDULE", "TEAM", "RECRUITING", "RANKINGS", "COACH", "MEDIA", "SYSTEM"]
# Where things live on the dashboard: (tab number or None for "anywhere", key). The
# tab pages and every "go here to do that" hint read from this, so they can't drift apart.
NAV = {"budget": (3, "$"), "roster": (3, "R"), "recruiting": (4, "R"), "board": (4, "B"), "portal": (4, "P"),
       "cfp": (5, "P"), "career": (6, "C"), "develop": (6, "D"), "staff": (6, "S"), "inbox": (None, "I"),
       "settings": (8, "S"), "play": (None, "A"), "sim": (None, "M"), "compliance": (3, "Y")}


def nav(what):
    """'tab 3 TEAM → [$]', or '[I] from any tab'."""
    tab, k = NAV[what]
    if tab is None:
        return f"[{k}] from any dashboard tab"
    return f"tab {tab} {TABS[tab - 1]} → [{k}]"
W3 = (34, 32, 32)          # three-column grid (plus two gaps) = 100
W2 = (50, 49)


# ─── what the dashboard is about ───────────────────────────────────────────

def focus_team(league):
    """Your team in a career; in spectator mode, the team you follow (the No. 1 team by default)."""
    if getattr(league, "mode", None) == "career":
        me = getattr(league, "user_coach", None)
        if me is not None and me.team is not None:
            return me.team
    t = getattr(league, "follow_team", None)
    if t is not None:
        return t
    order = league.rankings.order
    t = order[0] if order else league.teams[0]
    league.follow_team = t                     # pick once (the preseason No. 1) and stick with it — [F] changes it
    return t


def next_game(league, team):
    for g in league.team_games(team):
        if not g.played:
            return g
    return None


def last_game(league, team):
    done = [g for g in league.team_games(team) if g.played]
    return done[-1] if done else None


def _rank_tag(league, t):
    r = league.rankings.rank_of(t)
    return paint(f"#{r} ", C.BYELLOW, C.BOLD) if r else ""


# ─── header ─────────────────────────────────────────────────────────────────

def header(league, team):
    color = league.conference_color(team.conference)
    ap = league.rankings.rank_of(team)
    c = getattr(league, "committee", None)
    cfp = c.rank_of(team) if c is not None and c.released and c.year == league.year else None
    ranks = " · ".join(x for x in (f"Poll #{ap}" if ap else "", f"NP #{cfp}" if cfp else "") if x) or "NR"
    who = ""
    me = getattr(league, "user_coach", None)
    if getattr(league, "mode", None) == "career" and me is not None:
        import people
        n = people.unread(league)
        who = f"COACH {me.name.upper()}" + (f" · ✉ {n}" if n else "")
    elif getattr(league, "mode", None) == "spectator":
        who = "SPECTATOR · FOLLOWING"
    elif getattr(league, "mode", None) == "ad" and getattr(league, "ad_user", None):
        au = league.ad_user
        who = f"AD {au['name'].upper()} · BOARD {au['board']:.0f} · FANS {au['fans']:.0f}"
    right = f"{league.status.upper().replace(' SEASON ·', ' ·')}" + (f"  ·  {who}" if who else "") + "  "
    # The team name gives way first; the record and ranks always fit.
    tail = f"   {team.record} ({team.conf_record} {team.conference})   {ranks}"
    room = WIDTH - 4 - len(right) - 1 - len(tail) - 1
    name = team.full_name.upper() if len(team.full_name) <= room else team.school.upper()
    from ui import BAR_BG, BAR_EDGE, MUTED
    left = paint("  ", bg(color)) + paint("  " + truncate(name, max(8, room)), BAR_BG, "\033[1;97m") \
        + paint(tail, BAR_BG, "\033[38;5;252m")
    fill = WIDTH - visible_len(left) - len(right)
    top = left + paint(" " * max(0, fill), BAR_BG) + paint(right, BAR_BG, MUTED)
    return [top, paint("▀▀", color) + paint("▀" * (WIDTH - 2), BAR_EDGE)]


# ─── panels ─────────────────────────────────────────────────────────────────

def p_next_game(league, team, w):
    g = next_game(league, team)
    lines = []
    if league.season_complete:
        lines += [paint("SEASON COMPLETE", C.BYELLOW, C.BOLD), "",
                  paint("Advance to the offseason: the carousel,", C.GRAY),
                  paint("the portal and signing day.", C.GRAY)]
        return panel("NEXT UP", lines, w, height=6)
    if g is None:
        last = last_game(league, team)
        lines.append(paint("No game scheduled.", C.GRAY))
        if last:
            lines.append(paint(f"Season over at {team.record}.", C.GRAY))
        return panel("NEXT GAME", lines, w, height=6)
    opp = g.opponent_of(team)
    home = g.home is team
    site = "vs" if home or g.neutral else "at"
    lines.append(f"{_rank_tag(league, team)}{paint(team.school.upper(), C.BWHITE, C.BOLD)} {paint('(' + team.record + ')', C.GRAY)}")
    lines.append(f"  {paint(site, C.GRAY)} {_rank_tag(league, opp)}"
                 f"{paint(short_school(opp.school, w - 16).upper(), C.BWHITE, C.BOLD)} "
                 f"{paint('(' + opp.record + ')', C.GRAY)}")
    where = g.home.stadium if not g.neutral else (getattr(g, "bowl_name", None) or "neutral site")
    tag = g.game_type if g.game_type != "Regular Season" else league.week_name(g.week)
    lines.append(paint(truncate(f"{tag} · {where}", w - 4), C.GRAY))
    try:
        import carousel as cz
        p = cz.win_prob(team, opp, 0 if g.neutral else (1 if home else -1))
        p = min(0.99, max(0.01, p))                    # nothing's 100% on a Saturday
        col = C.BGREEN if p >= 0.6 else C.BYELLOW if p >= 0.4 else C.BRED
        import scout
        if scout.hidden(league, team):
            txt = scout.odds(p, league, team).replace("you're ", "")
            lines.append(f"Outlook: {paint(txt, col, C.BOLD)}")
        else:
            lines.append(f"Win chance {paint(f'{p * 100:.0f}%', col, C.BOLD)}  {meter(p * 100, 12, color=col)}")
    except Exception:
        pass
    from commentary import rivalry_name
    riv = rivalry_name(team, opp)
    level = paint("FCS", C.BYELLOW) if getattr(opp, "fcs", False) else \
        paint(truncate(opp.conference, w - 20), league.conference_color(opp.conference))
    lines.append(paint(f"★ {riv}", C.BMAGENTA) if riv else
                 (_matchup_words(team, opp, level, w)
                  if __import__('scout').hidden(league, team) else
                  f"{paint('OVR', C.GRAY)} {rating(team.team_ovr)} {paint('vs', C.GRAY)} {rating(opp.team_ovr)}  {level}"))
    try:
        import weather
        f = weather.forecast(g, league)
        if f["lead"] <= 2:
            col = C.BRED if f["severity"] >= 3 else C.BYELLOW if f["severity"] >= 2 else C.GRAY
            txt = "Indoors" if f["indoor"] else f"{f['temp']}° · {f['headline']}"
            lines.append(paint("Forecast ", C.GRAY) + paint(truncate(txt, w - 14), col))
    except Exception:
        pass
    return panel("NEXT GAME", lines, w, height=6, color=C.BYELLOW)


def _matchup_words(team, opp, level, w):
    """'Us below avg · Them good · Lake Country' — words, not codes (same scale as the team panel)."""
    import scout
    short = {"below average": "below avg"}
    def word(v):
        x = scout._w(scout.TEAM, v)
        return short.get(x, x)
    txt = f"Us {word(team.team_ovr)} · Them {word(opp.team_ovr)}"
    return truncate(txt + " · ", w - 4 - 3) + level if len(txt) + 12 < w else truncate(txt, w - 4)


def p_team(league, team, w):
    import scout
    lines = []
    if scout.hidden(league, team):
        for label, v in (("OVERALL", team.team_ovr), ("OFFENSE", team.offense_ovr), ("DEFENSE", team.defense_ovr)):
            lines.append(f"{paint(pad(label, 9), C.GRAY)}{scout.team(v, league, who=team)}")
        lines.append(f"{paint(pad('COACH', 9), C.GRAY)}{rating(team.ratings['coach'])}")
        lines.append(f"{paint(pad('PRESTIGE', 9), C.GRAY)}{rating(round(team.prestige))}")
        lines.append(paint(f"{len(team.roster)} players · {len(team.injured())} hurt", C.GRAY))
        return panel("TEAM  (staff read)", lines, w, height=6)
    for label, v in (("OVR", team.team_ovr), ("OFF", team.offense_ovr), ("DEF", team.defense_ovr),
                     ("COACH", team.ratings["coach"]), ("PRESTIGE", round(team.prestige))):
        lines.append(f"{paint(pad(label, 9), C.GRAY)}{rating(v)}  {bar(max(0, v - 40), w - 18, maximum=59, color=rating_color(v))}")
    lines.append(paint(f"{len(team.roster)} players · {len(team.injured())} hurt", C.GRAY))
    return panel("TEAM RATINGS  (starters)", lines, w, height=6)


# The AD's style in a few words, for the tight coach card (the profile has the full story).
AD_SHORT = {"patient": "patient", "win_now": "wins now", "big_game": "big games", "conference": "league titles",
            "analytics": "the process", "booster": "the boosters", "turnaround": "yearly gains",
            "recruiting": "recruiting", "traditionalist": "the rival", "budget": "hates buyouts",
            "brand": "TV & polls", "politician": "talk radio"}


def p_coach(league, team, w):
    import carousel as cz
    c = team.coach
    lines = []
    if c is None:
        return panel("HEAD COACH", [paint("Job open.", C.GRAY)], w, height=6)
    interim = cz.is_interim(c)
    lines.append(f"{paint(truncate(c.name, w - 12), C.BWHITE, C.BOLD)} {paint('OVR', C.GRAY)} {rating(c.overall)}")
    if interim:
        lines.append(chip("INTERIM", C.BYELLOW))
    else:
        heat = getattr(c, "seat", 30)
        col = C.BRED if heat >= 70 else C.BYELLOW if heat >= 50 else C.BGREEN
        head = (f"{paint('Hot seat:', C.GRAY)} {paint(cz.seat_label(heat).lower(), col, C.BOLD)} "
                f"{paint(f'({heat}/100)', C.GRAY)}")
        moved = heat - getattr(c, "seat_prev", heat)
        meter = f"{paint('cool', C.BGREEN)} {heat_meter(heat, w - 14)} {paint('hot', C.BRED)}"
        if moved and getattr(c, "is_user", False):
            # Say why it moved: a seat that cools after a 27-point loss needs a reason on screen.
            head = (f"{paint('Seat:', C.GRAY)} {paint(cz.seat_label(heat).lower(), col, C.BOLD)} "
                    f"{paint(str(heat), C.GRAY)} "
                    + paint(f"{'▲' if moved > 0 else '▼'}{abs(moved)}", C.BRED if moved > 0 else C.BGREEN, C.BOLD))
            why = cz.seat_word(c, weeks=1)
            if not why:
                recent = [e for e in getattr(c, "seat_log", []) if len(e) == 4 and e[0] == league.year
                          and e[1] >= league.week - 1 and (e[2] < 0) == (moved < 0)]
                if recent:
                    big = max(recent, key=lambda e: abs(e[2]))
                    why = big[3] + (f" (+{len(recent) - 1} more)" if len(recent) > 1 else "")
            if why:
                why = (why.replace("the AD liked your reply to ", "AD liked ")
                          .replace("the AD didn’t like your reply to ", "AD disliked ")
                          .replace("the AD liked your ", "AD liked your ")
                          .replace("the AD didn’t like your ", "AD disliked your "))
                meter = paint(truncate(f"{why}", w - 4), C.GRAY)
        lines.append(head)
        lines.append(meter)
    k = fi.contract(c)
    if k:
        left = fi.years_left(k, league)
        lines.append(paint(f"{fi.money(k['salary'], exact=True)}/yr · {left} yr{'s' if left != 1 else ''} left", C.GRAY))
    ad = f"AD: {cz.AD_STYLES[team.ad['style']][0]}"
    more = f" ({AD_SHORT.get(team.ad['style'], '')})"
    lines.append(paint(ad + more if len(ad + more) <= w - 4 else ad, C.GRAY))
    if getattr(c, "is_user", False):
        tab, k = NAV["develop"]
        lines.append(f"{paint('Bank', C.GRAY)} {paint(fi.money(getattr(c, 'bank', 0)), C.BGREEN, C.BOLD)}"
                     + paint(f"  (tab {tab} → {k})", C.GRAY))
    return panel("HEAD COACH", lines, w, height=6)


def p_poll(league, w, n=10):
    lines = []
    order = league.rankings.order[:n]
    c = getattr(league, "committee", None)
    use_cfp = c is not None and c.released and c.year == league.year
    title = "NP TOP 10" if use_cfp else "POLL TOP 10"
    if use_cfp:
        order = c.order[:n]
    for i, t in enumerate(order, 1):
        col = league.conference_color(t.conference)
        lines.append(f"{paint(f'{i:>2}', C.BYELLOW if i <= 4 else C.BWHITE, C.BOLD)} "
                     f"{pad(paint(short_school(t.school, w - 14), col, C.BOLD), w - 13)}{paint(t.record, C.GRAY)}")
    if not lines:
        lines.append(paint("The first poll comes out in the preseason.", C.GRAY))
    return panel(title, lines, w, height=n)


def p_standings(league, team, w, n=10):
    conf = [t for t in league.teams if t.conference == team.conference]
    conf.sort(key=lambda t: (-t.conf_win_pct, -t.conf_wins, -t.win_pct, -t.prestige))
    lines = [paint(pad("", w - 16) + pad("CONF", 5, "right") + pad("ALL", 6, "right"), C.GRAY)]
    for i, t in enumerate(conf[:n - 1], 1):
        me = t is team
        name = paint(short_school(t.school, w - 17), C.BWHITE if me else C.WHITE, C.BOLD if me else "")
        mark = paint("▶", C.BYELLOW) if me else " "
        lines.append(f"{mark}{pad(name, w - 17)}{pad(t.conf_record, 5, 'right')} {paint(pad(t.record, 5, 'right'), C.GRAY)}")
    return panel(f"{team.conference.upper()} STANDINGS", lines, w, height=n)


def p_recruiting(league, team, w, n=10, tail=()):
    cycle = league.recruiting
    commits = cycle.commitments(team)
    lines = []
    rank = cycle.class_rank(team)
    avg = sum(r.stars for r in commits) / len(commits) if commits else 0
    rank_txt = paint('#' + str(rank), C.BYELLOW, C.BOLD) if rank else paint('Unranked', C.GRAY)
    lines.append(f"{paint('Class', C.GRAY)} {rank_txt} · "
                 f"{paint(str(len(commits)), C.BWHITE, C.BOLD)} {paint('commit' if len(commits) == 1 else 'commits', C.GRAY)}"
                 + (f" · {avg:.1f}★" if commits else ""))
    mine = getattr(league, "mode", None) == "career" and team is getattr(league, "user_team", None)
    if mine:
        hrs, tot = cycle.remaining_hours(team), cycle.hours_for(team)
        if tot == 0 and league.week == 0:
            lines.append(f"{paint('Hours', C.GRAY)} {paint('none until Week 1', C.BYELLOW)}")
        else:
            lines.append(f"{paint('Hours', C.GRAY)} {hrs}/{tot}  {meter(hrs, w - 20, maximum=max(1, tot), color=C.BCYAN)}")
        lines.append(f"{paint('Board', C.GRAY)} {len(team.recruiting_targets)}/40")
        lines.append(f"{paint('NIL free', C.GRAY)} {paint(fi.money(fi.available(league, team)), C.BGREEN)}")
    for r in sorted(commits, key=lambda r: r.national_rank)[:n - len(lines)]:
        lines.append(f"{paint('◆', C.BGREEN)} {pad(truncate(r.name, w - 17), w - 16)}"
                     f"{paint(pad(r.position, 3), C.BCYAN)} {paint('★' * r.stars, C.BYELLOW)}")
    if not commits:
        lines.append(paint("No commitments yet.", C.GRAY))
    if tail:
        lines = lines[:n - len(tail) - 1] + [""] + list(tail)
    return panel("RECRUITING", lines, w, height=n)


def headlines(league, team, n=6):
    """(color, text) for the week, most newsworthy first: your team's result and
    signings, top-10 showdowns, upsets, major injuries, the carousel, then the
    biggest recruiting news elsewhere. A three-star to a Group of Five school
    doesn't outrank No. 1 vs No. 2."""
    scored = []                                   # (priority, color, text)
    last = last_game(league, team)
    if last:
        opp = last.opponent_of(team)
        won = last.winner is team
        s1, s2 = last.score_for(team), last.score_for(opp)
        import news_writer
        if last.week == league.week or not won:
            _pr, txt, _u = news_writer.result(league, last)
        else:
            txt = f"{team.school} {'beat' if won else 'fell to'} {opp.school} {max(s1, s2)}-{min(s1, s2)}"
        scored.append((100, C.BGREEN if won else C.BRED, txt))
    wk = league.week
    import news_writer
    fcs_n = 0
    for g in league.schedule.get(wk, []):
        if not g.played or g.winner is None or team in (g.home, g.away):
            continue
        pr, txt, upset = news_writer.result(league, g)
        if getattr(g.winner, "fcs", False) and not getattr(g.loser, "fcs", False):
            pr -= fcs_n * 20                                     # one FCS stunner, not four
            fcs_n += 1
        if pr > 0:
            scored.append((pr, C.BYELLOW, ("UPSET: " if upset and pr >= 60 else "") + txt))
    try:                                           # the weather: a storm coming ashore, snow in the forecast
        import weather
        if not league.season_complete:
            nxt = league.week + 1
            for w_, name, states in weather.tropical(league.year):
                if w_ == nxt:
                    scored.append((80, C.BRED, f"Tropical Storm {name} bears down on Saturday's games "
                                               f"({', '.join(states)})"))
            mine = next_game(league, team)
            if mine is not None and mine.week == nxt:
                f = weather.forecast(mine, league, 0)
                if f["severity"] >= 2 and not f["indoor"]:
                    scored.append((72, C.BCYAN, f"Forecast for {team.school}'s game: {f['headline'].lower()}, "
                                                f"{f['temp']}°"))
        for g in league.schedule.get(wk, []):
            wx = getattr(g, "wx", None)
            if g.played and wx and weather.severity(wx) >= 4 and (ranked_g := (getattr(g, "ranks", None) or {})):
                if any(ranked_g.get(t) for t in (g.home, g.away)):
                    scored.append((58, C.BCYAN, f"{weather.label(wx)} game: {g.winner.school} "
                                                f"{g.score_for(g.winner)}, {g.loser.school} {g.score_for(g.loser)}"))
    except Exception:
        pass
    # Major injuries: a real starter at a ranked (or your) program, out a month or more.
    ranked = {t: league.rankings.rank_of(t) for t in league.teams}
    for t in league.teams:
        if not (ranked.get(t) or t is team):
            continue
        for p in t.roster:
            if getattr(p, "inj_week", 0) == wk and wk and getattr(p, "inj_games", 0) >= 4 and p.overall >= 72:
                long = "out for the season" if p.inj_games >= 99 else f"out about {p.inj_games} weeks"
                pr = 68 + (p.overall - 72) * 0.5 + (10 if t is team else 0) - (ranked.get(t) or 25) * 0.3
                pos = "starting QB" if p.position == "QB" else p.position
                scored.append((pr, C.BRED, f"{t.school} loses {pos} {p.name} ({p.inj_desc}), {long}"))
    for kind, text in list(getattr(league, "carousel", {}).get(league.year, []))[-2:]:
        scored.append((60, C.BMAGENTA, text))
    try:
        import compliance
        for item in compliance.recent_news(league, 14):
            fresh = (item["year"] == league.year and item["week"] >= wk - 1) or \
                    (wk <= 1 and item["year"] == league.year - 1 and item["week"] >= 18)
            if not fresh:
                continue
            mine_ = item.get("school") == team.school
            big = (item.get("level") or 3) <= 2
            pr = 93 if mine_ else 74 if big else 44
            if item["kind"] == "cleared":
                pr -= 15
            scored.append((pr, C.BRED if item["kind"] in ("ruling", "report", "allegations", "inquiry") else C.BYELLOW,
                           item["text"]))
    except Exception:
        pass
    try:
        import records
        for w_, pr, text in records.news(league, week=max(0, wk - 1)):
            scored.append((pr + (8 if team.school in text else 0), C.BYELLOW, text))
    except Exception:
        pass
    meta = getattr(league.recruiting, "news_meta", {})
    for week, kind, text in getattr(league.recruiting, "news", [])[:40]:
        m = meta.get(text)
        school, stars = (m[1], m[2]) if m else (None, None)
        recent = week >= wk - 1
        if school == team.school and recent:
            scored.append((90 if kind == "commit" else 88, C.BCYAN, text))
        elif recent and (stars or 0) >= 4:
            scored.append((40 + (stars or 0) * 3, C.BCYAN, text))
        elif m is None and recent and kind != "commit":
            scored.append((30, C.BCYAN, text))
    if league.week == 0:
        scored += [(50 - i, col, txt) for i, (col, txt) in enumerate(preseason_headlines(league))]
    scored.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for _, col, txt in scored:
        if txt not in seen:
            seen.add(txt)
            out.append((col, txt))
    if not out:
        out.append((C.GRAY, "Quiet week around college football."))
    return out[:n]


def preseason_headlines(league):
    """August talk: the champ, the Golden Helmet favorites, the hot seats, the portal's big moves."""
    import random
    out = []
    order = league.rankings.order
    try:
        import postseason as ps
        champ = ps.defending_champion(league)
        t = next((x for x in league.teams if x.school == champ), None)
        if t is not None:
            r = league.rankings.rank_of(t)
            out.append((C.BYELLOW, f"Defending champion {champ} opens {league.year} "
                                   + (f"at No. {r} in the media poll" if r else "outside the Top 25")))
    except Exception:
        pass
    top = order[:15]
    qbs = sorted((p for t in top for p in t.roster if p.position == "QB"), key=lambda p: -p.overall)[:3]
    if qbs:
        out.append((C.BCYAN, "Golden Helmet favorites: " + ", ".join(f"{p.name} ({p.team.school})" for p in qbs)))
    hot = sorted((t.coach for t in league.teams if t.coach is not None), key=lambda c: -getattr(c, "seat", 0))[:3]
    hot = [c for c in hot if getattr(c, "seat", 0) >= 60]
    if hot:
        out.append((C.BRED, "Hot seat watch: " + ", ".join(f"{c.name} ({c.team.school})" for c in hot)))
    movers = sorted((p for t in league.teams for p in t.roster if getattr(p, "transfer_from", None)
                     and p.transfer_from != t.school), key=lambda p: -p.overall)[:2]
    for p in movers:
        out.append((C.BMAGENTA, f"Portal splash: {p.position} {p.name} arrives at {p.team.school} from {p.transfer_from}"))
    new = [t for t in league.teams if t.coach is not None and t.coach.hired_year == league.year]
    if new:
        rng = random.Random(f"news:{league.seed}:{league.year}")
        t = max(new, key=lambda t: t.prestige + rng.random())
        out.append((C.BGREEN, f"New era: {t.coach.name} takes over at {t.school}"))
    return out


def p_headlines(league, team, w):
    import textwrap
    lines = []
    for col, text in headlines(league, team, n=8):
        parts = textwrap.wrap(text, w - 7)            # whole words, never "Pendlet…"
        if len(lines) + len(parts) > 6:
            if len(lines) >= 5:
                break
            continue                                  # skip one that won't fit; a shorter one might
        lines += [(paint("● ", col) if j == 0 else "  ") + part for j, part in enumerate(parts)]
    return panel("AROUND THE SPORT", lines, w, height=6)


def p_leaders(league, team, w):
    lines = []
    # Before a snap is played, show who led last year among the players still here.
    fresh = not any(p.season_stats.get(k, 0) for p in team.roster for k in ("pass_yds", "rush_yds", "rec_yds", "tkl"))
    if fresh:
        def stat(p, k):
            return (p.yearly_stats.get(league.year - 1) or {}).get(k, 0)
    else:
        def stat(p, k):
            return p.season_stats.get(k, 0)
    for label, key in (("PASS", "pass_yds"), ("RUSH", "rush_yds"), ("REC", "rec_yds"), ("TKL", "tkl")):
        best = max(team.roster, key=lambda p: stat(p, key), default=None)
        if best is None or not stat(best, key):
            lines.append(f"{paint(pad(label, 5), C.GRAY)}{paint('—', C.GRAY)}")
            continue
        val = stat(best, key)
        unit = "yds" if key != "tkl" else "tkl"
        room = w - 19
        name = next((n for n in (best.name, best.short_name, best.last_name) if len(n) <= room), best.last_name)
        lines.append(f"{paint(pad(label, 5), C.GRAY)}{pad(truncate(name, room), w - 18)}"
                     f"{paint(f'{val:,} {unit}', C.BWHITE, C.BOLD)}")
    if fresh and all("—" in ln for ln in lines):
        return panel("TEAM LEADERS", [paint("No stats yet.", C.GRAY),
                                      paint("They start in Week 1.", C.GRAY)], w, height=6)
    return panel(f"TEAM LEADERS ({league.year - 1})" if fresh else "TEAM LEADERS", lines, w, height=6)


def p_schedule(league, team, w, n=14):
    lines = []
    games = league.team_games(team)
    weeks = {g.week for g in games}
    rows = list(games)
    for wk in range(1, 14):                                  # an open date shows as BYE
        if wk not in weeks and any(g.week > wk for g in games):
            rows.append(wk)
    rows.sort(key=lambda x: x if isinstance(x, int) else x.week)
    for g in rows[:n]:
        if isinstance(g, int):
            lines.append(paint(f"{pad(league.week_name(g), 10)}BYE", C.GRAY))
            continue
        opp = g.opponent_of(team)
        site = "vs" if g.home is team or g.neutral else "at"
        wk = league.week_name(g.week) if g.week <= 13 else truncate(g.game_type, 10)
        if g.played:
            won = g.winner is team
            res = paint(("W " if won else "L ") + f"{g.score_for(team)}-{g.score_for(opp)}",
                        C.BGREEN if won else C.BRED, C.BOLD)
        else:
            res = paint("—", C.GRAY)
        kick = (getattr(g, "ranks", None) or {}).get(opp) if g.played else None
        tag = (paint(f"#{kick} ", C.BYELLOW) if kick else "") if g.played else _rank_tag(league, opp)
        name = tag + short_school(opp.school, w - 36)      # the rank sits inside the column (at kickoff once played)
        lines.append(f"{paint(pad(wk, 10), C.GRAY)}{paint(site, C.GRAY)} {pad(name, w - 30)}{res}")
    title = f"{league.year} SCHEDULE"
    try:
        import sos
        row = sos.of(league, team)
        if row and row.get("rank_full"):
            title += f" · SOS No. {row['rank_full']} ({sos.word(row['rank_full'])[0]})"
    except Exception:
        pass
    return panel(title, lines, w, height=n)


def p_heisman(league, w, n=6):
    lines = []
    for i, (p, score, blurb) in enumerate(league.rankings.heisman[:n], 1):
        ab = str(p.team.abbr)[:5]
        nw = max(10, min(16, w - 4 - 4 - 4 - len(ab) - 1))   # the school always shows; the name gives way
        name = p.name if len(p.name) <= nw else p.short_name
        lines.append(f"{paint(f'{i:>2}.', C.BYELLOW)} {pad(truncate(name, nw), nw + 1)}{paint(pad(p.position, 3), C.BCYAN)} "
                     f"{paint(ab, C.GRAY)}")
    if not lines:
        lines.append(paint("Watch list after week one.", C.GRAY))
    return panel("HEISMAN WATCH", lines, w, height=n)


def p_actions(title, items, w, n=None):
    return panel(title, items, w, height=n, color=C.BCYAN, title_color=C.BCYAN)


# ─── tab pages ──────────────────────────────────────────────────────────────

def p_todo(league, team, w):
    """THIS WEEK: what's waiting on you, each with the key that gets you there."""
    items = []

    inner = w - 4

    def add(ok, text, where):
        mark = paint("✓", C.BGREEN, C.BOLD) if ok else paint("●", C.BYELLOW, C.BOLD)
        hint = paint(where, C.GRAY) if where and not ok else ""
        room = inner - 2 - visible_len(hint) - (1 if hint else 0)
        items.append((ok, f"{mark} {pad(truncate(text, room), room)}" + (" " + hint if hint else "")))
    try:
        import people
        n = people.unread(league)
        add(n == 0, f"{n} unread message{'s' if n != 1 else ''}" if n else "Inbox clear", "I")
    except Exception:                               # noqa: BLE001, S110 — one line never blocks the dashboard
        pass
    try:
        cyc = league.recruiting
        if not league.season_complete:
            tot, left = cyc.hours_for(team), cyc.remaining_hours(team)
            import recruit_plus as rp
            q = len(rp.queue(cyc, team))
            board = len(team.recruiting_targets)
            if board == 0:
                add(False, "Recruiting board empty", "4→F")
            elif tot and not q and left == tot:
                add(False, f"{tot} hours unplanned", "4→R→Q")
            else:
                add(True, f"Board {board} · {q} order{'s' if q != 1 else ''} queued", "")
    except Exception:                               # noqa: BLE001, S110 — one line never blocks the dashboard
        pass
    try:
        g = next_game(league, team)
        if g is not None and not league.season_complete:
            import sideline
            mine = sideline.plan_of(team, league.year, g.week)
            add(bool(mine), "Game plan set" if mine else "Game plan: staff's", "A→G")
    except Exception:                               # noqa: BLE001, S110 — one line never blocks the dashboard
        pass
    try:
        hurt = [p for p in team.injured() if p in team.players_at(p.position)[:2]]
        add(not hurt, f"{len(hurt)} starter{'s' if len(hurt) != 1 else ''} hurt" if hurt else "Starters healthy",
            "3→H")
        ideas = [x for x in getattr(team, "depth_ideas", []) if x[4] == league.year and x[0] in team.roster
                 and x[0].position == x[1]]
        if ideas:
            add(False, f"{len(ideas)} depth idea{'s' if len(ideas) != 1 else ''} from staff", "3→H")
    except Exception:                               # noqa: BLE001, S110 — one line never blocks the dashboard
        pass
    try:
        import skills
        pts = skills._st(league.user_coach)["points"]
        if pts:
            add(False, f"{pts} tree point{'s' if pts != 1 else ''} to spend", "6→T")
    except Exception:                               # noqa: BLE001, S110 — one line never blocks the dashboard
        pass
    try:
        import career_plus
        live = career_plus.alerts(league)
        for al in live[:2]:
            add(False, al["text"], al["keys"])
        if len(live) > 2:
            add(False, f"{len(live) - 2} more in Heads Up", "/heads up")
        import cp_sched
        if 6 <= league.week <= 13 and not career_plus.nonconf_plan(league, league.year + 1) \
                and not cp_sched.booked(league, league.year + 1):
            add(False, f"{league.year + 1} non-conference: not set", "2→N")
    except Exception:                               # noqa: BLE001, S110 — one line never blocks the dashboard
        pass
    items.sort(key=lambda x: x[0])                     # what still needs you comes first
    lines = [t for _, t in items][:6] or [paint("Nothing waiting on you.", C.GRAY)]
    return panel("THIS WEEK", lines, w, height=6)


def page_home(league, team):
    career = getattr(league, "mode", None) == "career" and team is getattr(league, "user_team", None)
    mid = p_todo(league, team, W3[1]) if career else p_team(league, team, W3[1])
    rows = columns(p_next_game(league, team, W3[0]), mid, p_coach(league, team, W3[2]))
    if getattr(league, "mode", None) == "spectator":
        import book_screens                           # The Window takes the recruiting slot
        poll, stand = p_poll(league, W3[0]), p_standings(league, team, W3[1])
        tall = max(len(poll), len(stand)) - 2
        rows += columns(poll, stand, book_screens.home_panel(league, W3[2], height=tall))
    else:
        rows += columns(p_poll(league, W3[0]), p_standings(league, team, W3[1]), p_recruiting(league, team, W3[2]))
    rows += columns(p_headlines(league, team, W2[0] + 20), p_leaders(league, team, W2[1] - 20))
    return rows


def page_schedule(league, team):
    acts = [key("S", "Full schedule & results"), key("W", "Scores around the country"),
            key("T", "Conference standings"), key("F", "Forecast & weather center", C.BCYAN),
            key("O", "Strength of schedule"), key("G", "Another team's schedule"),
            *([key("N", "Next year's non-conference")] if getattr(league, "mode", None) == "career" else []),
            paint("Ranks: at kickoff once played,", C.GRAY),
            paint("this week's poll for games ahead.", C.GRAY)]
    try:
        import weather
        g = next_game(league, team)
        if g is not None and not league.season_complete:
            f = weather.forecast(g, league)
            acts += ["", paint("NEXT GAME FORECAST", C.BCYAN, C.BOLD),
                     paint(truncate(f["headline"], 35), C.BRED if f["severity"] >= 3 else
                           C.BYELLOW if f["severity"] >= 2 else C.GRAY)]
            if not f["indoor"]:
                acts.append(paint(f"{f['temp']}° · {f['pop']}% precip · wind {f['wind'][0]}-{f['wind'][1]}", C.GRAY))
    except Exception:
        pass
    return columns(p_schedule(league, team, 60), p_actions("SCHEDULE", acts, 39, n=14))


def page_team(league, team):
    acts = [key("R", "Full roster"), key("T", "Team page"), key("S", "Team statistics", C.BCYAN),
            key("$", "Budget & NIL"), key("Y", "Compliance & integrity"), key("O", "Look at another team")]
    if getattr(league, "mode", None) == "career" and team is getattr(league, "user_team", None):
        acts.insert(2, key("P", "Practice report", C.BGREEN))
        acts.insert(3, key("N", "Storylines", C.BMAGENTA))
    if getattr(league, "mode", None) == "spectator":
        acts.append(key("F", "Follow a different team"))
    rows = columns(p_team(league, team, 50), p_leaders(league, team, 49))
    rows += columns(p_actions("TEAM", acts, 50, n=10), p_standings(league, team, 49, n=10))
    return rows


def page_recruiting(league, team):
    career = getattr(league, "mode", None) == "career" and team is getattr(league, "user_team", None)
    acts = [key("R", "Recruiting hub"), key("F", "Recruit finder" + ("" if career else " (view)")),
            key("B", "My board" if career else "Their board"), key("K", "Class"), key("P", "Transfer portal"), key("W", "Transfer watch"),
            key("N", "Recruiting news")]
    extra = []
    if career:
        import recruiting_screens
        import textwrap
        need = recruiting_screens._needs_line(league, team).replace("Still need: ", "Needs: ")
        extra = [paint(x, C.BYELLOW) for x in textwrap.wrap(need, 44)]
    left = p_recruiting(league, team, 50, n=10, tail=extra)
    return columns(left, p_actions("RECRUITING · OPTIONS", acts, 49, n=10))


def page_rankings(league, team):
    acts = [key("T", "Media Top 25"), key("P", "NP Playoff Rankings"), key("C", "Selection Committee"),
            key("H", "Golden Helmet race"), key("N", "National champions"), key("S", "Toughest venues"),
            key("R", "Record book", C.BGREEN), key("F", "Hall of Fame", C.BGREEN), key("O", "Strength of schedule"), key("E", "Edit the rankings", C.BCYAN)]
    try:
        import halloffame
        mine = halloffame.user_school(league)
        if mine and mine in halloffame.hall(league).pending:
            acts.append(paint("  HOF selections waiting ([F])", C.BMAGENTA))
    except Exception:
        pass
    return columns(p_poll(league, 38), p_heisman(league, 31, n=11), p_actions("RANKINGS", acts, 29, n=11))


def page_coach(league, team):
    career = getattr(league, "mode", None) == "career" and getattr(league, "user_coach", None) is not None
    acts = []
    if career:
        import people
        n = people.unread(league)
        import skills
        pts = skills._st(league.user_coach)["points"]
        acts += [key("I", f"Inbox ({n} unread)" if n else "Inbox"), key("C", "My career"),
                 key("T", f"Skill tree ({pts} to spend)" if pts else "Skill tree"),
                 key("D", "Develop your coach"), key("S", "My staff"),
                 key("L", "Legacy & trophy case", C.BCYAN), key("W", "Coaching tree (your assistants)")]
    if getattr(league, "mode", None) == "ad" and getattr(league, "ad_user", None):
        acts += [key("C", "AD office (from any tab)")]
    acts += [key("K", "Coaches & carousel"), key("P", "Full head coach profile"), key("Y", "Compliance & integrity")]
    if getattr(league, "mode", None) == "spectator":
        acts.append(key("F", "Follow a different team"))
    import faces_ui
    rows = columns(faces_ui.coach_in_panel(league, team, lambda lg, t, w: p_coach(lg, t, w), 50),
                   p_actions("COACH", acts, 49, n=11))
    book, ad = p_coach_book(league, team, 50), p_ad_expects(league, team, 49)
    tall = max(len(book), len(ad)) - 2
    rows += columns(p_coach_book(league, team, 50, tall), p_ad_expects(league, team, 49, tall))
    return rows


def p_coach_book(league, team, w, height=None):
    """Career record, years at the school, and the whole contract."""
    import carousel as cz
    c = team.coach
    lines = []
    if c is None:
        return panel("RECORD & CONTRACT", [paint("Job open.", C.GRAY)], w, height=9)
    yrs = max(1, league.year - (c.hired_year or league.year) + 1)
    ten, car = cz.splits(cz.tenure_seasons(c)), cz.splits(c.history)
    if not (c.history and c.history[-1].get("year") == league.year):       # this season isn't in the book yet
        for d in (ten, car):
            d["w"], d["l"] = d["w"] + team.wins, d["l"] + team.losses
    import textwrap
    lines.append(f"{paint('Age', C.GRAY)} {c.age} · {paint(cz.PERSONALITIES[c.personality][0], C.BWHITE)}")
    for part in textwrap.wrap(cz.personality_blurb(c), w - 6):          # the whole blurb, never cut off
        lines.append(paint(part, C.GRAY))
    lines.append(f"{paint('At ' + team.school, C.GRAY)} since {c.hired_year or league.year} "
                 f"{paint(f'(year {yrs})', C.GRAY)} · {ten['w']}-{ten['l']}")
    lines.append(f"{paint('Career', C.GRAY)} {car['w']}-{car['l']}"
                 + paint(f"  (records tracked from {__import__('records').book(league).since or league.year})", C.GRAY))
    k = fi.contract(c)
    if k:
        lines.append(f"{paint('Contract', C.GRAY)} {fi.deal_line(k, league, pay=False)}")
        lines.append(f"{paint('Pay', C.GRAY)} {fi.money(k['salary'], exact=True)}/yr · "
                     f"{paint('total', C.GRAY)} {fi.money(fi.deal_total(k, league), exact=True)}")
        lines.append(f"{paint('Owed if fired', C.GRAY)} {fi.money(fi.owed(c, league), exact=True)}")
        import textwrap
        for ln in fi.clause_lines(k, c, league):
            for j, part in enumerate(textwrap.wrap(ln, w - 6)):
                lines.append(paint(("· " if j == 0 else "  ") + part, C.GRAY))
    else:
        lines.append(paint("No contract on file.", C.GRAY))
    return panel("RECORD & CONTRACT", lines, w, height=height or max(9, len(lines)))


def p_ad_expects(league, team, w, height=None):
    """What the AD's label actually means: when he fires, what he's measuring."""
    import carousel as cz
    style, blurb, rules = cz.AD_STYLES[team.ad["style"]]
    import textwrap
    lines = [f"{paint(team.ad['name'], C.BWHITE, C.BOLD)} · {paint(style, C.BCYAN)}"]
    lines += [paint(x, C.GRAY) for x in textwrap.wrap(blurb, w - 4)]
    lines += [f"{paint('Fires around', C.GRAY)} {int(cz.fire_line(team))}/100 heat",
              f"{paint('Judges the goals from year', C.GRAY)} {rules.get('grace', 2) + 1}"]
    c = team.coach
    if c is not None and c.hired_year:
        lines.append(paint(f"{c.name.split()[-1]} is in year {league.year - c.hired_year + 1} at {team.school}", C.GRAY))
    for g in getattr(team, "goals", [])[:5]:
        status, info = cz.goal_status(team, c, g, league.year) if c is not None else ("", 0)
        mark = paint("✓", C.BGREEN) if status == "met" else paint("✗", C.BRED) if status == "failed" else paint("•", C.BYELLOW)
        import textwrap
        win = "every season" if g.window == 1 else f"{g.window} seasons"
        for j, part in enumerate(textwrap.wrap(f"{g.short} ({win})", w - 6)):   # whole words, no dangling "window:"
            lines.append(f"{mark if j == 0 else ' '} {part}")
    if not getattr(team, "goals", []):
        lines.append(paint("No written goals — the mood is the bar.", C.GRAY))
    return panel("WHAT THE AD EXPECTS", lines, w, height=height or max(9, len(lines)))


def page_media(league, team):
    acts = [key("M", "Media center", C.BGREEN), key("H", "History lookup"), key("N", "Recruiting news"),
            key("K", "Carousel news"), key("Y", "Compliance wire")]
    import media_hub
    return columns(p_headlines(league, team, 60), p_actions("MEDIA", acts, 39, n=6)) + \
        columns(media_hub.p_upsets(league, 50, n=6), media_hub.p_big_games(league, 49, n=6))


def page_system(league, team):
    import settings
    st = settings.load()
    info = [paint(f"World seed {league.seed}", C.GRAY),
            paint(f"{len(league.teams)} FBS programs · {sum(len(t.roster) for t in league.teams):,} players", C.GRAY),
            paint(f"Campus Countdown show {'ON' if st.get('gameday') else 'OFF'} · auto copy {'ON' if st.get('auto_copy') else 'OFF'}",
                  C.GRAY)]
    acts = [key("V", "Save game"), key("L", "Load game"), key("E", "Export to Sheets", C.BGREEN), key("S", "Settings"),
            key("H", "Manual"), key("Q", "Return to title screen", C.BRED)]
    return columns(panel("THIS WORLD", info, 50, height=6), p_actions("SYSTEM", acts, 49, n=6))


PAGES = [page_home, page_schedule, page_team, page_recruiting, page_rankings, page_coach, page_media, page_system]


def render(league, tab):
    team = focus_team(league)
    import hotseat
    import theme
    theme.set_current(team, persist=not hotseat.active(league))
    clear()
    for ln in header(league, team):
        print(ln)
    print(tabs(TABS, tab, color=league.team_color(team)))
    for ln in PAGES[tab - 1](league, team):
        print(ln)
    import preseason
    adv = "Advance to offseason" if league.season_complete else \
        "Preseason week" if preseason.needed(league) else f"Play {league.week_name(league.week + 1)}"
    bar_items = [key("1-8", "tabs", C.GRAY), key("A", adv, C.BGREEN), key("M", "sim weeks/seasons", C.BGREEN)]
    from netplay import lobby
    if lobby.active(league):                         # online: the host plays the week when everyone's ready
        bar_items = [key("1-8", "tabs", C.GRAY), key("A", "Ready / not ready", C.BGREEN)]
    if getattr(league, "mode", None) == "career" and getattr(league, "user_coach", None) is not None:
        import people
        n = people.unread(league)
        bar_items.append(key("I", f"inbox ({n})" if n else "inbox", C.BMAGENTA if n else C.BYELLOW))
        bar_items.append(key("C", "my career", C.BMAGENTA))
    if getattr(league, "mode", None) == "ad" and getattr(league, "ad_user", None):
        bar_items.append(key("C", "AD office", C.BMAGENTA))
    if getattr(league, "mode", None) == "spectator":
        bar_items.append(key("C", "recap & stories", C.BMAGENTA))
        bar_items.append(key("B", "sportsbook" + (" ●" if getattr(getattr(league, "book", None), "unseen", None) else ""),
                             C.BGREEN))
    bar_items += [key("/", "go to anything (or just type a name)", C.BCYAN), key("V", "save"), key("?", "manual"),
                  key("Q", "title screen", C.GRAY)]
    for ln in command_bar(bar_items):
        print(ln)
    return team


def pick_follow(league):
    from screens import pick_team
    t = pick_team(league)
    if t is not None:
        league.follow_team = t
