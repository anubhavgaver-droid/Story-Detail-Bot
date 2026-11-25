"""export.py — /export: saari stories ka CSV backup (sirf admin)"""
import csv
import io

from core import *  # noqa: F401,F403

FIELDS = ["name", "language", "status", "regular", "extra", "total", "price", "note", "channel_title"]


@app.on_message(filters.command("export") & filters.private)
async def export_csv(_, m):
    if not m.from_user or not await is_admin(m.from_user.id):
        return
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(FIELDS)
    async for s in stories.find({}).sort("name_lc", 1):
        w.writerow([s.get(f, "") if s.get(f) is not None else "" for f in FIELDS])
    data = io.BytesIO(("\ufeff" + buf.getvalue()).encode("utf-8"))   # BOM: Excel me Hindi theek dikhe
    data.name = "stories_backup.csv"
    await m.reply_document(data, caption="📦 Stories backup (CSV)")
