from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, BigInteger, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import JSON
class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    whatsapp_number_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_api_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    owner_phone: Mapped[str] = mapped_column(String(20), nullable=True) 
    welcome_media: Mapped[dict] = mapped_column(JSON, nullable=True)

class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    customer_phone: Mapped[str] = mapped_column(String(20), index=True)
    requires_human: Mapped[bool] = mapped_column(default=False, index=True)
    
    __table_args__ = (Index("idx_tenant_customer", "tenant_id", "customer_phone"),)

class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_base"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)

class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)