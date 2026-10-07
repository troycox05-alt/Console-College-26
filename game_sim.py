"""
game_sim.py — Runs a full game, snap by snap.

Owns the game state (score, clock, possession, down & distance, timeouts),
asks both head coaches for their calls each snap, hands the calls to the
engine, and applies the result: yards, first downs, turnovers, scores,
kicks, clock runoff (tempo, clock-stopping plays, timeouts), halftime and
college overtime. Keeps a full box score as it goes.
"""
from collections import Counter

from engine import field_goal, kickoff, punt, resolve
from playbook import (DEF_CALLS, OFFENSE_SCHEMES, _pick_play, choose_defense, choose_offense, is_hurry,
                      is_milking, score_diff, two_point_decision)
from injuries import SEASON, injury_chance, is_available, roll_severity
from models import POSITIONS
from momentum import Momentum
from traits import mod as trait_mod
from playbook import GamePlan
import sideline

DEPTH_NEED = {"QB": 1, "RB": 2, "WR": 4, "TE": 2, "OL": 5, "DL": 4, "LB": 3, "CB": 4, "S": 2, "K": 1, "P": 1}
OFFENSE_POS = ("QB", "RB", "WR", "TE", "OL")

QUARTER = 900


def build_profile(p):
    """Game composites from applied fundamentals (fundamental x proficiency)."""
    a = p.applied
    s, sp, q, iq, pm = a("strength"), a("speed"), a("quickness"), a("iq"), a("playmaker")
    return {
        "block": s * .5 + q * .2 + iq * .3,
        "pass_block": s * .4 + q * .35 + iq * .25,
        "rush": s * .35 + q * .4 + sp * .15 + pm * .1,
        "run_stop": s * .5 + q * .25 + iq * .25,
        "tackle": s * .35 + iq * .25 + q * .2 + sp * .2,
        "fit": iq * .4 + sp * .25 + q * .2 + s * .15,
        "cover": sp * .35 + q * .3 + iq * .25 + pm * .1,
        "route": q * .4 + sp * .3 + iq * .2 + pm * .1,
        "catch": pm * .5 + iq * .2 + q * .15 + s * .15,
        "elusive": q * .45 + pm * .35 + sp * .2,
        "power": s * .7 + pm * .3,
        "vision": iq * .7 + pm * .3,
        "accuracy": iq * .35 + pm * .35 + q * .15 + s * .15,
        "arm": s,
        "pocket": iq * .6 + q * .4,
        "security": s * .5 + iq * .5,
        "kick_power": s,
        "kick_acc": iq * .5 + pm * .5,
        "speed": sp, "quick": q, "iq": iq, "strength": s, "playmaker": pm,
    }


class _Score(dict):
    """The scoreboard. Every change is stamped with the quarter and clock, so a
    finished game remains a story (comebacks, lead changes, the last-second winner)."""

    def __init__(self, sim, start):
        super().__init__(start)
        self._sim = sim

    def __setitem__(self, team, value):
        super().__setitem__(team, value)
        s = getattr(self, "_sim", None)
        if s is not None and len(self) == 2:
            s.timeline.append((s.quarter, s.clock, self.get(s.home, 0), self.get(s.away, 0)))

    def __reduce__(self):
        return (dict, (dict(self),))              # saves as a plain dict


