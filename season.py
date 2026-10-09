"""
season.py — The calendar: schedule, weekly games, and the offseason.

Regular season = 12 weeks: 3 non-conference weeks, then 9 conference weeks.
Every game is simulated snap by snap (game_sim.py / engine.py / playbook.py).
After week 12, advancing runs the offseason:
    seniors graduate → everyone else develops → classes advance / redshirts
    → each team signs a freshman class → new season begins.
"""
import random
from collections import Counter
from development import develop_player
from injuries import heal_all, weekly_healing
import facilities
from portal import fill_gaps, run_portal
from recruiting import attach_class, signing_day
from roster import sign_class, trim_to_template
import postseason as ps
import dynasty
from datetime import date
from recruiting_data import REGION_NEIGHBORS, STATES

REGULAR_SEASON_WEEKS = 13          # 12 games plus one bye for everybody
GAMES_PER_TEAM = 12
BIG_CONFERENCES = {"SCC": 9, "Continental": 9, "Seaboard": 9, "Meridian": 9}
NONCONF_WEEKS = 3
# Non-conference scheduling (see build_schedule step 2).
POWER_INDEPENDENTS = {"South Bend"}
P4_REQUIRED = {"SCC"}                          # requires one Power-4 opponent a year
FCS_ODDS = {"SCC": 0.95, "Seaboard": 0.9, "Meridian": 0.9, "Continental": 0.6}   # chance a Power team buys an FCS game
FCS_WEEK_WEIGHT = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
FCS_GAMES_SOFT_CAP = 2                         # most FCS schools sell one or two FBS games a year
MONEY_GAME_AT_HOME = 0.9                       # the rest are the return trip of a home-and-home
HOME_FIELD = 2.5
REDSHIRT_ODDS = 0.45        # non-starting freshmen who redshirt

# Bowl names, venues, the playoff rotation and title-game sites live in postseason.py.
# Neutral-site rivalries.
NEUTRAL_SITES = {
    frozenset(("Georgia", "Florida")): {2026: "Atlanta Dome, Atlanta", 2027: "Hillsborough Stadium, Tampa",
                                         None: "St. Johns Riverfront Stadium, Jacksonville"},
    frozenset(("Texas", "Oklahoma")): {None: "Fair Park Stadium, Dallas"},
    frozenset(("Hudson", "Chesapeake")): {2026: "Meadowlands Stadium, East Rutherford",
                                          2027: "South Philadelphia Stadium, Philadelphia",
                                          None: "South Philadelphia Stadium, Philadelphia"},
}
_YEAR = [2026]


def league_year():
    return _YEAR[0]


def neutral_site(home, away, year):
    sites = NEUTRAL_SITES.get(frozenset((home.school, away.school)))
    if not sites:
        return False, None
    return True, sites.get(year, sites[None])


class Game:
    def __init__(self, week, home, away, conference_game, game_type="Regular Season", bowl_name=None,
                 venue=None, neutral=None, when=None, seeds=None):
        self.week = week
        self.home = home
        self.away = away
        self.conference_game = conference_game
        self.game_type = game_type
        self.bowl_name = bowl_name
        self.display_name = bowl_name     # "Arroyo Bowl Game", "SCC Championship", ...
        self.home_score = None
        self.away_score = None

        self.neutral, self.venue = neutral_site(home, away, league_year())
        if game_type != "Regular Season":
            # Postseason games say exactly where they are; campus games are never neutral.
            self.neutral = bool(neutral)
            self.venue = venue if venue else f"{home.stadium}"
        self.date = when                  # datetime.date, postseason only
        self.seeds = seeds or {}          # team -> NP seed
        # Bracket links (set when the bracket is built)
        self.next_game = None             # name of the bowl the winner moves on to
        self.next_date = None
        self.next_site = None
        self.partner = None               # the game whose winner this winner plays next
        self.waiting = None               # first round: the top-four seed waiting in the quarterfinal
        self.tier = None                  # bowls: 1 (best) to 3

        self.box = None                  # GameSim with the full box score, once played

    @property
    def played(self):
        return self.home_score is not None

    @property
    def winner(self):
        if not self.played:
            return None
        return self.home if self.home_score > self.away_score else self.away

    @property
    def loser(self):
        if not self.played:
            return None
        return self.away if self.winner is self.home else self.home

    def opponent_of(self, team):
        return self.away if team is self.home else self.home

    def score_for(self, team):
        return self.home_score if team is self.home else self.away_score


# ─── Schedule ───────────────────────────────────────────────────────────────

def _round_robin(teams, rng):
    t = list(teams)
    rng.shuffle(t)
    if len(t) % 2:
        t.append(None)
    n = len(t)
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = t[i], t[n - 1 - i]
            if a is not None and b is not None:
                pairs.append((a, b) if (r + i) % 2 == 0 else (b, a))
        rounds.append(pairs)
        t = [t[0], t[-1]] + t[1:-1]
    return rounds


def conference_game_count(conf, size):
    """How many league games this conference plays (capped by its size)."""
    target = BIG_CONFERENCES.get(conf, 8)
    k = max(0, min(target, size - 1))
    if k % 2 and size % 2:
        k -= 1                          # an odd slate needs an even-sized league
    return k


