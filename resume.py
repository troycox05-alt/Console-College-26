"""
resume.py — What the world can see about a coach: his résumé.

Nobody hiring a coach knows his ratings or his ceiling. An athletic director sees
what's on paper — records against what the roster should have done, the stage he
did it on, rings, playoff trips, recruiting classes, a coordinator's units — and
the impression the man leaves in an interview. How well an AD reads that paper
depends on the AD.

  reputation(coach)        the public read, on the same 40-97 scale as a rating
  recruit_rep(coach)       what his recruiting classes say about him as a recruiter
  read(team, coach)        one AD's read of a candidate: his eye, his tastes, his blind spots
  letter(v)                A+ … D for the screens
"""
import random


def _hist(coach):
    return list(getattr(coach, "history", []) or [])


def _track(coach, league):
    import carousel as cz
    return cz.track_record(coach, league)


def recruit_rep(coach):
    """What his signing classes say, 30-90. No head-coaching classes: nobody knows yet."""
    ranks = [s.get("class_rank") for s in _hist(coach)[-4:] if s.get("class_rank")]
    if not ranks:
        return 60.0
    avg = sum(ranks) / len(ranks)
    v = 60 + (40 - avg) * 0.5
    n = len(ranks)
    v = 60 + (v - 60) * n / (n + 1)                       # one class is a hint, four are a reputation
    return max(30.0, min(90.0, v))


def trend(coach):
    """Last two seasons' win share against the two before, -1..1."""
    h = _hist(coach)
    if len(h) < 3:
        return 0.0

    def pct(ss):
        w = sum(s["w"] for s in ss)
        g = w + sum(s["l"] for s in ss)
        return w / g if g else 0.5
    return max(-1.0, min(1.0, (pct(h[-2:]) - pct(h[-4:-2])) * 2))


def prior(coach):
    """What he did before this world's first season (or away from the FBS): the
    part of the résumé nobody here watched. It points toward what he is, loosely."""
    v = coach.__dict__.get("prior_rep")
    if v is None:
        r = random.Random(f"prior:{coach.name}")
        kind = getattr(coach, "kind", "")
        o = coach.overall
        if kind == "hs":
            v = 50 + r.gauss(0, 3)
        elif kind == "fcs" or "FCS" in (getattr(coach, "origin", "") or ""):
            v = 57 + (o - 62) * 0.5 + r.gauss(0, 4)
        elif kind == "coord" or getattr(coach, "role", "HC") in ("OC", "DC"):
            v = 58 + (o - 65) * 0.5 + r.gauss(0, 4.5)
        else:
            v = 68 + (o - 68) * 0.7 + r.gauss(0, 5)
        v = coach.__dict__["prior_rep"] = round(max(42.0, min(92.0, v)), 1)
    return v


def reputation(coach, league):
    """The public read on a coach, 40-97 — what his résumé says he is."""
    if coach is None:
        return 60.0
    if getattr(coach, "is_user", False) and not _hist(coach) and not getattr(coach, "coord_history", None):
        return float(coach.overall)                       # a brand-new career: your name is your rating
    key = (league.year, len(_hist(coach)), len(getattr(coach, "coord_history", []) or []))
    cached = coach.__dict__.get("_rep")
    if cached and cached[0] == key:
        return cached[1]
    import carousel as cz
    h = _hist(coach)
    if h:
        n = len(h)
        tr = _track(coach, league)
        level = cz.level_of(coach, league)
        recent = h[-5:]
        w = sum(s["w"] for s in recent)
        g = w + sum(s["l"] for s in recent)
        wpct = w / g if g else 0.5
        rings = 0.0
        for s in h[-10:]:
            age_ = league.year - s.get("year", league.year)
            fade = 1.0 if age_ <= 4 else 0.6
            rings += fade * (5.0 * s.get("title", False) + 1.6 * s.get("cfp", False)
                             + 1.0 * s.get("conf_champ", False) + 0.3 * s.get("bowl_win", False))
        rep = (52 + (level - 60) * 0.22 + tr * 55 + (wpct - 0.5) * 14 + min(10.0, rings)
               + (recruit_rep(coach) - 60) * 0.12 + min(n, 10) * 0.35)
        coord = getattr(coach, "coord_history", []) or []
        if n <= 2 and coord:                              # still partly judged on the units he ran
            import staff
            rep = rep * 0.7 + (60 + staff.resume_score(coach) * 1.2) * 0.3
        rep = (prior(coach) * 2.5 + rep * n) / (2.5 + n)  # the old résumé fades as the new one fills in
    elif getattr(coach, "coord_history", None):
        import staff
        rs = staff.resume_score(coach)
        stage = coach.team.prestige if coach.team is not None else 60
        n = len(coach.coord_history)
        rep = 57 + rs * 1.25 + (stage - 60) * 0.08
        rep = (prior(coach) * 2.0 + rep * n) / (2.0 + n)
    else:
        rep = prior(coach)
    rep = max(40.0, min(97.0, rep))
    coach.__dict__["_rep"] = (key, rep)
    return rep


def polish(coach):
    """How well he interviews — nothing to do with how well he coaches."""
    v = coach.__dict__.get("polish")
    if v is None:
        v = coach.__dict__["polish"] = round(random.Random(f"polish:{coach.name}").gauss(0, 1), 2)
    return v


def naive(coach, league):
    """The headline version of a résumé: last year's record, the rings, the name."""
    h = _hist(coach)
    if not h:
        return reputation(coach, league)
    last = h[-2:]
    w = sum(s["w"] for s in last)
    g = w + sum(s["l"] for s in last)
    pct = w / g if g else 0.5
    rings = sum(4.0 * s.get("title", False) + 2.0 * s.get("cfp", False) for s in h)
    import carousel as cz
    return max(40.0, min(97.0, 48 + (pct - 0.5) * 34 + min(12.0, rings) + (cz.level_of(coach, league) - 60) * 0.25))


def read(team, coach, league, rng=None):
    """How this school's AD reads this candidate. A sharp AD reads the résumé in
    context (what the roster should have done, the level he did it at); a weak one
    reads the headline and the interview. Neither one sees the ratings."""
    import ad_market
    ad = ad_market.ad_of(team)
    eye = ad_market.eye(team)                             # 0..1, how well he reads paper
    smart = reputation(coach, league)
    headline = naive(coach, league)
    v = eye * smart + (1 - eye) * headline
    traits = ad.get("traits", ())
    pol = polish(coach) * (2.0 + (1 - eye) * 5.0) * (1.6 if "headline" in traits else 1.0)
    v += pol
    if rng is not None:
        v += rng.gauss(0, 1.0 + (1 - eye) * 4.0 * (1.5 if "gambler" in traits else 0.6 if "steady" in traits else 1.0))
    return v


def letter(v):
    for cut, g in ((88, "A+"), (83, "A"), (79, "A-"), (75, "B+"), (71, "B"), (67, "B-"), (63, "C+"), (59, "C"),
                   (55, "C-"), (50, "D+")):
        if v >= cut:
            return g
    return "D"
