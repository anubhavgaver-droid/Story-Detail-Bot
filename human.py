"""human.py — group me insaan jaisa baat-cheet: story suggest, story request (nahi mili), greeting, thanks"""
import random
import re
import time

from core import *  # noqa: F401,F403
from phrases import (GREET, NOT_FOUND, NOT_FOUND_NONAME, SUGGEST_FALLBACK, SUGGEST_INTRO,
                     SUGGEST_NONE, SUGGEST_OUTRO, THANKS)
from wishlist import add_request

# ───────────── intent patterns ─────────────
_STORYW = re.compile(r"story|stori|kahani|स्टोरी|कहानी|sunn|सुन", re.I)
_SUG_STRONG = re.compile(r"suggest|sugest|recommend|sujh|सजेस्ट|सुझ", re.I)
_SUG_WEAK = re.compile(r"batao|bata\s*do|btao|kaun\s*si|konsi|kon\s*si|kya\s*sun|कौन\s*सी|बताओ|क्या\s*सुन", re.I)
_ADJ = re.compile(r"acc?h+[ia]|achch?[ia]|acha|achi|badhiya|badiya|mast|best|zabardast|top|nayi|naya|new|latest|famous|trending|hit|"
                  r"अच्छी|अच्छा|बढ़िया|मस्त|बेस्ट|नई|नया", re.I)
_KOI = re.compile(r"\bkoi\b|कोई", re.I)
_THANKS = re.compile(r"thank|thanx|thx|tnx|shukriya|dhanyava?d|शुक्रिया|धन्यवाद", re.I)
_GREET = re.compile(r"\b(hi+|hello+|hey+|namaste|namaskar|ram\s*ram|salaam?|gm|gn|kaise\s*ho|kya\s*haal|"
                    r"good\s*(morning|evening|night|afternoon))\b|नमस्ते|हैलो|हेलो|राम\s*राम|सलाम", re.I)

_REQ_LATIN = re.compile(r"\b(chah?iye|chahie|chaiye|cahiye|milegi|mil\s*(jayegi|jaegi|jaye|sakti|sakta)|"
                        r"hai\s*kya|h\s*kya|available|upload|daal\s*do|dal\s*do|de\s*do|dedo|bhej\s*do|bhejo|"
                        r"kab\s*(aayegi|ayegi|aaegi|tak)|kahan|kaha|link|story|stori|kahani|please|plz|pls)\b", re.I)
_REQ_HINDI = re.compile(r"चाहिए|मिलेगी|मिल\s*जाएगी|है\s*क्या|अपलोड|डाल\s*दो|दे\s*दो|भेजो|कब\s*आएगी|कहाँ|स्टोरी|कहानी")
_FILLER = re.compile(r"\b(bhai|yaar|bro|please|plz|pls|ek|koi|ki|ka|ke|kya|hai|h|ho|to|mujhe|mereko|mere\s*ko|"
                     r"hame|hamein|bot|admin|ji|sir|dedo|de\s*do|do|bhej|bhejo|chah?iye|chahie|chaiye|cahiye|"
                     r"milegi|available|upload|story|stori|kahani|link|kahan|kaha|mil|jayegi|sakti|sakta)\b", re.I)
_FILLER_HI = re.compile(r"भाई|यार|प्लीज|एक|कोई|की|का|के|क्या|है|मुझे|चाहिए|मिलेगी|स्टोरी|कहानी|भेजो|दे\s*दो|दो")

_COOL = {}


def cooling(m, kind, secs=25):
    """spam rokne ke liye: ek user ko ek hi tarah ka jawab thodi der baad hi"""
    key = (m.chat.id, m.from_user.id, kind)
    now = time.time()
    if now - _COOL.get(key, 0) < secs:
        return True
    _COOL[key] = now
    return False


_ME = {}


async def me():
    if "u" not in _ME:
        _ME["u"] = await app.get_me()
    return _ME["u"]


async def is_addressed(m):
    u = await me()
    r = m.reply_to_message
    if r and r.from_user and r.from_user.id == u.id:
        return True
    t = (m.text or "").lower()
    if u.username and f"@{u.username.lower()}" in t:
        return True
    return bool(re.search(r"(?<![a-z])bot(?![a-z])|बॉट|बोट", t))


