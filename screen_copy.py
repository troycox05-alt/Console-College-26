"""
screen_copy.py — "Auto copy output": after every screen, the text is on your
clipboard, ready to paste into a chatbot that's playing along with you.

How it works
  Everything the game prints is also recorded (colors stripped). Clearing the
  screen starts a fresh recording. Every time the game waits for you to type
  something, the recording so far — the whole screen, plus the prompt — is
  copied to the clipboard, and also written to last_screen.txt next to the
  game (handy if your system has no clipboard tool, or you'd rather attach a
  file). What you type is added to the recording, so a screen that asks more
  than one question still reads like a transcript.

Clipboard tools
  macOS: pbcopy (built in).  Windows: clip (built in).
  Linux: wl-copy, xclip or xsel, whichever is installed.
"""
import builtins
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAST_SCREEN = os.path.join(HERE, "last_screen.txt")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
MAX_BUFFER = 200_000

_buffer = []
_size = 0
_installed = False
_real_input = builtins.input
_tool = None


class _Tee:
    """Stands in for sys.stdout: prints as usual, and keeps a copy."""

    def __init__(self, real):
        self._real = real

    def write(self, text):
        _record(text)
        return self._real.write(text)

    def flush(self):
        return self._real.flush()

    def __getattr__(self, name):
        return getattr(self._real, name)


def _record(text):
    global _size
    _buffer.append(text)
    _size += len(text)
    if _size > MAX_BUFFER:                    # a very long screen: keep the end of it
        joined = "".join(_buffer)[-MAX_BUFFER // 2:]
        _buffer.clear()
        _buffer.append(joined)
        _size = len(joined)


def reset():
    """The screen was cleared: start a new recording."""
    global _size
    _buffer.clear()
    _size = 0


def screen_text():
    text = ANSI.sub("", "".join(_buffer))
    lines = [ln.rstrip() for ln in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    return "\n".join(lines).rstrip() + "\n"


def clipboard_tool():
    """The command that puts text on the clipboard here, or None."""
    global _tool
    if _tool is not None:
        return _tool or None
    if sys.platform == "darwin" and shutil.which("pbcopy"):
        _tool = ["pbcopy"]
    elif os.name == "nt":
        _tool = ["clip"]
    elif shutil.which("wl-copy"):
        _tool = ["wl-copy"]
    elif shutil.which("xclip"):
        _tool = ["xclip", "-selection", "clipboard"]
    elif shutil.which("xsel"):
        _tool = ["xsel", "--clipboard", "--input"]
    else:
        _tool = []
    return _tool or None


def copy(text):
    """Clipboard (if there's a tool) and last_screen.txt. Returns True if the clipboard got it."""
    try:
        with open(LAST_SCREEN, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass
    tool = clipboard_tool()
    if tool is None:
        return False
    try:
        if os.name == "nt":
            data = text.encode("utf-16-le")                 # clip reads UTF-16 cleanly (keeps ★ and box lines)
        else:
            data = text.encode("utf-8")
        env = dict(os.environ)
        env.setdefault("LANG", "en_US.UTF-8")                # pbcopy needs this to keep non-ASCII characters
        subprocess.run(tool, input=data, env=env, check=False, timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _enabled():
    try:
        import settings
        return bool(settings.load().get("auto_copy"))
    except Exception:
        return False


def _input(prompt=""):
    if _enabled():
        _record(str(prompt))                  # the prompt belongs to the screen being copied
        copy(screen_text())
        sys.stdout.write("")                  # (the prompt itself is shown by input below)
        answer = _real_input(_unrecorded(prompt))
    else:
        answer = _real_input(prompt)
    _record(f"{answer}\n")                    # what you typed, so the next copy reads like a transcript
    return answer


def _unrecorded(prompt):
    """input() writes its prompt through sys.stdout; skip recording it a second time."""
    global _skip_next
    _skip_next = str(prompt)
    return prompt


_skip_next = None


class _TeeSkipping(_Tee):
    def write(self, text):
        global _skip_next
        if _skip_next is not None and text == _skip_next:
            _skip_next = None
            return self._real.write(text)
        return super().write(text)


def install():
    """Start recording (cheap, always on) and route every input() through the copier."""
    global _installed
    if _installed:
        return
    _installed = True
    sys.stdout = _TeeSkipping(sys.stdout)
    builtins.input = _input
    import ui
    real_clear = ui.clear

    def clear():
        real_clear()
        reset()
    ui.clear = clear
    # Modules that already did `from ui import clear` get the recording version too.
    for mod in list(sys.modules.values()):
        if getattr(mod, "clear", None) is real_clear:
            try:
                mod.clear = clear
            except (AttributeError, TypeError):
                pass
