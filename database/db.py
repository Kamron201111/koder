from sqlalchemy import select, update
from database.models import User, Payment, SessionLocal
from datetime import datetime, date
from config import FREE_DAILY_LIMIT, PREMIUM_DAILY_LIMIT
import json

# ── USER ─────────────────────────────────────────────

async def get_or_create_user(user_id: int, username=None, full_name=None) -> User:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, username=username, full_name=full_name)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()


async def get_user(user_id: int) -> User | None:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()


async def update_user(user_id: int, **kwargs):
    db = SessionLocal()
    try:
        db.query(User).filter(User.id == user_id).update(kwargs)
        db.commit()
    finally:
        db.close()


async def get_all_users() -> list[User]:
    db = SessionLocal()
    try:
        return db.query(User).all()
    finally:
        db.close()


async def get_active_users() -> list[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.is_active == True, User.banned == False).all()
    finally:
        db.close()


async def check_and_increment(user_id: int) -> tuple[bool, int, int]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
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

        db.commit()
        return True, user.daily_count, limit
    finally:
        db.close()


async def expire_premiums() -> int:
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        users = db.query(User).filter(
            User.is_premium == True,
            User.premium_until < now
        ).all()

        for u in users:
            u.is_premium = False

        db.commit()
        return len(users)
    finally:
        db.close()


# ── TO‘LOVLAR ────────────────────────────────────────

async def create_payment(user_id: int, plan: str, amount: int) -> Payment:
    db = SessionLocal()
    try:
        p = Payment(user_id=user_id, plan=plan, amount=amount)
        db.add(p)
        db.commit()
        db.refresh(p)
        return p
    finally:
        db.close()


async def get_payment(pay_id: int) -> Payment | None:
    db = SessionLocal()
    try:
        return db.query(Payment).filter(Payment.id == pay_id).first()
    finally:
        db.close()


async def update_payment(pay_id: int, **kwargs):
    db = SessionLocal()
    try:
        db.query(Payment).filter(Payment.id == pay_id).update(kwargs)
        db.commit()
    finally:
        db.close()


async def get_pending_payments() -> list[Payment]:
    db = SessionLocal()
    try:
        return db.query(Payment).filter(Payment.status == "pending").all()
    finally:
        db.close()


# ── BLOKLANGANLAR ────────────────────────────────────

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
