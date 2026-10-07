"""
sitecrypto.py — Locking each team's private website file (Commissioner Mode).

A team's private bundle (its roster as the staff sees it, its board, its signing key...)
is locked before it leaves the commissioner's computer, and unlocked only in a browser
that knows the team's password. Nothing here needs an install: AES runs in plain Python
(about a tenth of a second per team); if the common `cryptography` package happens to be
installed it's used instead, with identical output.

FILE FORMAT (what the website's WebCrypto code reads)
  "CCX1" | salt (16) | PBKDF2 iterations (uint32, big-endian) | nonce (16) | MAC (32) | ciphertext
  keys        PBKDF2-HMAC-SHA256(password, salt, iterations) -> 64 bytes: AES-256 key | HMAC key
  ciphertext  AES-256-CTR(zlib(JSON)), counter = nonce with a 64-bit block counter in its low half
  MAC         HMAC-SHA256(HMAC key, everything before the MAC + ciphertext)   (encrypt-then-MAC)

Passwords are four short words and a number ("maple-tiger-orbit-river-42"), generated
here, never chosen by players: a locked file can be attacked offline, so it must be strong.
"""
import hashlib
import hmac
import secrets
import struct
import zlib

MAGIC = b"CCX1"
ITERATIONS = 150_000

# ═══ AES-256 (encryption direction only: CTR mode never decrypts a block) ═══

def _rotl8(x, s):
    return ((x << s) | (x >> (8 - s))) & 0xFF


