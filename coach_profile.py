"""Hidden staff strengths/weaknesses and sideline profile (v28)."""
import random

SIDELINE_KEYS = ("game_day", "adjustments", "motivation", "discipline", "evaluation", "relations")
SIDELINE_LABELS = {"game_day":"Game day", "adjustments":"Halftime adjustments", "motivation":"Motivation",
                   "discipline":"Discipline", "evaluation":"Evaluation eye", "relations":"Player relations"}


def _clamp(v, lo=25, hi=97):
    return int(max(lo, min(hi, round(v))))


def shape(coach, pinned=()):
    """Give a CPU coach 1-2 real rating strengths and 1-2 weaknesses, once."""
    if coach is None or getattr(coach, "_shaped", False) or getattr(coach, "is_user", False):
        if coach is not None and getattr(coach, "is_user", False):
            coach._shaped = True
            ensure_sideline(coach)
        return coach
    rng = random.Random(f"coach-shape:{coach.name}")
    keys = [k for k in coach.RATING_KEYS if k not in set(pinned)]
    rng.shuffle(keys)
    ns = min(len(keys), rng.randint(1, 2))
    nw = min(len(keys)-ns, rng.randint(1, 2))
    strengths, weaknesses = keys[:ns], keys[ns:ns+nw]
    for k in strengths:
        coach.ratings[k] = _clamp(coach.ratings[k] + rng.randint(5, 11))
    for k in weaknesses:
        coach.ratings[k] = _clamp(coach.ratings[k] - rng.randint(8, 16))
    coach._rating_strengths = strengths
    coach._rating_weaknesses = weaknesses
    coach._shaped = True
    ensure_sideline(coach)
    return coach


def ensure_sideline(coach):
    if coach is None:
        return {}
    cur = getattr(coach, "sideline_profile", None)
    if isinstance(cur, dict) and all(k in cur for k in SIDELINE_KEYS):
        return cur
    base = getattr(coach, "overall", 65)
    if getattr(coach, "is_user", False):
        prof = {k: base for k in SIDELINE_KEYS}
    else:
        rng = random.Random(f"sideline:{coach.name}")
        vals = {k: _clamp(rng.gauss(base, 8), 25, 97) for k in SIDELINE_KEYS}
        keys = list(SIDELINE_KEYS); rng.shuffle(keys)
        for k in keys[:2]: vals[k] = _clamp(vals[k] + rng.randint(5, 10))
        for k in keys[2:4]: vals[k] = _clamp(vals[k] - rng.randint(7, 13))
        prof = vals
    coach.sideline_profile = prof
    return prof


def value(coach, key):
    if coach is None:
        return 65
    return ensure_sideline(coach).get(key, getattr(coach, "overall", 65))


def delta(coach, key):
    return value(coach, key) - getattr(coach, "overall", 65)


def strengths_weaknesses(coach):
    prof = ensure_sideline(coach); base = getattr(coach, "overall", 65)
    hi = sorted(prof, key=lambda k: prof[k]-base, reverse=True)[:2]
    lo = sorted(prof, key=lambda k: prof[k]-base)[:2]
    return hi, lo
