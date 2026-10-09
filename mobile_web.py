"""
mobile_web.py — Console College, the full game, served to your phone.

    python mobile_web.py                 serves on 0.0.0.0:$PORT (default 8000)

This is the same bridge play.py uses for the desktop window: the real game (main.py) runs on a
background thread exactly as it does in a terminal, everything it prints is streamed to the page,
and every tap or typed answer goes back as the line the game was waiting for. Nothing is
reimplemented, so every screen, menu, prompt, Game Day snap and offseason step is the real thing.

Environment variables (all optional):
    PORT            port to listen on (Railway / Render / Fly set this for you)
    CC_PASSWORD     if set, the page asks for it once per device before showing the game
    CC_DATA_DIR     folder for saves/, settings.json and gui_prefs.json (point this at a
                    persistent volume on your host so careers survive redeploys)
"""
import hashlib
import hmac
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import play  # noqa: E402  (the bridge, the sidebar data and the request handler)

PASSWORD = os.environ.get("CC_PASSWORD", "").strip()
DATA_DIR = os.environ.get("CC_DATA_DIR", "").strip()
_COOKIE = "cc_auth"


# ═══ Where files live ═══════════════════════════════════════════════════════

def _use_data_dir():
    """Move saves / settings / window prefs to CC_DATA_DIR (a persistent volume), seeding it once."""
    if not DATA_DIR:
        return
    import shutil
    os.makedirs(os.path.join(DATA_DIR, "saves"), exist_ok=True)
    for name in ("settings.json", "gui_prefs.json"):
        src, dst = os.path.join(HERE, name), os.path.join(DATA_DIR, name)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
    src_saves = os.path.join(HERE, "saves")
    if os.path.isdir(src_saves) and not os.listdir(os.path.join(DATA_DIR, "saves")):
        for fn in os.listdir(src_saves):
            shutil.copy2(os.path.join(src_saves, fn), os.path.join(DATA_DIR, "saves", fn))
    import saves
    import settings
    saves.SAVE_DIR = os.path.join(DATA_DIR, "saves")
    settings.PATH = os.path.join(DATA_DIR, "settings.json")
    play.PREFS = os.path.join(DATA_DIR, "gui_prefs.json")


# ═══ The game thread: always running, restarted if you quit ═════════════════

_game = {"thread": None}
_glock = threading.Lock()


def _game_loop():
    """Run the real game. When it ends (you picked Quit), start a fresh title screen so the
    page always has a game behind it — your saves are untouched."""
    while True:
        play.BRIDGE.done = False
        play.BRIDGE.crashed = None
        play.run_game()
        if getattr(play.BRIDGE, "crashed", None):
            # Keep the error on screen (screenshot it!) and save it; restart only when the player says so.
            try:
                folder = DATA_DIR or HERE
                with open(os.path.join(folder, "last_crash.txt"), "w", encoding="utf-8") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + play.BRIDGE.crashed)
            except Exception:
                pass
            play.BRIDGE.push("out", "\n  Screenshot this and send it over. Then press Enter to restart the game.\n", aud="*")
            while not play.BRIDGE.main.q.empty():          # taps sent before the crash don't count
                try:
                    play.BRIDGE.main.q.get_nowait()
                except Exception:
                    break
            play.BRIDGE.done = False
            play.BRIDGE.input("Press Enter to restart:")    # wait for the player (the page shows Continue)
        time.sleep(1.5)                               # let the page read the goodbye
        with play.BRIDGE.lock:
            play.BRIDGE.events = []
        while not play.BRIDGE.main.q.empty():         # drop taps sent to the old game
            try:
                play.BRIDGE.main.q.get_nowait()
            except Exception:
                break
        play.BRIDGE.push("restart", aud="*")


def start_game():
    with _glock:
        if _game["thread"] is None:
            t = threading.Thread(target=_game_loop, name="game", daemon=True)
            _game["thread"] = t
            t.start()


# ═══ Phone extras: the page shell, the icon, the optional password ══════════

_MOBILE_HEAD = (
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="apple-mobile-web-app-capable" content="yes">\n'
    '<meta name="mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
    '<meta name="apple-mobile-web-app-title" content="Console College">\n'
    '<meta name="theme-color" content="#0b0f14">\n'
    '<link rel="apple-touch-icon" href="icon.png">\n'
    '<link rel="icon" href="icon.png">\n'
    '<link rel="manifest" href="manifest.json">\n'
)

