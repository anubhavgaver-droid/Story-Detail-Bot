"""episodes.py — caption / title se episode number, extra count aur /setvault command padhna (pure functions)"""
import re

_HI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# primary keywords: episode / ep / एपिसोड  |  secondary: part / भाग
_KW1 = r"(?:\b(?:episodes?|ep)\b\.?|एपिसोड|एपीसोड)"
_KW2 = r"(?:\bpart\b\.?|भाग)"
_SEP = r"[\s#:：\-–—.=_]*"
_NUM = r"(\d{1,5})(?!\d)"
_ORD = r"\s*(?:वां|वाँ|वा|st|nd|rd|th)?\s*"


def _pair(kw):
    return (re.compile(kw + _SEP + _NUM, re.I),                    # "Episode 12", "एपिसोड 12"
            re.compile(r"(?<!\d)(\d{1,5})" + _ORD + kw, re.I))     # "12 एपिसोड", "12th episode"


_STRICT = [_pair(_KW1), _pair(_KW2)]
_PURE = re.compile(r"^[^\w\u0900-\u097F]*(\d{1,5})[^\w\u0900-\u097F]*$")
_ANY = re.compile(r"(?<![\w.])(\d{1,5})(?![\w])")
_EXTRA = re.compile(r"(?:extra|एक्स्ट्रा|एक्सट्रा|बोनस|bonus)[^\d\n]{0,40}?(\d{1,4})(?!\d)", re.I)
_SETVAULT = re.compile(r"^/setvault(?:@\w+)?(?:\s+(.*))?$", re.I | re.S)


def to_ascii(text):
    return (text or "").translate(_HI_DIGITS)


def _clean(text, names):
    t = to_ascii(text).replace("_", " ")          # file names: My_Story_ep_45.mp3
    for n in names:
        if n and n.strip():
            t = re.sub(re.escape(n.strip()), " ", t, flags=re.I)
    return t.strip()


def _strict(t):
    for after, before in _STRICT:
        for rx in (after, before):
            m = rx.search(t)
            if m:
                return int(m.group(1))
    m = _PURE.match(t)
    return int(m.group(1)) if m else None


def extract_episode(sources, names=()):
    """sources: [caption, title, filename] (is order me). Pehle caption, phir title.
    names: story / channel ke naam — inhe hatane ke baad number dhundhta hai
    (taaki 'My Story 1' ka '1' episode na ban jaye)."""
    cleaned = [_clean(s, names) for s in sources if s and str(s).strip()]
    for t in cleaned:
        n = _strict(t)
        if n:
            return n
    for t in cleaned:                      # aakhri koshish: pehla alag number
        m = _ANY.search(t)
        if m and int(m.group(1)) > 0:
            return int(m.group(1))
    return None


def extract_extra(text):
    """'Extra Episodes available 5' / 'एक्स्ट्रा एपिसोड 5' -> 5"""
    m = _EXTRA.search(to_ascii(text))
    return int(m.group(1)) if m else None


def parse_setvault(text):
    """'/setvault Naam | 1378 | 2' -> {name, regular, extra}  (command na ho to None)"""
    m = _SETVAULT.match((text or "").strip())
    if not m:
        return None
    parts = [p.strip() for p in (m.group(1) or "").split("|")]

    def num(i):
        if i < len(parts):
            d = re.search(r"\d+", to_ascii(parts[i]))
            return int(d.group()) if d else None
        return None

    return {"name": parts[0] or None, "regular": num(1), "extra": num(2)}
