"""
core.py — shared base: Telegram client, MongoDB collections, helpers, story card + rich message.
Baaki saari files (search / panel / vault / channels) isse import karti hain.
"""
import asyncio
import html
import json
import logging
import re
import secrets
import time
import urllib.error
import urllib.request

# Python 3.13/3.14 me pyrogram import se pehle event loop chahiye
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from bson import ObjectId                                   # noqa: E402  (pymongo ke saath aata hai)
from bson.errors import InvalidId                           # noqa: E402
from pymongo import AsyncMongoClient                        # noqa: E402
from rapidfuzz import fuzz, process                         # noqa: E402
from pyrogram import Client, filters, idle                  # noqa: E402
from pyrogram.enums import (ChatAction, ChatMemberStatus,   # noqa: E402
                            ChatType, ParseMode)
from pyrogram.errors import MessageNotModified              # noqa: E402
from pyrogram.types import (CallbackQuery,                  # noqa: E402
                            InlineKeyboardButton as B,
                            InlineKeyboardMarkup as M)

import config as C                                          # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("storybot")

app = Client("storybot", api_id=C.API_ID, api_hash=C.API_HASH, bot_token=C.BOT_TOKEN,
             in_memory=True, parse_mode=ParseMode.HTML)

mongo = AsyncMongoClient(C.MONGO_URI)
db = mongo[C.DB_NAME]
stories, admins, buttons, settings = db.stories, db.admins, db.buttons, db.settings

S = C.STORY_SCHEMA
esc = html.escape
STATE = {}          # user_id -> chat flow (add / edit / button)
in_flow = filters.create(lambda _, __, m: bool(m.from_user) and m.from_user.id in STATE)


# ───────────── helpers ─────────────
def oid(x):
    try:
        return ObjectId(x)
    except (InvalidId, TypeError):
        return None


async def get_story(sid):
    i = oid(sid)
    return await stories.find_one({"_id": i}) if i else None


async def is_admin(uid):
    return uid == C.OWNER_ID or bool(await admins.find_one({"_id": uid}))


def choice_items(sch):
    ch = sch["choices"]
    return list(ch.items()) if isinstance(ch, dict) else [(c, c) for c in ch]


def status_icon(st):
    return {C.STATUS_COMPLETED: "✅", C.STATUS_ONGOING: "🔥"}.get(st, "📌")


def total_of(s):
    t = s.get("total")
    return int(t) if t is not None else int(s.get("regular", 0)) + int(s.get("extra", 0))


def card_rows(s):
    """[(emoji+label, value), ...]  config.CARD_ORDER ke hisab se"""
    rows = []
    for key in C.CARD_ORDER:
        v = total_of(s) if key == "total" else s.get(key)
        if v in (None, ""):
            continue
        sch = S[key]
        if sch["kind"] == "choice" and isinstance(sch["choices"], dict):
            v = sch["choices"].get(v, v)
        rows.append((f"{sch['emoji']} {sch['label']}", str(v)))
    return rows


def card(s):
    lines = [f"{S['name']['emoji']} <b>{esc(s['name'])}</b>\n"]
    lines += [f"{lbl}: <b>{esc(v)}</b>" for lbl, v in card_rows(s)]
    if s.get(C.NOTE_KEY):
        lines.append(f"\n{S[C.NOTE_KEY]['emoji']} {esc(s[C.NOTE_KEY])}")
    return "\n".join(lines)


def hdr(title):
    return f"<b>{title}</b>\n{C.DIVIDER}\n"


def bar(i, n):
    return "▰" * i + "▱" * (n - i)


def norm_url(u):
    u = (u or "").strip()
    if u.startswith("@"):
        return "https://t.me/" + u[1:]
    if re.match(r"^(t\.me|telegram\.me)/", u):
        return "https://" + u
    if re.match(r"^https?://\S+\.\S+$", u) or re.match(r"^tg://\S+$", u):
        return u
    return None


async def get_official():
    return await settings.find_one({"_id": "official"})


async def button_pairs(s=None):
    pairs = [(x["label"], x["url"]) for x in (s or {}).get("buttons", [])]
    async for x in buttons.find({}).sort("order", 1):
        pairs.append((x["label"], x["url"]))
    return pairs


async def build_kb(s=None):
    pairs = await button_pairs(s)
    return M([[B(label, url=url)] for label, url in pairs]) if pairs else None


# ───────────── Rich Message (Bot API 10.1+): table wala story card ─────────────
def rich_card(s):
    parts = []
    if s.get("photo"):
        parts.append('<img src="tg://photo?id=poster"/>')
    parts.append(f"<h2>{esc(s['name'])}</h2>")
    cell = 'align="left" valign="middle"'
    rows = [f'<tr><th {cell}>{esc(lbl)}</th><td {cell}>{esc(v)}</td></tr>'
            for lbl, v in card_rows(s)]
    attrs = "bordered" + (" striped" if C.RICH_TABLE_STRIPED else "")
    parts.append(f"<table {attrs}>{''.join(rows)}</table>")
    if s.get(C.NOTE_KEY):
        parts.append(f"<blockquote><p>{esc(s[C.NOTE_KEY])}</p></blockquote>")
    return "".join(parts)


def _api_call(method, payload):
    """Bot API ko seedha HTTPS se bulata hai (rich message ke liye)"""
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{C.BOT_TOKEN}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {"ok": False, "description": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "description": str(e)}


async def send_rich(chat_id, s, reply_to=None):
    rm = {"html": rich_card(s)}
    if s.get("photo"):
        rm["media"] = [{"id": "poster", "media": {"type": "photo", "media": s["photo"]}}]
    payload = {"chat_id": chat_id, "rich_message": rm}
    pairs = await button_pairs(s)
    if pairs:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": t, "url": u}] for t, u in pairs]}
    if reply_to:
        payload["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
    res = await asyncio.to_thread(_api_call, "sendRichMessage", payload)
    if not res.get("ok"):
        log.warning("sendRichMessage fail, purana format use hoga: %s", res.get("description"))
    return bool(res.get("ok"))


async def send_story(chat_id, s):
    if C.RICH_MESSAGES and await send_rich(chat_id, s):
        return
    kb = await build_kb(s)
    if s.get("photo"):
        try:
            return await app.send_photo(chat_id, s["photo"], caption=card(s), reply_markup=kb)
        except Exception as e:
            log.warning("photo send failed: %s", e)
    await app.send_message(chat_id, card(s), reply_markup=kb)


async def reply_story(m, s):
    if C.RICH_MESSAGES and await send_rich(m.chat.id, s, m.id):
        return
    kb = await build_kb(s)
    if s.get("photo"):
        try:
            return await m.reply_photo(s["photo"], caption=card(s), reply_markup=kb)
        except Exception as e:
            log.warning("photo reply failed: %s", e)
    await m.reply_text(card(s), reply_markup=kb)


async def typing(chat_id):
    """Bot ke naam ke neeche 'typing...' dikhata hai"""
    if not C.TYPING_ENABLED:
        return
    try:
        await app.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(C.TYPING_SECONDS)
    except Exception:
        pass


async def show(cq, text, kb=None):
    try:
        await cq.message.edit_text(text, reply_markup=kb)
    except MessageNotModified:
        pass
    except Exception:
        await cq.message.reply_text(text, reply_markup=kb)


async def respond(target, text, kb=None):
    if isinstance(target, CallbackQuery):
        await show(target, text, kb)
    else:
        await target.reply_text(text, reply_markup=kb)


def chat_of(target):
    return target.message.chat.id if isinstance(target, CallbackQuery) else target.chat.id


