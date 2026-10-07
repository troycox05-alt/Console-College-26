"""Preseason projections shown during the final offseason weeks."""
from collections import defaultdict


def _fbs(league):
    return [t for t in league.teams if not getattr(t, "fcs", False)]


def poll_rank(league, team):
    try:
        return league.rankings.rank_of(team)
    except Exception:
        return None


def conference_projection(league, team):
    members = [t for t in _fbs(league) if t.conference == team.conference]
    members.sort(key=lambda t: (-(getattr(t, "team_ovr", 0) * 1.5 + getattr(t, "prestige", 0) * .35), t.school))
    return next((i for i, t in enumerate(members, 1) if t is team), None), members


def projected_wins(league, team):
    try:
        import carousel
        games = [g for g in league.team_games(team) if g.game_type == "Regular Season"]
        return sum(carousel.win_prob(team, g.opponent_of(team), 0 if g.neutral else (1 if g.home is team else -1), league)
                   for g in games)
    except Exception:
        return max(0.0, min(12.0, 6.0 + (getattr(team, "team_ovr", 65) - 68) * .18))


def roster_strengths(team):
    from models import POSITIONS
    rows = []
    for pos in POSITIONS:
        room = team.players_at(pos)
        if not room:
            continue
        vals = sorted((p.overall_at(pos) for p in room), reverse=True)
        n = 2 if pos in ("QB", "RB", "TE", "LB", "CB", "S") else 3 if pos in ("WR", "DL") else 5 if pos == "OL" else 1
        score = sum(vals[:n]) / min(n, len(vals))
        rows.append((score, pos))
    return sorted(rows, reverse=True)


def award_watch(league, n=10):
    """Simple preseason national watch lists based on talent and team expectations."""
    poll = {t: (league.rankings.rank_of(t) or 45) for t in _fbs(league)}
    pools = defaultdict(list)
    for t in _fbs(league):
        team_bonus = max(0, 28 - poll[t]) * .10
        for p in t.roster:
            base = p.overall + team_bonus
            if p.position == "QB":
                pools["Golden Helmet"].append((base + 2.5, p, t))
                pools["Quarterback"].append((base, p, t))
            elif p.position == "RB":
                pools["Golden Helmet"].append((base + 1.0, p, t))
                pools["Running Back"].append((base, p, t))
            elif p.position in ("WR", "TE"):
                pools["Golden Helmet"].append((base, p, t))
                pools["Receiver"].append((base, p, t))
            elif p.position in ("DL", "LB", "CB", "S"):
                pools["Defender"].append((base, p, t))
    out = {}
    for name, rows in pools.items():
        rows.sort(key=lambda x: -x[0])
        out[name] = [(p, t) for _, p, t in rows[:n]]
    return out


def build(league, team):
    rank = poll_rank(league, team)
    conf_rank, conf = conference_projection(league, team)
    wins = projected_wins(league, team)
    strengths = roster_strengths(team)
    watch = award_watch(league)
    national_talent = sorted(_fbs(league), key=lambda t: (-getattr(t, "team_ovr", 0), -getattr(t, "prestige", 0)))
    talent_rank = next((i for i, t in enumerate(national_talent, 1) if t is team), None)
    return {
        "poll_rank": rank,
        "conference_rank": conf_rank,
        "conference_size": len(conf),
        "projected_wins": wins,
        "talent_rank": talent_rank,
        "strengths": strengths[:4],
        "weaknesses": sorted(strengths)[:4],
        "watch": watch,
    }


def summary_lines(league, team):
    x = build(league, team)
    poll = f"#{x['poll_rank']}" if x["poll_rank"] else "unranked"
    return [
        f"Preseason poll: {poll}",
        f"Conference prediction: #{x['conference_rank']} of {x['conference_size']}",
        f"Projected wins: {x['projected_wins']:.1f}",
        f"Roster talent: #{x['talent_rank']} nationally" if x["talent_rank"] else "Roster talent: —",
    ]


def preseason_honors(league, team):
    """Projected preseason all-conference and All-America mentions for the user's roster."""
    pos_slots = {"QB":1,"RB":2,"WR":3,"TE":1,"OL":5,"DL":4,"LB":3,"CB":2,"S":2,"K":1,"P":1}
    conf = [t for t in _fbs(league) if t.conference == team.conference]
    conf_picks = []
    aa_picks = []
    for pos, slots in pos_slots.items():
        cands = sorted(((p.overall_at(pos), p, t) for t in conf for p in t.players_at(pos)), key=lambda x: -x[0])
        for _, p, t in cands[:slots]:
            if t is team:
                conf_picks.append(p)
        nation = sorted(((p.overall_at(pos), p, t) for t in _fbs(league) for p in t.players_at(pos)), key=lambda x: -x[0])
        for _, p, t in nation[:slots]:
            if t is team:
                aa_picks.append(p)
    return conf_picks, aa_picks
