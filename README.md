# Story Detail Bot

Group me koi story ka naam type kare -> bot typing dikhake Rich Message (table) me poster + details + buttons bhejta hai.
PM me search sirf Owner/Admin ke liye. Normal user ko PM me Official Group button dikhta hai.
Admin control panel: bot ke private chat me /panel

## Libraries (sirf 3)
kurigram==2.2.26, pymongo==4.20.0, rapidfuzz==3.14.5   |   Python 3.13 (.python-version)

## Render Environment Variables
API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID
(optional) CHANNEL_NAME, CHANNEL_LINK, DEV_NAME, DEV_LINK, OFFICIAL_GROUP_NAME, OFFICIAL_GROUP_LINK
Official Group / buttons baad me /panel se bhi badal sakte ho.

## Panel
Add / Edit / Delete Story, All Stories, Global Buttons, Official Group, Stats, Admins
Edit me: Name, Poster, Language, Status, Regular, Extra, Total (override), Price, Note, Story Buttons
Har choice list (Language, Status) me "Custom" button.

## config.py me badalne layak
RICH_MESSAGES, TYPING_ENABLED, TYPING_SECONDS, FUZZY_SCORE_CUTOFF, AUTO_PICK_GAP,
STORY_SCHEMA, ADD_STEPS, EDIT_FIELDS, CARD_ORDER, LANGUAGES, PM_USER_TEXT

## Deploy
1. MongoDB Atlas (free) -> connection string, Network Access: 0.0.0.0/0
2. Files GitHub repo me daalo (.python-version me sirf 3.13)
3. Render -> New Web Service -> Free plan
   Build: pip install -r requirements.txt   Start: python bot.py
4. UptimeRobot se Render URL ko har 5 min ping karo
5. BotFather -> /setprivacy -> Disable, aur bot ko group me admin banao
