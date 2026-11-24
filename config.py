"""
config.py  —  Bot ki saari settings, texts aur Story ke "criteria" yahin hain.

Render me ye Environment Variables set karo:
    API_ID, API_HASH        -> https://my.telegram.org se
    BOT_TOKEN               -> @BotFather se
    MONGO_URI               -> MongoDB Atlas connection string
    OWNER_ID                -> tumhari Telegram numeric id
    CHANNEL_NAME, CHANNEL_LINK, DEV_NAME, DEV_LINK   (optional, pehli baar buttons banane ke liye)
"""
import os


def _req(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Environment variable {name} set nahi hai")
    return val


# ───────────── Telegram / Database ─────────────
API_ID = int(_req("API_ID"))
API_HASH = _req("API_HASH")
BOT_TOKEN = _req("BOT_TOKEN")
OWNER_ID = int(_req("OWNER_ID"))

MONGO_URI = _req("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "storybot")

# ───────────── Default buttons (sirf pehli baar DB me seed hote hain) ─────────────
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "Rk Officials")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "")      # https://t.me/yourchannel
DEV_NAME = os.getenv("DEV_NAME", "Developer")
DEV_LINK = os.getenv("DEV_LINK", "")              # https://t.me/yourusername

# ───────────── Render web service (free tier) ─────────────
PORT = int(os.getenv("PORT", "10000"))
SELF_PING_SECONDS = 540          # 9 min: free service ko sone se bachane ke liye

# ───────────── Search criteria ─────────────
MIN_QUERY_LEN = 3                # isse chhota text ignore hoga (group spam se bachne ke liye)
MAX_MATCHES = 6                  # kitni stories ke button dikhane hain
FUZZY_CUTOFF = 0.6               # spelling galti kitni chalegi (0.0 - 1.0)
REPLY_NOT_FOUND_IN_PRIVATE = True    # private chat me "nahi mili" bole; group me hamesha chup

# ───────────── Panel ─────────────
PAGE_SIZE = 8                    # list me ek page par kitni stories

# ───────────── Story ke criteria (kya-kya fields hote hain) ─────────────
STATUS_ONGOING = "ongoing"
STATUS_COMPLETED = "completed"
LANGUAGES = ["Hindi", "English", "Bengali", "Tamil"]

# kind: text | number | photo | choice
# required: True = skip nahi ho sakta   |   default: skip/na dene par ye value
STORY_SCHEMA = {
    "name":     dict(emoji="📖", label="Name", kind="text", required=True,
                     prompt="Story ka naam bhejo"),
    "photo":    dict(emoji="🖼", label="Poster", kind="photo", required=False,
                     prompt="Poster photo bhejo"),
    "language": dict(emoji="🗣", label="Language", kind="choice", required=True,
                     choices=LANGUAGES, allow_custom=True,
                     prompt="Language chuno ya type karo"),
    "status":   dict(emoji="📡", label="Status", kind="choice", required=True,
                     choices={STATUS_ONGOING: "🔥 Ongoing", STATUS_COMPLETED: "✅ Completed"},
                     prompt="Story ka status chuno"),
    "regular":  dict(emoji="📊", label="Regular Episodes", kind="number", required=True,
                     prompt="Regular episodes kitne hain? (number)"),
    "extra":    dict(emoji="💡", label="Extra Episodes", kind="number", required=True,
                     prompt="Extra episodes kitne hain? (0 bhi chalega)"),
    "price":    dict(emoji="💰", label="Price", kind="text", required=False,
                     prompt="Price bhejo (jaise ₹99)"),
    "note":     dict(emoji="📝", label="Note", kind="text", required=False,
                     prompt="Note / extra info bhejo"),
}

# Story add karte waqt kis order me kya puchna hai
ADD_STEPS = ["name", "photo", "language", "status", "regular", "extra", "price"]

# Edit menu me kaun-kaun se fields badal sakte hain
EDIT_FIELDS = ["name", "photo", "language", "status", "regular", "extra", "price", "note"]

# Story card me kya aur kis order me dikhana hai ("@total" = regular + extra)
CARD_ORDER = ["language", "status", "regular", "extra", "@total", "price"]
TOTAL_LABEL = "📚 Total Episodes"
NOTE_KEY = "note"                # card ke sabse neeche alag se dikhta hai

# ───────────── Texts ─────────────
WELCOME_TEXT = ("👋 <b>Story Details Bot</b>\n\n"
                "Kisi bhi story ka naam type karo, main uski poori details bhej dunga.")
HOME_TEXT = "🛠 <b>Control Panel</b>\n\nKya karna hai?"
NOT_FOUND_TEXT = "😕 Story nahi mili. Naam check karke dobara likho."
PICK_TEXT = "🔎 Kaun si story chahiye?"
SAVED_TEXT = ("✅ <b>Story save ho gayi!</b>\n\n"
              "Is story ke khaas buttons ke liye: Edit Story → Story Buttons")
