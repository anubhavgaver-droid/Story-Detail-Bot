"""
Story Details Bot + Admin Control Panel
Library: Kurigram (pyrogram) + PyMongo Async + RapidFuzz  |  Story card: Telegram Rich Message
Deploy: Render Web Service (free)
Saari settings / story criteria: config.py
"""
import asyncio
import html
import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# Python 3.13/3.14 me pyrogram import se pehle event loop chahiye
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from bson import ObjectId                                   # noqa: E402  (pymongo ke saath aata hai)
from bson.errors import InvalidId                           # noqa: E402
from pymongo import AsyncMongoClient                        # noqa: E402
from rapidfuzz import fuzz, process                         # noqa: E402
from pyrogram import Client, filters, idle                  # noqa: E402
from pyrogram.enums import ChatType, ParseMode              # noqa: E402
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


def card(s):
    lines = [f"{S['name']['emoji']} <b>{esc(s['name'])}</b>\n"]
    for key in C.CARD_ORDER:
        if key == "@total":
            total = int(s.get("regular", 0)) + int(s.get("extra", 0))
            lines.append(f"{C.TOTAL_LABEL}: <b>{total}</b>")
            continue
        v = s.get(key)
        if v in (None, ""):
            continue
        sch = S[key]
        if sch["kind"] == "choice" and isinstance(sch["choices"], dict):
            v = sch["choices"].get(v, v)
        lines.append(f"{sch['emoji']} {sch['label']}: <b>{esc(str(v))}</b>")
    note = s.get(C.NOTE_KEY)
    if note:
        lines.append(f"\n{S[C.NOTE_KEY]['emoji']} {esc(note)}")
    return "\n".join(lines)


def norm_url(u):
    u = (u or "").strip()
    if u.startswith("@"):
        return "https://t.me/" + u[1:]
    if re.match(r"^(t\.me|telegram\.me)/", u):
        return "https://" + u
    if re.match(r"^https?://\S+\.\S+$", u) or re.match(r"^tg://\S+$", u):
        return u
    return None


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
    rows = []
    for key in C.CARD_ORDER:
        if key == "@total":
            total = int(s.get("regular", 0)) + int(s.get("extra", 0))
            rows.append(f'<tr><th {cell}>{esc(C.TOTAL_LABEL)}</th><td {cell}><b>{total}</b></td></tr>')
            continue
        v = s.get(key)
        if v in (None, ""):
            continue
        sch = S[key]
        if sch["kind"] == "choice" and isinstance(sch["choices"], dict):
            v = sch["choices"].get(v, v)
        rows.append(f'<tr><th {cell}>{sch["emoji"]} {esc(sch["label"])}</th>'
                    f'<td {cell}>{esc(str(v))}</td></tr>')
    attrs = "bordered" + (" striped" if C.RICH_TABLE_STRIPED else "")
    parts.append(f"<table {attrs}>{''.join(rows)}</table>")
    note = s.get(C.NOTE_KEY)
    if note:
        parts.append(f"<blockquote><p>{esc(note)}</p></blockquote>")
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


NAMES = {"at": 0.0, "data": {}}


async def all_names():
    if time.time() - NAMES["at"] > C.NAME_CACHE_SECONDS:
        docs = await stories.find({}, {"name_lc": 1}).to_list()
        NAMES["data"] = {str(d["_id"]): d["name_lc"] for d in docs}
        NAMES["at"] = time.time()
    return NAMES["data"]


def invalidate_names():
    NAMES["at"] = 0.0


async def find_matches(q):
    """RapidFuzz se score ke hisab se best stories -> [(doc, score), ...]"""
    names = await all_names()
    if not names:
        return []
    hits = process.extract(q, names, scorer=fuzz.WRatio, limit=C.MAX_MATCHES,
                           score_cutoff=C.FUZZY_SCORE_CUTOFF)
    if not hits:
        return []
    ids = [oid(k) for _, _, k in hits]
    docs = {str(d["_id"]): d async for d in stories.find({"_id": {"$in": ids}})}
    return [(docs[k], score) for _, score, k in hits if k in docs]