def _rounds(members, k, rng):
    """k rounds of matchups where every team plays exactly once per round."""
    order = list(members)
    rng.shuffle(order)
    n = len(order)
    fixed, rotate = order[0], order[1:]
    rounds = []
    for _ in range(n - 1):
        pairs = [(fixed, rotate[0])]
        for i in range(1, n // 2):
            pairs.append((rotate[i], rotate[-i]))
        rounds.append(pairs)
        rotate = rotate[-1:] + rotate[:-1]
    rng.shuffle(rounds)
    return rounds[:k]


def _circulant_edges(members, k, rng):
    """A k-regular set of matchups for an odd-sized league (k must be even)."""
    order = list(members)
    rng.shuffle(order)
    n = len(order)
    edges = []
    for d in range(1, k // 2 + 1):
        for i in range(n):
            edges.append((order[i], order[(i + d) % n]))
    return edges


# Rivalry Week: the last Saturday of the regular season belongs to these.
RIVALRY_WEEK = [
    ("Alabama", "East Alabama"), ("Michigan", "Ohio State"), ("Mississippi", "Mississippi State"), ("Texas", "Brazos"),
    ("Tennessee", "Nashville"), ("Arkansas", "Missouri"), ("Bayou State", "Oklahoma"), ("Iowa", "Nebraska"),
    ("Minnesota", "Wisconsin"), ("Indiana", "Tippecanoe"), ("Illinois", "Lakeshore"), ("Pennsylvania", "Michigan State"),
    ("Los Angeles", "Southern California"), ("Oregon", "Washington"), ("Arizona", "Arizona State"), ("Kansas", "Kansas State"),
    ("Waco", "Fort Worth"), ("Provo", "Utah"), ("Iowa State", "Oklahoma State"), ("Virginia", "Blacksburg"),
    ("North Carolina", "NC State"), ("California", "Palo Alto"), ("Boston", "Syracuse"), ("Durham", "Winston-Salem"),
    ("Upcountry", "South Carolina"), ("Florida", "Florida State"), ("Georgia", "Atlanta"), ("Kentucky", "Louisville"),
    ("Hudson", "Chesapeake"), ("Cincinnati", "West Virginia"), ("Houston", "Lubbock"), ("Colorado", "Orlando"),
]
# Cross-conference rivalries played in September, not on Rivalry Week.
EARLY_RIVALRIES = {frozenset(("Iowa", "Iowa State")), frozenset(("Pittsburgh", "West Virginia"))}
# Rivalries played at their traditional mid-season spots.
FIXED_WEEKS = {frozenset(("Oklahoma", "Texas")): 7, frozenset(("Florida", "Georgia")): 10}


def _custom_rounds(members, k, first_round, fixed, rng):
    """A round robin whose round 0 is exactly `first_round` (rivalry week), with
    rounds containing `fixed` pairs pulled in. Circle method: seating the
    first round's pairs across the circle makes it round 0."""
    order_pairs = list(first_round)
    fixed_team, partner = order_pairs[0]
    n = len(members)
    rotate = [None] * (n - 1)
    rotate[0] = partner
    for i, (a, b) in enumerate(order_pairs[1:], 1):
        rotate[i], rotate[-i] = a, b
    rounds = []
    for _ in range(n - 1):
        pairs = [(fixed_team, rotate[0])]
        for i in range(1, n // 2):
            pairs.append((rotate[i], rotate[-i]))
        rounds.append(pairs)
        rotate = rotate[-1:] + rotate[:-1]
    first, rest = rounds[0], rounds[1:]
    must = []
    for r in rest:
        names = {frozenset((a.school, b.school)) for a, b in r}
        for pair, week in fixed.items():
            if pair in names:
                must.append((r, week))
    others = [r for r in rest if r not in [m[0] for m in must]]
    rng.shuffle(others)
    return first, must, others[:max(0, k - 1 - len(must))]


def _rivalry_matching(members, rng, cross):
    """Pair the conference for rivalry week: real rivals first; schools whose
    rival is in another conference are paired with each other (that game moves
    to the bye week so they're free for the real one); everyone else at random,
    never using a pair that has its own traditional week."""
    by = {t.school: t for t in members}
    pairs, used = [], set()
    for a, b in RIVALRY_WEEK:
        if a in by and b in by and a not in used and b not in used and a not in cross and b not in cross:
            pairs.append((by[a], by[b]))
            used.update((a, b))
    fixed = set(FIXED_WEEKS)
    for group in ([t for t in members if t.school in cross and t.school not in used],
                  [t for t in members if t.school not in used and t.school not in cross]):
        for _ in range(200):
            rng.shuffle(group)
            if all(frozenset((group[i].school, group[i + 1].school)) not in fixed for i in range(0, len(group) - 1, 2)):
                break
        for i in range(0, len(group) - 1, 2):
            pairs.append((group[i], group[i + 1]))
            used.update((group[i].school, group[i + 1].school))
    left = [t for t in members if t.school not in used]
    for i in range(0, len(left) - 1, 2):
        pairs.append((left[i], left[i + 1]))
    return pairs


def _protected(league):
    """Cross-conference rivalries the schedule keeps: the standing list, plus any
    rivalry that realignment split up (the schools keep playing it)."""
    from carousel import PROTECTED
    extra = [tuple(p) for p in (getattr(league, "realign", None) or {}).get("protected", [])]
    return list(PROTECTED) + [p for p in extra if p not in PROTECTED and p[::-1] not in PROTECTED]


def build_schedule(league, rng):
    """Every FBS team gets exactly 12 games across 13 weeks (one bye), laid out
    like a real season:

      Weeks 1-3 (or 1-4)  non-conference: guarantee games against FCS schools,
                          plus cross-conference matchups
      Mid-season          conference play, with each league's bye in the middle
      Week 13             Rivalry Week — every league's final round is built
                          around its rivalries, plus the protected cross-conference
                          ones (Upcountry–South Carolina, Florida–FSU, ...)
    The Red River Rivalry and Florida–Georgia keep their traditional mid-season weeks.
    """
    weeks = list(range(1, REGULAR_SEASON_WEEKS + 1))
    last = REGULAR_SEASON_WEEKS
    schedule = {w: [] for w in weeks}
    busy = {t: set() for t in league.teams + league.fcs_teams}
    need = {t: GAMES_PER_TEAM for t in league.teams}
    met = set()
    window_start = {}

    def add(week, home, away, conf_game):
        schedule[week].append(Game(week, home, away, conf_game))
        busy[home].add(week)
        busy[away].add(week)
        met.add(frozenset((home, away)))
        if not getattr(home, "fcs", False):
            need[home] -= 1
        if not getattr(away, "fcs", False):
            need[away] -= 1

    def host(a, b):
        return (a, b) if rng.random() < 0.5 else (b, a)

    # ── 1. conference slates ─────────────────────────────────────────────
    for conf in sorted({t.conference for t in league.teams}):
        members = league.conference_teams(conf)
        if conf == "Independent" or len(members) < 2:
            continue
        k = conference_game_count(conf, len(members))
        start = last - k                                  # conference play runs start..13 with one bye
        for t in members:
            window_start[t] = start
        window = list(range(start, last + 1))
        fixed = {p: w for p, w in FIXED_WEEKS.items() if all(any(t.school == s for t in members) for s in p)}
        bye_options = [w for w in window[1:-1] if w not in fixed.values()]
        bye = rng.choice(bye_options) if bye_options else None
        conf_weeks = [w for w in window if w != bye][-k:] if k else []
        if len(members) % 2 == 0 and k:
            PROTECTED = _protected(league)
            names = {t.school for t in members}
            cross = {x for p in PROTECTED if frozenset(p) not in EARLY_RIVALRIES for x in p if x in names
                     and any(o not in names and any(o == t.school for t in league.teams) for o in p if o != x)}
            first, must, others = _custom_rounds(members, k, _rivalry_matching(members, rng, cross), fixed, rng)
            add_round = lambda week, pairs: [add(week, *host(a, b), True) for a, b in pairs]
            moved = [(a, b) for a, b in first if a.school in cross and b.school in cross]
            add_round(last, [p for p in first if p not in moved])
            if bye is not None:
                add_round(bye, moved)              # free on Rivalry Week for the cross-conference rival
            else:
                add_round(last, moved)
            free_weeks = [w for w in conf_weeks if w != last and w not in fixed.values()]
            rng.shuffle(free_weeks)
            for r, week in must:
                if week in conf_weeks:
                    add_round(week, r)
                else:
                    others.append(r)
            for r, week in zip(others, free_weeks):
                add_round(week, r)
        elif k:                                           # odd league: colour it in
            PROTECTED = _protected(league)
            names = {t.school for t in members}
            cross = {x for p in PROTECTED if frozenset(p) not in EARLY_RIVALRIES for x in p if x in names
                     and any(o not in names and any(o == t.school for t in league.teams) for o in p if o != x)}
            edges = _circulant_edges(members, k, rng)
            rivals = {frozenset(p) for p in RIVALRY_WEEK}
            edges.sort(key=lambda e: frozenset((e[0].school, e[1].school)) not in rivals)
            for a, b in edges:
                keep13 = a.school in cross or b.school in cross       # saved for the cross-conference rival
                if (frozenset((a.school, b.school)) in rivals and not keep13
                        and last not in busy[a] and last not in busy[b]):
                    add(last, *host(a, b), True)
                    continue
                free = [w for w in conf_weeks if w not in busy[a] and w not in busy[b] and not (keep13 and w == last)]
                if not free:
                    free = [w for w in weeks if w not in busy[a] and w not in busy[b]]
                if not free:
                    continue
                week = min(free, key=lambda w: (len(schedule[w]), rng.random()))
                add(week, *host(a, b), True)

    # ── 1b. protected cross-conference rivalries on Rivalry Week ──────────
    by_name = {t.school: t for t in league.teams}
    for a_name, b_name in _protected(league):
        a, b = by_name.get(a_name), by_name.get(b_name)
        if a is None or b is None or a.conference == b.conference or frozenset((a, b)) in met:
            continue
        if need[a] <= 0 or need[b] <= 0:
            continue
        early_game = frozenset((a_name, b_name)) in EARLY_RIVALRIES          # Cy-Hawk, Backyard Brawl
        free = [w for w in (weeks if early_game else reversed(weeks)) if w not in busy[a] and w not in busy[b]]
        if early_game:
            free = sorted(free, key=lambda w: abs(w - 2))
        if free:
            home, away = (a, b) if (league.year + len(a_name)) % 2 else (b, a)
            add(free[0], home, away, False)

    # ── 1c. Coach Career: the games you asked your AD for (a neutral-site opener, home-and-homes) ──
    _requested_games(league, schedule, busy, need, met, add, window_start, weeks, last)

    # ── 2. non-conference: what each program actually goes out and buys ──
    # Real athletic directors don't build gauntlets. A Power program keeps
    # its one marquee game (or its protected rival), buys a Group of Five
    # team or two, and pays an FCS school for a September win. Group of
    # Five programs cash a check or two on a Power team's field, play a
    # regional G5 neighbour, and host their own FCS guarantee game.
    nonconf_so_far = {t: [] for t in league.teams}
    for w in weeks:
        for g in schedule[w]:
            if not g.conference_game:
                for t in (g.home, g.away):
                    if t in nonconf_so_far:
                        nonconf_so_far[t].append(g.opponent_of(t))
    wish = {t: _nonconf_wishes(t, need[t], nonconf_so_far[t], rng) for t in league.teams}
    import career_plus
    if career_plus.mine(league):
        u = league.user_team
        wish[u] = career_plus.apply_wish(league, u, wish[u], need[u], nonconf_so_far[u])

    def nonconf_week(t, w):
        return w < window_start.get(t, last + 1) or t.conference == "Independent"

    def fbs_left(t):
        return wish[t]["power"] + wish[t]["group"]

    def take(t, opp):
        """Use up the wish this game fills — or the closest one if plans changed."""
        cat = "fcs" if getattr(opp, "fcs", False) else schedule_tier(opp)
        for c in (cat, "group", "power", "fcs"):
            if wish[t][c] > 0:
                wish[t][c] -= 1
                return

    def book(week, a, b):
        """a and b are both FBS. Money games are played at the bigger program."""
        ta, tb = schedule_tier(a), schedule_tier(b)
        if ta != tb:
            big, small = (a, b) if ta == "power" else (b, a)
            home, away = (big, small) if rng.random() < MONEY_GAME_AT_HOME else (small, big)
        else:
            home, away = host(a, b)
        add(week, home, away, False)
        take(a, b)
        take(b, a)

    # 2a. FCS guarantee games, early — and at the FBS team's place
    for t in sorted(league.teams, key=lambda t: rng.random()):
        if not wish[t]["fcs"]:
            continue
        early = [w for w in weeks if w not in busy[t] and nonconf_week(t, w) and w <= 5]
        if not early:
            continue
        week = rng.choices(early, weights=[FCS_WEEK_WEIGHT.get(w, 1) for w in early])[0]
        opp = _pick_fcs(league, busy, week, rng, t, met=met)
        if opp is not None:
            add(week, t, opp, False)
            take(t, opp)

    # 2a½. South Bend-style independents book their national slate first. Power
    # programs will spend a September date — or their open week — on that game.
    for ind in [t for t in league.teams if t.conference == "Independent" and schedule_tier(t) == "power"]:
        for _ in range(GAMES_PER_TEAM):
            if wish[ind]["power"] <= 0:
                break
            options = []
            for b in league.teams:
                if schedule_tier(b) != "power" or b is ind or frozenset((ind, b)) in met or fbs_left(b) <= 0:
                    continue
                free = [w for w in weeks if w not in busy[ind] and w not in busy[b]]
                if free:
                    options.append((b, free))
            if not options:
                break
            weights = [_matchup_appeal(ind, b) * (3.0 if wish[b]["power"] > 0 else 1.0) for b, _ in options]
            b, free = rng.choices(options, weights=weights)[0]
            book(rng.choice(free), ind, b)

    # 2b. FBS non-conference games, week by week, matching what both sides want
    for week in weeks:
        open_teams = [t for t in league.teams if week not in busy[t] and fbs_left(t) > 0
                      and nonconf_week(t, week)]
        if not open_teams:
            continue
        slack = {t: sum(1 for w in weeks if w >= week and w not in busy[t] and nonconf_week(t, w)) - fbs_left(t)
                 for t in open_teams}
        rng.shuffle(open_teams)
        open_teams.sort(key=lambda t: slack[t])            # the teams with no wiggle room go first
        used = set()

        def partners(a, strict):
            out = []
            for b in open_teams:
                if b in used or b is a or b.conference == a.conference or frozenset((a, b)) in met:
                    continue
                if strict and not (wish[a][schedule_tier(b)] > 0 and wish[b][schedule_tier(a)] > 0):
                    continue
                out.append(b)
            return out

        for a in open_teams:
            if a in used:
                continue
            options = partners(a, strict=True)
            if not options and slack[a] <= 0:
                options = partners(a, strict=False)        # out of weeks: take the best game on offer
                options.sort(key=lambda b: -(wish[a][schedule_tier(b)] > 0) - (wish[b][schedule_tier(a)] > 0))
                options = options[:4]
            if not options:
                continue
            b = rng.choices(options, weights=[_matchup_appeal(a, o) for o in options])[0]
            book(week, a, b)
            used.update({a, b})

    # 2c. mop-up: anyone still short of FBS opponents, in any week they share
    for _ in range(3):
        short = [t for t in league.teams if fbs_left(t) > 0]
        rng.shuffle(short)
        for a in short:
            if fbs_left(a) <= 0:
                continue
            for b in sorted(short, key=lambda b: -_matchup_appeal(a, b)):
                if b is a or fbs_left(b) <= 0 or b.conference == a.conference or frozenset((a, b)) in met:
                    continue
                common = sorted(w for w in weeks if w not in busy[a] and w not in busy[b])
                if not common:
                    continue
                book(common[0], a, b)
                break

    # ── 3. FCS guarantee games: whatever is still open, as early as possible ──
    for t in sorted(league.teams, key=lambda t: -need[t]):
        while need[t] > 0:
            free = [w for w in weeks if w not in busy[t] and _pick_fcs(league, busy, w, rng, t, met=met)]
            if not free and not _make_room(schedule, busy, league, t, weeks, rng):
                break
            free = free or [w for w in weeks if w not in busy[t] and _pick_fcs(league, busy, w, rng, t, met=met)]
            if not free:
                break
            week = min(free)                                 # cupcakes come first
            opp = _pick_fcs(league, busy, week, rng, t, met=met)
            if opp is None:
                break
            add(week, t, opp, False)
    _balance_home_games(schedule, league, rng)
    for w in schedule:
        schedule[w].sort(key=lambda g: -(g.home.team_ovr + g.away.team_ovr))
    return schedule


def _poll_index(league, team):
    """Where a team sits in the full poll order (not just the Top 25)."""
    import committee
    try:
        return committee.order_for_selection(league).index(team)
    except ValueError:
        return 999


def generate_postseason_week(league, week):
    """Builds each postseason week as the one before it finishes."""
    if week not in league.schedule:
        league.schedule[week] = []
    season = league.year
    dates = ps.postseason_dates(season)

    if week == 14:
        # Conference championships: the top two in the standings. Power leagues
        # play at their fixed neutral sites; the rest at the higher seed's stadium.
        league.conf_champs = {}
        for conf in sorted({t.conference for t in league.teams}):
            if conf == "Independent":
                continue
            import dynasty
            standings = [t for t in league.standings(conf) if not dynasty.banned(league, t)]
            if len(standings) < 2:
                continue
            home, away = standings[0], standings[1]
            site = ps.CCG_SITES.get(conf)
            venue = f"{site[0]}, {site[1]}" if site else home.stadium
            game = Game(14, home, away, False, game_type="Conference Championship",
                        bowl_name=f"{conf} Championship", venue=venue, neutral=bool(site), when=dates["ccg"])
            game.seeds = {home: 1, away: 2}          # conference seeds, shown as (1)/(2)
            league.schedule[14].append(game)

    elif week == 15:
        # Selection Day: crown conference champions, seed the field, set the bowls.
        champs = []
        for conf in sorted({t.conference for t in league.teams}):
            if conf == "Independent":
                continue
            ccg = next((g for g in league.schedule.get(14, []) if g.bowl_name == f"{conf} Championship"), None)
            import dynasty
            ok = [t for t in league.standings(conf) if not dynasty.banned(league, t)]
            champ = ccg.winner if ccg and ccg.played else (ok[0] if ok else None)
            if champ:
                league.conf_champs[conf] = champ
                champ.achievements.append(f"{conf} Champion")
                champs.append(champ)

        order = lambda t: _poll_index(league, t)
        # 12-team format with straight seeding (2025 onward): the five highest-ranked
        # conference champions get in, then the seven highest-ranked other teams —
        # ranked by the Selection Committee's final Playoff Rankings, not the poll.
        auto_bids = sorted(champs, key=order)[:5]
        import committee
        at_large = [t for t in committee.order_for_selection(league)
                    if t not in auto_bids and not getattr(t, "fcs", False) and not dynasty.banned(league, t)][:7]
        seeds = sorted(auto_bids + at_large, key=order)
        league.playoff_seeds = seeds
        league.playoff_seed_map = {t: i + 1 for i, t in enumerate(seeds)}
        smap = league.playoff_seed_map
        for t in seeds:
            t.achievements.append("NP Appearance")

        qf_bowls, _ = ps.cfp_rotation(season)
        fr_days = dates["first_round"]
        # First round on campus: 5v12, 6v11, 7v10, 8v9. Winners meet 4, 3, 2, 1.
        first = []
        for i, (hi, lo) in enumerate(((4, 11), (5, 10), (6, 9), (7, 8))):
            home, away = seeds[hi], seeds[lo]
            g = Game(15, home, away, False, game_type="NP First Round", bowl_name="NP First Round",
                     venue=f"{home.stadium}", neutral=False, when=fr_days[0 if i == 3 else 1],
                     seeds={home: hi + 1, away: lo + 1})
            g.display_name = "NP First Round"
            first.append(g)
        league.schedule[15] = first
        # Link each first-round game to its quarterfinal.
        top_for = {0: 3, 1: 2, 2: 1, 3: 0}        # 5/12 → #4, 6/11 → #3, 7/10 → #2, 8/9 → #1
        for i, g in enumerate(first):
            top = seeds[top_for[i]]
            bowl, m, d = qf_bowls[top_for[i]]
            g.waiting = top
            g.next_game = ps.CFP_BOWLS[bowl][2]
            g.next_date = date(season + (1 if m == 1 else 0), m, d)

        # Bowls: best teams to the best bowls, trying not to pair conference-mates.
        eligible = sorted((t for t in league.teams if t.wins >= 6 and t not in seeds
                           and not dynasty.banned(league, t)), key=order)
        bowls = sorted(ps.BOWLS.items(), key=lambda kv: kv[1][2])       # tier 1 first
        rng = league.rng
        league.schedule[16] = []
        for name, (stadium, city, tier, (m, d)) in bowls:
            if len(eligible) < 2:
                break
            a_team = eligible.pop(0)
            pick = 0
            for i in range(min(6, len(eligible))):
                if eligible[i].conference != a_team.conference:
                    pick = i
                    break
            b_team = eligible.pop(pick)
            home, away = (a_team, b_team) if rng.random() < 0.5 else (b_team, a_team)
            g = Game(16, home, away, False, game_type="Bowl", bowl_name=name,
                     venue=f"{stadium}, {city}", neutral=True,
                     when=date(season + (1 if m == 1 else 0), m, d))
            g.tier = tier
            league.schedule[16].append(g)

    elif week == 16:
        # Quarterfinals at the Six Classics bowls in this year's rotation.
        seeds = league.playoff_seeds
        smap = league.playoff_seed_map
        qf_bowls, sf_bowls = ps.cfp_rotation(season)
        first = [g for g in league.schedule.get(15, []) if g.game_type == "NP First Round"]
        qfs = []
        for top_i, fr in zip((3, 2, 1, 0), first):          # #4, #3, #2, #1
            top = seeds[top_i]
            challenger = fr.winner or fr.home
            bowl, m, d = qf_bowls[top_i]
            stadium, city, display = ps.CFP_BOWLS[bowl]
            g = Game(16, top, challenger, False, game_type="NP Quarterfinal", bowl_name=bowl,
                     venue=f"{stadium}, {city}", neutral=True,
                     when=date(season + (1 if m == 1 else 0), m, d),
                     seeds={top: smap[top], challenger: smap[challenger]})
            g.display_name = display
            qfs.append(g)
        qfs.reverse()                                        # #1's game first
        # Bracket: (1 v 8/9) with (4 v 5/12) → first semifinal; (2 v 7/10) with (3 v 6/11) → second.
        sf_dates = ps.postseason_dates(season)["sf"]
        pairs = ((qfs[0], qfs[3], 0), (qfs[1], qfs[2], 1))
        for x, y, k in pairs:
            sf_name = ps.CFP_BOWLS[sf_bowls[k]][2]
            for g, p in ((x, y), (y, x)):
                g.partner = p
                g.next_game = sf_name
                g.next_date = sf_dates[k]
        league.schedule[16] = qfs + league.schedule.get(16, [])

    elif week == 17:
        smap = league.playoff_seed_map
        qfs = [g for g in league.schedule.get(16, []) if g.game_type == "NP Quarterfinal"]
        _, sf_bowls = ps.cfp_rotation(season)
        sf_dates = ps.postseason_dates(season)["sf"]
        site = ps.title_site(season)
        sfs = []
        for k, (x, y) in enumerate(((qfs[0], qfs[3]), (qfs[1], qfs[2]))):
            a_team, b_team = x.winner or x.home, y.winner or y.home
            home, away = sorted((a_team, b_team), key=lambda t: smap[t])
            bowl = sf_bowls[k]
            stadium, city, display = ps.CFP_BOWLS[bowl]
            g = Game(17, home, away, False, game_type="NP Semifinal", bowl_name=bowl,
                     venue=f"{stadium}, {city}", neutral=True, when=sf_dates[k],
                     seeds={home: smap[home], away: smap[away]})
            g.display_name = display
            g.next_game = "National Championship"
            g.next_date = ps.postseason_dates(season)["title"]
            g.next_site = f"{site[0]} in {site[1].split(',')[0]}"
            for t in (home, away):
                t.achievements.append("Playoff Semifinalist")
            sfs.append(g)
        sfs[0].partner, sfs[1].partner = sfs[1], sfs[0]
        league.schedule[17] = sfs

    elif week == 18:
        smap = league.playoff_seed_map
        sfs = league.schedule.get(17, [])
        if len(sfs) == 2:
            a_team = sfs[0].winner or sfs[0].home
            b_team = sfs[1].winner or sfs[1].home
            home, away = sorted((a_team, b_team), key=lambda t: smap[t])
            site = ps.title_site(season)
            g = Game(18, home, away, False, game_type="National Championship",
                     bowl_name="National Championship", venue=f"{site[0]}, {site[1]}", neutral=True,
                     when=ps.postseason_dates(season)["title"], seeds={home: smap[home], away: smap[away]})
            g.display_name = "NP National Championship"
            league.schedule[18] = [g]


def schedule_tier(team):
    """Who a program schedules as: a Power program or a Group of Five one.
    South Bend schedules like a Power program; Connecticut like a Group of Five one."""
    if getattr(team, "fcs", False):
        return "fcs"
    if team.conference in BIG_CONFERENCES or team.school in POWER_INDEPENDENTS:
        return "power"
    return "group"


def _requested_games(league, schedule, busy, need, met, add, window_start, weeks, last):
    """Your non-conference requests (career_plus.nonconf_screen), booked before anyone else's."""
    import career_plus
    if not career_plus.mine(league):
        return
    me = league.user_team
    by = {t.school: t for t in league.teams + list(getattr(league, "fcs_teams", []))}
    try:
        import cp_sched
        for d, side in cp_sched.booked(league, league.year):     # the games you signed, years ago
            t = by.get(d["school"])
            if t is None or (t.conference == me.conference and t.conference != "Independent") \
                    or frozenset((me, t)) in met or need[me] <= 0 or need.get(t, 1) <= 0:
                continue
            pref = (1, 2) if side == "neutral" else ()
            free = [w for w in pref if w not in busy[me] and w not in busy[t]]
            free = free or [w for w in weeks if w not in busy[me] and w not in busy[t]
                            and w < min(window_start.get(me, last + 1), window_start.get(t, last + 1))]
            free = free or [w for w in weeks if w not in busy[me] and w not in busy[t] and w != last]
            if not free:
                continue
            home, away = (t, me) if side == "away" else (me, t)
            add(free[0], home, away, False)
            if side == "neutral":
                g = schedule[free[0]][-1]
                g.neutral = True
                g.venue = d.get("venue") or g.venue
                g.showcase = "Kickoff Classic"
    except Exception as e:                                  # noqa: BLE001 — a booking never breaks the schedule
        league.__dict__.setdefault("error_log", []).append(f"cp_sched booking: {e!r}")
    plan = career_plus.nonconf_plan(league, league.year)
    if not plan:
        return
    opener = by.get(plan.get("opener") or "")
    if opener is not None and opener.conference != me.conference and frozenset((me, opener)) not in met \
            and need[me] > 0 and need[opener] > 0:
        wk = next((w for w in (1, 2) if w not in busy[me] and w not in busy[opener]), None)
        if wk is not None:
            home, away = (me, opener) if league.year % 2 else (opener, me)
            add(wk, home, away, False)
            g = schedule[wk][-1]
            try:
                import postseason as ps
                stadium, city = next(iter(ps.BOWLS.values()))[:2]
            except Exception:                               # noqa: BLE001
                stadium, city = home.stadium, ""
            g.neutral = True
            g.venue = f"{stadium}, {city}".strip(", ")
            g.showcase = "Kickoff Classic"
    for school in plan.get("ask", []):
        t = by.get(school)
        if t is None or t.conference == me.conference or frozenset((me, t)) in met or need[me] <= 0 or need[t] <= 0:
            continue
        free = [w for w in weeks if w not in busy[me] and w not in busy[t]
                and w < min(window_start.get(me, last + 1), window_start.get(t, last + 1))]
        free = free or [w for w in weeks if w not in busy[me] and w not in busy[t] and w != last]
        if free:
            home, away = (me, t) if (league.year + len(school)) % 2 else (t, me)    # home-and-home: it alternates
            add(free[0], home, away, False)


def _nonconf_wishes(team, slots, already, rng):
    """What a program wants from its open non-conference dates, as counts of
    'fcs', 'power' and 'group' opponents. `already` is the non-conference
    opponents it's locked into (protected rivals)."""
    wish = Counter(fcs=0, power=0, group=0)
    if slots <= 0:
        return wish
    power_now = sum(schedule_tier(o) == "power" for o in already)
    if schedule_tier(team) == "power":
        if team.conference == "Independent":                  # South Bend: a national schedule
            fcs = 0
            power = max(0, round(slots * 0.6) - power_now)
        else:
            fcs = 1 if rng.random() < FCS_ODDS.get(team.conference, 0.8) else 0
            r = rng.random()
            target = 0 if r < 0.30 else 1 if r < 0.92 else 2  # the marquee game, sometimes two
            if team.conference in P4_REQUIRED:
                target = max(target, 1)
            power = max(0, target - power_now)
    else:
        fcs = 1 if rng.random() < 0.75 else 0
        if team.conference == "Independent":                  # Connecticut: a dozen dates to fill
            fcs += rng.random() < 0.5
            target = round(slots * 0.3)
        else:
            r = rng.random()
            target = 0 if r < 0.08 else 1 if r < 0.55 else 2  # one or two guarantee checks
        power = max(0, target - power_now)
    fcs = min(fcs, slots)
    power = min(power, slots - fcs)
    wish.update(fcs=fcs, power=power, group=slots - fcs - power)
    return wish


def _nearby(a, b):
    """Non-conference games are mostly regional — buses are cheaper than planes."""
    sa, sb = getattr(a, "home_state", None), getattr(b, "home_state", None)
    if not sa or not sb or sa not in STATES or sb not in STATES:
        return 1.0
    if sa == sb:
        return 3.0
    ra, rb = STATES[sa][1], STATES[sb][1]
    if ra == rb:
        return 1.8
    return 1.0 if rb in REGION_NEIGHBORS.get(ra, ()) else 0.45


def _matchup_appeal(a, b):
    """How likely these two are to sign a contract. Power-vs-Power games pair
    programs of similar standing (the marquee games); money games care more
    about geography than about who's good."""
    ta, tb = schedule_tier(a), schedule_tier(b)
    gap = abs(a.prestige - b.prestige)
    if ta == tb:
        closeness = 1.0 if gap <= 12 else 0.5 if gap <= 25 else 0.25
    else:
        closeness = 1.0
    return closeness * _nearby(a, b)


def _conference_weeks(weeks, k, rng):
    """Conference play leans to the back half of the season, leaving the
    early weeks open for non-conference games."""
    pool = list(weeks)
    weights = {w: (0.3 if w <= 3 else 0.7 if w <= 5 else 1.0) for w in weeks}
    chosen = []
    while len(chosen) < k and pool:
        pick = rng.choices(pool, weights=[weights[w] for w in pool])[0]
        pool.remove(pick)
        chosen.append(pick)
    return sorted(chosen)


def _balance_home_games(schedule, league, rng):
    """Flip host duties until nearly everyone sits at six or seven home games.
    FCS guarantee games are always played at the FBS team's stadium."""
    home = {t: 0 for t in league.teams}
    games = [g for w in schedule for g in schedule[w]]
    for g in games:
        if g.home in home:
            home[g.home] += 1
    swappable = [g for g in games if g.home in home and g.away in home]
    # Flip home-and-homes between equals first; buy games stay at the buyer's place if at all possible.
    swappable.sort(key=lambda g: schedule_tier(g.home) != schedule_tier(g.away))
    for _ in range(600):
        hi = max(home, key=lambda t: home[t])
        lo = min(home, key=lambda t: home[t])
        if home[hi] <= 7 and home[lo] >= 6:
            break
        moved = False
        for g in swappable:
            if g.home is hi and home[g.away] < home[hi] - 1:
                g.home, g.away = g.away, g.home
                home[g.home] += 1
                home[g.away] -= 1
                moved = True
                break
            if g.away is lo and home[g.home] > home[lo] + 1:
                g.home, g.away = g.away, g.home
                home[g.home] += 1
                home[g.away] -= 1
                moved = True
                break
        if not moved:
            break


def _make_room(schedule, busy, league, team, weeks, rng):
    """Shift one of this team's games so it can open a week with an FCS
    opponent available. Rare, but it keeps everybody at 12 games."""
    for g in [g for w in weeks for g in schedule[w] if team in (g.home, g.away)]:
        other = g.away if g.home is team else g.home
        if not _pick_fcs(league, busy, g.week, rng):
            continue
        alt = [w for w in weeks if w not in busy[team] and w not in busy[other]]
        if not alt:
            continue
        old, new = g.week, rng.choice(alt)
        schedule[old].remove(g)
        g.week = new
        schedule[new].append(g)
        for t in (g.home, g.away):
            busy[t].discard(old)
            busy[t].add(new)
        return True
    return False


def _pick_fcs(league, busy, week, rng, team=None, met=None):
    """An FCS opponent free that week. Prefers schools that haven't sold many
    games yet and — for a given FBS team — schools close to home (and never one
    it already plays this season)."""
    options = [f for f in league.fcs_teams if week not in busy[f]
               and not (team is not None and met is not None and frozenset((team, f)) in met)]
    if not options:
        return None
    fewest = min(len(busy[f]) for f in options)
    options = [f for f in options if len(busy[f]) <= max(fewest, FCS_GAMES_SOFT_CAP - 1)]
    if team is None:
        return min(options, key=lambda f: (len(busy[f]), rng.random()))
    weights = [_nearby(team, f) / (1 + len(busy[f])) ** 2 for f in options]
    return rng.choices(options, weights=weights)[0]


# ─── Games ──────────────────────────────────────────────────────────────────

def record_result(game):
    for team in (game.home, game.away):
        won = team is game.winner
        team.wins += won
        team.losses += not won
        team.points_for += game.score_for(team)
        team.points_against += game.score_for(game.opponent_of(team))
        if game.conference_game and game.game_type == "Regular Season":
            team.conf_wins += won
            team.conf_losses += not won

    if game.winner:
        if getattr(game, "game_type", "") == "Bowl":
            game.winner.achievements.append(f"{game.bowl_name} Champion")
        elif getattr(game, "game_type", "") == "National Championship":
            for t in (game.winner, game.loser):
                if "Playoff Semifinalist" in t.achievements:
                    t.achievements.remove("Playoff Semifinalist")      # they got further than that
            game.winner.achievements.append("National Champion")
            game.loser.achievements.append("National Runner-Up")


def simulate_game(game, rng, narrator=None):
    """Plays the game snap by snap (see game_sim.py) and records the result."""
    from game_sim import GameSim
    sim = GameSim(game, rng, narrator)
    sim.play()
    game.box = sim
    record_result(game)
    for player, line in sim.stats.items():          # roll the box score into season totals
        player.season_stats.update(line)
        player.games_played += 1
        # Box-score participation is real game experience. Talent can carry a young player,
        # but repeated live reps make future performances steadier.
        if hasattr(player, "add_game_experience"):
            player.add_game_experience(3)
    return sim


_IMPORTANCE = {"National Championship": 0, "NP Semifinal": 1, "NP Quarterfinal": 2, "NP First Round": 3,
               "Conference Championship": 4, "Bowl": 5}


def matchup_order(games):
    """Biggest games first — in the postseason, the playoff before the bowls,
    and bowls in order of their tier and date."""
    def key(g):
        imp = _IMPORTANCE.get(g.game_type, 9)
        if g.game_type == "Bowl":
            return (imp, g.tier or 9, -(g.date.toordinal() if g.date else 0))
        return (imp, 0, -(g.home.team_ovr + g.away.team_ovr))
    return sorted(games, key=key)


def play_week(league, rng):
    """Fast-sims an entire week."""
    weekly_healing(league, league.week)
    league.week += 1
    games = league.schedule.get(league.week, [])
    import world_rules
    for g in games:
        g._injuries_enabled = world_rules.enabled(league, "injuries")
        simulate_game(g, rng)
    return games


# ─── Offseason ──────────────────────────────────────────────────────────────

class OffseasonReport:
    def __init__(self, year):
        self.year = year                 # the season that just ended
        self.graduated = []              # (team, player)
        self.developed = []              # (team, player, before, after)
        self.redshirted = 0
        self.cut = []                    # players who lost a roster spot
        self.portal = None               # PortalReport from the transfer window
        self.classes = {}                # team -> [recruits]
        self.recruiting = None           # ClassReport from signing day


def run_offseason(league, rng):
    """The whole offseason in one go (every mode but Commissioner, which runs it a stage per cycle)."""
    ctx = offseason_begin(league)
    for stage in OFFSEASON_STAGES:
        stage(league, rng, ctx)
    return ctx["report"]


def offseason_begin(league):
    """The context the stages share. Commissioner Mode keeps it on the league between cycles."""
    return {"report": OffseasonReport(league.year), "next_year": league.year + 1, "window": None,
            "interactive": False, "signing": None}


def off_carousel(league, rng, ctx):
    """Stage 1: the season is filed, everyone heals, coaches are judged, fired, hired, staffs rebuilt."""
    import archive
    archive.store_season(league)        # keep every game and box score before the new schedule replaces them
    report = ctx["report"]
    heal_all(league)                    # everyone is healthy by fall camp
    import compliance
    import world_rules
    if world_rules.enabled(league, "violations"):
        compliance.offseason_pre(league, rng)   # finals, APR, and the stretch where CAB cases move (before the carousel)
    import carousel
    if hasattr(league, "carousel") and world_rules.enabled(league, "carousel"):
        carousel.end_of_season(league, rng)          # coaches judged, fired, hired before the portal opens
        if any(t.coach is None for t in league.teams):
            carousel.fill_openings(league, rng)      # a head coach hired away late (as a coordinator): fill that job too
        report.carousel = league.carousel.get(league.year, [])
    _YEAR[0] = ctx["next_year"]


def off_awards(league, rng, ctx):
    import compliance, world_rules
    """Stage 2: the books close, awards, the draft, the Hall of Fame."""
    report = ctx["report"]
    _YEAR[0] = ctx["next_year"]
    import compliance
    import records
    records.close_season(league)                    # season records and career files, before the totals roll over
    import sos
    sos.snapshot(league)                            # the final strength-of-schedule table, kept for past seasons
    for team in league.teams + league.fcs_teams:    # season totals roll into career totals
        if not getattr(team, "fcs", False):
            # historical_records format: (year, wins, losses, conf_wins, conf_losses, achievements)
            team.historical_records.append((league.year, team.wins, team.losses, team.conf_wins, team.conf_losses,
                                            list(getattr(team, "achievements", [])), team.conference))
        for p in team.roster:
            for k, v in p.season_stats.items():
                if k.endswith("_long"):
                    p.career_stats[k] = max(p.career_stats[k], v)   # a career long is the longest, not the sum
                else:
                    p.career_stats[k] += v
            if sum(p.season_stats.values()) > 0:
                p.yearly_stats[league.year] = Counter(p.season_stats)
            p.career_games += p.games_played
            p.__dict__.setdefault("yearly_games", {})[league.year] = p.games_played
            p.season_stats.clear()
            p.games_played = 0

    import dynasty
    dynasty.update(league)                          # brand and legacy move with the season just played
    dynasty.shocks(league, rng)                     # booster windfalls
    if world_rules.enabled(league, "violations"):
        compliance.offseason_post(league)               # vacated wins come off the books
    import recruit_plus
    recruit_plus.pwo_scholarships(league)           # walk-ons who became players earn a scholarship
    recruit_plus.pipeline_offseason(league)         # high-school ties fade a little every year

    # Awards season and the Pro League Draft read the finished season. Underclassmen who
    # declare leave now; drafted seniors leave with everybody else at graduation.
    import draft
    report.awards = draft.awards_season(league)
    report.draft = draft.run_draft(league, rng)
    records.after_awards(league, report.awards, report.draft)   # honors and draft picks into the career files
    import halloffame
    report.hall = halloffame.offseason(league)      # the ballot, the vote, and every program's class


def off_winter(league, rng, ctx):
    """Stage 3: seniors graduate, everyone develops, redshirts; NIL raises are settled."""
    report = ctx["report"]
    next_year = ctx["next_year"]
    _YEAR[0] = next_year
    for team in league.teams:
        starters = {id(p) for group in team.starters().values() for p in group}

        # 1. Seniors graduate.
        for p in [p for p in team.roster if p.year == 3]:
            report.graduated.append((team, p))
            team.roster.remove(p)

        # 2. Everyone else develops (base skills, then proficiency) — the offseason's two-thirds;
        #    the other third happened week by week during the season (development.develop_in_season).
        for p in team.roster:
            before = p.overall
            develop_player(p, team.coach, facilities.training_rating(team), rng, season_year=next_year, team=team,
                           scale=1.0 if getattr(league.recruiting, "compressed", False) else None)
                                                    # world-building years have no Saturdays: the whole year here
            report.developed.append((team, p, before, p.overall))

        # 3. Class advancement / redshirts. A preseason protection plan is explicit;
        #    otherwise the old staff-driven freshman redshirt behavior remains.
        for p in team.roster:
            played = getattr(p, "yearly_games", {}).get(league.year, 0)
            planned = p.__dict__.get("redshirt_plan") == league.year
            auto = p.year == 0 and id(p) not in starters and rng.random() < REDSHIRT_ODDS
            if not p.redshirt and played <= 4 and (planned or auto):
                p.redshirt = True                       # four-game rule: preserve the class year
                p.events[league.year].append(f"Redshirted (played {played} game{'s' if played != 1 else ''})"
                                             if played else "Redshirted")
                report.redshirted += 1
            else:
                if planned and played > 4:
                    p.events[league.year].append(f"Redshirt plan burned after playing {played} games")
                p.year = min(3, p.year + 1)
            p.__dict__.pop("redshirt_plan", None)

    # 4. The transfer portal opens first, league-wide. Staffs find out who is
    #    leaving before they sign anybody, which is the whole point: a team that
    #    loses its quarterback in December can still go get one.
    league.nil_rolled = True            # budgets now read the roster as next season's roster
    window = None
    import hotseat
    interactive_offseason = getattr(league, "mode", None) == "career" and (getattr(league, "user_team", None) is not None
                                                      or hotseat.humans(league)) \
            and not getattr(league, "autosim", False)
    if interactive_offseason:
        window = getattr(league, "portal_hook", None)
        if window is not None and hotseat.state(league) is not None:
            inner = window
            def window(lg, rep, _inner=inner):
                def one():
                    if hotseat.seat_team(lg, hotseat.current(lg)) is not None:
                        hotseat.maybe_pass(lg, "THE TRANSFER PORTAL IS OPEN")
                        _inner(lg, rep)
                hotseat.each_seat(lg, one, simultaneous=True)
    ctx["window"], ctx["interactive"] = window, interactive_offseason
    import personalities
    import world_rules
    if world_rules.enabled(league, "nil_pressure"):
        personalities.resolve_demands(league, rng)          # NIL raises: paid, or he's thinking portal


def off_portal(league, rng, ctx):
    """Stage 4: the transfer portal, start to finish."""
    report = ctx["report"]
    _YEAR[0] = ctx["next_year"]
    if ctx["interactive"]:
        import offseason_cycle
        report.portal = offseason_cycle.run_winter_portal(league, rng, ctx["next_year"], window=ctx["window"])
    else:
        report.portal = run_portal(league, rng, ctx["next_year"], window=ctx["window"])
    if getattr(league, "mode", None) == "career" and not getattr(league, "autosim", False):
        try:
            import offseason_cal
            offseason_cal.portal_complete(league, report.portal)
        except Exception:
            raise


def off_signing(league, rng, ctx):
    """Stage 5: the last recruiting push and National Signing Day."""
    report = ctx["report"]
    next_year = ctx["next_year"]
    _YEAR[0] = next_year
    # 5. The last recruiting push now lives on the offseason clock. Recruiting remains
    #    open through Week 7; Week 8 is the real signing deadline.
    if ctx["interactive"]:
        import offseason_cycle
        offseason_cycle.run_recruiting_finish(league, league.recruiting, rng)
        offseason_cycle.signing_week(league)
    signing = signing_day(league, league.recruiting, rng, next_year)
    report.recruiting = signing
    ctx["signing"] = signing
    import recruit_plus
    recruit_plus.sign_pwos(league, league.recruiting, rng, next_year)   # your preferred walk-ons join
    import carousel
    if hasattr(league, "carousel"):
        carousel.record_classes(league, signing)


def off_arrivals(league, rng, ctx):
    """Stage 6: the new class arrives, then late transfers and walk-ons fill whatever is still short."""
    report = ctx["report"]
    next_year = ctx["next_year"]
    _YEAR[0] = next_year
    signing = ctx["signing"]
    for team in league.teams:
        team.reset_record()
        signed = attach_class(team, signing.classes.get(team, []), league.recruiting, rng, next_year)
        fill_gaps(team, report.portal, rng)          # a late transfer beats a walk-on
        report.classes[team] = signed + sign_class(team, rng, next_year)


def off_rollover(league, rng, ctx):
    """Stage 7: rosters trimmed to scholarship size, realignment, and the new year begins."""
    report = ctx["report"]
    next_year = ctx["next_year"]
    _YEAR[0] = next_year
    for team in league.teams:
        report.cut += trim_to_template(team)        # and the roster stays at scholarship size

    # 7. Conference realignment: announced moves take effect, TV deals renew, leagues shop.
    import realignment, world_rules
    report.realignment = (realignment.offseason(league, rng, next_year)
                          if world_rules.enabled(league, "realignment") else [])

    league.year = next_year
    league.week = 0
    league.nil_rolled = False
    league.build_fcs()                  # new FCS rosters every year
    league.schedule = build_schedule(league, rng)


OFFSEASON_STAGES = (off_carousel, off_awards, off_winter, off_portal, off_signing, off_arrivals, off_rollover)
