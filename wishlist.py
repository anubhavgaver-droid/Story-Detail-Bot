"""wishlist.py — group me jo story maangi gayi par bot me nahi hai: yaad rakhna + admin ko batana + panel list"""
import re
import time

from core import *  # noqa: F401,F403

reqs = db.requests


async def add_request(m, name):
    """story request note karta hai (unique users gine jate hain) aur zaroorat par owner ko batata hai"""
    key = re.sub(r"\s+", " ", name.lower().strip())[:60]
    if not key or not m.from_user:
        return
    uid = m.from_user.id
    old = await reqs.find_one({"name_lc": key})
    new_user = not old or uid not in old.get("users", [])
    if new_user:
        await reqs.update_one({"name_lc": key}, {
            "$set": {"name": name.strip()[:60], "last": time.time()},
            "$addToSet": {"users": uid}, "$inc": {"count": 1}}, upsert=True)
    else:
        await reqs.update_one({"name_lc": key}, {"$set": {"last": time.time()}})
        return
    doc = await reqs.find_one({"name_lc": key})
    if doc and doc.get("count", 0) in C.REQUEST_NOTIFY_AT:
        try:
            await app.send_message(
                C.OWNER_ID, hdr("📬  STORY REQUEST") + f"📖 <b>{esc(doc['name'])}</b>\n"
                f"👥 <b>{doc['count']}</b> log maang rahe hain\n"
                f"💬 Group: {esc(getattr(m.chat, 'title', None) or '—')}",
                M([[B("🗑 Hatao (add ho gayi)", callback_data=f"rq:d:{doc['_id']}")],
                   [B("📬 Saari requests", callback_data="rq:v")]]))
        except Exception as e:
            log.warning("request notify fail: %s", e)


async def clear_request(name_lc):
    """story add ho gayi to uski request hata do"""
    await reqs.delete_many({"name_lc": name_lc})


async def rq_view(cq):
    docs = await reqs.find({}).sort("count", -1).limit(15).to_list()
    total = await reqs.count_documents({})
    rows = [[B(f"🗑 {d['name']} · {d.get('count', 1)}"[:60], callback_data=f"rq:d:{d['_id']}")]
            for d in docs]
    if docs:
        rows.append([B("🧹 Sab hatao", callback_data="rq:clear")])
    rows.append([B("🏠 Menu", callback_data="p:home")])
    txt = hdr("📬  STORY REQUESTS")
    txt += (f"Total: <b>{total}</b>\nJo stories group me maangi gayi par bot me nahi hain "
            "(sabse zyada maangi wali upar).\n\nHatane ke liye tap karo." if docs
            else "Abhi koi pending request nahi hai 🎉")
    await show(cq, txt, M(rows))


@app.on_callback_query(filters.regex(r"^rq:"))
async def rq_cb(_, cq):
    if not await is_admin(cq.from_user.id):
        return await cq.answer("Sirf admin ke liye 🚫", show_alert=True)
    await cq.answer()
    p = cq.data.split(":")
    if p[1] == "d":
        i = oid(p[2])
        if i:
            await reqs.delete_one({"_id": i})
    elif p[1] == "clear":
        await reqs.delete_many({})
    await rq_view(cq)
