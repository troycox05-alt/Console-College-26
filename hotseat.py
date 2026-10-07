"""
hotseat.py — What's left of Hot Seat: one human per game.

Hot Seat (several coaches sharing one computer) and its network version were removed in v51.
The game still asks a few questions the old module answered — who the human coaches are,
"run this as that coach" — so they live here, answered for a single player. A save made
in Hot Seat loads as a normal Coach Career with whichever coach was on the keyboard.
"""
from contextlib import nullcontext

LEFT = [True]                      # (kept for old callers)


class Seat:                         # old Hot Seat saves unpickle into these; after_load drops them
    retired = False


class HotSeat:
    pass


def state(league):
    return None


def active(league):
    return False


def concurrent(league):
    return False


def seats(league):
    return []


def current(league):
    return None


def seat_team(league, seat):
    return None


def seat_coach(league, seat):
    return None


def seat_for_team(league, team):
    return None


def humans(league):
    """Every program a human coaches: your team in Coach Career, every player's in an online
    world (on the host), nobody otherwise."""
    if getattr(league, "mode", None) == "online":
        from netplay import seat
        return seat.humans(league)
    t = getattr(league, "user_team", None)
    return [t] if t is not None and getattr(league, "mode", None) == "career" else []


def is_human(league, team):
    return team is not None and any(team is t for t in humans(league))


def acting_as(league, team):
    if getattr(league, "mode", None) == "online":
        from netplay import seat
        return seat.acting_as(league, team)
    return nullcontext()


def acting_as_coach(league, coach):
    if getattr(league, "mode", None) == "online":
        return acting_as(league, getattr(coach, "team", None))
    return nullcontext()


def each_seat(league, fn, interactive=False, only_with_team=False, simultaneous=False):
    if getattr(league, "mode", None) == "online":           # every player's career, one at a time
        out = []
        for t in humans(league):
            with acting_as(league, t):
                out.append(fn())
        return out
    return [fn()]


def maybe_pass(league, headline=""):
    return None


def sync(league):
    return None


def neutral():
    return False


def covered():
    return False


def banner(league):
    return []


def blocking_begin():
    return 0


def blocking_end(d):
    return None


def lan_names():
    return []


def working_names():
    return []


def who(league):
    """The save header's Hot Seat line: nobody, now."""
    return ""


def after_load(league):
    """A save from the Hot Seat days: keep the coach who was on the keyboard, drop the table."""
    league.__dict__.pop("hotseat", None)


__all__ = ["acting_as", "acting_as_coach", "active", "each_seat", "humans", "is_human", "state"]