HOME_BACK = M([[B("🏠 Menu", callback_data="p:home")]])


def home_kb():
    return M([
        [B("➕ Add Story", callback_data="p:add"), B("✏️ Edit Story", callback_data="ls:e:0")],
        [B("🗑 Delete Story", callback_data="ls:d:0"), B("📋 All Stories", callback_data="ls:v:0")],
        [B("📊 Stats", callback_data="p:stats"), B("👥 Admins", callback_data="p:admins")],
        [B("🔘 Global Buttons", callback_data="p:gb")],
        [B("❌ Close", callback_data="p:close")],
    ])


def edit_kb(sid):
    rows, pair = [], []
    for key in C.EDIT_FIELDS:
        sch = S[key]
        if sch["kind"] == "choice" and not sch.get("allow_custom"):
            rows.append([B(lbl, callback_data=f"ev:{sid}:{key}:{val}")
                         for val, lbl in choice_items(sch)])
        else:
            pair.append(B(f"{sch['emoji']} {sch['label']}", callback_data=f"ed:{sid}:{key}"))
            if len(pair) == 2:
                rows.append(pair)
                pair = []
    if pair:
        rows.append(pair)
    rows.append([B("🔘 Story Buttons", callback_data=f"sb:{sid}")])
    rows.append([B("👁 Preview", callback_data=f"vi:{sid}"),
                 B("⬅️ Back", callback_data="ls:e:0")])
    return M(rows)


