from sqlalchemy import select, update
from database.models import User, Payment, AsyncSessionLocal
from datetime import datetime, date
from config import FREE_DAILY_LIMIT, PREMIUM_DAILY_LIMIT
import json

async def get_or_create_user(user_id: int, username=None, full_name=None) -> User:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(User.id == user_id))
        user = r.scalar_one_or_none()
        if not user:
            user = User(id=user_id, username=username, full_name=full_name)
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

async def get_user(user_id: int) -> User | None:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(User.id == user_id))
        return r.scalar_one_or_none()

async def update_user(user_id: int, **kwargs):
    async with AsyncSessionLocal() as db:
        await db.execute(update(User).where(User.id == user_id).values(**kwargs))
        await db.commit()

async def get_all_users() -> list[User]:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User))
        return list(r.scalars().all())

async def get_active_users() -> list[User]:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(User.is_active == True, User.banned == False))
        return list(r.scalars().all())

async def check_and_increment(user_id: int) -> tuple[bool, int, int]:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(User.id == user_id))
        user = r.scalar_one_or_none()
        if not user:
            return False, 0, 0
        today = date.today().isoformat()
        if user.last_reset != today:
            user.daily_count = 0
            user.last_reset = today
        limit = PREMIUM_DAILY_LIMIT if user.is_premium else FREE_DAILY_LIMIT
        if user.daily_count >= limit:
            return False, user.daily_count, limit
        user.daily_count += 1
        user.total_answered += 1
        await db.commit()
        return True, user.daily_count, limit

async def expire_premiums() -> int:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(
            User.is_premium == True,
            User.premium_until < datetime.utcnow()
        ))
        users = r.scalars().all()
        for u in users:
            u.is_premium = False
        await db.commit()
        return len(users)

# ── To'lovlar ────────────────────────────────────────
async def create_payment(user_id: int, plan: str, amount: int) -> Payment:
    async with AsyncSessionLocal() as db:
        p = Payment(user_id=user_id, plan=plan, amount=amount)
        db.add(p)
        await db.commit()
        await db.refresh(p)
        return p

async def get_payment(pay_id: int) -> Payment | None:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Payment).where(Payment.id == pay_id))
        return r.scalar_one_or_none()

async def update_payment(pay_id: int, **kwargs):
    async with AsyncSessionLocal() as db:
        await db.execute(update(Payment).where(Payment.id == pay_id).values(**kwargs))
        await db.commit()

async def get_pending_payments() -> list[Payment]:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Payment).where(Payment.status == "pending"))
        return list(r.scalars().all())

# ── Bloklangan senderlar ─────────────────────────────
async def get_blocked_senders(user_id: int) -> list[int]:
    user = await get_user(user_id)
    if not user:
        return []
    try:
        return json.loads(user.blocked_senders or "[]")
    except:
        return []

async def block_sender(owner_id: int, sender_id: int):
    blocked = await get_blocked_senders(owner_id)
    if sender_id not in blocked:
        blocked.append(sender_id)
        await update_user(owner_id, blocked_senders=json.dumps(blocked))

async def unblock_sender(owner_id: int, sender_id: int):
    blocked = await get_blocked_senders(owner_id)
    if sender_id in blocked:
        blocked.remove(sender_id)
        await update_user(owner_id, blocked_senders=json.dumps(blocked))
