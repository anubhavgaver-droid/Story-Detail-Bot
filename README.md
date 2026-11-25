# Story Detail Bot

Group me story ka naam type karo -> typing dikhake Rich Message (table) me poster + details + buttons.
PM me search sirf Owner/Admin ke liye; normal user ko Official Group button.
Admin panel: /panel   |   Backup: /export (CSV)

## Files
bot.py (start) | core.py (client, DB, card) | config.py (settings) | search.py (RapidFuzz search)
panel.py (admin panel) | vault.py (ek database channel) | channels.py (har story ka channel)
episodes.py (number padhna) | human.py (baat-cheet) | phrases.py (jumle) | wishlist.py (requests)
export.py (CSV) | webserver.py (Render keep-alive)

## Libraries: kurigram==2.2.26, pymongo==4.20.0, rapidfuzz==3.14.5 | Python 3.13

## Render Environment Variables
API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID
(optional) CHANNEL_NAME, CHANNEL_LINK, DEV_NAME, DEV_LINK, OFFICIAL_GROUP_NAME, OFFICIAL_GROUP_LINK

## Har story ka apna channel
1. Bot ko channel ka Admin banao  2. Channel me post: /setvault Story Naam   (poster: photo ke caption me)
3. Bot channel ke LATEST posts dekhkar episode count khud nikalta hai (poora channel nahi padhta)
4. Uske baad har naya audio/video/file post -> Regular apne-aap badhta hai (caption -> title -> file name)
5. Extra: channel me likho "Extra Episodes: 5" / "एक्स्ट्रा एपिसोड 5"

## Human touch (group me)
- Story nahi mili + maangne jaisa message -> chatty jawab ("admin se baat karta hoon") + request panel me (📬 Requests)
- "koi achhi story suggest karo" (hindi / complete / choti / lambi / nayi bhi samajhta hai) -> 3 stories + tap-to-open
- Bot ko address karo (reply / @mention / "bot") -> hello, thanks ka jawab
- Jumle badalne ke liye phrases.py; band karne ke liye config.py me HUMAN_MODE = False

## Deploy
1. MongoDB Atlas (free) -> connection string, Network Access 0.0.0.0/0
2. Files GitHub repo me (.python-version me 3.13)
3. Render -> New Web Service -> Free. Build: pip install -r requirements.txt  Start: python bot.py
4. UptimeRobot se Render URL har 5 min ping
5. BotFather -> /setprivacy -> Disable; bot ko group me admin banao
