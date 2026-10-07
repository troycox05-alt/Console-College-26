"""
export_sheets.py — Export the whole league to one formatted spreadsheet (.xlsx).

Opens in Excel, Numbers, LibreOffice, and Google Sheets (File > Import > Upload).
The file lands in the exports/ folder next to the game.

WHAT'S IN IT  (an Overview tab lists every sheet, with a link and a row count)
  League       Teams, Rankings, Schedule Grid, Schedule, Game History, Champions, Team History, Final Polls,
               Awards, Pro League Draft, Series, Carousel (and, optionally, every player's game-by-game log)
  Players      Rosters (every FBS player, every rating, all 11 position fits), Player Stats, Career Stats,
               Rating History, Player Events, Coaches, Transfer Portal
  Recruiting   the full recruit database (public and, optionally, hidden true ratings), who is after whom,
               every program's board, class rankings, signing history, your standing orders and actions
  You          your week-by-week decisions, headset calls, recruiting actions, inbox and career log
               (plus your bets, in Spectator mode)
  Compliance   every CAB case the world knows about, each program's APR and integrity, every player's GPA

Needs the openpyxl package. The screen offers to install it the first time. Read-only: exporting never
changes the league.
"""
from __future__ import annotations

import os
import re
import time
from collections import Counter, defaultdict

EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")

# ═══ Look ═══════════════════════════════════════════════════════════════════

FONT = "Arial"
GROUP_COLORS = {                # header fill by column group
    "base": "1F3864", "rating": "2E75B6", "role": "548235", "bio": "7F6000", "status": "7030A0",
    "prof": "C55A11", "hidden": "C00000", "stat": "375623", "yours": "0F7B78", "game": "44546A",
    "money": "806000",
}
TAB_COLORS = {"League": "2E75B6", "Players": "548235", "Recruiting": "C55A11", "You": "7030A0",
              "History": "7F7F7F", "Compliance": "C00000", "Overview": "1F3864"}
SCALES = {                      # (low, mid, high) values for the red-yellow-green color scale
    "rating": (35, 65, 92), "prof": (0.1, 0.65, 1.1), "pct": (0, 0.5, 1), "interest": (0, 40, 90),
    "fit": (0, 60, 100),
}
LOW, MID, HIGH = "F8696B", "FFEB84", "63BE7B"
WIN_FILL, WIN_TEXT = "C6EFCE", "006100"
LOSS_FILL, LOSS_TEXT = "FFC7CE", "9C0006"

_BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _clean(v):
    """Anything the sheet can hold: numbers and text; everything else becomes text."""
    if v is None:
        return None
    if isinstance(v, str):
        return _BAD.sub("", v)[:32000]
    if isinstance(v, bool):
        return "Yes" if v else ""
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return v if v == v and v not in (float("inf"), float("-inf")) else None
    if isinstance(v, (set, frozenset)):
        return ", ".join(sorted(str(x) for x in v))
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return _BAD.sub("", str(v))[:32000]


class Col:
    """One column: header, width, number format, header color group, alignment, color scale."""
    __slots__ = ("h", "w", "fmt", "grp", "align", "scale")

    def __init__(self, h, w=10, fmt=None, grp="base", align=None, scale=None):
        self.h, self.w, self.fmt, self.grp, self.align, self.scale = h, w, fmt, grp, align, scale


class Styled:
    """A cell with its own fill/text color (the schedule grid's wins and losses)."""
    __slots__ = ("v", "fill", "color", "bold")

    def __init__(self, v, fill=None, color=None, bold=False):
        self.v, self.fill, self.color, self.bold = v, fill, color, bold


def _num(w=None, fmt=None, grp="rating", scale=None):
    """Keyword bundle for a centered numeric column. The width belongs to C_(); `w` here is ignored."""
    return {"fmt": fmt, "grp": grp, "align": "center", "scale": scale}


def C_(h, w=10, **kw):
    return Col(h, w, **kw)


# ═══ The workbook wrapper ═══════════════════════════════════════════════════

class Sheets:
    """A write-only workbook: streams rows to disk, so 1M+ cells don't fill memory."""

    def __init__(self, progress=None):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils.indexed_list import IndexedList
        self._Font, self._Fill, self._Align = Font, PatternFill, Alignment
        self.wb = Workbook(write_only=True)
        self.wb._fonts = IndexedList([Font(name=FONT, sz=10, family=2)])       # Arial 10 everywhere
        self.progress = progress
        self.index = []              # (category, sheet name, description, rows)
        self.skipped = []            # (sheet name, why)
        self.overview = self.wb.create_sheet("Overview")
        self.overview.sheet_properties.tabColor = TAB_COLORS["Overview"]
        self._aligns = {}

    def _align(self, kind):
        a = self._aligns.get(kind)
        if a is None:
            a = self._aligns[kind] = self._Align(horizontal=kind, vertical="center")
        return a

    def add(self, category, name, desc, cols, rows, freeze=1, zebra=True, stream=False):
        """Write one sheet. `rows` is any iterable of lists, one value per column.
        A sheet that fails to build is skipped and noted on the Overview; the rest still export."""
        if self.progress:
            self.progress(name)
        try:
            if not stream:
                rows = list(rows)
            return self._write(category, name, desc, cols, rows, freeze, zebra)
        except Exception as e:                                  # never lose the whole export to one sheet
            self.skipped.append((name, f"{type(e).__name__}: {e}"))
            return 0

    def _write(self, category, name, desc, cols, rows, freeze, zebra):
        from openpyxl.cell import WriteOnlyCell
        from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
        from openpyxl.styles import Border, Side
        from openpyxl.utils import get_column_letter as L

        ws = self.wb.create_sheet(name[:31])
        ws.sheet_properties.tabColor = TAB_COLORS.get(category, "7F7F7F")
        for i, c in enumerate(cols, 1):
            ws.column_dimensions[L(i)].width = c.w
        ws.row_dimensions[1].height = 34
        ws.freeze_panes = f"{L(freeze + 1)}2" if freeze else "A2"

        Font, Fill = self._Font, self._Fill
        head = []
        for c in cols:
            cell = WriteOnlyCell(ws, value=c.h)
            cell.font = Font(name=FONT, sz=10, bold=True, color="FFFFFF")
            cell.fill = Fill("solid", fgColor=GROUP_COLORS.get(c.grp, GROUP_COLORS["base"]))
            cell.alignment = self._Align(horizontal="center", vertical="center", wrap_text=True)
            head.append(cell)
        ws.append(head)

        special_set = {i for i, c in enumerate(cols) if c.fmt or c.align}
        ncols = len(cols)
        n = 0
        for row in rows:
            out = []
            for i in range(ncols):
                v = row[i] if i < len(row) else None
                if isinstance(v, Styled):
                    cell = WriteOnlyCell(ws, value=_clean(v.v))
                    if v.fill:
                        cell.fill = Fill("solid", fgColor=v.fill)
                    if v.color or v.bold:
                        cell.font = Font(name=FONT, sz=10, bold=v.bold, color=v.color or "000000")
                    if cols[i].align:
                        cell.alignment = self._align(cols[i].align)
                    out.append(cell)
                    continue
                v = _clean(v)
                if i in special_set and v is not None:
                    c = cols[i]
                    cell = WriteOnlyCell(ws, value=v)
                    if c.fmt:
                        cell.number_format = c.fmt
                    if c.align:
                        cell.alignment = self._align(c.align)
                    out.append(cell)
                else:
                    out.append(v)
            ws.append(out)
            n += 1

        last = max(n, 1) + 1
        ws.auto_filter.ref = f"A1:{L(ncols)}{last}"
        for i, c in enumerate(cols, 1):                         # color scales first: they outrank the stripes
            if c.scale and n:
                lo, mid, hi = SCALES[c.scale]
                ws.conditional_formatting.add(
                    f"{L(i)}2:{L(i)}{last}",
                    ColorScaleRule(start_type="num", start_value=lo, start_color=LOW,
                                   mid_type="num", mid_value=mid, mid_color=MID,
                                   end_type="num", end_value=hi, end_color=HIGH))
        if zebra and n:
            ws.conditional_formatting.add(
                f"A2:{L(ncols)}{last}",
                FormulaRule(formula=["MOD(ROW(),2)=0"], fill=Fill("solid", bgColor="F3F6FA", fgColor="F3F6FA")))
        self.index.append((category, ws.title, desc, n))
        return n

    # ── the Overview tab ────────────────────────────────────────────────
    def finish_overview(self, facts, notes):
        from openpyxl.cell import WriteOnlyCell
        from openpyxl.worksheet.hyperlink import Hyperlink
        ws = self.overview
        Font, Fill = self._Font, self._Fill
        for col, w in (("A", 26), ("B", 92), ("C", 12)):
            ws.column_dimensions[col].width = w

        def cell(v, bold=False, size=10, color="000000", fill=None, wrap=False, link=None):
            c = WriteOnlyCell(ws, value=_clean(v))
            c.font = Font(name=FONT, sz=size, bold=bold, color=color, underline="single" if link else None)
            if fill:
                c.fill = Fill("solid", fgColor=fill)
            if wrap:
                c.alignment = self._Align(wrap_text=True, vertical="top")
            if link:
                c.hyperlink = Hyperlink(ref="A1", location=f"'{link}'!A1", display=str(v))
            return c

        ws.append([cell("Console College — League Export", bold=True, size=18, color="1F3864")])
        ws.append([cell(facts[0][1], size=11, color="595959")])
        ws.append([])
        for label, value in facts[1:]:
            ws.append([cell(label, bold=True), cell(value, wrap=True)])
        ws.append([])
        ws.append([cell("SHEETS", bold=True, color="FFFFFF", fill="1F3864"),
                   cell("What's in it", bold=True, color="FFFFFF", fill="1F3864"),
                   cell("Rows", bold=True, color="FFFFFF", fill="1F3864")])
        last_cat = None
        for cat, name, desc, n in self.index:
            if cat != last_cat:
                ws.append([cell(cat.upper(), bold=True, color="FFFFFF", fill=TAB_COLORS.get(cat, "7F7F7F")),
                           cell("", fill=TAB_COLORS.get(cat, "7F7F7F")), cell("", fill=TAB_COLORS.get(cat, "7F7F7F"))])
                last_cat = cat
            ws.append([cell(name, color="0563C1", link=name), cell(desc, wrap=True), cell(n)])
        if self.skipped:
            ws.append([])
            ws.append([cell("COULD NOT EXPORT", bold=True, color="FFFFFF", fill="C00000")])
            for name, why in self.skipped:
                ws.append([cell(name), cell(why, wrap=True)])
        ws.append([])
        ws.append([cell("NOTES", bold=True, color="FFFFFF", fill="1F3864")])
        for line in notes:
            ws.append([cell(""), cell(line, wrap=True)])
        ws.append([])
        ws.append([cell("HEADER COLORS", bold=True, color="FFFFFF", fill="1F3864")])
        legend = (("base", "Identity and basics"), ("rating", "Ratings"), ("role", "Role on the team"),
                  ("bio", "Bio and background"), ("status", "Status"), ("prof", "Position fit (0.10 to 1.20)"),
                  ("hidden", "HIDDEN in the game: a recruit's true ratings (spoilers)"),
                  ("yours", "About your program"), ("stat", "Statistics"), ("game", "Game details"),
                  ("money", "Money"))
        for grp, text in legend:
            ws.append([cell(grp.title(), bold=True, color="FFFFFF", fill=GROUP_COLORS[grp]), cell(text)])


# ═══ Small lookups ══════════════════════════════════════════════════════════