class GameSim:
    def __init__(self, game, rng, narrator=None, persist_injuries=True):
        self.game = game
        self.rng = rng
        self.narr = narrator
        self.ctl = getattr(game, "controller", None)   # you, calling the plays (coach_mode.Controller)
        self.last_runoff, self.last_runoff_q = 0, 1
        self.persist_injuries = persist_injuries
        self.home, self.away = game.home, game.away
        self.teams = (self.home, self.away)
        self.neutral = getattr(game, "neutral", False)
        import facilities
        self.momentum = Momentum(self.home, self.away, self.neutral,
                                 noise=facilities.crowd_noise(game) if getattr(game, "attendance", None) else None)
        self.plan = {t: GamePlan(t.coach) for t in self.teams}
        self.out = set()                 # injured for the rest of this game
        self.shaken = {}                 # player -> snaps until he returns
        self.contacts = []
        self.injuries = []               # (quarter, clock, team, player, desc, severity, games)
        self.depth, self.backup_depth = {}, {}
        self.sub_order = {t: {} for t in self.teams}       # in-game manual depth overrides by position
        self.manual_mass_subs = {t: False for t in self.teams}
        for t in self.teams:
            self._rebuild_depth(t)
        self.rested = set()
        self.rest = {}
        # A backup QB promised a role (the inbox's "build him a package") gets a few
        # real snaps a game: early downs, not in a two-minute drill.
        self.pkg, self.pkg_snaps, self._pkg_team = {}, {}, None
        for t in self.teams:
            starter = self.depth[t]["QB"][0] if self.depth[t]["QB"] else None
            for p in t.players_at("QB"):
                if p is not starter and getattr(p, "promise", None) == "role" and is_available(p):
                    self.pkg[t] = p
                    break
        self._prof = {}
        self._base = {}
        self._exp_form = {}
        # Game-day form: some Saturdays a team just has it (or doesn't).
        # Steady rosters show up the same every week; streaky ones don't. A team
        # full of clutch players is a different team in the last five minutes.
        self.form, self.clutch, self.flag_mult = {}, {}, {}
        for t in self.teams:
            starters = [p for grp in t.starters().values() for p in grp]
            # Experience does not make a player more talented; it narrows his Saturday range.
            # Raw players can still hit a huge positive day, but are much more likely to swing.
            for p in starters:
                exp = getattr(p, "experience_rating", max(1, min(99, 8 + getattr(p, "career_games", 0) * 4)))
                sigma = 2.9 - 1.9 * (exp / 99.0)
                self._exp_form[id(p)] = max(-5.0, min(5.0, rng.gauss(0, sigma)))
            spread = sum(trait_mod(p, "form") for p in starters) / max(1, len(starters))
            self.form[t] = max(-6.0, min(6.0, rng.gauss(0, 2.6 * spread)))
            if t.coach is not None:
                import coach_profile
                self.form[t] += coach_profile.delta(t.coach, "motivation") / 22 + trait_mod(t.coach, "motivation", 0.0)
                if not getattr(t, "fcs", False):
                    # the head coach himself: an elite one is worth about three points a week over an
                    # average one, a poor one costs about two
                    self.form[t] += max(-1.6, min(1.8, (t.coach.overall - 70) / 13))
                self.flag_mult[t] = max(0.65, min(1.45, (1 - coach_profile.delta(t.coach, "discipline") / 120) * trait_mod(t.coach, "discipline", 1.0)))
            else:
                self.flag_mult[t] = 1.0
            lift = sum(trait_mod(p, "clutch") - 1 for p in starters) / max(1, len(starters))
            self.clutch[t] = max(-1.9, min(1.9, lift * 36))
            self.form[t] += self._team_lift(t, starters)
            import personalities
            self.form[t] += personalities.chemistry_lift(t)     # the locker room, up to about a point either way
            import morale
            self.form[t] += morale.team_lift(t, starters)       # how the starters feel, about half a point
            import skills
            if skills.user_coach_of(t) is not None:            # your coaching tree
                opp_t = self.home if t is self.away else self.away
                from carousel import PRIMARY_RIVAL
                ranked = (getattr(self.game, "ranks", {}) or {}).get(opp_t)
                rival = PRIMARY_RIVAL.get(t.school) == opp_t.school or PRIMARY_RIVAL.get(opp_t.school) == t.school
                if skills.team_has(t, "big_game") and (ranked or rival):
                    self.form[t] += 0.5
                if skills.team_has(t, "stadium_exp") and t is self.home and not self.neutral:
                    self.form[t] += 0.3
                import difficulty
                self.form[t] += difficulty.form(t)             # how hard you chose the job to be
            if t.coach is not None and not getattr(t, "fcs", False):
                self.form[t] += (getattr(t.coach, "fit_with", None) or {}).get(t.school, 0.0)   # coach and place
            if not self.neutral and not getattr(self.home, "fcs", False):
                import stadium                                  # the building: the home locker room, the visitors' one
                self.form[t] += stadium.home_edge(self.home) if t is self.home else -stadium.visitor_penalty(self.home)
            # The practice week (your team only): what you worked on, and what you said Thursday.
            prep = getattr(t, "week_prep", None) or {}
            if prep:
                self.form[t] += prep.get("lift", 0.0)
                self.clutch[t] = max(-1.6, min(2.2, self.clutch[t] + prep.get("clutch", 0.0)))
            other = self.home if t is self.away else self.away
            self.form[t] += (getattr(other, "week_prep", None) or {}).get("opp_lift", 0.0)   # bulletin-board material
            # the season's run of form: a field goal, at most
            import season as _season
            import team_momentum
            self.form[t] += team_momentum.lift(t, other, _season.league_year(),
                                               bool((getattr(self.game, "ranks", {}) or {}).get(other)))
        # Rivalry games: throw out the records. The underdog plays above itself and the day is
        # less predictable for both sides — upsets come a little more often, never automatically.
        self.rivalry = False
        try:
            import rivalries
            self.rivalry = rivalries.is_rivalry(self.home, self.away)
        except Exception:                                       # noqa: BLE001
            self.rivalry = False
        if self.rivalry and not (getattr(self.home, "fcs", False) or getattr(self.away, "fcs", False)):
            dog, fav = sorted((self.home, self.away), key=lambda x: x.team_ovr)
            gap = fav.team_ovr - dog.team_ovr
            self.form[dog] += min(1.9, 0.6 + gap * 0.09)
            for t in self.teams:
                self.form[t] += rng.gauss(0, 1.2)
        import weather                                          # the day: rain, wind, cold, heat, altitude
        self.wx = getattr(game, "wx", None) or weather.truth(game)
        for t in self.teams:
            self.form[t] += weather.form_shift(self, t)
        self._wx_said = 0
        self._home_ids = {id(p) for p in self.home.roster}
        import skills
        self._fp = {t: skills.team_has(t, "field_position") for t in self.teams}
        self.quarter, self.clock = 1, QUARTER
        self.timeline = []               # (quarter, clock, home score, away score) after every change
        self.score = _Score(self, {t: 0 for t in self.teams})
        self.line = {t: [] for t in self.teams}
        self.timeouts = {t: 3 for t in self.teams}
        self.stats = {}
        self.pending = []
        self.statbook_version = 2          # v40.2: explosives/success/red-zone/fourth-down tracking
        self.team_stats = {t: Counter() for t in self.teams}
        self.scoring = []
        self.quarter, self.clock = 1, QUARTER
        self.offense = self.defense = None
        self.yardline, self.down, self.togo = 25, 1, 10
        self.drive = None
        self.drives = []
        self.ot_round = 0
        self.possession_over = False
        self.ot_walkoff = False
        self.second_half_kicker = None
        self.plays_run = 0
        self.last_kind = None
        sideline.attach(self)            # orders, the game plan, the people on the sideline

    def _team_lift(self, team, starters):
        """Leaders, road warriors, rivalry guys, November players — and a coach
        who owns the big game. Summed across the starters (and the head coach),
        capped so no locker room is worth more than a point and a half."""
        opp = self.other(team)
        keys = ["team_lift"]
        if not self.neutral:
            keys.append("home" if team is self.home else "road")
        from carousel import PRIMARY_RIVAL
        if PRIMARY_RIVAL.get(team.school) == opp.school or PRIMARY_RIVAL.get(opp.school) == team.school:
            keys.append("rival")
        week = getattr(self.game, "week", 0) or 0
        if week >= 10:
            keys.append("late")
        elif 1 <= week <= 3:
            keys.append("early")
        ranks = getattr(self.game, "ranks", {})
        if ranks.get(opp):
            keys.append("big_game")
        elif getattr(opp, "fcs", False) or (not ranks.get(opp) and opp.team_ovr <= team.team_ovr - 6):
            keys.append("weak")                       # a game he's supposed to win, and does it big
        total = sum(trait_mod(p, k, 0.0) for p in starters for k in keys)
        if team.coach is not None:
            total += sum(trait_mod(team.coach, k, 0.0) for k in keys)
        return max(-1.8, min(1.8, total))

    def __getstate__(self):
        """What a save keeps of a finished game: the box score, not the broadcast
        booth or your headset (neither survives a save, and neither is needed)."""
        state = self.__dict__.copy()
        state["score"] = dict(self.score)          # the live scoreboard's hook isn't saved
        state["narr"] = None
        state["ctl"] = None
        for scratch in ("_prof", "_base", "contacts", "pending", "rested", "shaken", "out"):
            state.pop(scratch, None)              # per-snap working memory, rebuilt if ever needed
        # Object ids don't survive a save, so remember the home side by the players themselves.
        seen = set(self.stats) | {i[3] for i in self.injuries}
        state["_home_players"] = [p for p in seen if id(p) in self._home_ids]
        state.pop("_home_ids", None)
        return state

    def __setstate__(self, state):
        home = state.pop("_home_players", [])
        self.__dict__.update(state)
        self._home_ids = {id(p) for p in home}
        self._prof, self._base = {}, {}
        self.contacts, self.pending = [], []
        self.rested, self.out, self.shaken = set(), set(), {}
        self.rest, self._depth_cache = {}, {}

    # ── helpers ───────────────────────────────────────────────────────────
    def other(self, team):
        return self.away if team is self.home else self.home

    def _rebuild_depth(self, team):
        """Healthy players by position, best first; emergency fill-ins if a room runs dry."""
        def ok(p):
            # A preseason redshirt plan protects the player from ordinary depth-chart
            # usage. Emergency fill-ins below can still break glass if the room runs dry.
            protected = bool(p.__dict__.get("redshirt_plan"))
            return is_available(p) and not protected and p not in self.out and p not in self.shaken and not sideline.is_benched(self, p)
        depth = {pos: [p for p in team.players_at(pos) if ok(p)] for pos in POSITIONS}
        for pos, need in DEPTH_NEED.items():
            if len(depth[pos]) < need:
                side = OFFENSE_POS if pos in OFFENSE_POS else tuple(x for x in POSITIONS if x not in OFFENSE_POS)
                spare = [p for q in side if q != pos for p in depth[q][DEPTH_NEED.get(q, 1) + 1:]]
                spare += [p for q in POSITIONS if q not in side for p in depth[q][DEPTH_NEED.get(q, 1):]]
                spare.sort(key=lambda p: -p.proficiency.get(pos, 0) * p.overall)
                for p in spare:
                    if len(depth[pos]) >= need:
                        break
                    if p not in depth[pos]:
                        depth[pos].append(p)
        # Still short? A roster this thin plays guys both ways, then plays guys who are hurt.
        # A lineup is never allowed to come up short (the play engine needs every spot filled).
        healthy = [p for p in team.roster if ok(p)]
        everyone = list(team.roster)
        for pos, need in DEPTH_NEED.items():
            if len(depth[pos]) >= need:
                continue
            side = OFFENSE_POS if pos in OFFENSE_POS else tuple(x for x in POSITIONS if x not in OFFENSE_POS)
            # nobody lines up in two spots on the same side of the ball
            on_field = {id(p) for q in side for p in depth[q][:DEPTH_NEED.get(q, 1)]}
            for pool in (healthy, everyone):
                cands = sorted((p for p in pool if p not in depth[pos] and id(p) not in on_field),
                               key=lambda p: -p.proficiency.get(pos, 0) * p.overall)
                for p in cands:
                    if len(depth[pos]) >= need:
                        break
                    depth[pos].append(p)
                    on_field.add(id(p))
                if len(depth[pos]) >= need:
                    break
            while depth[pos] and len(depth[pos]) < need:              # a roster smaller than a lineup
                depth[pos].append(depth[pos][len(depth[pos]) % len(depth[pos])])
        # Preserve any manual in-game swaps across injuries/rebuilds. Missing or injured players simply fall through.
        orders = getattr(self, "sub_order", {}).get(team, {})
        for pos, wanted in orders.items():
            if pos not in depth:
                continue
            keep = [p for p in wanted if p in depth[pos]]
            depth[pos] = keep + [p for p in depth[pos] if p not in keep]
        self.depth[team] = depth
        self.backup_depth[team] = {pos: (lst[len(lst) // 2:] + lst[:len(lst) // 2]) if pos not in ("K", "P") else lst
                                   for pos, lst in depth.items()}
        self.__dict__.setdefault("_depth_cache", {}).clear()

    def qb_of(self, team):
        """The quarterback on the field: the backup once the second team is in."""
        if getattr(self, "_pkg_team", None) is team:
            return self.pkg[team]
        if getattr(self, "manual_mass_subs", {}).get(team, False) or self.rest.get(team, 0) >= 2:
            return self.backup_depth[team]["QB"][0]
        return self.depth[team]["QB"][0]

    def set_mass_subs(self, team, enabled=True):
        """Put the second/third unit on the field until the user turns mass subs back off."""
        self.manual_mass_subs[team] = bool(enabled)
        if not enabled:
            self.rest[team] = 0
        self.__dict__.setdefault("_depth_cache", {}).clear()

    def switch_players(self, team, pos, first, second):
        """Swap two players in one position room for the remainder of this game."""
        if pos not in self.depth.get(team, {}):
            return False
        room = list(self.depth[team][pos])
        if first not in room or second not in room or first is second:
            return False
        i, j = room.index(first), room.index(second)
        room[i], room[j] = room[j], room[i]
        self.sub_order.setdefault(team, {})[pos] = room
        self._rebuild_depth(team)
        return True

    def boost(self, team):
        """Game-day form + home crowd + momentum, in rating points."""
        base = self.form[team] + self.momentum.effect(team) + sideline.team_boost(self, team)
        if self.quarter >= 4 and abs(self.score[self.home] - self.score[self.away]) <= 8:
            base += self.clutch[team]        # the fourth quarter of a one-score game
        if self.quarter >= 4 and self.score[team] > self.score[self.other(team)] and getattr(self, "_fp", {}).get(team):
            base += 0.4                      # Field Position (coaching tree)
        return base

    def prof(self, p):
        """His game skills right now: the base profile, this moment's sub-proficiencies
        (inside run, pass, after the catch... — set by the play as `_ctx`), plus form."""
        team = self.home if id(p) in self._home_ids else self.away
        exp = getattr(p, "experience_rating", max(1, min(99, 8 + getattr(p, "career_games", 0) * 4)))
        exp_form = self._exp_form.get(id(p), 0.0)
        composure = 0.0
        if self.quarter >= 4 and abs(self.score[self.home] - self.score[self.away]) <= 8:
            composure = (exp - 50) / 55.0   # roughly -0.9 raw to +0.9 veteran in pressure moments
        b = round((self.boost(team) + sideline.player_adj(self, p) + exp_form + composure) * 4) / 4
        ctx = self.__dict__.get("_ctx")
        key = (id(p), b, ctx)
        cached = self._prof.get(key)
        if cached is None:
            base = self._base.get(id(p))
            if base is None:
                base = self._base[id(p)] = build_profile(p)
            vals = dict(base)
            if ctx is not None:
                import subprof
                for sub, comps in subprof.CTX.get(ctx, {}).get(p.position, ()):
                    r = subprof.ratio(p, sub)
                    for c in comps:
                        vals[c] = vals[c] * r
            cached = self._prof[key] = {k: v + b for k, v in vals.items()}
        return cached

    # ── injuries ──────────────────────────────────────────────────────────
    def touch(self, p, weight=1.0):
        self.contacts.append((p, weight))

    def team_of(self, p):
        return self.home if id(p) in self._home_ids else self.away

    def check_injuries(self):
        if not getattr(self.game, "_injuries_enabled", True):
            self.contacts.clear()
            return
        if not self.contacts:
            return
        seen = set()
        turf = 1.0
        if not self.neutral and not getattr(self.home, "fcs", False):
            import stadium
            turf = stadium.injury_mult(self.home)              # worn turf hurts people; good grass saves them
        for p, w in self.contacts:
            if id(p) in seen or p in self.out or p in self.shaken:
                continue
            seen.add(id(p))
            if sideline.aggravated(self, p):                   # playing hurt, and he made it worse
                continue
            if self.rng.random() < injury_chance(p, w * turf):
                self.injure(p)
        self.contacts.clear()

    def injure(self, p):
        team = self.team_of(p)
        severity, games, desc = roll_severity(self.rng)
        starter = p in [x for pos, n in DEPTH_NEED.items() for x in self.depth[team][pos][:min(n, 3)]]
        if severity == "shaken":
            self.shaken[p] = self.rng.randint(3, 8)
        else:
            self.out.add(p)
            if games > 0 and self.persist_injuries:
                p.inj_games, p.inj_desc, p.inj_week = games, desc, self.game.week
        self.injuries.append((self.quarter, self.clock, team, p, desc, severity, games))
        self._rebuild_depth(team)
        self._n("injury", p, team, desc, severity, games, starter)
        if severity != "shaken" and starter and not sideline.trainer(self, p, team, severity, games, desc):
            self.shaken[p] = self.rng.randint(2, 4)          # taped up: back in a few snaps, hobbled
            self.out.discard(p)
            self._rebuild_depth(team)

    def _shaken_tick(self):
        back = []
        for p in list(self.shaken):
            self.shaken[p] -= 1
            if self.shaken[p] <= 0:
                del self.shaken[p]
                back.append(p)
        for p in back:
            self._rebuild_depth(self.team_of(p))
            self._n("player_returns", p)

    # ── momentum ──────────────────────────────────────────────────────────
    def swing(self, team, event):
        margin = self.score[team] - self.score[self.other(team)]
        before = self.momentum.leader()
        shift = self.momentum.swing(team, event, margin)
        after = self.momentum.leader()
        if (after is not None and after is not before) or abs(shift) >= 20:
            self._n("momentum", team, event)

    def stat(self, p, key, n=1):
        self.pending.append((p, key, n, False))

    def stat_max(self, p, key, v):
        self.pending.append((p, key, v, True))

    def discard_stats(self):
        self.pending.clear()

    def commit_stats(self):
        for p, key, n, is_max in self.pending:
            c = self.stats.get(p)
            if c is None:
                c = self.stats[p] = Counter()
            if is_max:
                if key not in c or n > c[key]:
                    c[key] = n
            else:
                c[key] += n
        self.pending.clear()

    def _n(self, method, *args):
        if self.narr is not None:
            getattr(self.narr, method)(self, *args)

    def spot(self, yardline=None, team=None):
        yl = self.yardline if yardline is None else yardline
        team = team or self.offense
        if yl == 50:
            return "midfield"
        if yl < 50:
            return f"{team.abbr} {yl}"
        return f"{self.other(team).abbr} {100 - yl}"

    # ── Substitutions: backups come in a wave at a time, and go back out ──
    # How safe a lead is depends on how much game is left: roughly 8.5 points for
    # every possession the other team still gets. Past that, the second team
    # rotates in at the skill spots and on defense; well past it the backup
    # quarterback plays; far past it, the whole third string. If the lead shrinks,
    # the starters go back in.
    SAFE_PER_POSS = 8.5

    def rest_level(self, team):
        if getattr(self, "manual_mass_subs", {}).get(team, False):
            self.rest[team] = 3
            return 3
        if self.quarter > 4:
            return 0
        secs = (4 - self.quarter) * 900 + self.clock
        opp_poss = secs / 330 + 0.5
        lead = self.score[team] - self.score[self.other(team)]
        safe = self.SAFE_PER_POSS * opp_poss
        target = 3 if lead >= safe + 16 else 2 if lead >= safe + 8 else 1 if lead >= safe else 0
        # Nobody empties the bench in a one- or two-score game, however little time is left:
        # that's the victory formation, not garbage time.
        target = min(target, 0 if lead < 17 else 1 if lead < 21 else 2 if lead < 25 else 3)
        cur = self.rest.get(team, 0)
        if target < cur and lead >= safe - 4 + (cur - 1) * 8:
            target = cur                                   # don't yo-yo on one score
        if target != cur:
            self.rest[team] = target
            if target > cur:
                self._n("starters_out" if target == 3 else "second_team_in", team, target)
            else:
                self._n("starters_back", team, target)
        return self.rest.get(team, 0)

    def resting(self, team):
        """Any backups in (the rotation and sportsmanship code read this)."""
        return self.rest_level(team) >= 1

    def lineup_depth(self, team):
        if getattr(self, "_pkg_team", None) is team:                       # the backup's package snap
            pq = self.pkg[team]
            d = dict(self.depth[team])
            d["QB"] = [pq] + [p for p in d["QB"] if p is not pq]
            return d
        lvl = self.rest_level(team)
        if lvl == 0:
            return self.depth[team]
        if lvl >= 3:
            return self.backup_depth[team]
        key = (id(team), lvl)
        cache = self.__dict__.setdefault("_depth_cache", {})
        if key not in cache:
            d = {pos: list(lst) for pos, lst in self.depth[team].items()}
            for pos in ("RB", "WR", "TE", "DL", "LB", "CB", "S"):
                lst = d[pos]
                n = {"WR": 2, "DL": 2, "LB": 1, "CB": 1, "S": 1}.get(pos, 1)
                bench = lst[len(lst) // 2:]
                for i in range(min(n, len(bench))):          # the second team takes some of the snaps
                    if bench[i] not in lst[:i + 1]:
                        lst.remove(bench[i])
                        lst.insert(i, bench[i])
            if lvl >= 2:
                d["QB"] = self.backup_depth[team]["QB"]
                ol = d["OL"]
                bench = ol[5:]
                for i in range(min(2, len(bench))):
                    ol.remove(bench[i])
                    ol.insert(i, bench[i])
            cache[key] = d
        return cache[key]

    @staticmethod
    def describe_td(r):
        who = r.carrier
        if who is None:
            return "Touchdown"
        name = f"{who.first_name[0]}. {who.last_name}"
        if r.kind == "pass" and r.passer is not None:
            return f"{name} {r.yards} yd pass from {r.passer.first_name[0]}. {r.passer.last_name}"
        return f"{name} {r.yards} yd run"

    def late_half(self):
        return self.quarter in (2, 4) and self.clock <= 120

    def clock_tick(self, seconds):
        if self.quarter > 4 or seconds <= 0:
            return
        used = min(self.clock, int(seconds))
        self.clock -= used
        if self.offense is not None:
            self.team_stats[self.offense]["top"] += used

    # ── game ──────────────────────────────────────────────────────────────
    def play(self):
        self._n("pregame")
        toss = self.rng.choice(self.teams)          # winner defers: kicks now, receives after half
        self.second_half_kicker = self.other(toss)
        self._n("coin_toss", toss)
        self.do_kickoff(toss)
        while self.quarter <= 4:
            if self.clock <= 0:
                self.end_quarter()
                continue
            self.run_down()
        if self.score[self.home] == self.score[self.away]:
            self.overtime()
        self.game.home_score = self.score[self.home]
        self.game.away_score = self.score[self.away]
        self._n("final")
        return self

    def end_quarter(self):
        for t in self.teams:
            self.line[t].append(self.score[t] - sum(self.line[t]))
        q = self.quarter
        self._n("quarter_end")
        if q == 2:
            self.end_drive("End of Half")
            self.quarter, self.clock = 3, QUARTER
            self.timeouts = {t: 3 for t in self.teams}
            import weather
            for t in self.teams:
                self.form[t] += weather.form_shift(self, t, second_half=True)   # the heat, the altitude
                if t.coach is not None:
                    import coach_profile
                    self.form[t] += coach_profile.delta(t.coach, "adjustments") / 24 + trait_mod(t.coach, "adjust", 0.0)
            self.momentum.halftime()
            for plan in self.plan.values():
                plan.halftime()
            import skills
            for t in self.teams:                          # Schemer (coaching tree): their adjustments blunted
                if skills.team_has(self.other(t), "schemer"):
                    p = self.plan[t]
                    p.iq *= 0.5
                    p.def_iq = getattr(p, "def_iq", p.iq) * 0.5
            self._n("halftime")
            if self.game.__dict__.get("halftime_team") is not None:
                import halftime
                halftime.ask_coach(self)              # your locker room: the adjustment and the message
            self._weather_turn()
            self.do_kickoff(self.second_half_kicker)
        elif q == 4:
            self.end_drive("End of Game")
            self.quarter = 5
        else:
            self.quarter, self.clock = q + 1, QUARTER
            if self.quarter == 4:
                sideline.late_returns(self)                   # the ones you held back for a close fourth
        if self.quarter in (2, 4) and q in (1, 3):
            self._weather_turn()

    def _weather_turn(self):
        """The weather changed with the quarter: tell the booth (if there is one)."""
        wx = getattr(self, "wx", None)
        if not wx or wx.get("indoor") or self.narr is None or not hasattr(self.narr, "weather_turn"):
            return
        a, b = wx["q"][self.quarter - 2], wx["q"][self.quarter - 1]
        change = None
        if b["p"] and not a["p"]:
            change = "start"
        elif a["p"] and not b["p"]:
            change = "stop"
        elif b["p"] > a["p"]:
            change = "harder"
        elif a["type"] != b["type"] and b["p"]:
            change = "turn"
        elif b["wind"] - a["wind"] >= 7:
            change = "wind"
        elif a["temp"] - b["temp"] >= 7:
            change = "colder"
        if change:
            self.narr.weather_turn(self, change, b)

    def _lightning_check(self):
        """Thunderstorms: a lightning delay stops the game (30 minutes after every strike)."""
        d = (self.wx or {}).get("delay")
        if not d or d.get("done") or self.quarter != d["q"] or self.clock > d["clock"]:
            return
        d["done"] = True
        self.momentum.halftime()                    # everybody goes to the locker room; the building resets
        if self.narr is not None and hasattr(self.narr, "weather_delay"):
            self.narr.weather_delay(self, d["mins"])

    # ── possessions & drives ──────────────────────────────────────────────
    def start_possession(self, team, yardline):
        sideline.on_new_drive(self)
        self.offense, self.defense = team, self.other(team)
        self.yardline = yardline
        self.down, self.togo = 1, min(10, 100 - yardline)
        self.drive = {"team": team, "start": yardline, "plays": 0, "q": self.quarter,
                      "clock": self.clock, "top0": self.team_stats[team]["top"], "red_zone": yardline >= 80}
        if yardline >= 80:
            self.team_stats[team]["red_zone_att"] += 1

    def end_drive(self, result):
        d = self.drive
        if d is None:
            return
        d["result"] = result
        d["yards"] = self.yardline - d["start"] if result not in ("Touchdown",) else 100 - d["start"]
        d["time"] = self.team_stats[d["team"]]["top"] - d["top0"]
        self.drives.append(d)
        self.drive = None
        self._n("drive_end", d)

    def change_possession(self, team, yardline):
        if self.quarter > 4:
            self.possession_over = True
            return
        self.start_possession(team, max(1, min(99, yardline)))

    # ── one snap ──────────────────────────────────────────────────────────
    def _package_check(self):
        """Maybe this snap is the backup QB's package snap."""
        self._pkg_team = None
        team = self.offense
        pq = self.pkg.get(team)
        if pq is None or pq in self.out or pq in self.shaken or self.pkg_snaps.get(team, 0) >= 5:
            return
        if self.depth[team]["QB"] and self.depth[team]["QB"][0] is pq:
            return                                       # he's the starter now anyway
        if self.down > 2 or self.quarter > 4 or is_hurry(self) or self.yardline >= 95:
            return
        if abs(score_diff(self)) <= 8 and self.quarter == 4:
            return                                       # the starter finishes close games
        if self.rng.random() < 0.07:
            self._pkg_team = team
            self.pkg_snaps[team] = self.pkg_snaps.get(team, 0) + 1

    def run_down(self):
        self._package_check()
        try:
            return self._run_down()
        finally:
            self._pkg_team = None

    def _run_down(self):
        if getattr(self, "wx", None) and self.wx.get("delay"):
            self._lightning_check()
        self.momentum.tick()
        if self.shaken:
            self._shaken_tick()
        action = choose_offense(self, self.rng)
        if self.ctl is not None and self.offense is self.ctl.team:
            mine = self.ctl.offense(self, action)
            if mine is not None:
                action = mine
            if self.down == 4 and getattr(self.ctl, "_fourth_asked", False):
                self.ctl._fourth_asked = False
                sideline.log_fourth(self, self.ctl, action, self.ctl._fourth_staff)
        if action[0] == "punt":
            return self.do_punt()
        if action[0] == "fg":
            return self.do_field_goal()
        if action[0] in ("fake_punt", "fake_fg"):
            return self.do_fake(action[0])
        _, call, personnel = action
        dcall = choose_defense(self, self.rng, personnel) if call.kind != "kneel" else DEF_CALLS["Goal Line"]
        if self.ctl is not None and self.defense is self.ctl.team and call.kind != "kneel":
            mine = self.ctl.defense(self, personnel, dcall)
            if mine is not None:
                dcall = mine
        before = (self.down, self.togo, self.yardline, self.quarter, self.clock)
        sideline.pre_snap(self)
        self._n("pre_snap", call, personnel, dcall)
        r = resolve(self, call, personnel, dcall)
        if getattr(r, "flag_option", None):
            sideline.flag_decision(self, r, before)          # accept or decline
        if call.kind != "kneel":
            sideline.challenge(self, r, before)              # the replay challenge
        self.commit_stats()
        self.plays_run += 1
        self.last_kind = call.kind
        if call.kind != "kneel" and not r.penalty:
            self.plan[self.offense].record_offense(call, dcall, before[0], before[1], r.yards, r.td, r=r,
                                                   yardline=before[2])
            self.plan[self.defense].record_defense(dcall, call.kind, r.yards, call=call, r=r, down=before[0],
                                                   togo=before[1], yardline=before[2])
        off, df = self.offense, self.defense
        self.apply(r, before)
        self._momentum_after(r, before, off, df)
        self.check_injuries()
        sideline.post_snap(self)
        sideline.after_snap(self, r, before, off)

    def _momentum_after(self, r, before, off, df):
        if r.penalty or r.kind == "kneel":
            return
        down, togo = before[0], before[1]
        if r.turnover:
            return                                  # handled where the turnover is applied
        if r.sack:
            self.swing(df, "sack")
        if r.td:
            return
        if any(tag == "trick" for tag, _ in r.color) and r.yards >= 10:
            self.swing(off, "trick_play")
        elif r.yards >= 40:
            self.swing(off, "explosive")
        elif r.yards >= 20:
            self.swing(off, "big_play")
        if down == 4:
            if r.yards >= togo:
                self.swing(off, "fourth_convert")
            else:
                self.swing(df, "goal_line_stand" if before[2] >= 95 else "fourth_stop")
        elif down == 3 and togo >= 7 and r.yards >= togo:
            self.swing(off, "third_long_convert")

    def apply(self, r, before):
        off, df = self.offense, self.defense
        ts = self.team_stats[off]
        self.clock_tick(r.duration)
        was_third = self.down == 3
        was_fourth = self.down == 4
        if self.drive:
            self.drive["plays"] += 1

        if r.penalty:
            name, team, yards, auto_first, replay = r.penalty
            if yards < 0 and -yards * 2 > self.yardline:
                yards = -(self.yardline // 2)
            if yards > 0 and yards * 2 > 100 - self.yardline:
                yards = (100 - self.yardline) // 2        # half the distance — at the 1, that's nothing
            self.yardline = max(1, min(99, self.yardline + yards))
            self.togo -= yards
            if auto_first or self.togo <= 0:
                self.down, self.togo = 1, min(10, 100 - self.yardline)
            self.team_stats[team]["penalties"] += 1
            self.team_stats[team]["pen_yds"] += abs(yards)
            self._n("play", r, before)
            return self.between_plays(stopped=True)

        if r.kind == "pass" and not r.sack:
            ts["pass_yds"] += r.yards
        elif r.sack:
            ts["sack_yds"] += r.yards
            ts["rush_yds"] += r.yards             # ...and counts against team rushing, as in the NCAA book
        elif r.kind in ("run", "kneel"):
            ts["rush_yds"] += r.yards             # kneels count as rushes, as in the NCAA book
        ts["total_yds"] += r.yards
        ts["plays"] += 1
        is_run_explosive = r.kind == "run" and r.yards >= 10
        is_pass_explosive = r.kind == "pass" and not r.sack and r.yards >= 20
        if is_run_explosive or is_pass_explosive:
            ts["explosive_plays"] += 1
        if r.yards >= 20:
            ts["plays_20_plus"] += 1
        if is_run_explosive:
            ts["runs_10_plus"] += 1
        if is_pass_explosive:
            ts["passes_20_plus"] += 1
        # Common college-football success rate: 50% of needed yards on 1st, 70% on 2nd,
        # and a conversion on 3rd/4th. Turnovers never count as successful plays.
        need_frac = .5 if before[0] == 1 else .7 if before[0] == 2 else 1.0
        if not r.turnover and (r.td or r.yards >= max(1, before[1] * need_frac)):
            ts["successful_plays"] += 1
        if was_fourth:
            ts["fourth_att"] += 1
        if self.drive is not None and not r.td and not self.drive.get("red_zone") and self.yardline + max(0, r.yards) >= 80:
            self.drive["red_zone"] = True
            ts["red_zone_att"] += 1
        if was_third:
            ts["third_att"] += 1

        if r.turnover:
            ts["turnovers"] += 1
            spot = self.yardline + r.yards
            new_yard = 100 - spot + r.return_yards
            self._n("play", r, before)
            self.end_drive("Interception" if r.turnover == "int" else "Fumble")
            self.swing(df, "pick_six" if new_yard >= 100 else "turnover")
            if new_yard >= 100:
                self.offense, self.defense = df, off
                self._n("defensive_td", df)
                if self.quarter > 4:
                    self.score[df] += 6
                    self.ot_walkoff = True
                    self.possession_over = True
                    return
                who = r.defender if r.turnover == "int" else getattr(r, "recovered_by", None)
                name = f"{who.first_name[0]}. {who.last_name} " if who is not None else ""
                kind = "interception return" if r.turnover == "int" else "fumble return"
                desc = f"{name}{max(0, spot)} yd {kind}" if name else kind.capitalize()
                return self.touchdown(df, return_td=True, desc=desc)
            return self.change_possession(df, new_yard)

        if r.safety:
            self._n("play", r, before)
            self.score[df] += 2
            self.swing(df, "safety")
            who = r.tackler
            self.scoring.append((self.quarter, self.clock, df,
                                 f"Safety ({who.first_name[0]}. {who.last_name})" if who is not None else "Safety"))
            self.end_drive("Safety")
            self._n("score", df, "SAFETY", 2)
            return self.do_kickoff(off, safety=True)

        if r.td:
            self.yardline = 100
            if self.drive is not None and self.drive.get("red_zone"):
                ts["red_zone_td"] += 1
            if was_third:
                ts["third_conv"] += 1
            if was_fourth:
                ts["fourth_conv"] += 1
            ts["first_downs"] += 1
            self._n("play", r, before)
            return self.touchdown(off, desc=self.describe_td(r))

        self.yardline += r.yards
        if r.yards >= self.togo:
            r.first_down = True
            self.down, self.togo = 1, min(10, 100 - self.yardline)
            ts["first_downs"] += 1
            if was_third:
                ts["third_conv"] += 1
            if was_fourth:
                ts["fourth_conv"] += 1
        else:
            self.down += 1
            self.togo -= r.yards
        self._n("play", r, before)

        if self.down > 4:
            self._n("turnover_on_downs")
            self.end_drive("Downs")
            return self.change_possession(df, 100 - self.yardline)

        stopped = r.incomplete or (r.out_of_bounds and self.late_half())
        # Inside two minutes a first down stops the clock only while the chains move;
        # it restarts on the ready-for-play, so the next snap still costs real time.
        chains = bool(r.first_down and self.late_half() and not stopped)
        self.between_plays(stopped, chains=chains)

    CHAIN_STOP = 4                   # seconds the clock sits still while the chains move

    def between_plays(self, stopped, chains=False):
        if self.quarter > 4 or self.clock <= 0:
            return
        self.last_runoff = 0
        if stopped:
            return
        if self._timeout_check():
            return
        t = self.tempo()
        if chains:
            t = max(3, t - self.CHAIN_STOP)
        self.last_runoff, self.last_runoff_q = min(self.clock, int(t)), self.quarter
        self.clock_tick(t)

    def tempo(self):
        if self.last_kind == "kneel":
            return 40
        if self.ctl is not None and self.offense is self.ctl.team and self.ctl.tempo != "normal":
            return self.rng.uniform(9, 15) if self.ctl.tempo == "hurry-up" else self.rng.uniform(34, 40)
        if is_hurry(self):
            return self.rng.uniform(9, 15)
        if is_milking(self):
            return self.rng.uniform(34, 40)
        sl_tempo = sideline.tempo(self)                      # tempo orders, a ball-control plan
        if sl_tempo == "hurry":
            return self.rng.uniform(10, 16)
        if sl_tempo == "milk":
            return self.rng.uniform(30, 38)
        import staff
        base = OFFENSE_SCHEMES[staff.play_caller(self.offense, "off").offense_scheme]["tempo"]
        import sim_strategy
        pref = sim_strategy.ensure(self.offense).get("tempo", "normal")
        if pref == "fast":
            base -= 5
        elif pref == "slow":
            base += 5
        return max(8, min(39, base + self.rng.gauss(0, 3)))

    def _timeout_check(self):
        df, off = self.defense, self.offense
        d_def = score_diff(self, df)
        mine = self.ctl.team if self.ctl is not None else None
        if (self.timeouts[df] and self.quarter == 4 and self.clock < 180 and -16 <= d_def <= 0
                and not is_hurry(self) and df is not mine):
            self.timeouts[df] -= 1
            self._n("timeout", df)
            return True
        # A staff whose building has turned on it calls time to settle things down (once a half).
        mv = self.momentum.value if df is self.home else -self.momentum.value
        if (df is not mine and self.timeouts[df] >= 2 and mv <= -60 and self.quarter <= 4
                and self.__dict__.setdefault("_settled", {}).get(df) != (self.quarter > 2)
                and self.rng.random() < 0.25):
            self._settled[df] = self.quarter > 2
            self.timeouts[df] -= 1
            sideline.settle(self, df)
            self._n("timeout", df)
            return True
        if (self.timeouts[off] and off is not mine and is_hurry(self) and self.quarter in (2, 4) and self.clock < 70
                and self.last_kind != "kneel"
                and (-16 <= score_diff(self) <= 0 if self.quarter == 4 else True)):   # no timeouts down 34
            self.timeouts[off] -= 1
            self._n("timeout", off)
            return True
        return False

    # ── scoring ───────────────────────────────────────────────────────────
    def touchdown(self, team, return_td=False, desc=None):
        self.score[team] += 6
        if not any(k in (desc or "").lower() for k in ("interception return", "fumble return")):
            self.swing(team, "return_td" if return_td else "touchdown")
        entry = [self.quarter, self.clock, team, desc or "Touchdown"]
        self.scoring.append(entry)
        self._n("score", team, "TOUCHDOWN", 6)
        if not return_td:
            self.end_drive("Touchdown")
        if self.quarter > 4 and getattr(self, "ot_second", False) and self.score[team] > self.score[self.other(team)]:
            self.ot_walkoff = True           # walk-off: no try needed in overtime
            self.possession_over = True
            return
        two, pick = sideline.try_choice(self, team, two_point_decision(self, team))
        if two:
            ok = self.two_point_try(team, choice=pick)
            sideline.log_try(self, team, True, ok)
            entry[3] += " (2-pt good)" if ok else " (2-pt failed)"
        else:
            good, text = field_goal(self, 20, kicking=team, pat=True)
            self.commit_stats()
            if good:
                self.score[team] += 1
            entry[3] += " (kick)" if good else " (kick failed)"
            self._n("extra_point", team, good, text)
        if self.quarter > 4:
            self.possession_over = True
            return
        if self.clock <= 0 and self.quarter in (2, 4):
            return
        self.do_kickoff(team)

    def two_point_try(self, team, ot_shootout=False, choice=None):
        saved = (self.offense, self.defense, self.yardline, self.down, self.togo, self.drive)
        self.offense, self.defense = team, self.other(team)
        self.yardline, self.down, self.togo, self.drive = 97, 1, 3, None
        import staff
        call, personnel = _pick_play(self, self.rng, staff.play_caller(team, "off"), score_diff(self), 3)
        if choice is not None:
            call, personnel = choice                          # your play
        if call.kind == "kneel":
            call = next(p for p in (call,))
        dcall = choose_defense(self, self.rng, personnel)
        self._n("two_point", team)
        self._n("pre_snap", call, personnel, dcall)
        r = resolve(self, call, personnel, dcall)
        self.discard_stats()
        good = r.td and not r.penalty
        if good:
            self.score[team] += 2
        self._n("two_point_result", team, good, r)
        self.offense, self.defense, self.yardline, self.down, self.togo, self.drive = saved
        return good

    # ── kicks ─────────────────────────────────────────────────────────────
    def do_kickoff(self, kicking, safety=False):
        receiving = self.other(kicking)
        d = self.score[kicking] - self.score[receiving]
        onside = (not safety and self.quarter == 4 and -16 <= d < 0 and self.clock < 150)
        style = sideline.kick_choice(self, kicking, safety)
        if style == "deep":
            onside, style = False, None
        res = kickoff(self, kicking, onside, style=style)
        who, yard, lines, td = res[:4]
        if onside or style in ("onside", "surprise"):
            self.sl.onsides[kicking] += 1
            sideline.log_kick(self, kicking, who == "kicking")
        self.commit_stats()
        if who == "kicking":
            self.swing(kicking, "onside" if onside else "turnover")
        if safety:
            lines.insert(0, "The free kick after the safety.")
        self._n("kick", lines)
        if not td and who == "receiving" and yard != 25:
            self.clock_tick(self.rng.randint(5, 8))
        team = kicking if who == "kicking" else receiving
        self.start_possession(team, yard if yard < 100 else 99)
        self.check_injuries()
        if td:
            self.drive = None
            self.touchdown(receiving, return_td=True, desc=self._return_desc("kickoff"))

    def _return_desc(self, kind):
        """'K. Dawson 67 yd punt return' for the scoring summary."""
        ret = getattr(self, "last_returner", None)
        self.last_returner = None
        if ret is None:
            return f"{kind.capitalize()} return"
        return f"{ret.first_name[0]}. {ret.last_name} {kind} return"

    def do_punt(self):
        off, df = self.offense, self.defense
        self._n("special_snap")                  # the fourth-down spot on screen, so the punt's numbers add up
        res = punt(self)
        yard, lines, td, blocked = res[:4]
        muffed = len(res) > 4
        sideline.resolve_special(self, "punt", not blocked and not td, "blocked" if blocked else
                                 "returned for a TD" if td else f"they start at their {yard}" if yard <= 50
                                 else f"they start at our {100 - yard}")
        self.commit_stats()
        self._n("kick", lines)
        self.clock_tick(self.rng.randint(6, 10))
        if self.drive and self.drive["plays"] <= 3 and not blocked:
            self.swing(df, "three_and_out")
        self.end_drive("Punt")
        self.check_injuries()
        if blocked:
            self.swing(df, "blocked_kick")
        if muffed:
            self.swing(off, "turnover")
            return self.start_possession(off, 100 - yard)
        if td:
            self.start_possession(df, 99)
            self.drive = None
            return self.touchdown(df, return_td=True, desc=self._return_desc("punt"))
        self.change_possession(df, yard)

    def do_field_goal(self):
        off, df = self.offense, self.defense
        self._n("special_snap")
        dist = 100 - self.yardline + 17
        self._iced = sideline.ice(self, dist)                # the other sideline may make him wait
        iced = bool(self._iced)
        good, text = field_goal(self, dist)
        self.__dict__.pop("_iced", None)
        if iced:
            sideline.log_ice(self, good)
        sideline.resolve_special(self, "fg", good)
        self.commit_stats()
        self.clock_tick(5)
        if good:
            self.score[off] += 3
            self.swing(off, "field_goal")
        self._n("field_goal", good, text, dist)
        if good:
            k = self.depth[off]["K"][0] if self.depth[off].get("K") else None
            who = f"{k.first_name[0]}. {k.last_name} " if k is not None else ""
            self.scoring.append((self.quarter, self.clock, off, f"{who}{dist} yd FG"))
            self.end_drive("Field Goal")
            if self.quarter > 4:
                self.possession_over = True
                return
            if self.clock <= 0 and self.quarter in (2, 4):
                return
            return self.do_kickoff(off)
        self.swing(df, "blocked_kick" if "BLOCKED" in text else "missed_fg")
        self.end_drive("Missed FG")
        self.change_possession(df, max(20, 100 - (self.yardline - 7)))

    def do_fake(self, kind):
        """Fake punt or fake field goal: a surprise, so it works more often than the down and distance says."""
        off, df = self.offense, self.defense
        rng = self.rng
        d = self.depth[off]
        if kind == "fake_punt":
            runner = (d["RB"][2:3] or d["RB"][-1:])[0]
            lines = [f"{d['P'][0].last_name} is back to punt... it's a FAKE! Direct snap to the upback, {runner.last_name}!"]
        else:
            runner = (d["TE"][1:2] or d["TE"][:1])[0]
            holder = (d["QB"][1:2] or d["QB"][:1])[0]
            lines = [f"Lined up for the field goal... FAKE! Holder {holder.last_name} flips it to {runner.last_name}!"]
        success = rng.random() < sideline.fake_odds(self, kind)   # they've seen one? it's late? it's long?
        self.sl.fakes[off] += 1
        sideline.resolve_special(self, kind, success, "converted" if success else "stopped")
        ytg_end = 100 - self.yardline
        gain = self.togo + rng.randint(0, 12) if success else rng.randint(-2, max(0, self.togo - 1))
        gain = min(gain, ytg_end)
        self.clock_tick(6)
        if self.drive:
            self.drive["plays"] += 1
        self.stat(runner, "rush_att")
        self.stat(runner, "rush_yds", gain)
        self.commit_stats()
        self.team_stats[off]["rush_yds"] += gain
        self.team_stats[off]["total_yds"] += gain
        self.team_stats[off]["plays"] += 1
        self.team_stats[off]["fourth_att"] += 1
        if gain >= 10:
            self.team_stats[off]["explosive_plays"] += 1
            self.team_stats[off]["runs_10_plus"] += 1
        if gain >= 20:
            self.team_stats[off]["plays_20_plus"] += 1
        if success:
            lines.append(f"He's got it — {gain} yards and a FIRST DOWN! The {off.nickname} pulled it off!")
        else:
            lines.append(f"Stuffed after {gain}! {df.school} wasn't fooled — turnover on downs.")
        self._n("kick", lines)
        if success:
            self.swing(off, "trick_play")
            self.team_stats[off]["first_downs"] += 1
            if gain >= ytg_end:
                self.yardline = 100
                return self.touchdown(off, desc=f"{runner.first_name[0]}. {runner.last_name} {gain} yd run (fake)")
            self.yardline += gain
            self.down, self.togo = 1, min(10, 100 - self.yardline)
            return
        self.swing(df, "fourth_stop")
        self.yardline += gain
        self.end_drive("Downs")
        self.change_possession(df, 100 - self.yardline)

    # ── overtime ──────────────────────────────────────────────────────────
    def overtime(self):
        self.quarter = 5
        base = {t: self.score[t] for t in self.teams}
        first = sideline.ot_choice(self, self.rng.choice(self.teams))   # the toss winner chooses
        self._n("overtime_start", first)
        while self.score[self.home] == self.score[self.away] and not self.ot_walkoff:
            self.ot_round += 1
            self._n("ot_round")
            for team in (first, self.other(first)):
                self.ot_second = team is not first
                if self.ot_round <= 2:
                    self.start_possession(team, 75)
                    self.possession_over = False
                    while not self.possession_over:
                        self.run_down()
                else:
                    self.two_point_try(team)
                if self.ot_walkoff:
                    break
            if self.ot_round >= 15:
                self.score[first] += 2           # absurd marathon safety valve
        for t in self.teams:
            self.line[t].append(self.score[t] - base[t])
