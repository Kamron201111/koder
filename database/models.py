from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, String, Boolean, Integer, DateTime, Text
from datetime import datetime
from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id              : Mapped[int]      = mapped_column(BigInteger, primary_key=True)
    username        : Mapped[str]      = mapped_column(String(64), nullable=True)
    full_name       : Mapped[str]      = mapped_column(String(128), nullable=True)
    phone           : Mapped[str]      = mapped_column(String(20), nullable=True)

    # Telethon session
    session_string  : Mapped[str]      = mapped_column(Text, nullable=True)
    is_active       : Mapped[bool]     = mapped_column(Boolean, default=False)

    # AI sozlamalari
    ai_persona      : Mapped[str]      = mapped_column(Text, default="")   # Kim bo'lib javob berishi
    ai_language     : Mapped[str]      = mapped_column(String(20), default="uz")
    ai_style        : Mapped[str]      = mapped_column(String(20), default="friendly")  # friendly/formal/short
    auto_read       : Mapped[bool]     = mapped_column(Boolean, default=True)   # O'qildi belgisi
    reply_delay     : Mapped[int]      = mapped_column(Integer, default=2)      # Javob kechikishi (soniya)

    # Premium
    is_premium      : Mapped[bool]     = mapped_column(Boolean, default=False)
    premium_until   : Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Statistika
    daily_count     : Mapped[int]      = mapped_column(Integer, default=0)
    last_reset      : Mapped[str]      = mapped_column(String(10), default="")
    total_answered  : Mapped[int]      = mapped_column(Integer, default=0)
    total_received  : Mapped[int]      = mapped_column(Integer, default=0)

    # Tizim
    banned          : Mapped[bool]     = mapped_column(Boolean, default=False)
    joined_at       : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen       : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Bloklangan senderlar (JSON string)
    blocked_senders : Mapped[str]      = mapped_column(Text, default="[]")

class Payment(Base):
    __tablename__ = "payments"

    id          : Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id     : Mapped[int]      = mapped_column(BigInteger)
    plan        : Mapped[str]      = mapped_column(String(20))
    amount      : Mapped[int]      = mapped_column(Integer)
    status      : Mapped[str]      = mapped_column(String(20), default="pending")
    created_at  : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at : Mapped[datetime] = mapped_column(DateTime, nullable=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
