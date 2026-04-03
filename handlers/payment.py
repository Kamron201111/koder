from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PhotoSize
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import get_user, create_payment, get_payment, update_payment, update_user
from config import PRICES, PLAN_NAMES, PLAN_MONTHS, PAYMENT_CARD, PAYMENT_OWNER, PAYMENT_ADMIN, FREE_DAILY_LIMIT
from datetime import datetime, timedelta

router = Router()

class P(StatesGroup):
    receipt = State()

@router.callback_query(F.data == "premium_menu")
async def premium_menu(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    is_prem = user.is_premium if user else False

    if is_prem and user.premium_until:
        days = (user.premium_until - datetime.utcnow()).days
        status = f"✅ Sizda **Premium** bor! {days} kun qoldi\n\n"
    else:
        status = f"🆓 Hozir bepul tarif: **{FREE_DAILY_LIMIT}** xabar/kun\n\n"

    kb = InlineKeyboardBuilder()
    kb.button(text=f"1 oy — {PRICES['1_month']:,} so'm", callback_data="buy_1_month")
    kb.button(text=f"3 oy — {PRICES['3_month']:,} so'm 🔥", callback_data="buy_3_month")
    kb.button(text=f"6 oy — {PRICES['6_month']:,} so'm 👑", callback_data="buy_6_month")
    kb.button(text="🔙 Orqaga", callback_data="back_main")
    kb.adjust(1)

    await cb.message.edit_text(
        f"💎 **Premium Tarif**\n\n"
        f"{status}"
        f"**Premium afzalliklari:**\n"
        f"• Cheksiz xabarlar ♾️\n"
        f"• Barcha AI sozlamalar\n"
        f"• Ustuvor qo'llab-quvvatlash\n\n"
        f"Tarifni tanlang 👇",
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("buy_"))
async def buy_plan(cb: CallbackQuery, state: FSMContext):
    plan = cb.data.replace("buy_", "")
    amount = PRICES.get(plan, 0)
    payment = await create_payment(cb.from_user.id, plan, amount)
    await state.update_data(payment_id=payment.id, plan=plan, amount=amount)
    await state.set_state(P.receipt)

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Bekor", callback_data="premium_menu")
    await cb.message.edit_text(
        f"💳 **To'lov**\n\n"
        f"Plan: **{PLAN_NAMES[plan]}**\n"
        f"Summa: **{amount:,} so'm**\n\n"
        f"Karta: `{PAYMENT_CARD}`\n"
        f"Egasi: **{PAYMENT_OWNER}**\n\n"
        f"1. Pul o'tkazing\n"
        f"2. Chek rasmini yuboring\n\n"
        f"_Tasdiqlanishi: 5-60 daqiqa_",
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

@router.message(P.receipt, F.photo)
async def receive_receipt(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    pay_id = data.get("payment_id")
    plan = data.get("plan")
    amount = data.get("amount")
    photo: PhotoSize = msg.photo[-1]

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"approve_{pay_id}")
    kb.button(text="❌ Rad etish", callback_data=f"reject_{pay_id}")
    kb.adjust(2)

    await bot.send_photo(
        PAYMENT_ADMIN, photo.file_id,
        caption=(
            f"💰 **Yangi to'lov!**\n\n"
            f"👤 {msg.from_user.full_name}\n"
            f"🆔 `{msg.from_user.id}`\n"
            f"📱 @{msg.from_user.username or 'yoq'}\n\n"
            f"📦 {PLAN_NAMES.get(plan, plan)}\n"
            f"💵 {amount:,} so'm\n"
            f"🔢 To'lov #{pay_id}"
        ),
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )
    await state.clear()
    await msg.answer("✅ Chek yuborildi! Tez orada tasdiqlanadi.")

@router.message(P.receipt)
async def wrong_receipt(msg: Message):
    await msg.answer("📸 Iltimos, to'lov **chek rasmini** yuboring.")

@router.callback_query(F.data.startswith("approve_"))
async def approve(cb: CallbackQuery, bot: Bot):
    if cb.from_user.id != PAYMENT_ADMIN:
        return
    pay_id = int(cb.data.replace("approve_", ""))
    pay = await get_payment(pay_id)
    if not pay or pay.status != "pending":
        await cb.answer("Allaqachon ko'rib chiqilgan")
        return
    months = PLAN_MONTHS.get(pay.plan, 1)
    user = await get_user(pay.user_id)
    now = datetime.utcnow()
    base = user.premium_until if (user and user.is_premium and user.premium_until and user.premium_until > now) else now
    new_until = base + timedelta(days=30 * months)
    await update_user(pay.user_id, is_premium=True, premium_until=new_until)
    await update_payment(pay_id, status="approved", reviewed_at=now)
    try:
        await bot.send_message(pay.user_id,
            f"🎉 **Premium faollashtirildi!**\n\n"
            f"Plan: {PLAN_NAMES.get(pay.plan)}\n"
            f"Tugaydi: **{new_until.strftime('%d.%m.%Y')}**\n\n"
            f"Cheksiz xabarlardan foydalaning! 🚀",
            parse_mode="Markdown"
        )
    except:
        pass
    await cb.message.edit_caption(cb.message.caption + "\n\n✅ TASDIQLANDI", parse_mode="Markdown")
    await cb.answer("✅ Premium berildi!")

@router.callback_query(F.data.startswith("reject_"))
async def reject(cb: CallbackQuery, bot: Bot):
    if cb.from_user.id != PAYMENT_ADMIN:
        return
    pay_id = int(cb.data.replace("reject_", ""))
    await update_payment(pay_id, status="rejected", reviewed_at=datetime.utcnow())
    try:
        await bot.send_message(
            (await get_payment(pay_id)).user_id,
            "❌ To'lovingiz rad etildi. Muammo bo'lsa admin bilan bog'laning."
        )
    except:
        pass
    await cb.message.edit_caption(cb.message.caption + "\n\n❌ RAD ETILDI", parse_mode="Markdown")
    await cb.answer("❌ Rad etildi")
