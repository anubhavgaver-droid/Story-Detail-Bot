"""phrases.py — bot ki "baat-cheet" ke jumle (Hinglish). Jitne chaho add/badlo; har baar random chunega.
{who} = user ka naam, {name} = story ka naam, {i}/{eps}... jahan likha ho wahan bharta hai."""

NOT_FOUND = [
    "Arre {who}, <b>{name}</b>? Ye story abhi mere paas nahi hai yaar 😅\nAdmin se baat karta hoon, aate hi bata dunga!",
    "Hmm 🤔 <b>{name}</b> abhi list me nahi dikh rahi. Maine admin ko bol diya hai, thoda sabr rakho {who}!",
    "Oho, <b>{name}</b> abhi bot me add nahi hui 🙈 Admin ko request bhej di hai, jaise hi aayegi yahin mil jayegi!",
    "{who} bhai, <b>{name}</b> nahi mili 😕 Spelling ek baar check kar lo. Sahi hai to admin se baat kar lete hain, wo add kar denge 🙌",
    "Yaar <b>{name}</b> abhi mere khazaane me nahi hai 😬 Admin ko note kara diya hai, bas thoda intezaar!",
]

NOT_FOUND_NONAME = [
    "Kaunsi story chahiye {who}? Naam bata do, main dhoondh deta hoon 🔍",
    "Haan {who}, bolo na, kis story ki baat kar rahe ho? Naam likh do 😊",
    "Naam to bata do bhai, phir dekhta hoon kya kar sakta hoon 🕵️",
]

SUGGEST_INTRO = [
    "Haan yaar {who}, ye try karo 👇",
    "Mere hisaab se ye mast hain 😎",
    "Suno {who}, ye stories bahut pasand ki jaati hain 🔥",
    "Chalo {who}, aaj ke liye ye lo 🎧",
]
SUGGEST_FALLBACK = [
    "Bilkul isi tarah ki to nahi mili 😅 par ye bhi kamaal hain 👇",
    "Exact wali nahi mili {who}, lekin ye zaroor pasand aayengi 👇",
]
SUGGEST_OUTRO = [
    "Kisi par tap karo, poori details aa jayengi 👆",
    "Pasand na aaye to dobara bol dena, aur dikhata hoon 😄",
    "Jo pasand aaye us par tap karo 👆",
]
SUGGEST_NONE = [
    "Abhi to koi story hi nahi hai bot me {who} 😅 Admin kaam par lage hain!",
    "Hmm, abhi list khaali hai {who} 🙈 Thodi der baad try karna.",
]

GREET = [
    "Namaste {who}! 🙏 Kaunsi story ki talash hai?",
    "Arre {who}! Kya haal hai 😄 Story ka naam bolo, main dhoondh deta hoon!",
    "Hello {who} 👋 Bolo, aaj kaunsi story sunni hai?",
    "Ram Ram {who} 🙏 Bataiye, kya seva karun?",
]
THANKS = [
    "Koi baat nahi {who} 😊 Maze se suno!",
    "Arre ye to mera kaam hai 😄 Enjoy karo!",
    "Welcome {who}! 🙌 Aur kuch chahiye to bolna.",
]