def _user_recruit_team(league):
    """The program whose board you work (career mode)."""
    return getattr(league, "user_team", None) if getattr(league, "mode", None) == "career" else None


def _sorted_teams(league):
    """Conference by conference, division by division, in standings order."""
    from league import CONFERENCES
    out = []
    for short, _, _ in CONFERENCES:
        for div in league.divisions(short):
            for i, t in enumerate(league.standings(short, div), 1):
                out.append((t, i))
    seen = {id(t) for t, _ in out}
    out += [(t, 0) for t in league.teams if id(t) not in seen]
    return out


def _trait_labels(holder):
    try:
        import traits
        return traits.labels(holder)
    except Exception:
        return list(getattr(holder, "traits", []) or [])


def _kick_text(minutes):
    if not isinstance(minutes, int):
        return ""
    h, m = divmod(minutes, 60)
    return f"{(h % 12) or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"


def _rec(team):
    return f"{team.wins}-{team.losses}"


def _stat_label(key):
    return _STAT_LABELS.get(key, key.replace("_", " ").title())


_STAT_ORDER = [
    ("pass_cmp", "Pass Cmp"), ("pass_att", "Pass Att"), ("pass_yds", "Pass Yds"), ("pass_td", "Pass TD"),
    ("pass_int", "Pass INT"), ("sacked", "Sacked"), ("rush_att", "Rush Att"), ("rush_yds", "Rush Yds"),
    ("rush_td", "Rush TD"), ("rush_long", "Rush Long"), ("fumbles", "Fumbles"), ("targets", "Targets"),
    ("rec", "Rec"), ("rec_yds", "Rec Yds"), ("rec_td", "Rec TD"), ("rec_long", "Rec Long"),
    ("tkl", "Tackles"), ("tfl", "TFL"), ("sack", "Sacks"), ("int", "INT"), ("pbu", "PBU"), ("ff", "Forced Fum"),
    ("fr", "Fum Rec"), ("missed_tkl", "Missed Tkl"), ("tgt_d", "Targeted (D)"), ("cmp_d", "Cmp Allowed"),
    ("fg_made", "FG Made"), ("fg_att", "FG Att"), ("fg_long", "FG Long"), ("xp_made", "XP Made"),
    ("xp_att", "XP Att"), ("punts", "Punts"), ("punt_yds", "Punt Yds"), ("kr", "KR"), ("kr_yds", "KR Yds"),
    ("kr_td", "KR TD"), ("pr", "PR"), ("pr_yds", "PR Yds"), ("pr_td", "PR TD"),
]
_STAT_LABELS = dict(_STAT_ORDER)


def _stat_keys(counters):
    """Known stats in a sensible order, then anything new the game adds later."""
    seen = set()
    for c in counters:
        seen.update(k for k, v in c.items() if v)
    keys = [k for k, _ in _STAT_ORDER if k in seen]
    keys += sorted(seen - set(keys))
    return keys


# ═══ League sheets ══════════════════════════════════════════════════════════

def _hot(league):
    import hotseat
    return hotseat.active(league)

def _owner(league, team, mine=None):
    """Who coaches this program at the table: the player's name in Hot Seat, 'Yes' for your own team."""
    if team is None:
        return ""
    if _hot(league):
        import hotseat
        s = hotseat.seat_for_team(league, team)
        return s.name if s is not None else ""
    return "Yes" if team is mine else ""

def _human_teams(league):
    if _hot(league):
        import hotseat
        return hotseat.humans(league)
    return []

class _Capture:
    """Stands in for the workbook while one seat's sheets are built, so they can be merged into one."""

    def __init__(self):
        self.sheets = {}

    def add(self, category, name, desc, cols, rows, freeze=1, zebra=True, stream=False):
        self.sheets[name] = (category, desc, cols, list(rows), freeze, zebra)
        return len(self.sheets[name][3])

def _per_seat(league, book, builders):
    """Hot Seat: build each coach's private sheets with him on the keyboard, then merge every coach's rows
    into one sheet with a Player column. builders: [(fn, takes_me)] — fn(league, book[, me])."""
    import hotseat
    merged = {}

    def one():
        seat = hotseat.current(league)
        me = getattr(league, "user_team", None)
        for fn, takes_me in builders:
            cap = _Capture()
            try:
                fn(league, cap, me) if takes_me else fn(league, cap)
            except Exception as e:
                book.skipped.append((f"{fn.__name__.replace('_sheet_', '').title()} ({seat.name})",
                                     f"{type(e).__name__}: {e}"))
                continue
            for name, (cat, desc, cols, rows, freeze, zebra) in cap.sheets.items():
                m = merged.setdefault(name, {"cat": cat, "desc": desc, "cols": cols, "rows": [], "freeze": freeze})
                m["rows"] += [[seat.name] + list(r) for r in rows]
    hotseat.each_seat(league, one)
    for name, m in merged.items():
        cols = [C_("Player", 12, grp="yours")] + list(m["cols"])
        book.add(m["cat"], name, m["desc"] + " One block per coach (see the Player column).", cols, m["rows"],
                 freeze=m["freeze"] + 1)

def _sheet_teams(league, book, mine):
    import recruiting
    from models import Team
    R = league.rankings
    cy = league.recruiting
    scores = {t: recruiting.class_points(cy.commitments(t)) for t in league.teams}
    order = sorted((t for t in league.teams if cy.commitments(t)), key=lambda t: -scores[t])
    class_rank = {t: i for i, t in enumerate(order, 1)}
    cols = [
        C_("Conference", 14), C_("Division", 11), C_("Div Rank", 6, align="center"), C_("Team", 24),
        C_("Nickname", 16), C_("Record", 8, align="center"),
        C_("W", 5, align="center"), C_("L", 5, align="center"), C_("Conf W", 6, align="center"),
        C_("Conf L", 6, align="center"), C_("Win %", 7, fmt="0.000", align="center"),
        C_("PF", 6, align="center"), C_("PA", 6, align="center"), C_("Diff", 6, align="center", fmt="+0;-0;0"),
        C_("Poll Rank", 7, align="center"),
        C_("Prestige", 8, **_num(8, scale="rating")), C_("Team OVR", 8, **_num(8, scale="rating")),
        C_("Off OVR", 8, **_num(8, scale="rating")), C_("Def OVR", 8, **_num(8, scale="rating")),
    ]
    cols += [C_(Team.RATING_LABELS[k], 10, **_num(10, scale="rating")) for k in Team.RATING_KEYS]
    cols += [
        C_("Brand", 8, **_num(8, fmt="0.0", scale="rating")),
        C_("Head Coach", 20, grp="status"), C_("OC", 18, grp="status"), C_("DC", 18, grp="status"),
        C_("Off Scheme", 14, grp="status"), C_("Def Scheme", 15, grp="status"),
        C_("Budget", 13, fmt="$#,##0", grp="money"), C_("Stadium", 28, grp="bio"),
        C_("Capacity", 10, fmt="#,##0", grp="bio"),
        C_("Facilities: Recruiting", 11, **_num(11, grp="bio")), C_("Facilities: Training", 11, **_num(11, grp="bio")),
        C_("Facilities: Stadium", 11, **_num(11, grp="bio")),
        C_("Home State", 8, grp="bio", align="center"), C_("Athletic Director", 18, grp="status"),
        C_("Draft Bonus", 8, fmt="0.0", grp="status", align="center"),
        C_("Recruiting Class Rank", 10, align="center", grp="yours"), C_("Commits", 8, align="center", grp="yours"),
        C_("Class Score", 9, fmt="0.0", grp="yours", align="center"),
        C_("Yours", 12, grp="yours", align="center"),
    ]
    rows = []
    for t, drank in _sorted_teams(league):
        fac = getattr(t, "fac", None) or {}
        c = t.coach
        rows.append([
            t.conference, t.division or "", drank, t.school, t.nickname, _rec(t), t.wins, t.losses, t.conf_wins,
            t.conf_losses, t.win_pct, t.points_for, t.points_against, t.points_for - t.points_against,
            R.rank_of(t), t.prestige, t.team_ovr, t.offense_ovr, t.defense_ovr,
            *[t.ratings[k] for k in Team.RATING_KEYS],
            t.__dict__.get("brand"),
            c.name if c else "", t.oc.name if getattr(t, "oc", None) else "",
            t.dc.name if getattr(t, "dc", None) else "",
            c.offense_scheme if c else "", c.defense_scheme if c else "",
            getattr(t, "budget", None), t.stadium, t.capacity,
            fac.get("recruiting"), fac.get("training"), fac.get("stadium"),
            t.home_state or "", (getattr(t, "ad", None) or {}).get("name", ""),
            getattr(t, "draft_bonus", None), class_rank.get(t), len(cy.commitments(t)), scores[t] or None,
            _owner(league, t, mine)])
    book.add("League", "Teams", "Every FBS program: record, ratings, coaches, budget, stadium, facilities, "
             "recruiting class. Sorted by conference and division standing.", cols, rows, freeze=4)


def _sheet_rankings(league, book):
    R = league.rankings
    prev = {t: i for i, t in enumerate(getattr(R, "last_order", []) or [], 1)}
    cols = [C_("Rank", 6, align="center"), C_("Last Week", 9, align="center"),
            C_("Move", 7, align="center", fmt="+0;-0;0"), C_("Team", 24), C_("Conference", 14),
            C_("Record", 8, align="center"), C_("Poll Points", 11, fmt="#,##0", align="center"),
            C_("Power Rating", 11, fmt="0.0", align="center", grp="rating")]
    rows = []
    for i, t in enumerate(R.order, 1):
        p = prev.get(t)
        rows.append([i, p, (p - i) if p else None, t.school, t.conference, _rec(t),
                     R.points.get(t), R.rating.get(t)])
    book.add("League", "Rankings", "The full national ranking of all FBS teams: poll-style order with poll points "
             "and movement (only the top 25 make the printed poll).", cols, rows, freeze=4)
    # Golden Helmet watch
    hs = list(getattr(R, "heisman", []) or [])
    if hs:
        cols = [C_("Rank", 6, align="center"), C_("Player", 22), C_("Team", 22), C_("Pos", 6, align="center"),
                C_("Class", 7, align="center"), C_("OVR", 6, **_num(6, scale="rating")),
                C_("Golden Helmet Score", 12, fmt="0.0", align="center"), C_("Season Line", 60)]
        rows = [[i, p.name, p.team.school if p.team else "", p.position, p.class_label, p.overall, sc, line]
                for i, (p, sc, line) in enumerate(hs, 1)]
        book.add("League", "Golden Helmet Watch", "This season's Golden Helmet race as the game sees it right now.", cols, rows,
                 freeze=2)


def _game_cols():
    return [
        C_("Season", 7, align="center"), C_("Week", 6, align="center"), C_("Round", 18), C_("Event", 26),
        C_("Date", 11, align="center"), C_("Kickoff", 9, align="center"), C_("Window", 10),
        C_("Away", 22), C_("Away Rank", 7, align="center"), C_("Away Seed", 7, align="center"),
        C_("Home", 22), C_("Home Rank", 7, align="center"), C_("Home Seed", 7, align="center"),
        C_("Neutral", 7, align="center"), C_("Venue", 30), C_("Status", 10, align="center"),
        C_("Away Score", 7, align="center", grp="game"), C_("Home Score", 7, align="center", grp="game"),
        C_("Winner", 22, grp="game"), C_("Margin", 7, align="center", grp="game"),
        C_("Total Pts", 7, align="center", grp="game"), C_("Conf Game", 7, align="center"),
        C_("OT", 5, align="center", grp="game"),
        *[C_(f"Away {q}", 6, align="center", grp="stat") for q in ("Q1", "Q2", "Q3", "Q4", "OT")],
        *[C_(f"Home {q}", 6, align="center", grp="stat") for q in ("Q1", "Q2", "Q3", "Q4", "OT")],
        C_("Away Yds", 7, align="center", grp="stat"), C_("Home Yds", 7, align="center", grp="stat"),
        C_("Away Pass", 7, align="center", grp="stat"), C_("Home Pass", 7, align="center", grp="stat"),
        C_("Away Rush", 7, align="center", grp="stat"), C_("Home Rush", 7, align="center", grp="stat"),
        C_("Away TO", 6, align="center", grp="stat"), C_("Home TO", 6, align="center", grp="stat"),
        C_("Attendance", 10, fmt="#,##0", grp="bio"), C_("Capacity", 10, fmt="#,##0", grp="bio"),
        C_("Weather", 30, grp="bio"), C_("Crowd Note", 22, grp="bio"),
    ]


