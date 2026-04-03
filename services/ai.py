"""
AI Service — Groq (asosiy) + Gemini (zaxira)
Har foydalanuvchi uchun alohida suhbat tarixi
"""
import aiohttp
import asyncio
import json
from config import GROQ_API_KEY, GEMINI_API_KEY, GROQ_MODEL, GEMINI_MODEL

# {owner_id: {sender_id: [messages]}}
_history: dict[int, dict[int, list]] = {}

def _build_system(persona: str, style: str, language: str) -> str:
    lang_map = {"uz": "o'zbek", "ru": "rus", "en": "ingliz"}
    style_map = {
        "friendly": "samimiy, iliq va do'stona",
        "formal":   "rasmiy va professional",
        "short":    "juda qisqa (1-2 jumla)",
        "humorous": "qiziqarli va hazilkash"
    }
    lang_str  = lang_map.get(language, "o'zbek")
    style_str = style_map.get(style, "samimiy")

    base = (
        f"Sen Telegram foydalanuvchisining shaxsiy yordamchisisisan. "
        f"{lang_str} tilida, {style_str} uslubda javob ber.\n\n"
        f"MUHIM QOIDALAR:\n"
        f"- Salomlashuvga salomlash bilan javob ber\n"
        f"- 'Yaxshimisiz/Qalaysiz/Charchamayapsizmi' -> samimiy, iliq javob\n"
        f"- Savol bo'lsa -> aniq va foydali javob ber\n"
        f"- Hech qachon 'Men AI man' yoki 'Men bot man' dema\n"
        f"- Egangiz band, sen uning nomidan javob berasan\n"
        f"- Tabiiy, insoniy uslubda yoz\n"
        f"- Imzo yoki qo'shimcha narsa QO'SHMA\n"
    )
    if persona:
        base += f"\nQO'SHIMCHA: {persona}"
    return base

def get_history(owner_id: int, sender_id: int) -> list:
    return _history.setdefault(owner_id, {}).setdefault(sender_id, [])

def add_to_history(owner_id: int, sender_id: int, role: str, content: str):
    h = get_history(owner_id, sender_id)
    h.append({"role": role, "content": content})
    if len(h) > 12:
        _history[owner_id][sender_id] = h[-12:]

def clear_history(owner_id: int, sender_id: int = None):
    if sender_id:
        _history.get(owner_id, {}).pop(sender_id, None)
    else:
        _history.pop(owner_id, None)

def get_user_count(owner_id: int) -> int:
    return len(_history.get(owner_id, {}))

# ── Groq ─────────────────────────────────────────────
async def _groq(messages: list, system: str) -> str | None:
    if not GROQ_API_KEY:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": 400,
        "temperature": 0.85
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as r:
            data = await r.json()
            if r.status == 200:
                return data["choices"][0]["message"]["content"].strip()
            print(f"[Groq {r.status}] {data.get('error', '')}")
            return None

# ── Gemini ───────────────────────────────────────────
async def _gemini(messages: list, system: str) -> str | None:
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    gemini_msgs = [
        {"role": "model" if m["role"] == "assistant" else "user",
         "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": gemini_msgs,
        "generationConfig": {"maxOutputTokens": 400, "temperature": 0.85}
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as r:
            data = await r.json()
            if r.status == 200:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"[Gemini {r.status}] {data.get('error', {}).get('message', '')}")
            return None

# ── Asosiy funksiya ───────────────────────────────────
async def get_response(
    owner_id: int,
    sender_id: int,
    message: str,
    persona: str = "",
    style: str = "friendly",
    language: str = "uz"
) -> str:
    system = _build_system(persona, style, language)
    add_to_history(owner_id, sender_id, "user", message)
    msgs = get_history(owner_id, sender_id)

    text = None

    # 1. Groq
    try:
        text = await _groq(msgs, system)
        if text:
            add_to_history(owner_id, sender_id, "assistant", text)
            return text
    except Exception as e:
        print(f"[Groq xato] {e}")

    # 2. Gemini zaxira
    try:
        text = await _gemini(msgs, system)
        if text:
            add_to_history(owner_id, sender_id, "assistant", text)
            return text
    except Exception as e:
        print(f"[Gemini xato] {e}")

    # 3. Ikkalasi ham ishlamasa
    get_history(owner_id, sender_id).pop()  # oxirgi xabarni olib tashla
    return "..."  # Jimlik — javob bermasligi ham tabiiy ko'rinadi
