"""panel.py — admin control panel: menus, add/edit flows, buttons, stats, callbacks"""
from core import *  # noqa: F401,F403
from search import invalidate_names
from vault import vault_view
from wishlist import clear_request


# ───────────── panel keyboards / texts ─────────────
HOME_BACK = M([[B("🏠 Menu", callback_data="p:home")]])
CANCEL_KB = M([[B("🚫 Cancel", callback_data="cancel")]])


async def home_text():
    tot = await stories.count_documents({})
    on = await stories.count_documents({"status": C.STATUS_ONGOING})
    done = await stories.count_documents({"status": C.STATUS_COMPLETED})
    return (hdr("🛠  CONTROL PANEL") +
            f"📚 Stories: <b>{tot}</b>\n🔥 Ongoing: <b>{on}</b>   ✅ Completed: <b>{done}</b>\n"
            f"{C.DIVIDER}\nNeeche se option chuno 👇")


def home_kb():
    return M([
        [B("➕ Add Story", callback_data="p:add"), B("✏️ Edit Story", callback_data="ls:e:0")],
        [B("🗑 Delete Story", callback_data="ls:d:0"), B("📋 All Stories", callback_data="ls:v:0")],
        [B("📡 Channels", callback_data="ls:c:0"), B("📥 Story Vault", callback_data="p:vault")],
        [B("🔘 Global Buttons", callback_data="p:gb"), B("🏠 Official Group", callback_data="p:og")],
        [B("📊 Stats", callback_data="p:stats"), B("👥 Admins", callback_data="p:admins")],
        [B("📬 Requests", callback_data="rq:v"), B("❌ Close", callback_data="p:close")],
    ])


def choice_rows(sch, cb, custom_cb):
    btns = [B(lbl, callback_data=cb(val)) for val, lbl in choice_items(sch)]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    if sch.get("allow_custom"):
        rows.append([B("✍️ Custom", callback_data=custom_cb)])
    return rows


def edit_text(s):
    return hdr("✏️  EDIT STORY") + card(s) + "\n\n<b>Kya edit karna hai?</b>"


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
    rows.append([B("🔘 Story Buttons", callback_data=f"sb:{sid}"),
                 B("📡 Channel", callback_data=f"ci:{sid}")])
    rows.append([B("👁 Preview", callback_data=f"vi:{sid}"),
                 B("⬅️ Back", callback_data="ls:e:0")])
    return M(rows)


async def list_kb(mode, page, query=None):
    query = query or {}
    total = await stories.count_documents(query)
    rows = []
    cur = stories.find(query, {"name": 1, "status": 1, "channel_lost": 1}) \
                 .sort("name_lc", 1).skip(page * C.PAGE_SIZE).limit(C.PAGE_SIZE)
    async for s in cur:
        icon = "⚠️" if s.get("channel_lost") else status_icon(s.get("status"))
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
    await show(cq, hdr("🔘  GLOBAL BUTTONS") +
               "Ye buttons <b>har story</b> ke neeche dikhte hain.\n"
               f"Abhi: <b>{len(btns)}</b>\n\nDelete karne ke liye button par tap karo.", M(rows))


async def sb_view(cq, s):
    sid = s["_id"]
    rows = [[B(f"🗑 {x['label']}"[:40], callback_data=f"sbd:{sid}:{i}")]
            for i, x in enumerate(s.get("buttons", []))]
    rows.append([B("➕ Add Button", callback_data=f"sba:{sid}")])
    rows.append([B("⬅️ Back", callback_data=f"ei:{sid}")])
    await show(cq, hdr("🔘  STORY BUTTONS") + f"📖 <b>{esc(s['name'])}</b>\n"
               "Ye buttons sirf is story ke neeche dikhte hain.\n\n"
               "Delete karne ke liye tap karo.", M(rows))


async def og_view(cq):
    og = await get_official()
    if og:
        txt = (hdr("🏠  OFFICIAL GROUP") + f"Button: <b>{esc(og['label'])}</b>\n"
               f"Link: {esc(og['url'])}\n\nNormal users ko PM me ye button dikhta hai.")
        rows = [[B("✏️ Change", callback_data="og:set"), B("🗑 Remove", callback_data="og:del")]]
    else:
        txt = (hdr("🏠  OFFICIAL GROUP") + "Abhi koi official group set nahi hai.\n\n"
               "Normal users PM me search nahi kar sakte; unhe ye group dikhaya jata hai.")
        rows = [[B("➕ Set Official Group", callback_data="og:set")]]
    rows.append([B("🏠 Menu", callback_data="p:home")])
    await show(cq, txt, M(rows))