def _game_row(g, year, league):
    played = g.played
    box = getattr(g, "box", None)
    home, away = g.home, g.away
    line = getattr(box, "line", None) or {}
    stats = getattr(box, "team_stats", None) or {}

    def ln(team):
        v = list(line.get(team, []) or [])
        v = (v + [None] * 5)[:5] if v else [None] * 5
        if len(line.get(team, []) or []) > 5:                    # extra overtimes fold into one number
            v[4] = sum(line[team][4:])
        return v

    def st(team, key):
        s = stats.get(team)
        return (s.get(key, 0) if s else None)

    ranks = getattr(g, "ranks", None) or {}
    seeds = getattr(g, "seeds", None) or {}
    wx = getattr(g, "wx", None) or {}
    ot = getattr(box, "ot_round", 0) if box is not None else 0
    winner = g.winner.school if played else ""
    margin = abs(g.home_score - g.away_score) if played else None
    date = getattr(g, "date", None)
    if getattr(g, "archived", False):
        venue = getattr(g, "site", "") or ""
    else:
        venue = getattr(g, "venue", "") or ""
    if g.game_type == "Regular Season":
        rnd = "Regular Season"
    else:
        rnd = g.game_type
    ev = getattr(g, "display_name", None) or g.bowl_name or ""
    a_ln, h_ln = ln(away), ln(home)
    return [
        year, g.week, rnd, ev, date.isoformat() if hasattr(date, "isoformat") else "",
        _kick_text(getattr(g, "kick", None)), getattr(g, "window", "") or "",
        away.school, ranks.get(away), seeds.get(away), home.school, ranks.get(home), seeds.get(home),
        "Yes" if getattr(g, "neutral", False) else "", venue, "Final" if played else "Scheduled",
        g.away_score, g.home_score, winner, margin, (g.home_score + g.away_score) if played else None,
        "Yes" if g.conference_game else "", "Yes" if ot else "",
        *a_ln, *h_ln,
        st(away, "total_yds"), st(home, "total_yds"), st(away, "pass_yds"), st(home, "pass_yds"),
        st(away, "rush_yds"), st(home, "rush_yds"), st(away, "turnovers"), st(home, "turnovers"),
        getattr(g, "attendance", None), getattr(g, "capacity", None), wx.get("summary", ""),
        getattr(g, "crowd_why", "") or ""]


def _sheet_schedule(league, book):
    games = [(w, g) for w in sorted(league.schedule) for g in league.schedule[w]]
    rows = [_game_row(g, league.year, league) for w, g in games]
    book.add("League", "Schedule", f"Every {league.year} game, played and upcoming, with scores, quarter lines, "
             "yardage, crowd and weather.", _game_cols(), rows, freeze=2)

    # the grid: one row per team, one column per week
    weeks = sorted(w for w in league.schedule if any(not getattr(g.home, "fcs", False) or
                                                     not getattr(g.away, "fcs", False) for g in league.schedule[w]))
    by_team = defaultdict(dict)
    for w in weeks:
        for g in league.schedule[w]:
            for t in (g.home, g.away):
                if not getattr(t, "fcs", False):
                    by_team[t][w] = g
    cols = [C_("Conference", 14), C_("Team", 24), C_("Record", 8, align="center")]
    cols += [C_(league.week_name(w) if w <= 13 else league.week_name(w), 20 if w > 13 else 19, align="center")
             for w in weeks]
    rows = []
    for t, _ in _sorted_teams(league):
        row = [t.conference, t.school, _rec(t)]
        for w in weeks:
            g = by_team[t].get(w)
            if g is None:
                row.append(Styled("BYE", color="A6A6A6"))
                continue
            opp = g.opponent_of(t)
            rk = (getattr(g, "ranks", None) or {}).get(opp)
            where = "vs " if g.home is t else "@ "
            if getattr(g, "neutral", False):
                where = "vs "
            name = f"{where}{'#%d ' % rk if rk else ''}{opp.school}"
            if g.played:
                won = g.winner is t
                txt = f"{'W' if won else 'L'} {g.score_for(t)}-{g.score_for(opp)} {name}"
                row.append(Styled(txt, WIN_FILL if won else LOSS_FILL, WIN_TEXT if won else LOSS_TEXT))
            else:
                row.append(name)
        rows.append(row)
    book.add("League", "Schedule Grid", "Each team's whole season on one row. Green = win, red = loss, plain = "
             "still to play. '@' is a road game.", cols, rows, freeze=2, zebra=False)


def _sheet_game_history(league, book):
    arc = getattr(league, "archive", {}) or {}
    rows = []
    for yr in sorted(arc):
        for g in arc[yr]:
            rows.append(_game_row(g, yr, league))
    if rows:
        book.add("History", "Game History", "Every game of every finished season the game kept "
                 "(scores, quarter lines, yardage, ranks, seeds, sites).", _game_cols(), rows, freeze=2)


def _sheet_game_logs(league, book):
    """Every player's stat line in every game: the biggest sheet, so it's optional."""
    def stat_iter():
        for yr, g in _all_games(league):
            box = getattr(g, "box", None)
            if box is None or not getattr(box, "stats", None):
                continue
            for p, cnt in box.stats.items():
                team = box.team_of(p)
                opp = g.away if team is g.home else g.home
                yield yr, g, team, opp, p, cnt
    keys = _stat_keys(cnt for *_, cnt in stat_iter())
    cols = [C_("Season", 7, align="center"), C_("Week", 6, align="center"), C_("Team", 22), C_("Opponent", 22),
            C_("Result", 12, align="center"), C_("#", 5, align="center"), C_("Player", 22), C_("Pos", 6, align="center"),
            C_("Class", 7, align="center")]
    cols += [C_(_stat_label(k), 9, align="center", grp="stat") for k in keys]

    def rows():
        for yr, g, team, opp, p, cnt in stat_iter():
            ts, os_ = g.score_for(team), g.score_for(opp)
            yield [yr, g.week, team.school, opp.school, f"{'W' if ts > os_ else 'L'} {ts}-{os_}",
                   p.number, p.name, p.position, p.class_label, *[cnt.get(k) or None for k in keys]]
    book.add("League", "Game Logs", "Every player's stat line in every game (this season and every archived "
             "season).", cols, rows(), freeze=7, stream=True)


def _all_games(league):
    for yr in sorted(getattr(league, "archive", {}) or {}):
        for g in league.archive[yr]:
            yield yr, g
    for w in sorted(league.schedule):
        for g in league.schedule[w]:
            if g.played:
                yield league.year, g


def _sheet_champions(league, book):
    cols = [C_("Season", 8, align="center"), C_("Champion", 22), C_("Runner-Up", 22),
            C_("Score", 10, align="center"), C_("Record", 9, align="center"), C_("Coach", 22), C_("Site", 40),
            C_("Note", 30), C_("Source", 14, align="center")]
    rows = [[c.season, c.champion, c.runner_up, f"{c.score}-{c.opp_score}", c.record, c.coach, c.site, c.note,
             "Real history" if c.real else "This world"] for c in sorted(league.champions, key=lambda c: c.season)]
    book.add("History", "Champions", "National champions, real history first and then this world's.", cols, rows,
             freeze=2)


def _sheet_team_history(league, book):
    polls = getattr(league, "final_polls", {}) or {}
    cols = [C_("Team", 24), C_("Conference", 14), C_("Season", 8, align="center"), C_("Record", 9, align="center"),
            C_("W", 5, align="center"), C_("L", 5, align="center"), C_("Conf Record", 10, align="center"),
            C_("Win %", 7, fmt="0.000", align="center"), C_("Final Poll Rank", 9, align="center"),
            C_("Season Score", 9, fmt="0.0", align="center", grp="rating"), C_("Achievements", 60)]
    rows = []
    for t, _ in _sorted_teams(league):
        scores = {y: s for y, s in (getattr(t, "season_scores", []) or [])}
        for rec in t.historical_records:
            yr, w, l, cw, cl, ach = rec[:6]
            conf = rec[6] if len(rec) > 6 else t.conference
            if not (w or l or ach):
                continue                                          # the pre-game burn-in years have no games
            fin = polls.get(yr)
            rank = fin.index(t.school) + 1 if fin and t.school in fin else None
            rows.append([t.school, conf, yr, f"{w}-{l}", w, l, f"{cw}-{cl}", w / (w + l) if w + l else None,
                         rank, scores.get(yr), ", ".join(ach)])
        if t.wins + t.losses:
            rows.append([t.school, t.conference, f"{league.year}*", _rec(t), t.wins, t.losses, t.conf_record,
                         t.win_pct, None, None,
                         ", ".join([*(getattr(t, "achievements", []) or []), "season in progress"])])
    book.add("History", "Team History", "Every program's season-by-season record, final poll rank and honors.",
             cols, rows, freeze=3)


def _sheet_final_polls(league, book):
    polls = getattr(league, "final_polls", {}) or {}
    if not polls:
        return
    cols = [C_("Season", 8, align="center"), C_("Rank", 6, align="center"), C_("Team", 24)]
    rows = [[y, i, s] for y in sorted(polls) for i, s in enumerate(polls[y], 1)]
    book.add("History", "Final Polls", "Each finished season's final top 25.", cols, rows, freeze=3)


def _sheet_awards(league, book):
    aw = getattr(league, "awards", {}) or {}
    cols = [C_("Season", 8, align="center"), C_("Award", 30), C_("Player / Coach", 24), C_("Team", 22),
            C_("Pos", 7, align="center"), C_("Detail", 60)]
    rows = []
    for yr in sorted(aw):
        a = aw[yr]
        if a.get("heisman"):
            p, t, line = a["heisman"]
            rows.append([yr, "Golden Helmet", p.name, t.school if t else "", p.position, line])
        for name, p, t, line in a.get("positional", []):
            rows.append([yr, name, p.name, t.school, p.position, line])
        if a.get("freshman"):
            p, t, line = a["freshman"]
            rows.append([yr, "Freshman of the Year", p.name, t.school, p.position, line])
        if a.get("coach"):
            name, t, rec = a["coach"]
            rows.append([yr, "Coach of the Year", name, t.school, "", rec])
        for label, key in (("First-team All-American", "first"), ("Second-team All-American", "second")):
            for grp, p, t in a.get(key, []):
                rows.append([yr, label, p.name, t.school, p.position, grp])
    book.add("History", "Awards", "Golden Helmet, position awards, freshman and coach of the year, and All-America "
             "teams for every season.", cols, rows, freeze=3)