def _make_sbox():
    sbox = [0] * 256
    p = q = 1
    while True:
        p = (p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)) & 0xFF      # p * 3
        q ^= q << 1                                                          # q / 3
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q ^ _rotl8(q, 1) ^ _rotl8(q, 2) ^ _rotl8(q, 3) ^ _rotl8(q, 4)
        sbox[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break
    sbox[0] = 0x63
    return sbox


_S = _make_sbox()


def _mul2(a):
    a <<= 1
    return (a ^ 0x11B) & 0xFF if a & 0x100 else a


def _rotr32(x, s):
    return ((x >> s) | (x << (32 - s))) & 0xFFFFFFFF


_TE0 = [(_mul2(s) << 24) | (s << 16) | (s << 8) | (_mul2(s) ^ s) for s in _S]
_TE1 = [_rotr32(t, 8) for t in _TE0]
_TE2 = [_rotr32(t, 16) for t in _TE0]
_TE3 = [_rotr32(t, 24) for t in _TE0]
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def _expand(key):
    if len(key) != 32:
        raise ValueError("AES-256 needs a 32-byte key")
    w = list(struct.unpack(">8I", key))
    S = _S
    for i in range(8, 60):
        t = w[i - 1]
        if i % 8 == 0:
            t = ((t << 8) | (t >> 24)) & 0xFFFFFFFF
            t = (S[t >> 24] << 24) | (S[(t >> 16) & 255] << 16) | (S[(t >> 8) & 255] << 8) | S[t & 255]
            t ^= _RCON[i // 8 - 1] << 24
        elif i % 8 == 4:
            t = (S[t >> 24] << 24) | (S[(t >> 16) & 255] << 16) | (S[(t >> 8) & 255] << 8) | S[t & 255]
        w.append(w[i - 8] ^ t)
    return w


def _encrypt_block(rk, s0, s1, s2, s3):
    T0, T1, T2, T3, S = _TE0, _TE1, _TE2, _TE3, _S
    s0 ^= rk[0]
    s1 ^= rk[1]
    s2 ^= rk[2]
    s3 ^= rk[3]
    k = 4
    for _ in range(13):
        t0 = T0[s0 >> 24] ^ T1[(s1 >> 16) & 255] ^ T2[(s2 >> 8) & 255] ^ T3[s3 & 255] ^ rk[k]
        t1 = T0[s1 >> 24] ^ T1[(s2 >> 16) & 255] ^ T2[(s3 >> 8) & 255] ^ T3[s0 & 255] ^ rk[k + 1]
        t2 = T0[s2 >> 24] ^ T1[(s3 >> 16) & 255] ^ T2[(s0 >> 8) & 255] ^ T3[s1 & 255] ^ rk[k + 2]
        t3 = T0[s3 >> 24] ^ T1[(s0 >> 16) & 255] ^ T2[(s1 >> 8) & 255] ^ T3[s2 & 255] ^ rk[k + 3]
        s0, s1, s2, s3 = t0, t1, t2, t3
        k += 4
    o0 = ((S[s0 >> 24] << 24) | (S[(s1 >> 16) & 255] << 16) | (S[(s2 >> 8) & 255] << 8) | S[s3 & 255]) ^ rk[k]
    o1 = ((S[s1 >> 24] << 24) | (S[(s2 >> 16) & 255] << 16) | (S[(s3 >> 8) & 255] << 8) | S[s0 & 255]) ^ rk[k + 1]
    o2 = ((S[s2 >> 24] << 24) | (S[(s3 >> 16) & 255] << 16) | (S[(s0 >> 8) & 255] << 8) | S[s1 & 255]) ^ rk[k + 2]
    o3 = ((S[s3 >> 24] << 24) | (S[(s0 >> 16) & 255] << 16) | (S[(s1 >> 8) & 255] << 8) | S[s2 & 255]) ^ rk[k + 3]
    return o0, o1, o2, o3


def aes256_block(key, block):
    """One raw AES-256 block encryption (for the FIPS-197 self-test)."""
    return struct.pack(">4I", *_encrypt_block(_expand(key), *struct.unpack(">4I", block)))


def _ctr_pure(key, nonce, data):
    rk = _expand(key)
    n0, n1 = struct.unpack(">2I", nonce[:8])
    blocks = (len(data) + 15) // 16
    out = bytearray()
    for i in range(blocks):
        out += struct.pack(">4I", *_encrypt_block(rk, n0, n1, (i >> 32) & 0xFFFFFFFF, i & 0xFFFFFFFF))
    ks = int.from_bytes(out[:len(data)], "big")
    return (int.from_bytes(data, "big") ^ ks).to_bytes(len(data), "big")


def ctr(key, nonce, data):
    """AES-256-CTR. The nonce's low 8 bytes must be zero (the block counter lives there)."""
    if not data:
        return b""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        c = Cipher(algorithms.AES(key), modes.CTR(nonce)).encryptor()
        return c.update(data) + c.finalize()
    except ImportError:
        return _ctr_pure(key, nonce, data)


# ═══ Keys, locking, unlocking ═══════════════════════════════════════════════

def normalize(password):
    return "".join(str(password).split()).lower()


def derive(password, salt, iterations=ITERATIONS):
    dk = hashlib.pbkdf2_hmac("sha256", normalize(password).encode("utf-8"), salt, iterations, 64)
    return dk[:32], dk[32:]


def lock(obj_bytes, keys, salt, iterations=ITERATIONS):
    """Bytes in (usually JSON), a locked file's bytes out."""
    enc, mac = keys
    nonce = secrets.token_bytes(8) + b"\0" * 8
    body = ctr(enc, nonce, zlib.compress(obj_bytes, 9))
    head = MAGIC + salt + struct.pack(">I", iterations) + nonce
    tag = hmac.new(mac, head + body, hashlib.sha256).digest()
    return head + tag + body


def unlock(blob, password):
    """The reverse (used by the program's own tests and the leak scan). Raises ValueError."""
    if blob[:4] != MAGIC:
        raise ValueError("not a locked team file")
    salt, iters, nonce = blob[4:20], struct.unpack(">I", blob[20:24])[0], blob[24:40]
    tag, body = blob[40:72], blob[72:]
    enc, mac = derive(password, salt, iters)
    if not hmac.compare_digest(tag, hmac.new(mac, blob[:40] + body, hashlib.sha256).digest()):
        raise ValueError("wrong password, or the file was changed")
    return zlib.decompress(ctr(enc, nonce, body))


# ═══ Passwords ══════════════════════════════════════════════════════════════

WORDS = ["acorn", "amber", "anchor", "apple", "arch", "arrow", "aspen", "atlas", "autumn", "badge", "baker", "bamboo", "banjo", "barn", "basin", "beacon", "bear", "berry", "birch", "bison", "blaze", "bloom", "bluff", "bolt", "bonfire", "border", "boulder", "bramble", "brass", "breeze", "brick", "bridge", "brook", "buckle", "buffalo", "bugle", "cabin", "cactus", "camel", "canal", "candle", "canoe", "canyon", "cardinal", "cargo", "castle", "cedar", "chalk", "channel", "cherry", "chestnut", "cinder", "citrus", "clover", "coast", "cobalt", "comet", "compass", "copper", "coral", "cotton", "cougar", "cove", "coyote", "crane", "creek", "crimson", "crown", "crystal", "cypress", "dawn", "delta", "desert", "diesel", "dove", "drum", "dune", "eagle", "ember", "falcon", "fern", "field", "flint", "forge", "fox", "frost", "gable", "garnet", "geyser", "ginger", "glacier", "granite", "gravel", "grove", "gull", "harbor", "harvest", "hawk", "hazel", "heron", "hickory", "hollow", "honey", "horizon", "husky", "iris", "island", "ivory", "jasper", "jetty", "juniper", "kettle", "kite", "lagoon", "lantern", "laurel", "ledge", "lemon", "lilac", "linen", "lion", "lodge", "lotus", "lumber", "magnet", "mallard", "mango", "maple", "marble", "marsh", "meadow", "mesa", "meteor", "mint", "mission", "moose", "mosaic", "motor", "nectar", "needle", "nickel", "north", "nutmeg", "oak", "oasis", "ocean", "olive", "onyx", "orbit", "orchard", "osprey", "otter", "outpost", "owl", "paddle", "panther", "pearl", "pebble", "pecan", "pepper", "pilot", "pine", "pioneer", "plaza", "plum", "polar", "pony", "prairie", "quartz", "quill", "rafter", "rain", "ranch", "raven", "reef", "ridge", "river", "robin", "rocket", "rodeo", "rover", "saddle", "sage", "salmon", "sapphire", "satchel", "scarlet", "shore", "sierra", "silver", "sky", "slate", "sparrow", "spruce", "stallion", "summit", "sunset", "tango", "thistle", "thunder", "timber", "topaz", "tower", "trail", "tulip", "tundra", "valley", "velvet", "violet", "voyage", "walnut", "walrus", "willow", "winter", "wolf", "yarrow", "zephyr"]


def new_password():
    w = [secrets.choice(WORDS) for _ in range(4)]
    return "-".join(w) + f"-{secrets.randbelow(90) + 10}"


def new_salt():
    return secrets.token_bytes(16)
