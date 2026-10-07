"""The in-game manual: reads MANUAL.txt beside the game and lets you browse it.

Contents -> pick a chapter -> page through it, jump chapters, or search every word.
The text file is the single source, so the printed manual and this viewer never disagree.
"""
import os
import re

from ui import C, paint, clear, ask, rule, title_bar, command_bar, key, WIDTH

PAGE = 34
_HEAD = re.compile(r"^ CHAPTER (\d+) · (.+)$")
_SECTION = re.compile(r"^\s{0,2}\d+\.\d+\s{2}\S")
_cache = None


def _path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "MANUAL.txt")


def load():
    """[(num, title, [lines])] plus the front matter as chapter 0."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(_path(), encoding="utf-8") as f:
            raw = f.read().splitlines()
    except OSError:
        _cache = []
        return _cache
    chapters, cur = [], [0, "Introduction", []]
    i = 0
    while i < len(raw):
        m = _HEAD.match(raw[i])
        if m and i > 0 and raw[i - 1].startswith("====="):
            if cur[2] and cur[2][-1].startswith("====="):
                cur[2].pop()                     # the ruler above belongs to the new chapter
            chapters.append((cur[0], cur[1], _trim(cur[2])))
            cur = [int(m.group(1)), m.group(2).strip(), []]
            i += 2                               # skip the ruler below the title
            continue
        cur[2].append(raw[i])
        i += 1
    chapters.append((cur[0], cur[1], _trim(cur[2])))
    _cache = chapters
    return chapters


def _trim(lines):
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def _style(line):
    s = line.rstrip()
    if _SECTION.match(s):
        return paint(s, C.BCYAN, C.BOLD)
    if s.strip() and set(s.strip()) <= set("-─"):
        return paint(s, C.GRAY)
    if s.strip().isupper() and len(s.strip()) > 3 and not s.startswith("    "):
        return paint(s, C.BYELLOW)
    return s


def _missing():
    clear()
    print(title_bar("THE MANUAL"))
    print(paint("\n  MANUAL.txt wasn't found beside the game files.", C.BYELLOW))
    print(paint("  Put it back in the game folder (it ships in the zip) and try again.", C.GRAY))
    ask("\n  Press Enter to go back... ")


def manual_screen(league=None, chapter=None):
    chs = load()
    if not chs:
        _missing()
        return
    if chapter is not None:
        if _read(chs, chapter) == "b":
            return
    while True:
        clear()
        print(title_bar("CONSOLE COLLEGE · THE MANUAL"))
        print(paint("  Everything a coach, AD or spectator needs, start to finish.", C.GRAY))
        print(rule())
        body = [c for c in chs if c[0] > 0]
        nice = _contents_names(chs)
        half = (len(body) + 1) // 2
        colw = WIDTH // 2 - 2
        for r in range(half):
            row = ""
            for c in (body[r], body[r + half] if r + half < len(body) else None):
                if c is None:
                    continue
                t = nice.get(c[0]) or c[1].capitalize()
                t = t if len(t) <= colw - 6 else t[:colw - 7] + "…"
                cell = paint(f"{c[0]:>3}", C.BYELLOW) + "  " + t
                row += cell + " " * max(1, colw - 5 - len(t))
            print(" " + row)
        for ln in command_bar([key("#", "open chapter"), key("0", "introduction"), key("S", "search"),
                               key("B", "back", C.GRAY)]):
            print(ln)
        ch = ask("Chapter # (S to search, Enter = back):").strip().lower()
        if ch in ("b", "", "q"):
            return
        if ch.startswith("s"):
            if _search(chs, ch[1:].strip()) == "b":
                return
        elif ch.isdigit() and _idx(chs, int(ch)) is not None:
            if _read(chs, _idx(chs, int(ch))) == "b":
                return


def _contents_names(chs):
    """The front matter's CONTENTS list has the chapter names in readable case."""
    names = {}
    for ln in chs[0][2] if chs and chs[0][0] == 0 else []:
        m = re.match(r"^\s+(\d+)\s{2}(\S.*)$", ln)
        if m:
            names[int(m.group(1))] = m.group(2).strip()
    return names


def _idx(chs, num):
    for i, c in enumerate(chs):
        if c[0] == num:
            return i
    return None