def _sheet_draft(league, book):
    drafts = getattr(league, "drafts", {}) or {}
    cols = [C_("Season", 8, align="center"), C_("Round", 6, align="center"), C_("Pick", 6, align="center"),
            C_("Overall", 7, align="center"), C_("Pro League Team", 20), C_("Player", 22), C_("Pos", 6, align="center"),
            C_("School", 22), C_("OVR", 6, **_num(6, scale="rating")), C_("Class", 7, align="center"),
            C_("Left Early", 9, align="center")]
    rows = [[y, x["round"], x["pick"], x["overall_pick"], x["nfl"], x["name"], x["pos"], x["school"], x["ovr"],
             x["cls"], "Yes" if x.get("early") else ""] for y in sorted(drafts) for x in drafts[y]]
    book.add("History", "Pro League Draft", "Every draft pick from every season: round, pick, team, school.", cols, rows,
             freeze=6)


def _sheet_series(league, book):
    series = getattr(league, "series", {}) or {}
    cols = [C_("Team A", 22), C_("Team B", 22), C_("Meetings", 9, align="center"), C_("A Wins", 8, align="center"),
            C_("B Wins", 8, align="center"), C_("First Meeting", 10, align="center"),
            C_("Last Meeting", 10, align="center"), C_("Last Winner", 22), C_("Last Score", 10, align="center")]
    rows = []
    for key, meets in series.items():
        if not meets:
            continue
        a, b = key.split("|")
        aw = sum(1 for m in meets if m.winner == a)
        last = max(meets, key=lambda m: (m.year, m.week))
        rows.append([a, b, len(meets), aw, len(meets) - aw, min(m.year for m in meets), last.year, last.winner,
                     f"{last.wscore}-{last.lscore}"])
    rows.sort(key=lambda r: (-r[2], r[0]))
    book.add("History", "Series", "Head-to-head records for every pair of teams that has met in this world.",
             cols, rows, freeze=2)


def _dict_rows(items, first):
    """Flatten a list of dicts to scalar columns: `first` keys first, then anything else."""
    keys = list(first)
    for d in items:
        for k, v in d.items():
            if k not in keys and isinstance(v, (str, int, float, bool)) or (k not in keys and v is None):
                keys.append(k)
    return keys


def _sheet_carousel(league, book):
    moves = getattr(league, "carousel_moves", {}) or {}
    rows = []
    for yr in sorted(moves):
        for m in moves[yr]:
            at, car = m.get("at") or {}, m.get("career") or {}
            rows.append([yr, m.get("week"), (m.get("side") or "").upper(), m.get("kind"), m.get("school"),
                         m.get("conf"), m.get("prestige"), m.get("coach"), m.get("age"), m.get("tenure"),
                         f"{at.get('w', 0)}-{at.get('l', 0)}" if at else "",
                         f"{car.get('w', 0)}-{car.get('l', 0)}" if car else "", m.get("dest"), m.get("note"),
                         "Yes" if m.get("user") else ""])
    cols = [C_("Season", 8, align="center"), C_("Week", 6, align="center"), C_("Move", 7, align="center"),
            C_("Kind", 12), C_("School", 22), C_("Conference", 14), C_("Prestige", 8, align="center"),
            C_("Coach", 22), C_("Age", 5, align="center"), C_("Years There", 8, align="center"),
            C_("Record There", 10, align="center"), C_("Career Record", 11, align="center"),
            C_("Destination", 22), C_("Note", 44), C_("You", 5, align="center")]
    if rows:
        book.add("History", "Carousel", "The coaching carousel: every firing, retirement and hire.", cols, rows,
                 freeze=5)
    sm = getattr(league, "staff_moves", {}) or {}
    items = [dict(m, year=yr) for yr in sorted(sm) for m in sm[yr] if isinstance(m, dict)]
    if items:
        keys = _dict_rows(items, ["year", "week", "school", "role", "coach", "kind", "note"])
        cols = [C_(k.replace("_", " ").title(), 22 if k in ("school", "coach", "note") else 12) for k in keys]
        book.add("History", "Staff Moves", "Coordinator hires and departures.", cols,
                 [[d.get(k) for k in keys] for d in items], freeze=1)


# ═══ Player sheets ══════════════════════════════════════════════════════════

def _origin(p):
    if getattr(p, "juco", None):
        return f"JUCO ({p.juco})"
    if getattr(p, "intl", None):
        return f"International ({p.intl})"
    if p.prev_school:
        return "Transfer"
    if p.walk_on:
        return "Walk-on"
    return "High school"


def _sheet_rosters(league, book):
    from models import FUNDAMENTAL_ABBR, POSITIONS, STARTING_LINEUP
    poss = list(POSITIONS)
    cols = [
        C_("Team", 22), C_("Conf", 12), C_("#", 5, align="center"), C_("Player", 22), C_("Pos", 6, align="center"),
        C_("Class", 7, align="center"),
        C_("OVR", 6, **_num(6, scale="rating")), C_("Potential", 9, align="center", grp="rating"),
        C_("Potential #", 9, **_num(9, scale="rating")), C_("Pos Ceiling", 9, fmt="0.00", grp="rating", align="center"),
        *[C_(FUNDAMENTAL_ABBR[f], 6, **_num(6, scale="rating")) for f in
          ("strength", "speed", "quickness", "iq", "injury", "playmaker")],
        C_("Durability", 14, grp="rating"),
        C_("Depth", 6, align="center", grp="role"), C_("Starter", 7, align="center", grp="role"),
        C_("Best Other Pos", 9, align="center", grp="role"), C_("OVR There", 8, **_num(8, grp="role", scale="rating")),
        C_("Height", 7, align="center", grp="bio"), C_("Weight", 7, align="center", grp="bio"),
        C_("Home State", 8, align="center", grp="bio"), C_("High School", 22, grp="bio"),
        C_("HS Stars", 7, align="center", grp="bio"), C_("Recruit Rank", 9, align="center", grp="bio"),
        C_("Origin", 20, grp="bio"), C_("Prev School", 20, grp="bio"), C_("Transfers", 8, align="center", grp="bio"),
        C_("Seasons Developed", 10, align="center", grp="bio"), C_("Redshirt", 8, align="center", grp="bio"),
        C_("Morale", 7, align="center", grp="status", fmt="0"), C_("Injury", 24, grp="status"),
        C_("Games Out", 8, align="center", grp="status"), C_("Traits", 26, grp="status"),
        C_("NIL / yr", 11, fmt="$#,##0", grp="money"), C_("Honors", 22, grp="status"),
        C_("GP (season)", 9, align="center", grp="stat"), C_("GP (career)", 9, align="center", grp="stat"),
        C_("Sub-skills", 46, grp="status"),
        *[C_(f"Fit: {p}", 7, fmt="0.00", grp="prof", align="center", scale="prof") for p in poss],
    ]
    rows = []
    for t, _ in _sorted_teams(league):
        depth = {}
        for pos in poss:
            for i, p in enumerate(t.players_at(pos), 1):
                depth[id(p)] = i
        for p in sorted(t.roster, key=lambda x: (poss.index(x.position), depth.get(id(x), 99))):
            d = depth.get(id(p), 99)
            alt, alt_ovr = p.best_alternate()
            inj = p.inj_desc if getattr(p, "inj_games", 0) > 0 else ""
            out = f"out for the season" if getattr(p, "inj_games", 0) >= 99 else ""
            honors = []
            if getattr(p, "all_american", 0):
                honors.append(f"All-American x{p.all_american}")
            if getattr(p, "generational", False):
                honors.append("Generational")
            sub = "; ".join(f"{pos}: " + ", ".join(f"{k} {v:+.2f}" for k, v in d_.items())
                            for pos, d_ in (getattr(p, "subprof", None) or {}).items())
            fund = p.fundamentals
            rows.append([
                t.school, t.conference, p.number, p.name, p.position, p.class_label, p.overall, p.potential_grade,
                p.potential, p.prof_ceiling,
                fund["strength"], fund["speed"], fund["quickness"], fund["iq"], fund["injury"], fund["playmaker"],
                p.durability, d, "Yes" if d <= STARTING_LINEUP.get(p.position, 0) else "", alt, alt_ovr,
                p.height_str, p.weight, p.home_state or "", getattr(p, "hs_name", "") or "", p.hs_stars,
                p.recruit_rank, _origin(p), p.prev_school or "", p.transfers, p.seasons_developed,
                "Yes" if p.redshirt else "", getattr(p, "morale", None),
                (inj or "") + (f" ({p.inj_games} games)" if inj and p.inj_games < 99 else (" (season)" if inj else "")),
                (p.inj_games if p.inj_games > 0 else None), ", ".join(_trait_labels(p)), p.nil or None,
                ", ".join(honors), p.games_played, p.career_games + p.games_played, sub,
                *[p.proficiency.get(pos) for pos in poss]])
    book.add("Players", "Rosters", "Every FBS player: ratings, six fundamentals, all 11 position fits, "
             "depth chart spot, bio, injury, morale, NIL, traits.", cols, rows, freeze=4)


def _sheet_player_stats(league, book):
    players = [(t, p) for t, _ in _sorted_teams(league) for p in t.roster]
    counters = []
    for t, p in players:
        counters += list(p.yearly_stats.values()) + [p.season_stats]
    keys = _stat_keys(counters)
    head = [C_("Season", 8, align="center"), C_("Team", 22), C_("Player", 22), C_("Pos", 6, align="center"),
            C_("Class", 7, align="center"), C_("GP", 5, align="center", grp="stat")]
    head += [C_(_stat_label(k), 9, align="center", grp="stat") for k in keys]
    rows = []
    for t, p in players:
        yg = getattr(p, "yearly_games", {}) or {}
        for yr in sorted(p.yearly_stats):
            cnt = p.yearly_stats[yr]
            rows.append([yr, t.school, p.name, p.position, p.class_label, yg.get(yr),
                         *[cnt.get(k) or None for k in keys]])
        if any(p.season_stats.values()):
            rows.append([league.year, t.school, p.name, p.position, p.class_label, p.games_played,
                         *[p.season_stats.get(k) or None for k in keys]])
    rows.sort(key=lambda r: (-r[0], r[1], r[2]))
    book.add("Players", "Player Stats", "One row per player per season (current roster players): every "
             "stat the game tracks.", head, rows, freeze=3)

    head = [C_("Team", 22), C_("Player", 22), C_("Pos", 6, align="center"), C_("Class", 7, align="center"),
            C_("Seasons", 8, align="center", grp="stat"), C_("Games", 6, align="center", grp="stat")]
    head += [C_(_stat_label(k), 9, align="center", grp="stat") for k in keys]
    rows = []
    for t, p in players:
        total = Counter(p.career_stats)
        for k, v in p.season_stats.items():
            total[k] = max(total[k], v) if k.endswith("_long") else total[k] + v
        if not any(total.values()):
            continue
        seasons = len(p.yearly_stats) + (1 if any(p.season_stats.values()) else 0)
        rows.append([t.school, p.name, p.position, p.class_label, seasons, p.career_games + p.games_played,
                     *[total.get(k) or None for k in keys]])
    book.add("Players", "Career Stats", "Career totals for every player on a roster, this season included.", head,
             rows, freeze=2)


def _sheet_rating_history(league, book):
    players = [(t, p) for t, _ in _sorted_teams(league) for p in t.roster]
    years = sorted({y for _, p in players for y, _ in p.history})
    cols = [C_("Team", 22), C_("Player", 22), C_("Pos", 6, align="center"), C_("Class", 7, align="center"),
            *[C_(str(y), 7, **_num(7, scale="rating")) for y in years],
            C_("Change", 8, fmt="+0;-0;0", align="center"), C_("Potential", 9, align="center", grp="rating")]
    rows = []
    for t, p in players:
        h = dict(p.history)
        vals = [h.get(y) for y in years]
        known = [v for v in vals if v is not None]
        rows.append([t.school, p.name, p.position, p.class_label, *vals,
                     (known[-1] - known[0]) if len(known) > 1 else None, p.potential_grade])
    book.add("Players", "Rating History", "Each player's overall rating, year by year (freshman year, then "
             "after each offseason).", cols, rows, freeze=2)


