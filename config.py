import os
from dotenv import load_dotenv
load_dotenv()

# ── Main Bot ─────────────────────────────────────────
BOT_TOKEN     = os.getenv("BOT_TOKEN", "7810689974:AAHbALRBHfRtEgvmbr-hFnNaE4CmG-3ImKM")
ADMIN_IDS     = list(map(int, os.getenv("ADMIN_IDS", "6498632307").split(",")))

# ── Telegram API ─────────────────────────────────────
API_ID        = int(os.getenv("API_ID", "23651528"))
API_HASH      = os.getenv("API_HASH", "ca42cf77a78ee409550aac24e179c87e")

# ── AI (Groq primary + Gemini fallback) ─────────────
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "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")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAwNgcob0p0We23O0k8eMlUddWgXxdyZLI")

GROQ_MODEL   = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"

# ── Database ─────────────────────────────────────────
DATABASE_URL  = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/chatspyer")

# ── Limitlar ─────────────────────────────────────────
FREE_DAILY_LIMIT    = 30
PREMIUM_DAILY_LIMIT = 999999

# ── Premium narxlar (UZS) ────────────────────────────
PRICES = {
    "1_month":  49900,
    "3_month": 119900,
    "6_month": 199900,
}
PLAN_MONTHS = {"1_month": 1, "3_month": 3, "6_month": 6}
PLAN_NAMES  = {"1_month": "1 oylik", "3_month": "3 oylik", "6_month": "6 oylik"}

# ── To'lov ───────────────────────────────────────────
PAYMENT_CARD  = os.getenv("PAYMENT_CARD", "8600 0000 0000 0000")
PAYMENT_OWNER = os.getenv("PAYMENT_OWNER", "Admin")
PAYMENT_ADMIN = int(os.getenv("PAYMENT_ADMIN", str(ADMIN_IDS[0])))