# ───────────── admin commands ─────────────
@app.on_message(filters.command("panel"))
async def panel(_, m):
    if not m.from_user or not await is_admin(m.from_user.id):
        return
    if m.chat.type != ChatType.PRIVATE:
        return await m.reply_text("🔒 Panel sirf bot ke private chat me khulta hai.")
    STATE.pop(m.from_user.id, None)
    await m.reply_text(await home_text(), reply_markup=home_kb())


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
def add_head(st):
    n = len(C.ADD_STEPS)
    return hdr("➕  ADD STORY") + f"{bar(st['i'] + 1, n)}  <b>{st['i'] + 1}/{n}</b>\n\n"


async def ask_step(target, uid):
    st = STATE[uid]
    key = C.ADD_STEPS[st["i"]]
    sch = S[key]
    text = add_head(st) + f"{sch['emoji']} <b>{sch['label']}</b>\n{sch['prompt']}"
    rows = []
    if sch["kind"] == "choice":
        rows += choice_rows(sch, lambda v: f"af:{key}:{v}", "af:custom")
    if not sch.get("required"):
        text += "\n\n<i>Chhodne ke liye /skip ya Skip button</i>"
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
    await clear_request(doc["name_lc"])
    cid = chat_of(target)
    await app.send_message(cid, C.SAVED_TEXT)
    await send_story(cid, doc)
    await app.send_message(cid, await home_text(), reply_markup=home_kb())


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
    if kind == "choice":
        for val, lbl in choice_items(sch):
            if txt.lower() in (val.lower(), lbl.lower()):
                return True, val, None
        if sch.get("allow_custom"):
            return True, txt[:40], None
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
        return await m.reply_text(await home_text(), reply_markup=home_kb())

    mode = st["mode"]

    if mode == "btn":
        if st["step"] == "label":
            if not txt:
                return await m.reply_text("Button ka naam text me bhejo.")
            st["label"] = txt[:40]
            st["step"] = "url"
            return await m.reply_text(
                "Ab button ka <b>link</b> bhejo\n(https://... ya @username ya t.me/...):",
                reply_markup=CANCEL_KB)
        url = norm_url(txt)
        if not url:
            return await m.reply_text("❌ Sahi link bhejo (https://... ya @username):")
        STATE.pop(uid, None)
        item = {"label": st["label"], "url": url}
        if st["scope"] == "official":
            await settings.update_one({"_id": "official"}, {"$set": item}, upsert=True)
            return await m.reply_text("✅ Official Group set ho gaya!", reply_markup=M([
                [B("🏠 Official Group", callback_data="p:og")],
                [B("🏠 Menu", callback_data="p:home")]]))
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
        await m.reply_text("✅ <b>Update ho gaya!</b>\n\n" + edit_text(s), reply_markup=edit_kb(sid))


# ───────────── callbacks ─────────────
STORY_CB = {"ei", "vi", "di", "dy", "sb", "sbd", "sba", "ed", "ev", "ec", "ci", "cu"}
BTN_PROMPT = "🔘 <b>Button ka naam</b> bhejo\n(jaise: 💬 Contact, 💰 Buy Now):"


