"""
bot.py — entry point. Sab handlers import hote hi register ho jate hain.

Files:  config.py   settings + story criteria + texts
        core.py     client, MongoDB, helpers, story card (rich message)
        search.py   RapidFuzz search, /start, PM rules
        panel.py    admin control panel
        vault.py    ek private channel se caption-format import
        channels.py har story ka channel: /setvault, episode + extra auto count
        episodes.py caption/title se number padhna (pure functions)
        export.py   /export CSV backup
        webserver.py Render keep-alive
"""
import threading
import time

import core                                    # sabse pehle (event loop + client)
from core import C, app, buttons, get_official, idle, log, settings, stories
import search, vault, panel, channels, export  # noqa: F401,E401  (handlers register)
from webserver import run_web, self_ping


async def main():
    await stories.create_index("name_lc")
    await stories.create_index("channel_id", sparse=True)
    if not await settings.find_one({"_id": "seeded"}):      # pehli baar default buttons
        t = time.time()
        if C.CHANNEL_LINK:
            await buttons.insert_one({"label": f"👑 {C.CHANNEL_NAME} 👑",
                                      "url": C.CHANNEL_LINK, "order": t})
        if C.DEV_LINK:
            await buttons.insert_one({"label": f"👨‍💻 {C.DEV_NAME}",
                                      "url": C.DEV_LINK, "order": t + 1})
        await settings.insert_one({"_id": "seeded"})
    if C.OFFICIAL_GROUP_LINK and not await get_official():
        await settings.insert_one({"_id": "official", "label": C.OFFICIAL_GROUP_NAME,
                                   "url": C.OFFICIAL_GROUP_LINK})
    await app.start()
    me = await app.get_me()
    log.info("Bot started: @%s", me.username)
    await idle()
    await app.stop()


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    core.loop.run_until_complete(main())