def _sheet_player_events(league, book):
    cols = [C_("Team", 22), C_("Player", 22), C_("Pos", 6, align="center"), C_("Season", 8, align="center"),
            C_("Event", 70)]
    rows = []
    for t, _ in _sorted_teams(league):
        for p in t.roster:
            for yr in sorted(p.events):
                for ev in p.events[yr]:
                    rows.append([t.school, p.name, p.position, yr, ev])
    book.add("Players", "Player Events", "Every player's story: signings, redshirts, honors, transfers, "
             "injuries, draft picks.", cols, rows, freeze=2)


def _coach_personality(c):
    try:
        import carousel
        return carousel.PERSONALITIES[c.personality][0]
    except Exception:
        return str(getattr(c, "personality", "") or "").replace("_", " ").title()


def _sheet_coaches(league, book):
    from models import Coach
    cols = [C_("Team", 22), C_("Conf", 12), C_("Role", 6, align="center"), C_("Name", 22),
            C_("Age", 5, align="center"), C_("Overall", 8, **_num(8, scale="rating"))]
    cols += [C_(Coach.RATING_LABELS[k], 12, **_num(12, scale="rating")) for k in Coach.RATING_KEYS]
    cols += [C_("Off Scheme", 14, grp="status"), C_("Def Scheme", 15, grp="status"),
             C_("Aggression", 9, **_num(9, grp="status")), C_("Traits", 26, grp="status"),
             C_("Personality", 12, grp="status"), C_("Seat Heat", 8, **_num(8, grp="status")),
             C_("Hired", 7, align="center", grp="bio"), C_("Background", 30, grp="bio"),
             C_("Alma Mater", 18, grp="bio"), C_("Salary", 12, fmt="$#,##0", grp="money"),
             C_("Contract Yrs", 8, align="center", grp="money"), C_("Contract End", 8, align="center", grp="money"),
             C_("Buyout %", 8, fmt="0%", align="center", grp="money"),
             C_("Career Earnings", 13, fmt="$#,##0", grp="money"), C_("Past Stops", 60, grp="bio")]
    rows = []

    def add(t, c, role):
        k = getattr(c, "contract", None) or {}
        stops = "; ".join(f"{s.get('job', '')} at {s.get('school', '')} ({s.get('start', '')}-{s.get('end', '')})"
                          for s in (getattr(c, "stops", None) or []))
        rows.append([t.school if t else "", t.conference if t else "", role, c.name, getattr(c, "age", None),
                     c.overall, *[c.ratings[x] for x in Coach.RATING_KEYS], c.offense_scheme, c.defense_scheme,
                     c.aggression, ", ".join(_trait_labels(c)), _coach_personality(c),
                     getattr(c, "seat", None), getattr(c, "hired_year", None), getattr(c, "origin", ""),
                     getattr(c, "alma_mater", "") or "", k.get("salary"), k.get("years"), k.get("end"),
                     k.get("buyout"), getattr(c, "career_earnings", None) or None, stops])
    for t, _ in _sorted_teams(league):
        for role, c in (("HC", t.coach), ("OC", getattr(t, "oc", None)), ("DC", getattr(t, "dc", None))):
            if c is not None:
                add(t, c, role)
    for c in getattr(league, "coach_pool", []) or []:
        if hasattr(c, "ratings"):
            add(None, c, "Pool")
    book.add("Players", "Coaches", "Every head coach and coordinator (plus unemployed coaches in the pool): "
             "ratings, schemes, contracts, background.", cols, rows, freeze=4)


def _sheet_portal(league, book):
    rep = getattr(league, "last_portal", None)
    if rep is None:
        return
    cols = [C_("Season", 8, align="center"), C_("Player", 22), C_("Pos", 6, align="center"),
            C_("OVR", 6, **_num(6, scale="rating")), C_("From", 22), C_("To", 22), C_("Why He Left", 34),
            C_("Depth Chart Spot", 9, align="center"), C_("Suitors", 8, align="center"),
            C_("NIL Deal", 11, fmt="$#,##0", grp="money")]
    dest = {id(e): t for e, t in getattr(rep, "moves", [])}
    rows = []
    for e in rep.entries:
        to = dest.get(id(e)) or getattr(e, "destination", None)
        rows.append([rep.year, e.player.name, e.position, e.overall, getattr(e.origin, "school", e.origin),
                     getattr(to, "school", to) if to else "Unsigned", e.reason, e.depth, len(e.suitors),
                     (getattr(rep, "deals", {}) or {}).get(e)])
    book.add("Players", "Transfer Portal", f"The {rep.year} transfer portal: who entered, why, and where he "
             "landed.", cols, rows, freeze=2)


# ═══ Recruiting sheets ══════════════════════════════════════════════════════

def _recruit_status(r):
    if r.signed:
        return "Signed"
    return "Committed" if r.committed_to is not None else "Uncommitted"


def _sheet_recruits(league, book, me, hidden):
    import recruit_plus as rp
    from recruiting_data import PERSONALITIES, PRIORITY_LABELS, STATES
    cy = league.recruiting
    cols = [
        C_("Nat'l Rank", 8, align="center"), C_("Name", 22), C_("Pos", 6, align="center"),
        C_("Stars", 6, align="center"), C_("Type", 8, align="center"), C_("High School / School", 26),
        C_("State", 6, align="center"), C_("Region", 11),
        C_("Height", 7, align="center", grp="bio"), C_("Weight", 7, align="center", grp="bio"),
        C_("Personality", 12, grp="bio"), C_("Priority 1", 18, grp="bio"), C_("Priority 2", 18, grp="bio"),
        C_("Priority 3", 18, grp="bio"),
        C_("Status", 12, grp="status"), C_("Committed To", 22, grp="status"),
        C_("Commit Week", 8, align="center", grp="status"), C_("Commit Type", 9, align="center", grp="status"),
        C_("Silent Commit", 8, align="center", grp="status"), C_("Early Signee", 8, align="center", grp="status"),
        C_("Offers", 7, align="center", grp="status"), C_("Official Visits", 30, grp="status"),
        C_("Leader", 22, grp="status"), C_("Lead Margin", 8, fmt="0.0", align="center", grp="status"),
        C_("Crystal Ball", 24, grp="status"), C_("Attention", 8, align="center", grp="status"),
        C_("Top 5 Schools (interest)", 60, grp="status"), C_("Offered By", 60, grp="status"),
    ]
    if hidden:
        cols += [C_("True Stars", 8, **_num(8, grp="hidden")), C_("True OVR", 8, **_num(8, grp="hidden", scale="rating")),
                 *[C_(a, 6, **_num(6, grp="hidden", scale="rating")) for a in
                   ("STR", "SPD", "QCK", "IQ", "DUR", "PLY")],
                 C_("Fit at Pos", 8, fmt="0.00", grp="hidden", align="center", scale="prof"),
                 C_("Pos Ceiling", 8, fmt="0.00", grp="hidden", align="center"),
                 C_("Potential", 8, grp="hidden", align="center"), C_("Potential #", 8, **_num(8, grp="hidden")),
                 C_("Generational", 9, grp="hidden", align="center")]
    hot = _hot(league)
    if hot:
        cols += [C_("On Boards Of", 24, grp="yours"), C_("Offered By (Players)", 24, grp="yours")]
    if me is not None:
        cols += [C_("On Your Board", 8, grp="yours", align="center"), C_("You Offered", 8, grp="yours", align="center"),
                 C_("Your Interest", 9, **_num(9, grp="yours", fmt="0.0", scale="interest")),
                 C_("Your Standing", 14, grp="yours"), C_("Relationship", 10, **_num(10, grp="yours", fmt="0.0")),
                 C_("Scouting (0-3)", 9, **_num(9, grp="yours")), C_("Scouted OVR Range", 12, grp="yours", align="center"),
                 C_("Priorities You Know", 40, grp="yours")]
    board = set(map(id, me.recruiting_targets)) if me is not None else set()
    rows = []
    kinds = {"hs": "HS", "juco": "JUCO", "intl": "Intl"}
    for r in cy.pool:
        p = r.player
        kind = rp.g(r, "kind", "hs")
        ov = rp.g(r, "ov") or {}
        tops = "; ".join(f"{t.school} {v:.1f}" for t, v in sorted(r.interest.items(), key=lambda x: -x[1])[:5])
        offered = ", ".join(sorted(t.school for t in r.offers))
        cb = rp.crystal(r, getattr(league, "recruiting", None))
        leader = r.leader()
        pri = [PRIORITY_LABELS.get(k, k) for k in r.priorities] + ["", "", ""]
        row = [
            r.national_rank, p.name, r.position, r.stars, kinds.get(kind, kind), rp.origin_line(r), r.home_state,
            r.region, p.height_str, p.weight, PERSONALITIES[r.personality]["label"], pri[0], pri[1], pri[2],
            _recruit_status(r), r.committed_to.school if r.committed_to else "", r.commit_week,
            (rp.g(r, "commit_kind") or "").title() if r.committed_to else "",
            "Yes" if rp.g(r, "silent", False) else "", "Yes" if rp.g(r, "early", False) else "", len(r.offers),
            "; ".join(f"{t.school} wk {w}" for t, w in ov.items()), leader.school if leader else "",
            r.lead_margin() if r.interest else None, f"{cb[0].school} ({cb[1]}%)" if cb else "", r.attention,
            tops, offered]
        if hidden:
            f = p.fundamentals
            row += [rp.truth_stars(r), r.true_grade, f["strength"], f["speed"], f["quickness"], f["iq"],
                    f["injury"], f["playmaker"], p.proficiency.get(r.position), p.prof_ceiling, p.potential_grade,
                    p.potential, "Yes" if getattr(p, "generational", False) else ""]
        if hot:
            import hotseat
            hum = hotseat.seats(league)
            row += [", ".join(s_.name for s_ in hum if r in (getattr(hotseat.seat_team(league, s_), "recruiting_targets", None) or [])),
                    ", ".join(s_.name for s_ in hum if hotseat.seat_team(league, s_) in r.offers)]
        if me is not None:
            lo, hi = r.scouting_range(me)
            row += [
                "Yes" if id(r) in board else "", "Yes" if me in r.offers else "", r.interest.get(me, 0.0) or None,
                r.standing(me) if r.interest.get(me, 0) else "", cy.relationship.get((me, r), 0.0) or None,
                r.scout.get(me, 0), f"{lo}-{hi}" if r.scout.get(me, 0) else "",
                ", ".join(PRIORITY_LABELS.get(k, k) for k in rp.known(r, me))]
        rows.append(row)
    book.add("Recruiting", "Recruits", f"The whole {league.year} recruiting pool: high school, JUCO and "
             "international prospects, who's after them, where they stand" +
             (", and their hidden true ratings." if hidden else "."), cols, rows, freeze=2)