def who(m):
    n = (m.from_user.first_name or "").strip() if m.from_user else ""
    return esc(n[:20]) if n else "bhai"


def detect_intent(q, addressed=False):
    if _STORYW.search(q) and (_SUG_STRONG.search(q) or (_SUG_WEAK.search(q) and _ADJ.search(q))
                              or (_ADJ.search(q) and _KOI.search(q))):
        return "suggest"
    if addressed:
        if _THANKS.search(q):
            return "thanks"
        if _GREET.search(q) and len(q.split()) <= 6:
            return "greet"
    return None


def looks_like_request(q, addressed=False):
    if len(q.split()) > 12:
        return False
    return bool(addressed or _REQ_LATIN.search(q) or _REQ_HINDI.search(q))


def strip_cues(q):
    t = _FILLER.sub(" ", q)
    t = _FILLER_HI.sub(" ", t)
    t = re.sub(r"[^\w\u0900-\u097F ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def suggest_query(q):
    qq, newest = {}, False
    for lang in C.LANGUAGES:
        if lang.lower() in q:
            qq["language"] = lang
    if "hindi" in q or "हिंदी" in q or "हिन्दी" in q:
        qq["language"] = "Hindi"
    if re.search(r"complete|completed|khatam|poori|pura|पूरी|पूरा|खत्म", q):
        qq["status"] = C.STATUS_COMPLETED
    elif re.search(r"ongoing|chal\s*rahi|chalu|चालू|जारी", q):
        qq["status"] = C.STATUS_ONGOING
    if re.search(r"choti|chhoti|short|छोटी", q):
        qq["regular"] = {"$lte": C.SHORT_MAX}
    elif re.search(r"lambi|long|badi|बड़ी|लंबी", q):
        qq["regular"] = {"$gte": C.LONG_MIN}
    if re.search(r"nayi|naya|new|latest|नई|नया", q):
        newest = True
    return qq, newest


async def _pick(qq, newest, n):
    pipe = [{"$match": qq}]
    pipe += [{"$sort": {"created": -1}}, {"$limit": n}] if newest else [{"$sample": {"size": n}}]
    cur = await stories.aggregate(pipe)
    return await cur.to_list()


# ───────────── responders ─────────────
async def suggest(m, q):
    if cooling(m, "suggest", 15):
        return
    await typing(m.chat.id)
    qq, newest = suggest_query(q)
    docs, fallback = await _pick(qq, newest, C.SUGGEST_COUNT), False
    if not docs and qq:
        docs, fallback = await _pick({}, newest, C.SUGGEST_COUNT), True
    w = who(m)
    if not docs:
        return await m.reply_text(random.choice(SUGGEST_NONE).format(who=w))
    lines = []
    for i, d in enumerate(docs, 1):
        state = "✅ complete" if d.get("status") == C.STATUS_COMPLETED else "🔥 ongoing"
        lines.append(f"{i}. <b>{esc(d['name'])}</b> — {esc(d.get('language', ''))}, "
                     f"{total_of(d)} eps, {state}")
    intro = random.choice(SUGGEST_FALLBACK if fallback else SUGGEST_INTRO).format(who=w)
    text = intro + "\n\n" + "\n".join(lines) + "\n\n" + random.choice(SUGGEST_OUTRO)
    kb = M([[B(f"📖 {d['name'][:40]}", callback_data=f"pk:{d['_id']}")] for d in docs])
    await m.reply_text(text, reply_markup=kb)


async def small_talk(m, kind):
    if cooling(m, kind, 20):
        return
    await typing(m.chat.id)
    await m.reply_text(random.choice(GREET if kind == "greet" else THANKS).format(who=who(m)))


async def not_found(m, guess):
    if cooling(m, "nf", 20):
        return
    await typing(m.chat.id)
    name = (guess or "").strip()
    if len(name) >= C.MIN_QUERY_LEN:
        await add_request(m, name)
        await m.reply_text(random.choice(NOT_FOUND).format(who=who(m), name=esc(name[:50])))
    else:
        await m.reply_text(random.choice(NOT_FOUND_NONAME).format(who=who(m)))
