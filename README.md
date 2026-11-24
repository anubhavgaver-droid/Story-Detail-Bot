# Story Detail Bot

Group me koi story ka naam type kare -> bot poster + poori details + buttons bhejta hai.
Admin control panel: bot ke private chat me /panel

## Files
- bot.py          : main bot (Kurigram + PyMongo)
- config.py       : saari settings, texts, story criteria
- requirements.txt: kurigram, pymongo
- .python-version : Python 3.13
- render.yaml     : Render free web service

## Render Environment Variables
API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID
(optional) CHANNEL_NAME, CHANNEL_LINK, DEV_NAME, DEV_LINK

## Deploy
1. MongoDB Atlas (free) -> connection string, Network Access: 0.0.0.0/0
2. Files GitHub repo me daalo
3. Render -> New Web Service -> Free plan
   Build: pip install -r requirements.txt   Start: python bot.py
4. UptimeRobot se Render URL ko har 5 min ping karo
5. BotFather -> /setprivacy -> Disable, aur bot ko group me admin banao
