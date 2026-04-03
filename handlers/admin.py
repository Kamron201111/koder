from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import get_all_users, get_user, update_user, get_pending_payments
from services.userbot import is_running, count as bot_count
from config import ADMIN_IDS
from datetime import datetime, timedelta

router = Router()

def is_admin(uid): return uid in ADMIN_IDS

def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Statistika", callback_data="adm_stat")
    kb.button(text="👥 Foydalanuvchilar", callback_data="adm_users")
    kb.button(text="💰 To'lovlar", callback_data="adm_payments")
    kb.button(text="📢 Broadcast", callback_data="adm_broadcast")
    kb.adjust(2)
    return kb.as_markup()

@router.message(Command("admin"))
async def admin(msg: Message):
    if not is_admin(msg.from_user.id): return
    await msg.answer("🛠 **Admin Panel**", reply_markup=admin_kb(), parse_mode="Markdown")

@router.callback_query(F.data == "adm_stat")
async def adm_stat(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    users = await get_all_users()
    total = len(users)
    premium = sum(1 for u in users if u.is_premium)
    active = bot_count()
    banned = sum(1 for u in users if u.banned)
    msgs = sum(u.total_answered for u in users)
    pending = len(await get_pending_payments())

    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Orqaga", callback_data="adm_back")
    await cb.message.edit_text(
        f"📊 **Bot Statistikasi**\n\n"
        f"👥 Jami foydalanuvchi: **{total}**\n"
        f"💎 Premium: **{premium}**\n"
        f"🟢 Aktiv bot: **{active}**\n"
        f"🚫 Ban: **{banned}**\n"
        f"💬 Jami javoblar: **{msgs:,}**\n"
        f"💰 Kutayotgan to'lov: **{pending}**\n"
        f"🕐 {datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC",
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

@router.callback_query(F.data == "adm_users")
async def adm_users(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    users = await get_all_users()
    lines = []
    for u in sorted(users, key=lambda x: x.joined_at, reverse=True)[:20]:
        icon = "💎" if u.is_premium else ("🟢" if is_running(u.id) else "⚫")
        name = (u.full_name or "Nomaʼlum")[:15]
        lines.append(f"{icon} {name} — {u.total_answered} javob")

    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Orqaga", callback_data="adm_back")
    await cb.message.edit_text(
        f"👥 **Oxirgi 20 ta foydalanuvchi:**\n\n" + "\n".join(lines),
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

@router.callback_query(F.data == "adm_payments")
async def adm_payments(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    payments = await get_pending_payments()
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Orqaga", callback_data="adm_back")
    if not payments:
        await cb.message.edit_text("✅ Kutayotgan to'lovlar yo'q", reply_markup=kb.as_markup())
        return
    lines = [f"• #{p.id} | `{p.user_id}` | {p.plan} | {p.amount:,} so'm" for p in payments]
    await cb.message.edit_text(
        f"💰 **Kutayotgan to'lovlar: {len(payments)} ta**\n\n" + "\n".join(lines),
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

# ── Admin buyruqlar ───────────────────────────────────
@router.message(Command("give_premium"))
async def give_premium(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.answer("`/give_premium USER_ID MONTHS`", parse_mode="Markdown"); return
    uid, months = int(parts[1]), int(parts[2])
    until = datetime.utcnow() + timedelta(days=30 * months)
    await update_user(uid, is_premium=True, premium_until=until)
    await msg.answer(f"✅ `{uid}` ga {months} oy premium. Tugaydi: `{until.strftime('%d.%m.%Y')}`", parse_mode="Markdown")

@router.message(Command("remove_premium"))
async def remove_premium(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: return
    await update_user(int(parts[1]), is_premium=False, premium_until=None)
    await msg.answer(f"✅ `{parts[1]}` premium o'chirildi.", parse_mode="Markdown")

@router.message(Command("ban"))
async def ban(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: return
    await update_user(int(parts[1]), banned=True, is_active=False)
    await msg.answer(f"🚫 `{parts[1]}` banlandi.", parse_mode="Markdown")

@router.message(Command("unban"))
async def unban(msg: Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: return
    await update_user(int(parts[1]), banned=False)
    await msg.answer(f"✅ `{parts[1]}` bandan chiqdi.", parse_mode="Markdown")

# ── Broadcast ─────────────────────────────────────────
_waiting_broadcast: set[int] = set()

@router.callback_query(F.data == "adm_broadcast")
async def broadcast_start(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    _waiting_broadcast.add(cb.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Bekor", callback_data="adm_back")
    await cb.message.edit_text(
        "📢 **Broadcast**\n\nBarcha foydalanuvchilarga yuboriladigan xabarni yozing:",
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

@router.message(F.from_user.id.in_(ADMIN_IDS))
async def broadcast_send(msg: Message, bot: Bot):
    if msg.from_user.id not in _waiting_broadcast: return
    _waiting_broadcast.discard(msg.from_user.id)
    users = await get_all_users()
    sent = failed = 0
    for u in users:
        try:
            await bot.copy_message(u.id, msg.chat.id, msg.message_id)
            sent += 1
        except:
            failed += 1
    await msg.answer(f"📢 Broadcast tugadi!\n✅ {sent} ta\n❌ {failed} ta")

@router.callback_query(F.data == "adm_back")
async def adm_back(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    await cb.message.edit_text("🛠 **Admin Panel**", reply_markup=admin_kb(), parse_mode="Markdown")
