from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import update_user, get_user
from services import userbot

router = Router()

class States(StatesGroup):
    phone    = State()
    code     = State()
    password = State()

def cancel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Bekor qilish", callback_data="back_main")
    return kb.as_markup()

# ── Akkunt ulash ──────────────────────────────────────
@router.callback_query(F.data == "connect")
async def connect_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(States.phone)
    await cb.message.edit_text(
        "📱 **Akkunt ulash**\n\n"
        "Telegram raqamingizni kiriting:\n"
        "_(Masalan: +998901234567)_\n\n"
        "⚠️ Faqat siz foydalanадиgan raqam",
        reply_markup=cancel_kb(), parse_mode="Markdown"
    )

@router.message(States.phone)
async def process_phone(msg: Message, state: FSMContext):
    phone = msg.text.strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    wait = await msg.answer("⏳ Kod yuborilmoqda...")
    result = await userbot.send_code(msg.from_user.id, phone)
    if not result["ok"]:
        await wait.edit_text(f"❌ Xato: `{result['error']}`\n\nQaytadan urinib ko'ring.", parse_mode="Markdown")
        await state.clear()
        return
    await state.update_data(phone=phone)
    await state.set_state(States.code)
    await wait.edit_text(
        f"✅ **{phone}** ga SMS kod yuborildi!\n\n"
        "Kodni kiriting _(masalan: 12345)_:",
        reply_markup=cancel_kb(), parse_mode="Markdown"
    )

@router.message(States.code)
async def process_code(msg: Message, state: FSMContext):
    code = msg.text.strip().replace(" ", "")
    result = await userbot.verify_code(msg.from_user.id, code)
    if result.get("need_2fa"):
        await state.set_state(States.password)
        await msg.answer("🔐 **2FA parol** kiriting:", reply_markup=cancel_kb(), parse_mode="Markdown")
        return
    if not result["ok"]:
        await msg.answer(f"❌ Xato: `{result.get('error')}`", reply_markup=cancel_kb(), parse_mode="Markdown")
        return
    await _finish(msg, state, result["session"])

@router.message(States.password)
async def process_2fa(msg: Message, state: FSMContext):
    result = await userbot.verify_2fa(msg.from_user.id, msg.text.strip())
    if not result["ok"]:
        await msg.answer(f"❌ Parol noto'g'ri: `{result.get('error')}`", reply_markup=cancel_kb(), parse_mode="Markdown")
        return
    await _finish(msg, state, result["session"])

async def _finish(msg: Message, state: FSMContext, session: str):
    await state.clear()
    await update_user(msg.from_user.id, session_string=session, is_active=True)
    user = await get_user(msg.from_user.id)
    ok = await userbot.start(msg.from_user.id, session)

    kb = InlineKeyboardBuilder()
    kb.button(text="⚙️ AI Sozlamalari", callback_data="settings")
    kb.button(text="🏠 Bosh menyu", callback_data="back_main")
    kb.adjust(1)

    if ok:
        await msg.answer(
            "🎉 **Akkunt ulandi va AI yoqildi!**\n\n"
            "✅ Endi lichkangizga kimdir yozsa — AI o'zi javob beradi.\n"
            "Siz hech narsa qilmaysiz!\n\n"
            "⚙️ Sozlamalarda AI uslubini o'zgartiring.",
            reply_markup=kb.as_markup(), parse_mode="Markdown"
        )
    else:
        await msg.answer(
            "⚠️ Sessiya saqlandi lekin AI ishga tushmadi.\n"
            "Menyudan qayta yoqib ko'ring.",
            reply_markup=kb.as_markup(), parse_mode="Markdown"
        )

# ── Toggle ────────────────────────────────────────────
@router.callback_query(F.data == "toggle")
async def toggle(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    if not user or not user.session_string:
        await cb.answer("❌ Avval akkuntingizni ulang!", show_alert=True)
        return

    running = userbot.is_running(cb.from_user.id)
    if running:
        await userbot.stop(cb.from_user.id)
        await update_user(cb.from_user.id, is_active=False)
        await cb.answer("🔴 AI to'xtatildi")
        msg = "🔴 **AI to'xtatildi**\n\nEndi lichkangizga javob bermaydi."
    else:
        ok = await userbot.start(cb.from_user.id, user.session_string)
        if ok:
            await update_user(cb.from_user.id, is_active=True)
            await cb.answer("🟢 AI yoqildi!")
            msg = "🟢 **AI yoqildi!**\n\nEndi lichkangizga kimdir yozsa AI o'zi javob beradi."
        else:
            await cb.answer("❌ Xato! Qayta ulang.", show_alert=True)
            return

    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Bosh menyu", callback_data="back_main")
    await cb.message.edit_text(msg, reply_markup=kb.as_markup(), parse_mode="Markdown")
