from sqlalchemy import create_engine, BigInteger, String, Boolean, Integer, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from datetime import datetime
from config import DATABASE_URL

# 🔥 psycopg2 uchun SYNC engine
engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id              : Mapped[int]      = mapped_column(BigInteger, primary_key=True)
    username        : Mapped[str]      = mapped_column(String(64), nullable=True)
    full_name       : Mapped[str]      = mapped_column(String(128), nullable=True)
    phone           : Mapped[str]      = mapped_column(String(20), nullable=True)

    session_string  : Mapped[str]      = mapped_column(Text, nullable=True)
    is_active       : Mapped[bool]     = mapped_column(Boolean, default=False)

    ai_persona      : Mapped[str]      = mapped_column(Text, default="")
    ai_language     : Mapped[str]      = mapped_column(String(20), default="uz")
    ai_style        : Mapped[str]      = mapped_column(String(20), default="friendly")
    auto_read       : Mapped[bool]     = mapped_column(Boolean, default=True)
    reply_delay     : Mapped[int]      = mapped_column(Integer, default=2)

    is_premium      : Mapped[bool]     = mapped_column(Boolean, default=False)
    premium_until   : Mapped[datetime] = mapped_column(DateTime, nullable=True)

    daily_count     : Mapped[int]      = mapped_column(Integer, default=0)
    last_reset      : Mapped[str]      = mapped_column(String(10), default="")
    total_answered  : Mapped[int]      = mapped_column(Integer, default=0)
    total_received  : Mapped[int]      = mapped_column(Integer, default=0)

    banned          : Mapped[bool]     = mapped_column(Boolean, default=False)
    joined_at       : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen       : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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


# 🔥 sync init_db (lekin async signature qoldi)
async def init_db():
    Base.metadata.create_all(bind=engine)
