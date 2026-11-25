"""
config.py  —  Bot ki saari settings, texts aur Story ke "criteria" yahin hain.

Render me ye Environment Variables set karo:
    API_ID, API_HASH        -> https://my.telegram.org se
    BOT_TOKEN               -> @BotFather se
    MONGO_URI               -> MongoDB Atlas connection string
    OWNER_ID                -> tumhari Telegram numeric id
    CHANNEL_NAME, CHANNEL_LINK, DEV_NAME, DEV_LINK   (optional, pehli baar buttons banane ke liye)
    OFFICIAL_GROUP_NAME, OFFICIAL_GROUP_LINK         (optional; panel se bhi set/change hota hai)
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
OFFICIAL_GROUP_NAME = os.getenv("OFFICIAL_GROUP_NAME", "👥 Official Group")
OFFICIAL_GROUP_LINK = os.getenv("OFFICIAL_GROUP_LINK", "")   # normal users ko PM me ye dikhega

# ───────────── Render web service (free tier) ─────────────
PORT = int(os.getenv("PORT", "10000"))
SELF_PING_SECONDS = 540          # 9 min: free service ko sone se bachane ke liye

# ───────────── Search criteria (RapidFuzz) ─────────────
MIN_QUERY_LEN = 3                # isse chhota text ignore hoga (group spam se bachne ke liye)
MAX_MATCHES = 6                  # kitni stories ke button dikhane hain
FUZZY_SCORE_CUTOFF = 70          # 0-100: isse kam score wali story match nahi hogi
AUTO_PICK_GAP = 10               # top story dusri se itna aage ho to seedha bhej do, warna buttons
NAME_CACHE_SECONDS = 30          # story ke naam memory me cache (DB baar-baar nahi padhna)
REPLY_NOT_FOUND_IN_PRIVATE = True    # owner/admin ke PM me "nahi mili" bole; group me hamesha chup
# PM me search sirf OWNER + ADMINS ke liye hai. Normal user ko PM_USER_TEXT + Official Group button milta hai.

# ───────────── Typing animation (story milne par bot ke naam ke neeche "typing...") ─────────────
TYPING_ENABLED = True
TYPING_SECONDS = 1.5             # kitni der typing dikhe, phir story bheje

# ───────────── Rich Message (Telegram Bot API 10.1+) ─────────────
RICH_MESSAGES = True             # True: story card rich format (table) me; fail ho to purana format
RICH_TABLE_STRIPED = True        # table ki alternate rows ka shade

# ───────────── Panel ─────────────
PAGE_SIZE = 8                    # list me ek page par kitni stories
DIVIDER = "━━━━━━━━━━━━━━━━"

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
                     allow_custom=True, prompt="Story ka status chuno ya custom likho"),
    "regular":  dict(emoji="📊", label="Regular Episodes", kind="number", required=True,
                     prompt="Regular episodes kitne hain? (number)"),
    "extra":    dict(emoji="💡", label="Extra Episodes", kind="number", required=True,
                     prompt="Extra episodes kitne hain? (0 bhi chalega)"),
    "total":    dict(emoji="📚", label="Total Episodes", kind="number", required=False,
                     prompt="Total episodes bhejo (khali = Regular + Extra apne-aap jodta hai)"),
    "price":    dict(emoji="💰", label="Price", kind="text", required=False,
                     prompt="Price bhejo (jaise ₹99)"),
    "note":     dict(emoji="📝", label="Note", kind="text", required=False,
                     prompt="Note / extra info bhejo"),
}

# Story add karte waqt kis order me kya puchna hai
ADD_STEPS = ["name", "photo", "language", "status", "regular", "extra", "price"]

# Edit menu me kaun-kaun se fields badal sakte hain
EDIT_FIELDS = ["name", "photo", "language", "status", "regular", "extra", "total", "price", "note"]

# Story card me kya aur kis order me dikhana hai
# "total": agar admin ne total set kiya hai to wahi, warna regular + extra
CARD_ORDER = ["language", "status", "regular", "extra", "total", "price"]
NOTE_KEY = "note"                # card ke sabse neeche alag se dikhta hai

# ───────────── Texts ─────────────
WELCOME_TEXT = ("👋 <b>Story Details Bot</b>\n\n"
                "Kisi bhi story ka naam type karo, main uski poori details bhej dunga.")
PM_USER_TEXT = ("🔒 <b>Story search yahan available nahi hai.</b>\n\n"
                "Story ki details paane ke liye hamare <b>Official Group</b> me aao "
                "aur wahan story ka naam type karo 👇")
NOT_FOUND_TEXT = "😕 Story nahi mili. Naam check karke dobara likho."
PICK_TEXT = "🔎 Kaun si story chahiye?"
SAVED_TEXT = ("✅ <b>Story save ho gayi!</b>\n\n"
              "Is story ke khaas buttons ke liye: Edit Story → Story Buttons")

# ───────────── Story Vault (private channel se auto import) ─────────────
VAULT_DEFAULT_LANGUAGE = "Hindi"         # caption me Language na ho to
VAULT_DEFAULT_STATUS = STATUS_ONGOING    # caption me Status na ho to
VAULT_REPORT_DELAY = 8                   # bulk forward ke baad itni der shaanti = ek hi report
VAULT_CODE_MINUTES = 10                  # connect code kitni der valid

VAULT_FORMAT_HELP = (
    "📄 <b>VAULT CAPTION FORMAT</b>\n"
    "━━━━━━━━━━━━━━━━\n"
    "Channel me <b>poster photo</b> ke saath ye caption daalo:\n\n"
    "<pre>Bhai Hero, Main Villain\n"
    "Language: Hindi\n"
    "Status: Ongoing\n"
    "Regular: 1378\n"
    "Extra: 2\n"
    "Total: 1380\n"
    "Price: ₹99\n"
    "Note: Roz 5 episode aate hain</pre>\n"
    "• Pehli line = story ka naam (ya <code>Name: ...</code>)\n"
    "• <b>Zaroori sirf:</b> Naam + Regular\n"
    "• Language, Status, Extra, Total, Price, Note — optional\n"
    "• Language/Status na do to Hindi / Ongoing maana jayega\n"
    "• Total na do to Regular + Extra khud judega\n"
    "• Status: Ongoing / Completed (ya Chalu / Complete)\n"
    "• Post <b>edit</b> karoge to story bhi update ho jayegi\n"
    "• Purane cards seedha <b>forward</b> bhi kar sakte ho\n"
    "• Same naam dobara aaye to nayi nahi banegi, update hogi"
)

# ───────────── Har story ka apna channel (episode auto count) ─────────────
TRACK_TEXT_POSTS = False     # False: sirf audio/video/file posts episode maani jayengi (text announcements nahi)
MAX_EP_JUMP = 50             # itne se bada jump mile to admin se poochhega (galat number se bachav)
CHANNEL_MATCH_SCORE = 88     # bot Admin bante hi channel ke naam se story match (0-100)

# ───────────── Channel: latest post se count (bootstrap) ─────────────
BOOTSTRAP_SCAN = 30          # /setvault ke waqt channel ke aakhri itne messages dekhkar episode count nikalta hai

# ───────────── Human touch (group me baat-cheet) ─────────────
HUMAN_MODE = True            # False: bot sirf seedha search kare, baat-cheet nahi
SUGGEST_COUNT = 3            # "koi achhi story suggest karo" par kitni stories
SHORT_MAX = 150              # "choti story" = itne episode tak
LONG_MIN = 500               # "lambi story" = itne episode se zyada
REQUEST_NOTIFY_AT = (1, 3, 5, 10, 25, 50, 100)   # itne log maangein to owner ko PM jayega
# baat-cheet ke jumle: phrases.py