def _sheet_interest(league, book, me):
    import recruit_plus as rp
    cy = league.recruiting
    cols = [C_("Nat'l Rank", 8, align="center"), C_("Recruit", 22), C_("Pos", 6, align="center"),
            C_("Stars", 6, align="center"), C_("School", 22), C_("His Rank for School", 9, align="center"),
            C_("Interest", 9, **_num(9, fmt="0.0", grp="status", scale="interest")),
            C_("Offered", 8, align="center"), C_("Relationship", 10, **_num(10, grp="status", fmt="0.0")),
            C_("Scouting (0-3)", 9, align="center"), C_("Official Visit Week", 9, align="center"),
            C_("Committed Here", 9, align="center")]
    rows = []
    for r in cy.pool:
        ov = rp.g(r, "ov") or {}
        for i, (t, v) in enumerate(sorted(r.interest.items(), key=lambda x: -x[1]), 1):
            if v < 1:
                continue
            rows.append([r.national_rank, r.player.name, r.position, r.stars, t.school, i, v,
                         "Yes" if t in r.offers else "", cy.relationship.get((t, r), 0.0) or None,
                         r.scout.get(t, 0) or None, ov.get(t), "Yes" if r.committed_to is t else ""])
    book.add("Recruiting", "Recruit Interest", "Who is after whom: every school's interest level in every "
             "recruit (one row per recruit per school).", cols, rows, freeze=2)


def _sheet_boards(league, book, me):
    cy = league.recruiting
    cols = [C_("Team", 22), C_("Conf", 12), C_("Slot", 6, align="center"), C_("Recruit", 22),
            C_("Pos", 6, align="center"), C_("Stars", 6, align="center"), C_("Nat'l Rank", 8, align="center"),
            C_("Status", 12, grp="status"), C_("Committed To", 22, grp="status"),
            C_("Interest", 9, **_num(9, fmt="0.0", grp="status", scale="interest")),
            C_("Standing", 14, grp="status"), C_("Offered", 8, align="center"),
            C_("Relationship", 10, **_num(10, fmt="0.0", grp="status")),
            C_("Scouting (0-3)", 9, align="center"), C_("Yours", 12, align="center", grp="yours")]
    teams = [t for t, _ in _sorted_teams(league)]
    humans = _human_teams(league) or ([me] if me is not None else [])
    for h in reversed(humans):
        if h in teams:
            teams.remove(h)
            teams.insert(0, h)                                  # human boards first
    rows = []
    for t in teams:
        board = cy.board_for(t) if any(t is h for h in humans) else list(cy.by_team.get(t, []))
        for i, r in enumerate(board, 1):
            rows.append([t.school, t.conference, i, r.player.name, r.position, r.stars, r.national_rank,
                         _recruit_status(r), r.committed_to.school if r.committed_to else "",
                         r.interest.get(t, 0.0) or None, r.standing(t) if r.interest.get(t, 0) else "",
                         "Yes" if t in r.offers else "", cy.relationship.get((t, r), 0.0) or None,
                         r.scout.get(t, 0) or None, _owner(league, t, me)])
    book.add("Recruiting", "Recruiting Boards", "Every program's recruiting board, ordered as the staff has it. "
             "Yours comes first.", cols, rows, freeze=4)


def _sheet_classes(league, book, me):
    import recruiting
    cy = league.recruiting
    scores = {t: recruiting.class_points(cy.commitments(t)) for t in league.teams}
    cols = [C_("Rank", 6, align="center"), C_("Team", 22), C_("Conf", 12), C_("Commits", 8, align="center"),
            C_("Class Score", 10, fmt="0.0", align="center"), C_("Avg Stars", 8, fmt="0.00", align="center"),
            C_("5-Star", 7, align="center"), C_("4-Star", 7, align="center"), C_("3-Star", 7, align="center"),
            C_("2-Star", 7, align="center"), C_("Hard Commits", 9, align="center"),
            C_("Best Commit", 30), C_("Yours", 12, align="center", grp="yours")]
    ordered = sorted(league.teams, key=lambda t: (-scores[t], t.school))
    rows = []
    rank = 0
    for t in ordered:
        cm = cy.commitments(t)
        if cm:
            rank += 1
        top = max(cm, key=lambda r: (r.stars, -r.national_rank), default=None)
        stars = Counter(r.stars for r in cm)
        rows.append([rank if cm else None, t.school, t.conference, len(cm), scores[t] or None,
                     (sum(r.stars for r in cm) / len(cm)) if cm else None, stars[5] or None, stars[4] or None,
                     stars[3] or None, stars[2] or None,
                     sum(1 for r in cm if getattr(r, "commit_kind", None) == "hard" or r.signed) or None,
                     f"{top.player.name} ({top.stars}★ {top.position})" if top else "", _owner(league, t, me)])
    book.add("Recruiting", "Class Rankings", "Recruiting class rankings: who has committed where, the star "
             "breakdown and the best get.", cols, rows, freeze=2)


def _sheet_signing_history(league, book):
    cols = [C_("Team", 22), C_("Signed For", 9, align="center"), C_("Player", 22), C_("Pos", 6, align="center"),
            C_("Stars", 6, align="center"), C_("Nat'l Rank", 9, align="center"), C_("Type", 8, align="center"),
            C_("High School / School", 26), C_("Early Signee", 8, align="center"),
            C_("Walk-On Invite", 9, align="center"), C_("OVR Now", 8, **_num(8, scale="rating")),
            C_("Class Now", 8, align="center"), C_("Still on Roster", 9, align="center"),
            C_("Drafted", 22, grp="status")]
    kinds = {"hs": "HS", "juco": "JUCO", "intl": "Intl"}
    rows = []
    for t, _ in _sorted_teams(league):
        for e in (t.__dict__.get("signing_book") or []):
            p = e["player"]
            dr = getattr(p, "drafted", None)
            here = p in t.roster
            rows.append([t.school, e["year"], p.name, e["pos"], e["stars"], e["rank"], kinds.get(e["kind"], e["kind"]),
                         e["hs"], "Yes" if e["early"] else "", "Yes" if e["pwo"] else "",
                         p.overall if here else None, p.class_label if here else "", "Yes" if here else "",
                         f"{dr[0]}: round {dr[1]}, pick {dr[2]}" if dr else ""])
    book.add("Recruiting", "Signing History", "Every class each program has signed (recent classes): who "
             "signed, how good he was, where he is now.", cols, rows, freeze=3)


def _sheet_recruit_news(league, book):
    news = list(league.recruiting.news)
    if not news:
        return
    cols = [C_("Week", 6, align="center"), C_("Type", 10), C_("Headline", 120)]
    book.add("Recruiting", "Recruiting News", "The recruiting wire for this class.", cols,
             [[w, k, t] for w, k, t in news], freeze=1)


def _sheet_orders(league, book, me):
    import recruit_plus as rp
    from recruiting_data import ACTIONS, PRIORITY_LABELS
    cy = league.recruiting
    cols = [C_("#", 5, align="center"), C_("Recruit", 22), C_("Pos", 6, align="center"), C_("Stars", 6, align="center"),
            C_("Nat'l Rank", 8, align="center"), C_("Action", 24), C_("Repeats", 28), C_("Pitch", 20),
            C_("Times Run", 8, align="center"), C_("Last Run", 10, align="center"), C_("Added", 10, align="center"),
            C_("Hours Each", 8, align="center"), C_("Status", 22), C_("Your Interest", 9, fmt="0.0", align="center"),
            C_("You Offered", 8, align="center", grp="yours")]
    rows = []
    for i, e in enumerate(rp.queue(cy, me), 1):
        r, a = e["r"], e["a"]
        status, _ok = rp._check(cy, me, e, (league.year, league.week))
        rows.append([i, r.player.name, r.position, r.stars, r.national_rank, ACTIONS[a][0], rp.rule_text(e),
                     "best he cares about" if e.get("pitch") in (None, "auto") else PRIORITY_LABELS.get(e["pitch"], e["pitch"]),
                     e["runs"], f"{e['last'][0]} wk {e['last'][1]}" if e.get("last") else "",
                     f"{e['added'][0]} wk {e['added'][1]}" if e.get("added") else "", rp.action_cost(me, a),
                     status, r.interest.get(me, 0.0) or None, "Yes" if me in r.offers else ""])
    book.add("You", "Recruit Orders", "Your standing orders: the recruiting queue that runs at the end of each "
             "week, in order.", cols, rows, freeze=2)


def _sheet_recruit_actions(league, book, me):
    log = list(getattr(league, "recruit_actions", []) or [])
    cols = [C_("Season", 8, align="center"), C_("Week", 6, align="center"), C_("Recruit", 22),
            C_("Pos", 6, align="center"), C_("Stars", 6, align="center"), C_("Nat'l Rank", 8, align="center"),
            C_("Action", 26), C_("Hours", 6, align="center"), C_("Pitch", 16), C_("Chosen By", 18),
            C_("Result", 70), C_("Interest After", 9, fmt="0.0", align="center", grp="status"),
            C_("Relationship After", 10, fmt="0.0", align="center", grp="status")]
    rows = [[a["year"], a["week"], a["recruit"], a["pos"], a["stars"], a["rank"], a["action"], a["hours"],
             a.get("pitch", ""), a.get("source", "you"), a["result"], a.get("interest"), a.get("relationship")]
            for a in log]
    book.add("You", "Recruit Actions", "Every recruiting move you made: calls, offers, visits, camps, walk-on "
             "invites, standing orders. (Recorded from this build on; older saves start empty.)", cols, rows, freeze=3)


def _sheet_recruit_notes(league, book, me):
    import recruit_plus as rp
    S = rp.S(league.recruiting)
    rows = []
    for (team, r), entries in S["log"].items():
        if team is me:
            for wk, text in entries:
                rows.append([league.year, wk, r.player.name, r.position, r.stars, "Story", text])
    for rep in S["visits"].get(me, []):
        rows.append([league.year, rep.get("week"), rep.get("name") or rep.get("recruit", ""), "", None, "Official visit",
                     rep.get("headline", "")])
    for text in S["weekly_note"].get(me, []):
        rows.append([league.year, league.week, "", "", None, "This week", text])
    for summ in ([S["summary"].get(me)] if S["summary"].get(me) else []):
        wk = summ.get("week")
        for name, act, cost, msg in summ.get("ran", []):
            rows.append([league.year, wk, name, "", None, "Standing order ran", f"{act} ({cost}h)"])
        for name, act, cost in summ.get("cut", []):
            rows.append([league.year, wk, name, "", None, "Standing order cut", f"{act}: out of hours"])
    cols = [C_("Season", 8, align="center"), C_("Week", 6, align="center"), C_("Recruit", 22),
            C_("Pos", 6, align="center"), C_("Stars", 6, align="center"), C_("Kind", 18), C_("Note", 100)]
    if rows:
        book.add("You", "Recruit Notes", "The running story on your recruits: pitch reactions, official visit "
                 "reports, commitments, and last week's standing-order results.", cols, rows, freeze=3)


# ═══ You: decisions ═════════════════════════════════════════════════════════