_MANIFEST = (
    '{"name":"Console College","short_name":"Console College","start_url":"/","display":"standalone",'
    '"background_color":"#0b0f14","theme_color":"#0b0f14",'
    '"icons":[{"src":"/icon.png","sizes":"180x180","type":"image/png"}]}'
)


def _page(index_html):
    """gui/index.html with the phone viewport, home-screen tags, mobile.css and mobile.js added."""
    html = index_html.replace('<meta name="viewport" content="width=device-width, initial-scale=1">', _MOBILE_HEAD)
    html = html.replace('<link rel="stylesheet" href="style.css">',
                        '<link rel="stylesheet" href="style.css">\n<link rel="stylesheet" href="mobile.css">\n'
                        '<link rel="stylesheet" href="native.css">')
    html = html.replace('<script src="app.js"></script>',
                        '<script src="mobile.js"></script>\n<script src="app.js"></script>\n<script src="native.js"></script>')
    return html


def _token():
    return hmac.new(PASSWORD.encode(), b"console-college", hashlib.sha256).hexdigest()


_LOGIN = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0b0f14"><link rel="apple-touch-icon" href="icon.png">
<title>Console College</title><style>
html,body{margin:0;height:100%%;background:#0b0f14;color:#cdd6df;font:16px system-ui,-apple-system,sans-serif}
form{max-width:340px;margin:0 auto;padding:22vh 24px 0}
h1{font-size:15px;letter-spacing:.14em;color:#f2c14e;margin:0 0 20px}
input,button{width:100%%;box-sizing:border-box;font:16px system-ui;padding:13px;border-radius:10px;margin-top:10px}
input{background:#111821;border:1px solid #243140;color:#cdd6df}
button{background:#f2c14e;border:0;color:#1a1405;font-weight:700}
p{color:#ff7b72;font-size:14px;min-height:20px}</style></head><body>
<form method="post" action="/login"><h1>🏈 CONSOLE COLLEGE</h1>
<input type="password" name="pw" placeholder="Password" autofocus autocomplete="current-password">
<button type="submit">Play</button><p>%s</p></form></body></html>"""


class Handler(play.Handler):
    """play.py's handler (the game bridge API and the gui/ files) plus the phone extras."""

    def _authed(self):
        if not PASSWORD:
            return True
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == _COOKIE and hmac.compare_digest(v, _token()):
                return True
        return False

    def _send(self, data, ctype, code=200, extra=()):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _gate(self, path):
        if self._authed() or path in ("/icon.png", "/manifest.json", "/login"):
            return True
        if path in play._API or path == "/links":
            self._send('{"ok":false,"error":"login"}', "application/json", 401)
        else:
            self._send(_LOGIN % "", "text/html; charset=utf-8")
        return False

    def do_GET(self):
        path = self.path.split("?")[0]
        if not self._gate(path):
            return
        if path in ("/", "/index.html"):
            with open(os.path.join(play.GUI, "index.html"), encoding="utf-8") as f:
                return self._send(play._tr(_page(f.read())), "text/html; charset=utf-8")
        if path == "/manifest.json":
            return self._send(_MANIFEST, "application/manifest+json")
        if path == "/healthz":
            return self._send("ok", "text/plain")
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/login":
            n = int(self.headers.get("Content-Length") or 0)
            from urllib.parse import parse_qs
            pw = (parse_qs(self.rfile.read(n).decode("utf-8", "replace")).get("pw") or [""])[0]
            if PASSWORD and hmac.compare_digest(pw, PASSWORD):
                cookie = f"{_COOKIE}={_token()}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax"
                if (self.headers.get("X-Forwarded-Proto") or "").lower() == "https":
                    cookie += "; Secure"
                return self._send("", "text/html", 303, [("Location", "/"), ("Set-Cookie", cookie)])
            return self._send(_LOGIN % "That isn't it.", "text/html; charset=utf-8", 401)
        if not self._gate(path):
            return
        if path == "/copy":                     # the phone copies on its own; the server has no clipboard
            return self._json({"ok": False})
        return super().do_POST()


def run(host="0.0.0.0", port=None):
    port = int(port or os.environ.get("PORT", "8000"))
    _use_data_dir()
    play.install()                              # the game's print/input/clear now go to the page
    start_game()
    srv = play.ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    sys.__stdout__.write(f"Console College is running at http://localhost:{port}/"
                         f"{'  (password protected)' if PASSWORD else ''}\n")
    sys.__stdout__.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