@app.on_callback_query(~filters.regex(r"^(ch|rq):"))
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
        await typing(cq.message.chat.id)
        return await send_story(cq.message.chat.id, s)

    if not await is_admin(uid):
        return await cq.answer("Sirf admin ke liye 🚫", show_alert=True)
    await cq.answer()

    if d in ("cancel", "p:home"):
        STATE.pop(uid, None)
        return await show(cq, await home_text(), home_kb())

    if d == "p:close":
        return await cq.message.delete()

    if d == "p:add":
        STATE[uid] = {"mode": "add", "i": 0, "data": {}}
        return await ask_step(cq, uid)

    if d == "p:stats":
        tot = await stories.count_documents({})
        on = await stories.count_documents({"status": C.STATUS_ONGOING})
        done = await stories.count_documents({"status": C.STATUS_COMPLETED})
        cur = await stories.aggregate([{"$group": {"_id": None, "t": {"$sum": {"$ifNull": [
            "$total", {"$add": [{"$ifNull": ["$regular", 0]}, {"$ifNull": ["$extra", 0]}]}]}},
            "r": {"$sum": {"$ifNull": ["$regular", 0]}}, "e": {"$sum": {"$ifNull": ["$extra", 0]}}}}])
        agg = await cur.to_list()
        t, r, e = (agg[0]["t"], agg[0]["r"], agg[0]["e"]) if agg else (0, 0, 0)
        n_adm = await admins.count_documents({})
        n_ch = await stories.count_documents({"channel_id": {"$exists": True}})
        return await show(cq, (
            hdr("📊  STATS") +
            f"📚 Total stories: <b>{tot}</b>\n🔥 Ongoing: <b>{on}</b>\n"
            f"✅ Completed: <b>{done}</b>\n📌 Other: <b>{tot-on-done}</b>\n{C.DIVIDER}\n"
            f"🎬 Total episodes: <b>{t}</b>\n📊 Regular: <b>{r}</b>   💡 Extra: <b>{e}</b>\n"
            f"{C.DIVIDER}\n📡 Linked channels: <b>{n_ch}</b>\n👥 Admins: <b>{n_adm+1}</b>"), HOME_BACK)

    if d == "p:admins":
        ids = [str(a["_id"]) async for a in admins.find({})]
        return await show(cq, (
            hdr("👥  ADMINS") + f"👑 Owner: <code>{C.OWNER_ID}</code>\n"
            f"🛡 Admins: {', '.join(ids) if ids else 'koi nahi'}\n\n"
            "Owner commands:\n/addadmin user_id\n/rmadmin user_id"), HOME_BACK)

    if d == "p:vault":
        return await vault_view(cq)

    if d == "vault:connect":
        code = f"VAULT-{secrets.randbelow(900000) + 100000}"
        await settings.update_one({"_id": "vault_pending"}, {"$set": {
            "code": code, "uid": uid, "exp": time.time() + C.VAULT_CODE_MINUTES * 60}}, upsert=True)
        return await show(cq, hdr("🔗  CONNECT VAULT") +
                          "1️⃣ Ek <b>private channel</b> banao\n"
                          "2️⃣ Is bot ko channel ka <b>Admin</b> banao (Post, Edit, Delete messages)\n"
                          "3️⃣ Channel me ye code post karo:\n\n"
                          f"<code>{code}</code>\n\n"
                          f"⏳ Code {C.VAULT_CODE_MINUTES} minute tak chalega.",
                          M([[B("📄 Caption Format", callback_data="vault:guide")],
                             [B("⬅️ Back", callback_data="p:vault")]]))

    if d == "vault:off":
        await settings.delete_one({"_id": "vault"})
        await settings.delete_one({"_id": "vault_pending"})
        return await vault_view(cq)

    if d == "vault:guide":
        return await show(cq, C.VAULT_FORMAT_HELP, M([[B("⬅️ Back", callback_data="p:vault")]]))

    if d == "p:gb":
        return await gb_view(cq)

    if d == "p:og":
        return await og_view(cq)

    if d == "og:set":
        STATE[uid] = {"mode": "btn", "scope": "official", "step": "label"}
        return await show(cq, hdr("🏠  OFFICIAL GROUP") +
                          "Button ka <b>naam</b> bhejo (jaise: 👥 Official Group):", CANCEL_KB)

    if d == "og:del":
        await settings.delete_one({"_id": "official"})
        return await og_view(cq)

    if d == "gb:add":
        STATE[uid] = {"mode": "btn", "scope": "global", "step": "label"}
        return await show(cq, BTN_PROMPT, CANCEL_KB)

    if k == "gbd":
        i = oid(p[1])
        if i:
            await buttons.delete_one({"_id": i})
        return await gb_view(cq)

    if k == "ls":
        mode, page = p[1], int(p[2])
        query = {"channel_id": {"$exists": True}} if mode == "c" else None
        kb, total = await list_kb(mode, page, query)
        title = {"e": "✏️  EDIT STORY", "d": "🗑  DELETE STORY", "v": "📋  ALL STORIES",
                 "c": "📡  LINKED CHANNELS"}[mode]
        extra = ("\n<i>Channel me <code>/setvault Story Naam | 1378</code> post karo.\n"
                 "⚠️ = channel se bot hat gaya</i>\n") if mode == "c" else ""
        return await show(cq, hdr(title) + f"Total: <b>{total}</b>{extra}\nStory chuno 👇", kb)

    if k == "af":                                    # add-flow ke buttons
        st = STATE.get(uid)
        if not st or st["mode"] != "add":
            return
        key = C.ADD_STEPS[st["i"]]
        if p[1] == "custom":
            return await show(cq, add_head(st) + f"✍️ <b>Custom {S[key]['label']}</b>\n"
                              "Apni value type karke bhejo:", CANCEL_KB)
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
        await show(cq, edit_text(s), edit_kb(sid))

    elif k == "vi":
        await send_story(cq.message.chat.id, s)

    elif k == "di":
        await show(cq, hdr("🗑  DELETE STORY") + card(s) + "\n\n⚠️ <b>Pakka delete karna hai?</b>",
                   M([[B("✅ Haan, delete", callback_data=f"dy:{sid}"),
                       B("❌ Nahi", callback_data="ls:d:0")]]))

    elif k == "dy":
        await stories.delete_one({"_id": s["_id"]})
        invalidate_names()
        kb, total = await list_kb("d", 0)
        await show(cq, hdr("🗑  DELETE STORY") +
                   f"✅ '<b>{esc(s['name'])}</b>' delete ho gayi.\n\nTotal: <b>{total}</b>", kb)

    elif k == "ev":                                  # choice field ki value seedhe set
        key, val = p[2], d.split(":", 3)[3]
        await stories.update_one({"_id": s["_id"]}, {"$set": {key: val}})
        s[key] = val
        STATE.pop(uid, None)
        await show(cq, edit_text(s), edit_kb(sid))

    elif k == "ed":                                  # field edit
        key = p[2]
        sch = S[key]
        rows = []
        if sch["kind"] == "choice":
            rows += choice_rows(sch, lambda v: f"ev:{sid}:{key}:{v}", f"ec:{sid}:{key}")
        if sch["kind"] != "choice" or sch.get("allow_custom"):
            STATE[uid] = {"mode": "edit", "sid": sid, "key": key}
        hint = "\n\n<i>Hatane ke liye <code>-</code> bhejo.</i>" if not sch.get("required") else ""
        rows.append([B("🚫 Cancel", callback_data="cancel")])
        await show(cq, hdr("✏️  EDIT") + f"{sch['emoji']} <b>{sch['label']}</b>\n"
                   f"{sch['prompt']}{hint}", M(rows))

    elif k == "ec":                                  # custom value type karni hai
        key = p[2]
        STATE[uid] = {"mode": "edit", "sid": sid, "key": key}
        await show(cq, hdr("✏️  CUSTOM") + f"{S[key]['emoji']} <b>{S[key]['label']}</b>\n"
                   "Apni value type karke bhejo:", CANCEL_KB)

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
        await show(cq, BTN_PROMPT, CANCEL_KB)

    elif k == "ci":                                  # story ka channel link
        if s.get("channel_id"):
            lost = "\n⚠️ <b>Bot channel se hat gaya hai</b> — nayi posts track nahi hongi." \
                   if s.get("channel_lost") else ""
            await show(cq, hdr("📡  CHANNEL") + f"📖 <b>{esc(s['name'])}</b>\n"
                       f"📡 Channel: <b>{esc(s.get('channel_title', '—'))}</b>\n"
                       f"📊 Regular: <b>{s.get('regular', 0)}</b>   💡 Extra: <b>{s.get('extra', 0)}</b>"
                       f"{lost}\n\nNaya episode post hote hi Regular apne-aap badhta hai.",
                       M([[B("🔌 Unlink", callback_data=f"cu:{sid}")],
                          [B("⬅️ Back", callback_data=f"ei:{sid}")]]))
        else:
            await show(cq, hdr("📡  CHANNEL") + f"📖 <b>{esc(s['name'])}</b>\n\n"
                       "Abhi koi channel juda nahi hai.\nBot ko channel ka Admin banao aur "
                       f"channel me ye post karo:\n<code>/setvault {esc(s['name'])}</code>",
                       M([[B("⬅️ Back", callback_data=f"ei:{sid}")]]))

    elif k == "cu":                                  # unlink
        await stories.update_one({"_id": s["_id"]}, {"$unset": {
            "channel_id": "", "channel_title": "", "channel_lost": "", "linked_by": ""}})
        kb, total = await list_kb("c", 0, {"channel_id": {"$exists": True}})
        await show(cq, hdr("📡  LINKED CHANNELS") + f"🔌 '<b>{esc(s['name'])}</b>' unlink ho gayi.\n\n"
                   f"Total: <b>{total}</b>", kb)


