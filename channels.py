"""channels.py — har story ka apna channel: /setvault se link, episodes + extra auto count"""
import time

from core import *  # noqa: F401,F403
from search import all_names, invalidate_names
from episodes import extract_episode, extract_extra, parse_setvault

MEDIA = ("audio", "video", "document", "voice", "video_note", "animation")
_ME = {}


async def my_id():
    if "id" not in _ME:
        _ME["id"] = (await app.get_me()).id
    return _ME["id"]


async def pm(uid, text, kb=None):
    try:
        await app.send_message(uid, text, reply_markup=kb)
    except Exception as e:
        log.warning("PM %s fail: %s", uid, e)


async def trusted_admin(chat_id):
    """Is channel me owner ya koi bot-admin khud Admin hai? to uski user id, warna None"""
    ids = [C.OWNER_ID] + [a["_id"] async for a in admins.find({})]
    for uid in ids:
        try:
            cm = await app.get_chat_member(chat_id, uid)
            if cm.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
                return uid
        except Exception:
            continue
    return None


async def link_story(chat_id, title, name, by, photo=None, regular=None, extra=None):
    """channel ko story se jodta hai (story na ho to banata hai) -> (story_doc, created)"""
    name_lc = name.lower()
    fields = {"channel_id": chat_id, "channel_title": title,
              "channel_lost": False, "linked_by": by}
    if photo:
        fields["photo"] = photo
    if regular is not None:
        fields["regular"] = regular
    if extra is not None:
        fields["extra"] = extra
    # ye channel pehle kisi aur story se juda tha to wahan se hata do
    await stories.update_many({"channel_id": chat_id, "name_lc": {"$ne": name_lc}},
                              {"$unset": {"channel_id": "", "channel_title": "",
                                          "channel_lost": "", "linked_by": ""}})
    story = await stories.find_one({"name_lc": name_lc})
    created = story is None
    if created:
        story = {"name": name, "name_lc": name_lc, "language": C.VAULT_DEFAULT_LANGUAGE,
                 "status": C.VAULT_DEFAULT_STATUS, "regular": 0, "extra": 0,
                 "buttons": [], "created": time.time(), **fields}
        await stories.insert_one(story)
    else:
        await stories.update_one({"_id": story["_id"]}, {"$set": fields})
        story.update(fields)
    invalidate_names()
    return story, created


# ───────────── channel posts ─────────────
@app.on_message(filters.channel, group=2)
@app.on_edited_message(filters.channel, group=2)
async def channel_post(_, m):
    txt = (m.caption or m.text or "").strip()
    cmd = parse_setvault(txt)
    if cmd is not None:
        if not m.edit_date:
            await on_setvault(m, cmd)
        return
    story = await stories.find_one({"channel_id": m.chat.id})
    if story:
        await track_post(m, story, txt)


async def on_setvault(m, cmd):
    uid = await trusted_admin(m.chat.id)
    if uid is None:                          # ajnabi channel — chup-chaap ignore
        return
    title = m.chat.title or "Channel"
    name = cmd["name"] or title
    story, created = await link_story(m.chat.id, title, name, uid,
                                      m.photo.file_id if m.photo else None,
                                      cmd["regular"], cmd["extra"])
    try:
        await m.delete()
    except Exception:
        pass
    await pm(uid, hdr("📡  CHANNEL LINKED") +
             f"📡 Channel: <b>{esc(title)}</b>\n📖 Story: <b>{esc(story['name'])}</b> "
             f"{'(nayi bani)' if created else '(pehle se thi)'}\n"
             f"📊 Regular: <b>{story.get('regular', 0)}</b>   💡 Extra: <b>{story.get('extra', 0)}</b>"
             f"{'   🖼 Poster set' if m.photo else ''}\n\n"
             "Ab is channel me naya episode aate hi Regular apne-aap badhega.\n"
             "Extra ke liye channel me likho: <code>Extra Episodes: 5</code>")


async def track_post(m, story, txt):
    has_media = any(getattr(m, a, None) for a in MEDIA)

    ex = extract_extra(txt) if txt else None
    if ex is not None:                       # "Extra Episodes available 5"
        new = max(story.get("extra", 0), ex) if has_media else ex
        if new != story.get("extra", 0):
            await stories.update_one({"_id": story["_id"]}, {"$set": {"extra": new}})
        return

    if not has_media and not C.TRACK_TEXT_POSTS:
        return                               # sirf audio/video/file posts episode maani jati hain

    def attr(obj, name):
        return getattr(getattr(m, obj, None), name, None) if getattr(m, obj, None) else None

    title = attr("audio", "title")
    fname = attr("audio", "file_name") or attr("video", "file_name") or attr("document", "file_name")
    ep = extract_episode([txt, title, fname], [story["name"], m.chat.title or ""])
    if not ep:
        return
    cur = story.get("regular", 0)
    if ep <= cur:
        return
    if cur and ep - cur > C.MAX_EP_JUMP:     # shaq wala bada jump — admin se poochho
        await pm(story.get("linked_by") or C.OWNER_ID,
                 hdr("⚠️  EPISODE CHECK") + f"📖 <b>{esc(story['name'])}</b>\n"
                 f"Abhi: <b>{cur}</b>  →  Naya mila: <b>{ep}</b>\n\nSahi hai? Set kar dun?",
                 M([[B(f"✅ Haan, {ep} set karo", callback_data=f"ch:ep:{story['_id']}:{ep}"),
                     B("❌ Nahi", callback_data="ch:n")]]))
        return
    await stories.update_one({"_id": story["_id"]}, {"$max": {"regular": ep}})


