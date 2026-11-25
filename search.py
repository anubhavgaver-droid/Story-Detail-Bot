"""search.py — RapidFuzz search, /start, group + PM search handlers"""
from core import *  # noqa: F401,F403


# ───────────── search (RapidFuzz) ─────────────
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




# ───────────── public: start + search ─────────────
async def pm_user_reply(m):
    """PM me normal user: search nahi, sirf Official Group dikhao"""
    rows = []
    og = await get_official()
    if og:
        rows.append([B(og["label"], url=og["url"])])
    rows += [[B(label, url=url)] for label, url in await button_pairs()]
    await m.reply_text(C.PM_USER_TEXT, reply_markup=M(rows) if rows else None)


@app.on_message(filters.command("start"))
async def start(_, m):
    adm = bool(m.from_user) and await is_admin(m.from_user.id)
    if m.chat.type == ChatType.PRIVATE and not adm:
        return await pm_user_reply(m)
    txt = C.WELCOME_TEXT + ("\n\n🛠 Admin: /panel" if adm else "")
    await m.reply_text(txt, reply_markup=await build_kb())


@app.on_message(filters.text & ~filters.regex(r"^/") & ~in_flow & ~filters.via_bot)
async def search(_, m):
    if not m.from_user or m.from_user.is_bot:
        return
    private = m.chat.type == ChatType.PRIVATE
    if private and not await is_admin(m.from_user.id):
        return await pm_user_reply(m)
    q = m.text.strip().lower()
    if len(q) < C.MIN_QUERY_LEN:
        return
    res = await find_matches(q)
    if not res:
        if private and C.REPLY_NOT_FOUND_IN_PRIVATE:
            await m.reply_text(C.NOT_FOUND_TEXT)
        return
    await typing(m.chat.id)
    best, best_score = res[0]
    if (len(res) == 1 or best["name_lc"] == q
            or best_score - res[1][1] >= C.AUTO_PICK_GAP):
        return await reply_story(m, best)
    kb = M([[B(doc["name"][:60], callback_data=f"pk:{doc['_id']}")] for doc, _sc in res])
    await m.reply_text(C.PICK_TEXT, reply_markup=kb)