async def list_kb(mode, page):
    total = await stories.count_documents({})
    rows = []
    cur = stories.find({}, {"name": 1, "status": 1}).sort("name_lc", 1) \
                 .skip(page * C.PAGE_SIZE).limit(C.PAGE_SIZE)
    async for s in cur:
        icon = "✅" if s.get("status") == C.STATUS_COMPLETED else "🔥"
        rows.append([B(f"{icon} {s['name']}"[:60], callback_data=f"{mode}i:{s['_id']}")])
    nav = []
    if page > 0:
        nav.append(B("⬅️ Prev", callback_data=f"ls:{mode}:{page-1}"))
    if (page + 1) * C.PAGE_SIZE < total:
        nav.append(B("Next ➡️", callback_data=f"ls:{mode}:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([B("🏠 Menu", callback_data="p:home")])
    return M(rows), total


async def gb_view(cq):
    btns = await buttons.find({}).sort("order", 1).to_list()
    rows = [[B(f"🗑 {x['label']}"[:40], callback_data=f"gbd:{x['_id']}")] for x in btns]
    rows.append([B("➕ Add Button", callback_data="gb:add")])
    rows.append([B("🏠 Menu", callback_data="p:home")])
    await show(cq, "🔘 <b>Global Buttons</b>\n(har story ke neeche dikhte hain)\n\n"
                   "Delete karne ke liye button par tap karo.", M(rows))


async def sb_view(cq, s):
    sid = s["_id"]
    rows = [[B(f"🗑 {x['label']}"[:40], callback_data=f"sbd:{sid}:{i}")]
            for i, x in enumerate(s.get("buttons", []))]
    rows.append([B("➕ Add Button", callback_data=f"sba:{sid}")])
    rows.append([B("⬅️ Back", callback_data=f"ei:{sid}")])
    await show(cq, f"🔘 <b>{esc(s['name'])}</b> ke buttons\n(sirf is story ke neeche dikhte hain)"
                   "\n\nDelete karne ke liye tap karo.", M(rows))


# ───────────── public: start + search ─────────────
@app.on_message(filters.command("start"))
async def start(_, m):
    txt = C.WELCOME_TEXT
    if m.from_user and await is_admin(m.from_user.id):
        txt += "\n\n🛠 Admin: /panel"
    await m.reply_text(txt, reply_markup=await build_kb())


@app.on_message(filters.text & ~filters.regex(r"^/") & ~in_flow & ~filters.via_bot)
async def search(_, m):
    if not m.from_user or m.from_user.is_bot:
        return
    q = m.text.strip().lower()
    if len(q) < C.MIN_QUERY_LEN:
        return
    res = await find_matches(q)
    if not res:
        if m.chat.type == ChatType.PRIVATE and C.REPLY_NOT_FOUND_IN_PRIVATE:
            await m.reply_text(C.NOT_FOUND_TEXT)
        return
    best, best_score = res[0]
    if (len(res) == 1 or best["name_lc"] == q
            or best_score - res[1][1] >= C.AUTO_PICK_GAP):
        return await reply_story(m, best)
    kb = M([[B(doc["name"][:60], callback_data=f"pk:{doc['_id']}")] for doc, _sc in res])
    await m.reply_text(C.PICK_TEXT, reply_markup=kb)


# ───────────── admin commands ─────────────
@app.on_message(filters.command("panel"))
async def panel(_, m):
    if not m.from_user or not await is_admin(m.from_user.id):
        return
    if m.chat.type != ChatType.PRIVATE:
        return await m.reply_text("🔒 Panel sirf bot ke private chat me khulta hai.")
    STATE.pop(m.from_user.id, None)
    await m.reply_text(C.HOME_TEXT, reply_markup=home_kb())


@app.on_message(filters.command(["addadmin", "rmadmin"]))
async def manage_admin(_, m):
    if not m.from_user or m.from_user.id != C.OWNER_ID:
        return
    cmd = m.command[0].lower()
    if len(m.command) < 2 or not m.command[1].isdigit():
        return await m.reply_text(f"Use: /{cmd} user_id")
    uid = int(m.command[1])
    if cmd == "addadmin":
        await admins.update_one({"_id": uid}, {"$set": {"added": time.time()}}, upsert=True)
        await m.reply_text(f"✅ {uid} ab admin hai.")
    else:
        await admins.delete_one({"_id": uid})
        await m.reply_text(f"🗑 {uid} admin se hata diya.")


# ───────────── add-story flow (config.ADD_STEPS se chalta hai) ─────────────
async def ask_step(target, uid):
    st = STATE[uid]
    key = C.ADD_STEPS[st["i"]]
    sch = S[key]
    text = (f"➕ <b>Add Story</b>  ({st['i']+1}/{len(C.ADD_STEPS)})\n\n"
            f"{sch['emoji']} <b>{sch['label']}</b> — {sch['prompt']}")
    rows = []
    if sch["kind"] == "choice":
        btns = [B(lbl, callback_data=f"af:{key}:{val}") for val, lbl in choice_items(sch)]
        rows += [btns[i:i + 2] for i in range(0, len(btns), 2)]
    if not sch.get("required"):
        text += "\n\n(Chhodne ke liye /skip ya Skip button)"
        rows.append([B("⏭ Skip", callback_data="af:skip")])
    rows.append([B("🚫 Cancel", callback_data="cancel")])
    await respond(target, text, M(rows))


async def advance(target, uid):
    st = STATE[uid]
    st["i"] += 1
    if st["i"] >= len(C.ADD_STEPS):
        return await finish_add(target, uid)
    await ask_step(target, uid)


async def finish_add(target, uid):
    d = STATE.pop(uid)["data"]
    doc = {}
    for key, sch in S.items():
        if key in d:
            doc[key] = d[key]
        elif "default" in sch:
            doc[key] = sch["default"]
    doc.update(name_lc=doc["name"].lower(), buttons=[], created=time.time())
    await stories.insert_one(doc)
    invalidate_names()
    cid = chat_of(target)
    await app.send_message(cid, C.SAVED_TEXT)
    await send_story(cid, doc)
    await app.send_message(cid, C.HOME_TEXT, reply_markup=home_kb())


async def parse_value(key, m, txt, clearing=False):
    """-> (ok, value, error)"""
    sch = S[key]
    kind = sch["kind"]
    if kind == "photo":
        if m.photo:
            return True, m.photo.file_id, None
        return False, None, "🖼 Photo bhejo."
    if not txt:
        return False, None, "Text bhejo."
    if clearing and txt == "-" and not sch.get("required"):
        return True, None, None
    if kind == "number":
        if txt.isdigit():
            return True, int(txt), None
        return False, None, "Sirf number bhejo (jaise 25)."
    if kind == "choice" and not sch.get("allow_custom"):
        for val, lbl in choice_items(sch):
            if txt.lower() in (val.lower(), lbl.lower()):
                return True, val, None
        return False, None, "Button se chuno."
    return True, txt, None


@app.on_message(in_flow & filters.private & (filters.text | filters.photo))
async def flow_input(_, m):
    uid = m.from_user.id
    st = STATE[uid]
    txt = (m.text or "").strip()
    low = txt.lower()

    if low == "/cancel":
        STATE.pop(uid, None)
        return await m.reply_text(C.HOME_TEXT, reply_markup=home_kb())

    mode = st["mode"]

    if mode == "btn":
        if st["step"] == "label":
            if not txt:
                return await m.reply_text("Button ka naam text me bhejo.")
            st["label"] = txt[:40]
            st["step"] = "url"
            return await m.reply_text(
                "Ab button ka <b>link</b> bhejo\n(https://... ya @username ya t.me/...):",
                reply_markup=M([[B("🚫 Cancel", callback_data="cancel")]]))
        url = norm_url(txt)
        if not url:
            return await m.reply_text("❌ Sahi link bhejo (https://... ya @username):")
        STATE.pop(uid, None)
        item = {"label": st["label"], "url": url}
        if st["scope"] == "global":
            await buttons.insert_one({**item, "order": time.time()})
            kb = M([[B("🔘 Global Buttons", callback_data="p:gb")],
                    [B("🏠 Menu", callback_data="p:home")]])
        else:
            sid = st["scope"]
            await stories.update_one({"_id": oid(sid)}, {"$push": {"buttons": item}})
            kb = M([[B("🔘 Story Buttons", callback_data=f"sb:{sid}")],
                    [B("⬅️ Edit Menu", callback_data=f"ei:{sid}")]])
        return await m.reply_text("✅ Button add ho gaya!", reply_markup=kb)

    if mode == "add":
        key = C.ADD_STEPS[st["i"]]
        if low == "/skip":
            if S[key].get("required"):
                return await m.reply_text("Ye step skip nahi ho sakta.")
            return await advance(m, uid)
        ok, val, err = await parse_value(key, m, txt)
        if not ok:
            return await m.reply_text(err)
        if key == "name" and await stories.find_one({"name_lc": val.lower()}):
            return await m.reply_text("⚠️ Ye story pehle se hai. Dusra naam bhejo:")
        st["data"][key] = val
        return await advance(m, uid)

    if mode == "edit":
        key, sid = st["key"], st["sid"]
        ok, val, err = await parse_value(key, m, txt, clearing=True)
        if not ok:
            return await m.reply_text(err)
        upd = {key: val}
        if key == "name":
            dup = await stories.find_one({"name_lc": val.lower(), "_id": {"$ne": oid(sid)}})
            if dup:
                return await m.reply_text("⚠️ Ye naam pehle se kisi aur story ka hai.")
            upd["name_lc"] = val.lower()
        await stories.update_one({"_id": oid(sid)}, {"$set": upd})
        invalidate_names()
        STATE.pop(uid, None)
        s = await get_story(sid)
        await m.reply_text("✅ Update ho gaya!\n\n" + card(s) + "\n\n<b>Aur kuch edit karna hai?</b>",
                           reply_markup=edit_kb(sid))


# ───────────── callbacks ─────────────
STORY_CB = {"ei", "vi", "di", "dy", "sb", "sbd", "sba", "ed", "ev"}


@app.on_callback_query()
async def on_cb(_, cq):
    d = cq.data or ""
    p = d.split(":")
    k = p[0]
    uid = cq.from_user.id

    if k == "pk":                                   # group user ne story chuni
        s = await get_story(p[1])
        await cq.answer()
        if not s:
            return await show(cq, "Story ab available nahi hai.")
        await cq.message.delete()
        return await send_story(cq.message.chat.id, s)

    if not await is_admin(uid):
        return await cq.answer("Sirf admin ke liye 🚫", show_alert=True)
    await cq.answer()

    if d in ("cancel", "p:home"):
        STATE.pop(uid, None)
        return await show(cq, C.HOME_TEXT, home_kb())

    if d == "p:close":
        return await cq.message.delete()

    if d == "p:add":
        STATE[uid] = {"mode": "add", "i": 0, "data": {}}
        return await ask_step(cq, uid)

    if d == "p:stats":
        tot = await stories.count_documents({})
        on = await stories.count_documents({"status": C.STATUS_ONGOING})
        cur = await stories.aggregate([{"$group": {
            "_id": None, "r": {"$sum": "$regular"}, "e": {"$sum": "$extra"}}}])
        agg = await cur.to_list()
        r, e = (agg[0]["r"], agg[0]["e"]) if agg else (0, 0)
        n_adm = await admins.count_documents({})
        return await show(cq, (
            f"📊 <b>Stats</b>\n\n📚 Total stories: <b>{tot}</b>\n"
            f"🔥 Ongoing: <b>{on}</b>\n✅ Completed: <b>{tot-on}</b>\n"
            f"🎬 Total episodes: <b>{r+e}</b> (Regular {r} + Extra {e})\n"
            f"👥 Admins: <b>{n_adm+1}</b>"), HOME_BACK)

    if d == "p:admins":
        ids = [str(a["_id"]) async for a in admins.find({})]
        return await show(cq, (
            f"👥 <b>Admins</b>\n\nOwner: <code>{C.OWNER_ID}</code>\n"
            f"Admins: {', '.join(ids) if ids else 'koi nahi'}\n\n"
            "Owner commands:\n/addadmin user_id\n/rmadmin user_id"), HOME_BACK)

    if d == "p:gb":
        return await gb_view(cq)

    if d == "gb:add":
        STATE[uid] = {"mode": "btn", "scope": "global", "step": "label"}
        return await show(cq, "🔘 <b>Button ka naam</b> bhejo\n(jaise: 💬 Contact, 💰 Buy Now):",
                          M([[B("🚫 Cancel", callback_data="cancel")]]))

    if k == "gbd":
        i = oid(p[1])
        if i:
            await buttons.delete_one({"_id": i})
        return await gb_view(cq)

    if k == "ls":
        mode, page = p[1], int(p[2])
        kb, total = await list_kb(mode, page)
        title = {"e": "✏️ Edit", "d": "🗑 Delete", "v": "📋 All Stories"}[mode]
        return await show(cq, f"<b>{title}</b>  (total {total})\nStory chuno 👇", kb)

    if k == "af":                                    # add-flow ke buttons
        st = STATE.get(uid)
        if not st or st["mode"] != "add":
            return
        key = C.ADD_STEPS[st["i"]]
        if p[1] == "skip":
            if S[key].get("required"):
                return
        else:
            _, fkey, val = d.split(":", 2)
            if fkey != key:
                return
            st["data"][key] = val
        return await advance(cq, uid)

    if k not in STORY_CB:
        return
    s = await get_story(p[1])
    if not s:
        return await show(cq, "Story nahi mili.", HOME_BACK)
    sid = str(s["_id"])

    if k == "ei":
        await show(cq, card(s) + "\n\n<b>Kya edit karna hai?</b>", edit_kb(sid))

    elif k == "vi":
        await send_story(cq.message.chat.id, s)

    elif k == "di":
        await show(cq, card(s) + "\n\n⚠️ <b>Pakka delete karna hai?</b>", M([[
            B("✅ Haan, delete", callback_data=f"dy:{sid}"),
            B("❌ Nahi", callback_data="ls:d:0")]]))

    elif k == "dy":
        await stories.delete_one({"_id": s["_id"]})
        invalidate_names()
        kb, total = await list_kb("d", 0)
        await show(cq, f"🗑 '<b>{esc(s['name'])}</b>' delete ho gayi.\n\nTotal: {total}", kb)

    elif k == "ev":                                  # choice field ki value seedhe set
        key, val = p[2], d.split(":", 3)[3]
        await stories.update_one({"_id": s["_id"]}, {"$set": {key: val}})
        s[key] = val
        STATE.pop(uid, None)
        await show(cq, card(s) + "\n\n<b>Kya edit karna hai?</b>", edit_kb(sid))

    elif k == "ed":                                  # text/number/photo field edit
        key = p[2]
        sch = S[key]
        rows = []
        if sch["kind"] == "choice":
            btns = [B(lbl, callback_data=f"ev:{sid}:{key}:{val}") for val, lbl in choice_items(sch)]
            rows += [btns[i:i + 2] for i in range(0, len(btns), 2)]
        if sch["kind"] != "choice" or sch.get("allow_custom"):
            STATE[uid] = {"mode": "edit", "sid": sid, "key": key}
        hint = "\nHatane ke liye <code>-</code> bhejo." if not sch.get("required") else ""
        rows.append([B("🚫 Cancel", callback_data="cancel")])
        await show(cq, f"✏️ {sch['emoji']} <b>{sch['label']}</b> — {sch['prompt']}{hint}", M(rows))

    elif k == "sb":
        await sb_view(cq, s)

    elif k == "sbd":
        bl = s.get("buttons", [])
        idx = int(p[2])
        if 0 <= idx < len(bl):
            bl.pop(idx)
            await stories.update_one({"_id": s["_id"]}, {"$set": {"buttons": bl}})
            s["buttons"] = bl
        await sb_view(cq, s)

    elif k == "sba":
        STATE[uid] = {"mode": "btn", "scope": sid, "step": "label"}
        await show(cq, "🔘 <b>Button ka naam</b> bhejo\n(jaise: 💬 Contact, 💰 Buy Now):",
                   M([[B("🚫 Cancel", callback_data="cancel")]]))


# ───────────── Render keep-alive web server ─────────────
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Story bot is running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


def run_web():
    HTTPServer(("0.0.0.0", C.PORT), Ping).serve_forever()


def self_ping():
    import os
    url = os.getenv("RENDER_EXTERNAL_URL")
    while url:
        time.sleep(C.SELF_PING_SECONDS)
        try:
            urllib.request.urlopen(url, timeout=20)
        except Exception:
            pass


async def main():
    await stories.create_index("name_lc")
    if not await settings.find_one({"_id": "seeded"}):      # pehli baar default buttons
        t = time.time()
        if C.CHANNEL_LINK:
            await buttons.insert_one({"label": f"👑 {C.CHANNEL_NAME} 👑",
                                      "url": C.CHANNEL_LINK, "order": t})
        if C.DEV_LINK:
            await buttons.insert_one({"label": f"👨‍💻 {C.DEV_NAME}",
                                      "url": C.DEV_LINK, "order": t + 1})
        await settings.insert_one({"_id": "seeded"})
    await app.start()
    me = await app.get_me()
    log.info("Bot started: @%s", me.username)
    await idle()
    await app.stop()


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    loop.run_until_complete(main())
