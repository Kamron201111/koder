"""
Userbot Manager
Har foydalanuvchi uchun alohida Telethon instance
AI to'liq avtonom — hech qanday qo'shimcha narsa yo'q
"""
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import User as TLUser
import asyncio
from datetime import datetime
from config import API_ID, API_HASH
from services import ai
from database import db

# Aktiv userbotlar: {owner_id: TelegramClient}
_bots: dict[int, TelegramClient] = {}

# Login jarayoni: {owner_id: {client, phone, phone_code_hash}}
_pending: dict[int, dict] = {}

# ── Userbot ishga tushirish ───────────────────────────
async def start(owner_id: int, session_string: str) -> bool:
    if owner_id in _bots:
        return True
    try:
        client = TelegramClient(
            StringSession(session_string), API_ID, API_HASH,
            device_model="iPhone 15 Pro",
            system_version="iOS 17.4",
            app_version="10.3.2",
        )
        await client.connect()
        if not await client.is_user_authorized():
            return False

        # ── Xabarlarni tinglash ──────────────────────
        @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def on_msg(event):
            await _process(event, owner_id, client)

        _bots[owner_id] = client
        asyncio.create_task(client.run_until_disconnected())
        return True
    except Exception as e:
        print(f"[Userbot start xato] {owner_id}: {e}")
        return False

async def stop(owner_id: int):
    c = _bots.pop(owner_id, None)
    if c:
        try:
            await c.disconnect()
        except:
            pass

def is_running(owner_id: int) -> bool:
    return owner_id in _bots

def count() -> int:
    return len(_bots)

# ── Xabarni qayta ishlash ─────────────────────────────
async def _process(event, owner_id: int, client: TelegramClient):
    try:
        sender: TLUser = await event.get_sender()
        if not sender or getattr(sender, 'bot', False):
            return

        msg_text = event.message.text or ""
        if not msg_text.strip():
            return

        sender_id = sender.id

        # Foydalanuvchi ma'lumotlari
        user = await db.get_user(owner_id)
        if not user or user.banned or not user.is_active:
            return

        # Bloklangan sender?
        blocked = await db.get_blocked_senders(owner_id)
        if sender_id in blocked:
            return

        # Limit tekshirish
        can, used, limit = await db.check_and_increment(owner_id)
        if not can:
            print(f"[Limit] owner={owner_id} limit={limit}")
            return

        # Statistika yangilash
        await db.update_user(owner_id,
            total_received=user.total_received + 1,
            last_seen=datetime.utcnow()
        )

        # O'qildi belgisi
        if user.auto_read:
            await asyncio.sleep(0.5)
            await client.send_read_acknowledge(event.chat_id)

        # Yozmoqda animatsiyasi
        delay = max(1, min(user.reply_delay, 8))
        async with client.action(event.chat_id, 'typing'):
            # AI javob olish
            response = await ai.get_response(
                owner_id=owner_id,
                sender_id=sender_id,
                message=msg_text,
                persona=user.ai_persona,
                style=user.ai_style,
                language=user.ai_language
            )
            # Tabiiy kechikish
            await asyncio.sleep(delay)
            await event.reply(response)

        sender_name = getattr(sender, 'first_name', '') or 'Nomaʼlum'
        print(f"✅ [{owner_id}] → {sender_name}: {response[:50]}...")

    except FloodWaitError as e:
        print(f"[FloodWait] {owner_id}: {e.seconds}s")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"[Process xato] {owner_id}: {e}")

# ── Login ─────────────────────────────────────────────
async def send_code(owner_id: int, phone: str) -> dict:
    try:
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        await c.connect()
        res = await c.send_code_request(phone)
        _pending[owner_id] = {"client": c, "phone": phone, "hash": res.phone_code_hash}
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def verify_code(owner_id: int, code: str) -> dict:
    p = _pending.get(owner_id)
    if not p:
        return {"ok": False, "error": "Sessiya topilmadi, qayta boshlang"}
    try:
        await p["client"].sign_in(p["phone"], code, phone_code_hash=p["hash"])
        session = p["client"].session.save()
        _pending.pop(owner_id, None)
        return {"ok": True, "session": session}
    except SessionPasswordNeededError:
        return {"ok": False, "need_2fa": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def verify_2fa(owner_id: int, password: str) -> dict:
    p = _pending.get(owner_id)
    if not p:
        return {"ok": False, "error": "Sessiya topilmadi"}
    try:
        await p["client"].sign_in(password=password)
        session = p["client"].session.save()
        _pending.pop(owner_id, None)
        return {"ok": True, "session": session}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── Barcha aktiv userbotlarni yuklash ────────────────
async def load_all() -> int:
    users = await db.get_active_users()
    ok = 0
    for u in users:
        if u.session_string:
            if await start(u.id, u.session_string):
                ok += 1
            await asyncio.sleep(0.3)
    return ok
