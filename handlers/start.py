from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import get_or_create_user, get_user
from services.userbot import is_running
from datetime import datetime
from config import FREE_DAILY_LIMIT

router = Router()

def main_kb(active: bool, is_premium: bool):
    kb = InlineKeyboardBuilder()
    status = "🟢 Yoqiq" if active else "🔴 O'chiq"
    kb.button(text=f"🤖 AI Yordamchi: {status}", callback_data="toggle")
    kb.button(text="📱 Akkunt ulash" if not active else "🔄 Qayta ulash", callback_data="connect")
    kb.button(text="⚙️ AI Sozlamalari", callback_data="settings")
    kb.button(text="📊 Mening hisobim", callback_data="myaccount")
    kb.button(text="💎 Premium", callback_data="premium_menu")
    kb.button(text="❓ Yordam", callback_data="help_menu")
    kb.adjust(1)
    return kb.as_markup()

@router.message(CommandStart())
async def start(msg: Message):
    user = await get_or_create_user(msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
    active = is_running(user.id)

    if user.is_premium and user.premium_until:
        days = (user.premium_until - datetime.utcnow()).days
        tarif = f"💎 Premium — {days} kun qoldi"
    else:
        tarif = f"🆓 Bepul — kuniga {FREE_DAILY_LIMIT} ta xabar"

    text = (
        f"👋 Salom, **{msg.from_user.first_name}**!\n\n"
        f"🤖 **ChatSpyer** — AI Avtonom Yordamchi\n\n"
        f"Akkuntingizni ulang — lichkangizga kimdir yozsa "
        f"**AI o'zi javob beradi**. Siz hech narsa qilmaysiz!\n\n"
        f"Tarif: {tarif}"
    )
    await msg.answer(text, reply_markup=main_kb(active, user.is_premium), parse_mode="Markdown")

@router.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    active = is_running(cb.from_user.id)
    if user and user.is_premium and user.premium_until:
        days = (user.premium_until - datetime.utcnow()).days
        tarif = f"💎 Premium — {days} kun qoldi"
    else:
        tarif = f"🆓 Bepul — kuniga {FREE_DAILY_LIMIT} ta xabar"

    await cb.message.edit_text(
        f"🏠 **Asosiy menyu**\n"
        f"Holat: {'🟢 Ishlayapti' if active else '🔴 To\\'xtatilgan'}\n"
        f"Tarif: {tarif}",
        reply_markup=main_kb(active, user.is_premium if user else False),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "myaccount")
async def my_account(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    if not user:
        await cb.answer("Topilmadi")
        return
    active = is_running(user.id)
    from config import PREMIUM_DAILY_LIMIT
    limit = PREMIUM_DAILY_LIMIT if user.is_premium else FREE_DAILY_LIMIT

    text = (
        f"📊 **Hisobim**\n\n"
        f"{'🟢 AI ishlayapti' if active else '🔴 AI to\\'xtatilgan'}\n\n"
        f"Bugun: **{user.daily_count}** / {limit}\n"
        f"Jami javoblar: **{user.total_answered}**\n"
        f"Jami kelgan: **{user.total_received}**\n"
        f"Tarif: {'💎 Premium' if user.is_premium else '🆓 Bepul'}\n"
    )
    if user.is_premium and user.premium_until:
        text += f"Tugaydi: **{user.premium_until.strftime('%d.%m.%Y')}**\n"

    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Orqaga", callback_data="back_main")
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "help_menu")
async def help_menu(cb: CallbackQuery):
    text = (
        "❓ **Qanday ishlaydi?**\n\n"
        "1️⃣ **Akkunt ulang** — telefon raqam + SMS kod\n"
        "2️⃣ **AI yoqing** — tugmani bosing\n"
        "3️⃣ **Tayyor!** — kimdir yozsa AI o'zi javob beradi\n\n"
        "**AI sozlamalari:**\n"
        "• Uslub: do'stona / rasmiy / qisqa / hazilkash\n"
        "• Til: o'zbek / rus / ingliz\n"
        "• Persona: AI kimga o'xshab javob bersin\n"
        "• Kechikish: javob qancha vaqtda kelsin\n"
        "• O'qildi belgisi: avtomatik o'qildi ko'rsatsin\n\n"
        "**Muammo?** Admin bilan bog'laning"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Orqaga", callback_data="back_main")
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
