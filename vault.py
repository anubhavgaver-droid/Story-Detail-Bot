"""vault.py — ek private channel se auto import (caption format se stories)"""
from core import *  # noqa: F401,F403
from search import invalidate_names
from wishlist import clear_request


# ───────────── Story Vault: private channel se auto import ─────────────
# (order important: pehle specific labels)
LABELS = [
    ("extra", r"extra\s*episodes?|extra|bonus"),
    ("total", r"total\s*episodes?|total"),
    ("regular", r"regular\s*episodes?|regular|episodes?|eps?"),
    ("language", r"language|lang|bhasha|भाषा"),
    ("status", r"status|state|स्टेटस"),
    ("price", r"price|cost|rate|प्राइस|कीमत"),
    ("note", r"notes?|info|about|नोट"),
    ("name", r"name|title|naam|नाम"),
]
_SEP = r"[:：\-–—|=\t]"
_PRE = r"^[^\w\u0900-\u097F]*"
_NUMERIC = {"regular", "extra", "total"}
_RX = {k: (re.compile(_PRE + rf"(?:{lab})\s*{_SEP}+\s*(.+?)\s*$", re.I),
           re.compile(_PRE + rf"(?:{lab})\s+(\d[\d,]*)\s*(?:episodes?|eps?)?\s*$", re.I))
       for k, lab in LABELS}


def _num(v):
    m = re.search(r"\d[\d,]*", str(v))
    return int(m.group().replace(",", "")) if m else None


def _status(v):
    t = v.lower()
    if re.search(r"\b(complete|completed|finished|done|ended)\b|पूर्ण|समाप्त|✅", t):
        return C.STATUS_COMPLETED
    if re.search(r"\b(ongoing|running|live|active)\b|चालू|जारी|चल रही|🔥", t):
        return C.STATUS_ONGOING
    return v.strip()[:40]


def parse_vault_caption(text):
    """caption -> {name, language, status, regular, extra, total, price, note} (jo mila wahi)"""
    out, first = {}, True
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or re.fullmatch(r"(?i)[^\w]*story\s*details[^\w]*", line):
            continue
        hit = None
        for key, _lab in LABELS:
            r1, r2 = _RX[key]
            m1 = r1.match(line)
            if m1:
                hit = (key, m1.group(1))
                break
            if key in _NUMERIC:
                m2 = r2.match(line)
                if m2:
                    hit = (key, m2.group(1))
                    break
        if hit:
            key, val = hit
            if key in _NUMERIC:
                val = _num(val)
            elif key == "status":
                val = _status(val)
            if val not in (None, ""):
                out.setdefault(key, val)
        elif first:
            name = re.sub(r"^[^\w\u0900-\u097F]+", "", line).strip(" *_`\"'")
            if name:
                out["name"] = name
        first = False
    return out


REPORT = {"added": 0, "updated": 0, "failed": [], "task": None}


async def _flush_report():
    await asyncio.sleep(C.VAULT_REPORT_DELAY)
    a, u, f = REPORT["added"], REPORT["updated"], REPORT["failed"][:]
    REPORT.update(added=0, updated=0, failed=[], task=None)
    vault = await settings.find_one({"_id": "vault"}) or {}
    txt = (hdr("📥  VAULT REPORT") + f"✅ Nayi stories: <b>{a}</b>\n🔄 Update hui: <b>{u}</b>\n"
           f"⚠️ Parse nahi hui: <b>{len(f)}</b>")
    if f:
        txt += "\n\n" + "\n".join(f"• {esc(x)}" for x in f[:15]) + ("\n…" if len(f) > 15 else "")
        txt += "\n\nFormat ke liye: /panel → Story Vault → Caption Format"
    try:
        await app.send_message(vault.get("by") or C.OWNER_ID, txt)
    except Exception as e:
        log.warning("vault report send fail: %s", e)


def note_report(kind, info=None):
    if kind == "fail":
        REPORT["failed"].append(info)
    else:
        REPORT[kind] += 1
    t = REPORT["task"]
    if t and not t.done():
        t.cancel()
    REPORT["task"] = asyncio.get_running_loop().create_task(_flush_report())