# ───────────── bot ko admin banaya / hataya ─────────────
@app.on_chat_member_updated(group=3)
async def my_status(_, u):
    try:
        new = u.new_chat_member
        if not new or not new.user or new.user.id != await my_id():
            return
        chat = u.chat
        if chat.type != ChatType.CHANNEL:
            return
        title = chat.title or "Channel"
        actor = u.from_user.id if u.from_user else None

        if new.status == ChatMemberStatus.ADMINISTRATOR:
            if not actor or not await is_admin(actor):
                return
            hit = None
            names = await all_names()
            if names:
                hit = process.extractOne(title.lower(), names, scorer=fuzz.WRatio,
                                         score_cutoff=C.CHANNEL_MATCH_SCORE)
            rows = []
            if hit:
                s = await get_story(hit[2])
                txt = (hdr("📡  NAYA CHANNEL MILA") + f"Channel: <b>{esc(title)}</b>\n"
                       f"Milti-julti story: <b>{esc(s['name'])}</b>\n\nIse jod dun?")
                rows.append([B("✅ Haan, jodo", callback_data=f"ch:y:{chat.id}:{hit[2]}")])
            else:
                txt = (hdr("📡  NAYA CHANNEL MILA") + f"Channel: <b>{esc(title)}</b>\n"
                       "Is naam ki koi story nahi mili.")
            rows.append([B("➕ Is naam se nayi story", callback_data=f"ch:mk:{chat.id}")])
            rows.append([B("❌ Abhi nahi", callback_data="ch:n")])
            txt += "\n\n<i>Ya channel me post karo: <code>/setvault Story Naam</code></i>"
            await pm(actor, txt, M(rows))

        elif new.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED,
                            ChatMemberStatus.RESTRICTED):
            linked = await stories.find({"channel_id": chat.id}).to_list()
            if not linked:
                return
            await stories.update_many({"channel_id": chat.id}, {"$set": {"channel_lost": True}})
            for s in linked:
                await pm(s.get("linked_by") or C.OWNER_ID,
                         hdr("⚠️  CHANNEL SE BOT HATA") + f"📡 <b>{esc(title)}</b>\n"
                         f"📖 Story: <b>{esc(s['name'])}</b>\n\n"
                         "Story ka saara data bot me surakshit hai, par nayi posts track nahi hongi.\n"
                         "Kisi channel me dobara jodne ke liye wahan "
                         f"<code>/setvault {esc(s['name'])}</code> post karo.")
    except Exception as e:
        log.warning("my_status error: %s", e)


# ───────────── buttons (ch:...) ─────────────
@app.on_callback_query(filters.regex(r"^ch:"))
async def on_ch_cb(_, cq):
    uid = cq.from_user.id
    if not await is_admin(uid):
        return await cq.answer("Sirf admin ke liye 🚫", show_alert=True)
    await cq.answer()
    p = cq.data.split(":")

    if p[1] == "n":
        return await cq.message.delete()

    if p[1] == "ep":                         # ch:ep:<story_id>:<n>
        i = oid(p[2])
        if i:
            await stories.update_one({"_id": i}, {"$set": {"regular": int(p[3])}})
        return await show(cq, f"✅ Regular episodes <b>{p[3]}</b> set ho gaye.")

    chat_id = int(p[2])
    try:
        chat = await app.get_chat(chat_id)
        title = chat.title or "Channel"
    except Exception:
        title = "Channel"

    if p[1] == "y":                          # ch:y:<chat_id>:<story_id>
        s = await get_story(p[3])
        if not s:
            return await show(cq, "Story nahi mili.")
        s, _c = await link_story(chat_id, title, s["name"], uid)
    else:                                    # ch:mk:<chat_id>
        s, _c = await link_story(chat_id, title, title, uid)
    await show(cq, hdr("📡  CHANNEL LINKED") + f"📡 <b>{esc(title)}</b>  →  📖 <b>{esc(s['name'])}</b>\n"
               f"📊 Regular: <b>{s.get('regular', 0)}</b>   💡 Extra: <b>{s.get('extra', 0)}</b>\n\n"
               "Naya episode aate hi Regular apne-aap badhega.")
