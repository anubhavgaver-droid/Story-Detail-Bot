# Story Detail Bot

Group me koi story ka naam type kare -> bot Rich Message (table) me poster + details + buttons bhejta hai.
Admin control panel: bot ke private chat me /panel

## Libraries (sirf 3)
- kurigram==2.2.26   (pyrogram namespace)
- pymongo==4.20.0    (async client, MongoDB)
- rapidfuzz==3.14.5  (search score)
Python 3.13 (.python-version)

## Files
- bot.py / config.py / requirements.txt / .python-version / render.yaml

## Render Environment Variables
API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID
(optional) CHANNEL_NAME, CHANNEL_LINK, DEV_NAME, DEV_LINK

## Settings (config.py)
- RICH_MESSAGES = True/False     (rich format on/off; fail hone par purana format apne-aap)
- FUZZY_SCORE_CUTOFF, AUTO_PICK_GAP, MAX_MATCHES (RapidFuzz search)
- STORY_SCHEMA, ADD_STEPS, EDIT_FIELDS, CARD_ORDER (story ke fields)

## Deploy
1. MongoDB Atlas (free) -> connection string, Network Access: 0.0.0.0/0
2. Files GitHub repo me daalo (.python-version me sirf 3.13)
3. Render -> New Web Service -> Free plan
   Build: pip install -r requirements.txt   Start: python bot.py
4. UptimeRobot se Render URL ko har 5 min ping karo
5. BotFather -> /setprivacy -> Disable, aur bot ko group me admin banao