def _read(chs, i, line=0):
    """Page through chapter index i. Returns 'b' to leave the manual, 'c' for contents."""
    page = line // PAGE
    while True:
        num, name, lines = chs[i]
        pages = max(1, (len(lines) + PAGE - 1) // PAGE)
        page = max(0, min(page, pages - 1))
        clear()
        head = f"CHAPTER {num} · {name}" if num else "INTRODUCTION"
        print(title_bar(head))
        for ln in lines[page * PAGE:(page + 1) * PAGE]:
            print(_style(ln))
        for _ in range(PAGE - len(lines[page * PAGE:(page + 1) * PAGE])):
            print()
        print(rule())
        print(paint(f"  page {page + 1} of {pages}", C.GRAY)
              + paint(f"   ·   chapter {num} of {chs[-1][0]}", C.GRAY))
        items = []
        if page < pages - 1:
            items.append(key("N", "next page", C.BGREEN))
        if page > 0:
            items.append(key("P", "prev page"))
        items += [key("]", "next chapter"), key("[", "prev chapter"), key("#", "chapter"),
                  key("S", "search"), key("C", "contents"), key("B", "back", C.GRAY)]
        for ln in command_bar(items):
            print(ln)
        ch = ask("Select:").strip().lower()
        if ch in ("", "n"):
            if page < pages - 1:
                page += 1
            elif i < len(chs) - 1 and ch == "":
                i, page = i + 1, 0
            elif ch == "":
                return "c"
        elif ch == "p":
            if page > 0:
                page -= 1
            elif i > 0:
                i -= 1
                page = 10 ** 6                   # last page of the previous chapter
        elif ch == "]":
            if i < len(chs) - 1:
                i, page = i + 1, 0
        elif ch == "[":
            if i > 0:
                i, page = i - 1, 0
        elif ch == "c":
            return "c"
        elif ch in ("b", "q"):
            return "b"
        elif ch.startswith("s"):
            r = _search(chs, ch[1:].strip())
            if r == "b":
                return "b"
        elif ch.isdigit() and _idx(chs, int(ch)) is not None:
            i, page = _idx(chs, int(ch)), 0


def search(chs, term):
    t = term.lower()
    hits = []
    for i, (num, name, lines) in enumerate(chs):
        for n, ln in enumerate(lines):
            if t in ln.lower():
                hits.append((i, n, ln.strip()))
    return hits


def _search(chs, term=""):
    if not term:
        term = ask("  Search the manual for: ").strip()
    if not term:
        return None
    hits = search(chs, term)
    start = 0
    per = 25
    while True:
        clear()
        print(title_bar(f"SEARCH · \"{term}\" · {len(hits)} match{'es' if len(hits) != 1 else ''}"))
        if not hits:
            print(paint("\n  Nothing found. Try a shorter word (\"visit\", \"bond\", \"hot seat\").", C.GRAY))
        for k, (i, n, ln) in enumerate(hits[start:start + per], start + 1):
            num = chs[i][0]
            where = paint(f"ch {num:>2} p{n // PAGE + 1}", C.GRAY)
            text = ln if len(ln) <= WIDTH - 22 else ln[:WIDTH - 23] + "…"
            pos = text.lower().find(term.lower())
            if pos >= 0:
                text = text[:pos] + paint(text[pos:pos + len(term)], C.BYELLOW, C.BOLD) + text[pos + len(term):]
            print(f"  {paint(f'{k:>3}', C.BCYAN)}  {where}  {text}")
        print(rule())
        items = [key("#", "open match")]
        if start + per < len(hits):
            items.append(key("N", "more"))
        if start > 0:
            items.append(key("P", "back a page"))
        items += [key("S", "new search"), key("B", "back", C.GRAY)]
        for ln in command_bar(items):
            print(ln)
        ch = ask("Select:").strip().lower()
        if ch in ("b", "", "c"):
            return None
        if ch == "q":
            return "b"
        if ch == "n" and start + per < len(hits):
            start += per
        elif ch == "p" and start > 0:
            start -= per
        elif ch.startswith("s"):
            term = ch[1:].strip() or ask("  Search the manual for: ").strip()
            if not term:
                return None
            hits, start = search(chs, term), 0
        elif ch.isdigit() and 1 <= int(ch) <= len(hits):
            i, n, _ = hits[int(ch) - 1]
            if _read(chs, i, n) == "b":
                return "b"
