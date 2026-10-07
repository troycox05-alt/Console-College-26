"""
gameday_history.py — Where the pregame show had already been before your world began.

Campuses that hosted the show before 2026, so it never calls a return trip its first
visit. The built-in universe starts fresh (empty); a universe file can fill it in.
"""

REAL_HOSTS = set()


def hosted_before(school):
    return school in REAL_HOSTS
