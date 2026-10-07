"""
coach_facts.py — What's on the record for named head coaches.

FACTS: name -> (age in 2026, first season at his current school)
ALMA:  name -> where he played / went to school (any school, not just FBS)
STOPS: name -> prior jobs, most recent first: (school or team, job, start, end)
RECENT_WINNERS: coaches who've won a title lately (a hiring-market bump)

The built-in universe's coaches are fictional, so these start empty and everything
falls back to generated values. A universe file can fill them in (universe.py).
"""

FACTS = {}

ALMA = {}

STOPS = {}

RECENT_WINNERS = set()


def stops_for(name):
    """The prior-stop dicts the coach card expects, or []."""
    return [{"school": s, "job": j, "start": a, "end": b} for s, j, a, b in STOPS.get(name, [])]