def _decisions(league, me):
    """Your week-by-week decisions: the saved decision log, plus this season's games rebuilt from the
    sideline records for anything the log doesn't have (older saves)."""
    import week
    out = {(d["year"], d["week"]): d for d in (getattr(league, "decision_log", []) or [])}
    if me is None:
        return sorted(out.values(), key=lambda d: (d["year"], d["week"]))
    try:
        import sideline
    except Exception:
        sideline = None
    for w in sorted(league.schedule):
        for g in league.schedule[w]:
            if not g.played or me not in (g.home, g.away) or (league.year, g.week) in out:
                continue
            box = getattr(g, "box", None)
            sl = box.__dict__.get("sl") if box is not None else None
            if sl is None:
                continue
            gp = (getattr(sl, "gp", None) or {}).get(me) or {}
            cr = getattr(sl, "credit", None) or {}
            opp = g.opponent_of(me)
            calls = [{"q": e.get("q"), "clock": e.get("clock"), "kind": e.get("kind"), "text": str(e.get("text", "")),
                      "staff": e.get("staff"), "yours": "" if e.get("yours") is None else str(e.get("yours")),
                      "chart": "" if e.get("chart") is None else str(e.get("chart")),
                      "result": "" if e.get("result") is None else str(e.get("result")),
                      "score": list(e["score"]) if e.get("score") else None} for e in (getattr(sl, "log", None) or [])]
            focus = cr.get("focus")
            out[(league.year, g.week)] = {
                "year": league.year, "week": g.week, "opp": opp.school, "home": g.home is me,
                "result": "W" if g.score_for(me) > g.score_for(opp) else "L",
                "score": [g.score_for(me), g.score_for(opp)],
                "focus": week.FOCUS[focus][0] if focus in week.FOCUS else "",
                "routine": cr.get("routine") or "", "pressed": None,
                "plan_off": sideline.OFF_KEYS.get(gp.get("off"), (gp.get("off", ""),))[0] if sideline and gp else "",
                "plan_def": sideline.DEF_KEYS.get(gp.get("def"), (gp.get("def", ""),))[0] if sideline and gp else "",
                "script": bool(gp.get("script")), "plan_by": cr.get("whose") or ("yours" if gp.get("mine") else ""),
                "lift": cr.get("total"), "pts": cr.get("pts"), "margin": cr.get("margin"), "calls": calls}
    return sorted(out.values(), key=lambda d: (d["year"], d["week"]))


def _sheet_decisions(league, book, me):
    items = _decisions(league, me)
    if not items:
        return
    cols = [C_("Season", 8, align="center"), C_("Week", 6, align="center"), C_("Opponent", 22),
            C_("H/A", 5, align="center"), C_("Result", 7, align="center"), C_("Score", 9, align="center"),
            C_("Practice Focus", 22, grp="yours"), C_("Routine", 18, grp="yours"),
            C_("Press Conference", 10, align="center", grp="yours"), C_("Offensive Plan", 26, grp="yours"),
            C_("Defensive Plan", 28, grp="yours"), C_("Scripted Openers", 10, align="center", grp="yours"),
            C_("Plan Set By", 11, align="center", grp="yours"),
            C_("Week's Work (points)", 11, fmt="+0.0;-0.0;0.0", align="center", grp="stat"),
            C_("Margin", 7, align="center", grp="stat"), C_("Headset Calls", 8, align="center", grp="stat")]
    rows = []
    for d in items:
        pressed = d.get("pressed")
        rows.append([d["year"], d["week"], d["opp"], "H" if d["home"] else "A", d["result"],
                     f"{d['score'][0]}-{d['score'][1]}", d["focus"], d["routine"],
                     "" if pressed is None else ("Yes" if pressed else "Skipped"), d["plan_off"], d["plan_def"],
                     "Yes" if d["script"] else "", d["plan_by"], d.get("pts"), d.get("margin"), len(d["calls"])])
    book.add("You", "Week Decisions", "What you chose each game week: practice focus, routine, press conference, "
             "game plan, scripted openers, and what it was worth.", cols, rows, freeze=3)

    cols = [C_("Season", 8, align="center"), C_("Week", 6, align="center"), C_("Opponent", 22),
            C_("Qtr", 5, align="center"), C_("Clock", 7, align="center"), C_("Type", 12),
            C_("Situation", 70), C_("Your Call", 16, grp="yours"), C_("Chart's Call", 14, grp="yours"),
            C_("Result", 24), C_("Score (you-opp)", 11, align="center"), C_("Staff", 14)]
    rows = []
    for d in items:
        for c in d["calls"]:
            clk = c.get("clock")
            sc = c.get("score")
            rows.append([d["year"], d["week"], d["opp"],
                         ("OT" if (c.get("q") or 0) > 4 else f"Q{c.get('q')}") if c.get("q") else "",
                         f"{clk // 60}:{clk % 60:02d}" if isinstance(clk, int) else "", c.get("kind"), c.get("text"),
                         c.get("yours"), c.get("chart"), c.get("result"), f"{sc[0]}-{sc[1]}" if sc else "",
                         c.get("staff") or ""])
    if rows:
        book.add("You", "Headset Calls", "Every call you (or your staff) made on the headset during games: 4th "
                 "downs, two-point tries, challenges, and how each worked out.", cols, rows, freeze=3)


def _sheet_inbox(league, book, me):
    inbox = list(getattr(league, "inbox", []) or [])
    if not inbox:
        return
    cols = [C_("Season", 8, align="center"), C_("Week", 6, align="center"), C_("From", 22), C_("Role", 22),
            C_("Subject", 44), C_("Message", 110), C_("Kind", 10), C_("Read", 6, align="center"),
            C_("Your Answer", 40, grp="yours")]
    rows = []
    for m in inbox:
        answer = ""
        if m.get("answered"):
            answer = next((lab for k, lab in (m.get("replies") or []) if k == m["answered"]), str(m["answered"]))
        rows.append([m.get("year"), m.get("week"), m.get("sender"), m.get("role"), m.get("subject"),
                     m.get("body"), m.get("kind"), "Yes" if m.get("read") else "", answer])
    book.add("You", "Inbox", "Your inbox, and the answer you chose on each message that asked for one.", cols, rows,
             freeze=2)


def _sheet_career_log(league, book):
    log = list(getattr(league, "career_log", []) or [])
    if not log:
        return
    cols = [C_("Season", 8, align="center"), C_("Entry", 130)]
    book.add("You", "Career Log", "Your career, in order: jobs, contracts, reputations, development picks.", cols,
             [[y, t] for y, t in log], freeze=1)


def _sheet_bets(league, book):
    bk = getattr(league, "book", None)
    bets = list(getattr(bk, "bets", []) or [])
    if not bets:
        return
    cols = [C_("Bet #", 7, align="center"), C_("Season", 8, align="center"), C_("Week", 6, align="center"),
            C_("Type", 10), C_("Stake", 10, fmt="$#,##0.00", grp="money"), C_("Odds", 8, align="center", fmt="+0;-0"),
            C_("Status", 9, align="center"), C_("Payout", 11, fmt="$#,##0.00", grp="money"),
            C_("Net", 11, fmt="$#,##0.00;[Red]-$#,##0.00", grp="money"), C_("Legs", 110)]
    rows = []
    for b in bets:
        legs = " | ".join(str(getattr(l, "label", "")) for l in b.legs)
        net = (b.payout - b.stake) if b.status not in ("open",) else None
        rows.append([b.id, b.year, b.week, b.kind, b.stake, b.odds, b.status, b.payout or None, net, legs])
    book.add("You", "Bets", "Every bet you've placed in the sportsbook.", cols, rows, freeze=1)


# ═══ Compliance & academics ═════════════════════════════════════════════════

def _sheet_compliance_cases(league, book, me):
    import compliance as cp
    cols = [C_("Case #", 7, align="center"), C_("School", 22), C_("Level", 10, align="center", grp="hidden"),
            C_("Matter", 24), C_("Stage", 22, grp="status"), C_("Opened", 8, align="center"),
            C_("Weeks Open", 9, align="center"), C_("Came Out", 18), C_("Cooperation", 12, align="center"),
            C_("Counsel", 8, align="center"), C_("Self-Reported", 10, align="center"),
            C_("Cover-Up", 9, align="center"), C_("What Happened", 80), C_("Penalties", 90), C_("Outcome", 40)]
    mine_school = me.school if me is not None else None
    rows = []
    for c in cp.root(league)["cases"]:
        if c["status"] == "hidden" and not (c["user"] and c["school"] == mine_school):
            continue                                              # the world doesn't know about it yet: no spoilers
        coop = ("full" if c["coop"] >= 2 else "good" if c["coop"] == 1 else "standard" if c["coop"] == 0
                else "grudging" if c["coop"] == -1 else "stonewalling")
        rows.append([c["id"], c["school"], cp.LEVEL_WORD[c["level"]], cp.KINDS[c["kind"]]["label"], cp.stage_label(c),
                     c["year"], c["age"], c["how"] or "", coop, "Yes" if c["counsel"] else "",
                     "Yes" if c["self_reported"] else "", "Yes" if c["cover"] and c["school"] == mine_school else "",
                     c["text"], "; ".join((c["ruling"] or {}).get("lines", [])), c["outcome"] or ""])
    book.add("Compliance", "Compliance Cases", "Every CAB case the world knows about (and any only you know about).",
             cols, rows, freeze=3)


def _sheet_apr_integrity(league, book, me):
    import compliance as cp
    aprs = cp.root(league)["aprs"]
    years = sorted(aprs)[-5:]
    cols = [C_("Team", 22), C_("Conf", 12), C_("Integrity", 9, **_num(9, scale="rating")),
            C_("Compliance Office", 10, **_num(10, scale="rating")), C_("Office Budget", 10, align="center"),
            C_("Academic Support", 10, align="center"), C_("Academics Rating", 10, **_num(10, scale="rating")),
            *[C_(f"APR {y}", 9, **_num(9, fmt="0", scale="rating")) for y in years],
            C_("Sanctions", 60, grp="hidden"), C_("Probation Through", 10, align="center"),
            C_("Scholarships Lost (this class)", 12, align="center"), C_("Open Cases", 9, align="center")]
    rows = []
    for t, _ in _sorted_teams(league):
        s = cp._tables_ok(cp.st(t))
        sanc = getattr(t, "sanctions", None) or {}
        live = sanc and sanc.get("until", 0) >= league.year
        bits = []
        if live:
            bits = [f"ban {b}" for b in sorted(set(sanc.get("bans") or [])) if b >= league.year]
            if sanc.get("recruit_mult", 1.0) < 1.0:
                bits.append(f"recruiting cut {int((1 - sanc['recruit_mult']) * 100)}%")
        rows.append([t.school, t.conference, round(s["rep"]), cp.office_eff(t),
                     cp.OFFICE_TIER[s["tier"]][2], cp.SUPPORT_TIER[s["support"]][2], t.ratings.get("academics"),
                     *[aprs[y].get(t.school) for y in years], "; ".join(bits),
                     sanc.get("probation_until") if live else None, cp.class_cut(t, league) or None,
                     len(cp.public_cases(league, t))])
    book.add("Compliance", "APR & Integrity", "Every program's compliance office, integrity, APR history and live sanctions.",
             cols, rows, freeze=2)


def _sheet_academics(league, book):
    import compliance as cp
    cols = [C_("Team", 22), C_("Player", 22), C_("Pos", 6, align="center"), C_("Class", 7, align="center"),
            C_("OVR", 6, **_num(6, scale="rating")), C_("GPA", 7, **_num(7, fmt="0.00", scale="rating")),
            C_("Standing", 12, align="center", grp="status"), C_("Status", 28, grp="status")]
    rows = []
    for t, _ in _sorted_teams(league):
        for p in sorted(t.roster, key=lambda q: cp.gpa(q)):
            g = cp.gpa(p)
            held = (p.inj_desc or "") if getattr(p, "suspended", False) else ""
            rows.append([t.school, p.name, p.position, p.class_label, p.overall, g, cp.gpa_word(g), held])
    book.add("Compliance", "Academics", "Every player's GPA and academic standing.", cols, rows, freeze=3)


# ═══ Overview and orchestration ═════════════════════════════════════════════