async def vault_ingest(m):
    txt = (m.caption or m.text or "").strip()
    f = parse_vault_caption(txt)
    first_line = (txt.splitlines() or ["(khali)"])[0][:40]
    if "name" not in f or ("regular" not in f and "total" not in f):
        why = "naam nahi mila" if "name" not in f else "Regular episodes nahi mile"
        return note_report("fail", f"#{m.id} {first_line} — {why}")

    msg_key = f"{m.chat.id}:{m.id}"
    old = (await stories.find_one({"vault_msg": msg_key})
           or await stories.find_one({"name_lc": f["name"].lower()}))

    tot = f.pop("total", None)
    reg, ext = f.get("regular"), f.get("extra")
    if reg is None:                         # sirf total diya ho
        reg, ext = tot, (ext or 0)
    upd = {k: v for k, v in f.items() if k in S}
    upd["regular"] = reg
    if ext is not None:
        upd["extra"] = ext
    if m.photo:
        upd["photo"] = m.photo.file_id
    upd["vault_msg"] = msg_key
    upd["name_lc"] = f["name"].lower()
    final_ext = upd.get("extra", (old or {}).get("extra", 0))
    if tot is not None:
        upd["total"] = tot if tot != reg + final_ext else None

    if old:
        await stories.update_one({"_id": old["_id"]}, {"$set": upd})
        note_report("updated")
    else:
        doc = {"language": C.VAULT_DEFAULT_LANGUAGE, "status": C.VAULT_DEFAULT_STATUS,
               "extra": 0, "buttons": [], "created": time.time(), **upd}
        await stories.insert_one(doc)
        await clear_request(doc["name_lc"])
        note_report("added")
    invalidate_names()


@app.on_message(filters.channel, group=1)
@app.on_edited_message(filters.channel, group=1)
async def vault_post(_, m):
    txt = (m.caption or m.text or "").strip()
    pend = await settings.find_one({"_id": "vault_pending"})
    if pend and txt == pend["code"]:                       # channel connect code
        if pend["exp"] > time.time():
            if await stories.find_one({"channel_id": m.chat.id}):    # ye kisi story ka apna channel hai
                await app.send_message(pend["uid"], "⚠️ Ye channel kisi story se juda hai, "
                                       "Database channel ke liye alag channel use karo.")
                return
            title = m.chat.title or "Channel"
            await settings.update_one({"_id": "vault"}, {"$set": {
                "chat_id": m.chat.id, "title": title, "by": pend["uid"]}}, upsert=True)
            await settings.delete_one({"_id": "vault_pending"})
            try:
                await m.delete()
            except Exception:
                pass
            await app.send_message(pend["uid"], hdr("📥  VAULT CONNECTED") +
                                   f"🔗 Channel: <b>{esc(title)}</b>\n\n"
                                   "Ab is channel me story cards post ya forward karo, "
                                   "story apne-aap judti jayegi.\nFormat: /panel → Story Vault.")
        return
    vault = await settings.find_one({"_id": "vault"})
    if vault and vault["chat_id"] == m.chat.id:
        await vault_ingest(m)


async def vault_view(cq):
    v = await settings.find_one({"_id": "vault"})
    n = await stories.count_documents({"vault_msg": {"$exists": True}})
    if v:
        txt = (hdr("📥  STORY VAULT") + f"🔗 Connected: <b>{esc(v.get('title', 'Channel'))}</b>\n"
               f"📚 Vault se aayi stories: <b>{n}</b>\n\n"
               "Channel me caption format ke hisab se post / forward karo, story apne-aap judegi.")
        rows = [[B("🔄 Change Channel", callback_data="vault:connect"),
                 B("❌ Disconnect", callback_data="vault:off")]]
    else:
        txt = (hdr("📥  STORY VAULT") + "Abhi koi channel connected nahi hai.\n\n"
               "Private channel connect karo, phir usme cards post / forward karte hi "
               "stories apne-aap bot me add ho jayengi.")
        rows = [[B("🔗 Connect Channel", callback_data="vault:connect")]]
    rows.append([B("📄 Caption Format", callback_data="vault:guide")])
    rows.append([B("🏠 Menu", callback_data="p:home")])
    await show(cq, txt, M(rows))


