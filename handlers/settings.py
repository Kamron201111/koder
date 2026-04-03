from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import get_user, update_user
from services import ai

router = Router()

class S(StatesGroup):
    persona = State()
    delay   = State()

def settings_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🗣 Uslub", callback_data="set_style")
    kb.button(text="🌐 Til", callback_data="set_language")
    kb.button(text="🧠 Persona (tavsif)", callback_data="set_persona")
    kb.button(text="⏱ Javob kechikishi", callback_data="set_delay")
    kb.button(text="👁 O'qildi belgisi", callback_data="toggle_read")
    kb.button(text="🗑 Suhbat tarixini tozalash", callback_data="clear_ai_history")
    kb.button(text="🔙 Orqaga", callback_data="back_main")
    kb.adjust(2, 1, 1, 1, 1, 1)
    return kb.as_markup()

STYLE_NAMES = {
    "friendly": "😊 Do'stona",
    "formal":   "👔 Rasmiy",
    "short":    "⚡ Qisqa",
    "humorous": "😄 Hazilkash"
}
LANG_NAMES = {
    "uz": "🇺🇿 O'zbek",
    "ru": "🇷🇺 Rus",
    "en": "🇺🇸 Ingliz"
}

@router.callback_query(F.data == "settings")
async def settings_menu(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    style = STYLE_NAMES.get(user.ai_style if user else "friendly", "Do'stona")
    lang  = LANG_NAMES.get(user.ai_language if user else "uz", "O'zbek")
    has_persona = "✅" if user and user.ai_persona else "❌"
    delay = user.reply_delay if user else 2
    read  = "✅ Yoqiq" if user and user.auto_read else "❌ O'chiq"

    text = (
        "⚙️ **AI Sozlamalari**\n\n"
        f"🗣 Uslub: **{style}**\n"
        f"🌐 Til: **{lang}**\n"
        f"🧠 Persona: {has_persona}\n"
        f"⏱ Kechikish: **{delay} soniya**\n"
        f"👁 O'qildi: **{read}**\n\n"
        "Quyidagilardan birini o'zgartiring 👇"
    )
    await cb.message.edit_text(text, reply_markup=settings_kb(), parse_mode="Markdown")

# ── Uslub ─────────────────────────────────────────────
@router.callback_query(F.data == "set_style")
async def set_style(cb: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="😊 Do'stona", callback_data="style_friendly")
    kb.button(text="👔 Rasmiy", callback_data="style_formal")
    kb.button(text="⚡ Qisqa", callback_data="style_short")
    kb.button(text="😄 Hazilkash", callback_data="style_humorous")
    kb.button(text="🔙 Orqaga", callback_data="settings")
    kb.adjust(2, 2, 1)
    await cb.message.edit_text("🗣 **Uslub tanlang:**\n\nAI qanday uslubda javob bersin?", reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("style_"))
async def apply_style(cb: CallbackQuery):
    style = cb.data.replace("style_", "")
    await update_user(cb.from_user.id, ai_style=style)
    ai.clear_history(cb.from_user.id)
    await cb.answer(f"✅ Uslub: {STYLE_NAMES.get(style, style)}")
    await settings_menu(cb)

# ── Til ───────────────────────────────────────────────
@router.callback_query(F.data == "set_language")
async def set_language(cb: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 O'zbek", callback_data="lang_uz")
    kb.button(text="🇷🇺 Rus", callback_data="lang_ru")
    kb.button(text="🇺🇸 Ingliz", callback_data="lang_en")
    kb.button(text="🔙 Orqaga", callback_data="settings")
    kb.adjust(3, 1)
    await cb.message.edit_text("🌐 **Til tanlang:**", reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("lang_"))
async def apply_lang(cb: CallbackQuery):
    lang = cb.data.replace("lang_", "")
    await update_user(cb.from_user.id, ai_language=lang)
    ai.clear_history(cb.from_user.id)
    await cb.answer(f"✅ Til: {LANG_NAMES.get(lang, lang)}")
    await settings_menu(cb)

# ── Persona ───────────────────────────────────────────
@router.callback_query(F.data == "set_persona")
async def set_persona_start(cb: CallbackQuery, state: FSMContext):
    user = await get_user(cb.from_user.id)
    cur = f"\n\n📌 Hozirgi:\n_{user.ai_persona[:200]}_" if user and user.ai_persona else ""
    await state.set_state(S.persona)
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Bekor", callback_data="settings")
    await cb.message.edit_text(
        f"🧠 **Persona kiriting:**\n\n"
        f"AI qanday muloqot qilishini belgilang.\n"
        f"_(Masalan: Men dasturchi yordamchisiman, texnik savollarni hal qilaman)_"
        f"{cur}\n\n"
        f"O'chirish uchun: `-` yuboring",
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

@router.message(S.persona)
async def process_persona(msg: Message, state: FSMContext):
    await state.clear()
    persona = "" if msg.text.strip() == "-" else msg.text.strip()[:500]
    await update_user(msg.from_user.id, ai_persona=persona)
    ai.clear_history(msg.from_user.id)
    result = "o'chirildi" if not persona else "saqlandi"
    kb = InlineKeyboardBuilder()
    kb.button(text="⚙️ Sozlamalar", callback_data="settings")
    await msg.answer(f"✅ Persona {result}!", reply_markup=kb.as_markup())

# ── Kechikish ─────────────────────────────────────────
@router.callback_query(F.data == "set_delay")
async def set_delay_menu(cb: CallbackQuery):
    kb = InlineKeyboardBuilder()
    for sec in [1, 2, 3, 5, 8]:
        kb.button(text=f"{sec} soniya", callback_data=f"delay_{sec}")
    kb.button(text="🔙 Orqaga", callback_data="settings")
    kb.adjust(3, 2, 1)
    await cb.message.edit_text(
        "⏱ **Javob kechikishi:**\n\n"
        "AI necha soniyadan keyin javob bersin?\n"
        "_(Tabiiyroq ko'rinish uchun 2-3 son tavsiya)_",
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("delay_"))
async def apply_delay(cb: CallbackQuery):
    delay = int(cb.data.replace("delay_", ""))
    await update_user(cb.from_user.id, reply_delay=delay)
    await cb.answer(f"✅ Kechikish: {delay} soniya")
    await settings_menu(cb)

# ── O'qildi belgisi ───────────────────────────────────
@router.callback_query(F.data == "toggle_read")
async def toggle_read(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    new_val = not (user.auto_read if user else True)
    await update_user(cb.from_user.id, auto_read=new_val)
    state = "Yoqildi" if new_val else "O'chirildi"
    await cb.answer(f"👁 O'qildi belgisi: {state}")
    await settings_menu(cb)

# ── Tarixni tozalash ──────────────────────────────────
@router.callback_query(F.data == "clear_ai_history")
async def clear_history_cb(cb: CallbackQuery):
    count = ai.get_user_count(cb.from_user.id)
    ai.clear_history(cb.from_user.id)
    await cb.answer(f"🗑 {count} ta suhbat tarixi tozalandi!", show_alert=True)
