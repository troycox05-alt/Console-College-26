"""
momentum.py — Momentum and the crowd, built so it can't break a game.

One number, -100 (all away) to +100 (all home). Big moments push it toward
the team that made them; it bleeds back toward zero every snap, and halftime
resets most of it.

What momentum does: every player on the team riding it plays up to
MAX_EFFECT rating points better, and the other side the same amount worse.
At full tilt that is worth a few points on the scoreboard, not a guaranteed
comeback or blowout.

Guard rails:
  * hard cap at ±100, decays 6% per snap, 60% of it gone at halftime
  * swings shrink as momentum is already pointing that way (diminishing returns)
  * a team getting blown out doesn't feed the leader's momentum further
  * a loud home crowd amplifies the home team's swings and rattles road
    offenses (more false starts); neutral sites have no crowd edge
"""

MAX_EFFECT = 2.0          # rating points at ±100
DECAY = 0.972
HALFTIME_KEEP = 0.4
HOME_EDGE = 0.8           # baseline home-field boost, rating points
BIG_CROWD = 85000

SWINGS = {
    "touchdown": 22, "return_td": 32, "field_goal": 7, "turnover": 26, "pick_six": 38,
    "sack": 7, "big_play": 10, "explosive": 14, "three_and_out": 8, "fourth_stop": 22,
    "fourth_convert": 12, "missed_fg": 12, "blocked_kick": 30, "safety": 24,
    "onside": 25, "third_long_convert": 6, "goal_line_stand": 20, "trick_play": 12,
}


class Momentum:
    def __init__(self, home, away, neutral=False, noise=None):
        self.home, self.away = home, away
        self.neutral = neutral
        self.value = 0.0
        self.last_shift = 0.0
        # noise: how loud the building actually is today (facilities.crowd_noise) —
        # ~0.3 for a half-empty stadium, ~1.0 for a full one, ~1.3 for 100,000 in an elite one.
        if noise is None:
            noise = 1.0 if home.capacity >= BIG_CROWD else 0.85
        self.noise = 0.0 if neutral else noise
        self.crowd = 0.0 if neutral else 1.0 + 0.2 * noise

    def swing(self, team, event, score_margin=0):
        """score_margin: the swinging team's lead after the play (positive = ahead)."""
        base = SWINGS.get(event, 0)
        if not base:
            return 0.0
        sign = 1 if team is self.home else -1
        amp = self.crowd if (team is self.home and self.crowd) else 1.0
        if score_margin >= 24:                      # piling on doesn't build much
            amp *= 0.35
        same_way = self.value * sign
        if same_way > 0:
            amp *= 1 - same_way / 150                # diminishing returns
        delta = sign * base * amp
        before = self.value
        self.value = max(-100.0, min(100.0, self.value + delta))
        self.last_shift = self.value - before
        return self.last_shift

    def tick(self):
        self.value *= DECAY

    def halftime(self):
        self.value *= HALFTIME_KEEP

    def effect(self, team):
        """Rating-point adjustment for a team right now (crowd + momentum)."""
        sign = 1 if team is self.home else -1
        edge = HOME_EDGE * (0.3 + self.noise) if (team is self.home and not self.neutral) else 0.0
        return edge + sign * self.value / 100 * MAX_EFFECT

    def leader(self):
        if abs(self.value) < 15:
            return None
        return self.home if self.value > 0 else self.away

    def false_start_bump(self, offense):
        """Road offenses in loud buildings jump early more often."""
        if self.neutral or offense is self.home:
            return 0.0
        return 0.006 * self.crowd + max(0.0, self.value) / 100 * 0.01
