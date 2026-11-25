# Story Detail Bot

Group me story ka naam type karo -> typing dikhake Rich Message (table) me poster + details + buttons.
PM me search sirf Owner/Admin ke liye; normal user ko Official Group button.
Admin panel: bot ke private chat me /panel     |     Backup: /export (CSV)

## Files (alag-alag, halka code)
bot.py       entry point (start)          core.py      client, MongoDB, helpers, story card
config.py    settings + story criteria    search.py    RapidFuzz search, /start, PM rules
panel.py     admin control panel          vault.py     ek private channel se caption-format import
channels.py  har story ka channel         episodes.py  caption/title se number padhna
export.py    /export CSV backup           webserver.py Render keep-alive

## Libraries: kurigram==2.2.26, pymongo==4.20.0, rapidfuzz==3.14.5  |  Python 3.13

## Render Environment Variables
API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID
(optional) CHANNEL_NAME, CHANNEL_LINK, DEV_NAME, DEV_LINK, OFFICIAL_GROUP_NAME, OFFICIAL_GROUP_LINK

## Har story ka apna channel (episodes auto count)
1. Bot ko us story ke channel ka Admin banao
2. Channel me post karo:   /setvault Story Naam
   (poster chahiye to photo ke caption me yahi command; purane episodes: /setvault Story Naam | 1378 | 2)
3. Uske baad channel me audio/video/file post hote hi Regular episodes apne-aap badhte hain
   - number caption se, na ho to title / file name se (Episode 12, एपिसोड 12, भाग 12, sirf 12, १२)
   - Extra: channel me likho  "Extra Episodes: 5"  /  "एक्स्ट्रा एपिसोड 5"
4. Sirf unhi channels ki /setvault maani jati hai jisme Owner ya bot-admin khud Admin ho
5. Panel -> Channels me linked channels, unlink, aur channel se bot hatne ka warning (⚠️)

## Deploy
1. MongoDB Atlas (free) -> connection string, Network Access: 0.0.0.0/0
2. Files GitHub repo me daalo (.python-version me sirf 3.13)
3. Render -> New Web Service -> Free plan.  Build: pip install -r requirements.txt   Start: python bot.py
4. UptimeRobot se Render URL ko har 5 min ping karo
5. BotFather -> /setprivacy -> Disable, aur bot ko group me admin banao