def _facts(league, me, opts, counts):
    cy = league.recruiting
    mode = {"career": "Coach Career", "spectator": "Spectator", "ad": "Athletic Director"}.get(
        getattr(league, "mode", None), "—")
    played = sum(1 for w in league.schedule for g in league.schedule[w] if g.played)
    total = sum(len(v) for v in league.schedule.values())
    facts = [("title", f"{league.status}  ·  exported {time.strftime('%b %d, %Y  %I:%M %p')}"),
             ("Mode", mode), ("World seed", league.seed),
             ("FBS programs", f"{len(league.teams)} programs · {sum(len(t.roster) for t in league.teams):,} players"),
             ("This season", f"{played} of {total} games played"),
             ("Seasons of game history", ", ".join(str(y) for y in sorted(getattr(league, 'archive', {}) or {})) or "none yet"),
             ("Recruiting pool", f"{len(cy.pool):,} prospects in the {league.year} class · "
                                 f"{sum(1 for r in cy.pool if r.committed_to is not None):,} committed")]
    champ = league.champion_of(league.year)
    if champ:
        facts.append((f"{league.year} champion", f"{champ.champion} ({champ.record}) over {champ.runner_up}"))
    if _hot(league):
        import hotseat
        facts[1] = ("Mode", "Hot Seat (several coaches, one world)")
        for s_ in hotseat.seats(league):
            t_, c_ = hotseat.seat_team(league, s_), hotseat.seat_coach(league, s_)
            facts.append((f"Player: {s_.name}", (f"{t_.full_name} ({t_.conference}) · {_rec(t_)}" if t_ is not None
                                                 else "between jobs") + (f" · coach {c_.name}" if c_ else "")))
    if me is not None:
        c = me.coach
        facts.append(("Your program", f"{me.full_name} ({me.conference}) · {_rec(me)}"
                                       + (f" · coach {c.name}" if c else "")))
        try:
            facts.append(("Recruiting hours", cy.hours_explained(me)))
        except Exception:
            pass
        try:
            import recruit_plus as rp
            ap = rp.autopilot(cy, me)
            facts.append(("Coordinator autopilot", "; ".join(
                f"{r} {'ON, ' + str(ap[r]['hours']) + ' hrs' if ap[r]['on'] else 'off'}" for r in ("OC", "DC"))))
        except Exception:
            pass
        goals = [getattr(g, "short", "") for g in (getattr(me, "goals", []) or [])]
        if goals:
            facts.append(("AD's goals", " · ".join(goals)))
    facts.append(("Export options", f"player game logs {'ON' if opts.get('logs') else 'off'} · "
                                    f"recruits' hidden true ratings {'ON' if opts.get('hidden') else 'off'}"))
    return facts


def _notes(league, me, opts):
    notes = [
        "Every sheet has frozen headers, a filter on every column, and striped rows. Click a header's filter "
        "arrow to sort or filter; in Google Sheets, use Data > Create a filter view to keep your own view.",
        "Sheets with a color scale (ratings, position fit, interest) shade low values red and high values green.",
        "Rosters cover the 138 FBS programs. FCS opponents appear on schedules and in game history but have no "
        "rosters (the game rebuilds them each season).",
        f"Recruiting: prospects in the {league.year} class sign this winter and arrive as freshmen the following "
        "season (JUCO transfers arrive as juniors).",
    ]
    if opts.get("hidden"):
        notes.append("The red-headed columns on the Recruits sheet are HIDDEN in the game: the recruit's true stars, "
                     "true rating, fundamentals and potential. Exported because you asked for the full database; "
                     "re-export without them for a spoiler-free copy.")
    if _hot(league):
        notes.append("HOT SEAT: the You sheets (Recruit Orders, Recruit Actions, Recruit Notes, Week Decisions, Headset "
                     "Calls, Inbox, Career Log) hold one block per coach — see the Player column. This file shows "
                     "every coach's private recruiting board, inbox and plans: share it with the table only after "
                     "the game, or leave out the hidden ratings.")
    if me is not None or _hot(league):
        notes.append("Recruit Actions and Week Decisions are recorded from the version that added this export. "
                     "This season's games are rebuilt from the game's sideline records, but recruiting moves and "
                     "older seasons' decisions were never logged, so they start filling in from now on.")
    notes.append("The export is a snapshot: it never changes the league. Export again any time.")
    return notes


def default_name(league, me=None):
    if _hot(league):
        who = "HotSeat_" + "_".join(s.name for s in __import__("hotseat").seats(league))[:40]
    else:
        who = me.school if me is not None else f"World {league.seed}"
    stamp = f"Wk{league.week}" if league.week else "Pre"
    safe = re.sub(r"[^A-Za-z0-9]+", "_", f"ConsoleCollege_{who}_{league.year}_{stamp}").strip("_")
    return safe + ".xlsx"


def export_league(league, path=None, logs=False, hidden=True, progress=None):
    """Write the whole league to an .xlsx and return its path. Raises ImportError if openpyxl is missing."""
    hot = _hot(league)
    if hot:
        import hotseat
        hotseat.sync(league)
    me = None if hot else _user_recruit_team(league)           # Hot Seat: no single "you"
    title_team = None if hot else getattr(league, "user_team", None)
    opts = {"logs": bool(logs), "hidden": bool(hidden)}
    if path is None:
        os.makedirs(EXPORT_DIR, exist_ok=True)
        path = os.path.join(EXPORT_DIR, default_name(league, title_team))
        base, n = path[:-5], 2
        while os.path.exists(path):
            path, n = f"{base}_{n}.xlsx", n + 1
    book = Sheets(progress)

    # League
    for fn, args in (
        (_sheet_teams, (league, book, title_team)), (_sheet_rankings, (league, book)),
        (_sheet_schedule, (league, book)), (_sheet_game_history, (league, book)),
    ):
        _run(book, fn, *args)
    if opts["logs"]:
        _run(book, _sheet_game_logs, league, book)
    # Players
    for fn in (_sheet_rosters, _sheet_player_stats, _sheet_rating_history, _sheet_player_events, _sheet_coaches,
               _sheet_portal):
        _run(book, fn, league, book)
    # Recruiting
    _run(book, _sheet_recruits, league, book, me, opts["hidden"])
    _run(book, _sheet_interest, league, book, me)
    _run(book, _sheet_boards, league, book, me)
    _run(book, _sheet_classes, league, book, me)
    _run(book, _sheet_signing_history, league, book)
    _run(book, _sheet_recruit_news, league, book)
    # You
    if hot:
        _run(book, _per_seat, league, book, [
            (_sheet_orders, True), (_sheet_recruit_actions, True), (_sheet_recruit_notes, True),
            (_sheet_decisions, True), (_sheet_inbox, True), (_sheet_career_log, False)])
    elif me is not None:
        _run(book, _sheet_orders, league, book, me)
        _run(book, _sheet_recruit_actions, league, book, me)
        _run(book, _sheet_recruit_notes, league, book, me)
    if not hot and (title_team is not None or getattr(league, "decision_log", None)):
        _run(book, _sheet_decisions, league, book, title_team if getattr(league, "mode", None) == "career" else None)
    if not hot:
        if getattr(league, "mode", None) == "career":
            _run(book, _sheet_inbox, league, book, me)
        _run(book, _sheet_career_log, league, book)
    if getattr(league, "mode", None) == "spectator":
        _run(book, _sheet_bets, league, book)
    # History
    for fn in (_sheet_champions, _sheet_team_history, _sheet_final_polls, _sheet_awards, _sheet_draft,
               _sheet_series, _sheet_carousel):
        _run(book, fn, league, book)
    # Compliance
    _run(book, _sheet_compliance_cases, league, book, title_team if getattr(league, "mode", None) == "career" else None)
    _run(book, _sheet_apr_integrity, league, book, me)
    _run(book, _sheet_academics, league, book)

    book.index.sort(key=lambda x: ["League", "Players", "Recruiting", "You", "History", "Compliance"].index(x[0]))
    book.finish_overview(_facts(league, title_team, opts, None), _notes(league, title_team, opts))
    if progress:
        progress("Saving the file")
    book.wb.save(path)
    return path


def _run(book, fn, *args):
    """Build one sheet function; a failure is noted on the Overview instead of stopping the export."""
    try:
        fn(*args)
    except Exception as e:
        book.skipped.append((fn.__name__.replace("_sheet_", "").replace("_", " ").title(),
                             f"{type(e).__name__}: {e}"))


# ═══ The screen ═════════════════════════════════════════════════════════════

def _have_openpyxl():
    try:
        import openpyxl  # noqa: F401
        return True
    except ImportError:
        return False


def _offer_install():
    from ui import C, ask, paint
    print(paint("\n   Export to Sheets needs one small package: openpyxl (it writes the spreadsheet).", C.BYELLOW))
    if ask("Install it now with pip? (y/N)").lower() not in ("y", "yes"):
        print(paint("   No problem. Later, run:   python -m pip install openpyxl", C.GRAY))
        return False
    import subprocess
    import sys
    print(paint("\n   Installing…", C.GRAY), flush=True)
    r = subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl"])
    if r.returncode != 0 or not _have_openpyxl():
        print(paint("\n   The install didn't work. Try in a terminal:   python -m pip install openpyxl", C.BRED))
        return False
    return True


def _open_file(path):
    import subprocess
    import sys
    try:
        if os.name == "nt":
            os.startfile(path)                                   # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def export_screen(league):
    from ui import C, ask, back_key, clear, footer, key, on_off, paint, pause, title_bar
    opts = {"logs": False, "hidden": True}
    while True:
        clear()
        print(title_bar("EXPORT TO SHEETS", sub="SYSTEM"))
        print()
        print(paint(f"   {league.status}", C.BWHITE, C.BOLD))
        print(paint("   Writes the whole league to one Excel workbook (opens in Google Sheets, too):", C.GRAY))
        for line in ("teams, rankings, schedules, every game and champion",
                     "every FBS roster with all the player info, stats, rating history and coaches",
                     "the full recruit database, every board, class rankings and signing history",
                     "your decisions, headset calls, recruiting actions and inbox"):
            print(paint(f"     · {line}", C.GRAY))
        print()
        print(f"   {key('1', 'Player game logs')}   {on_off(opts['logs'])}   "
              + paint("every stat line in every game; makes a much bigger file", C.GRAY))
        print(f"   {key('2', 'Recruits’ hidden ratings')}   {on_off(opts['hidden'])}   "
              + paint("true stars, true rating, potential (spoilers)", C.GRAY))
        print(paint(f"\n   Saved to: {os.path.relpath(EXPORT_DIR)}{os.sep}", C.GRAY))
        footer(key("Enter", "export", C.BGREEN), key("1", "game logs"), key("2", "hidden ratings"), back_key())
        choice = ask("Export?").lower()
        if choice in ("b", "back"):
            return
        if choice == "1":
            opts["logs"] = not opts["logs"]
            continue
        if choice == "2":
            opts["hidden"] = not opts["hidden"]
            continue
        if choice != "":
            continue
        if not _have_openpyxl() and not (_offer_install() and _have_openpyxl()):
            pause()
            continue
        print(paint("\n   Building the workbook…\n", C.BWHITE), flush=True)
        start = time.time()
        try:
            path = export_league(league, logs=opts["logs"], hidden=opts["hidden"],
                                 progress=lambda name: print(paint(f"     {name}", C.GRAY), flush=True))
        except Exception as e:
            print(paint(f"\n   Couldn't export: {type(e).__name__}: {e}", C.BRED))
            pause()
            continue
        size = os.path.getsize(path) / 1e6
        print(paint(f"\n   ✓ Exported in {time.time() - start:.0f}s  ·  {size:.1f} MB", C.BGREEN, C.BOLD))
        print(paint(f"   {os.path.abspath(path)}", C.BWHITE))
        print(paint("   Google Sheets: sheets.new (or Drive) > File > Import > Upload.", C.GRAY))
        footer(key("O", "open it now"), back_key("Done"))
        if ask("Open the file?").lower() == "o":
            if not _open_file(path):
                print(paint("   Couldn't open it from here. Find it in the folder above.", C.BYELLOW))
                pause()
        return
