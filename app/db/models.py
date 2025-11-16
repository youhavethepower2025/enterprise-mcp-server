"""SQLAlchemy models for MedTainer MCP database."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, Index, JSON
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class ToolExecution(Base):
    """
    Log of all tool executions through the MCP server.
    
    This table provides a complete audit trail of what tools were called,
    with what parameters, and what the results were.
    """
    
    __tablename__ = "tool_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    tool_name = Column(String(100), nullable=False)
    params = Column(JSON)  # Tool parameters as JSON
    response = Column(JSON)  # Tool response as JSON
    duration_ms = Column(Integer)  # Execution duration in milliseconds
    status = Column(String(20), nullable=False)  # 'success', 'error', 'timeout'
    error_message = Column(Text)
    source = Column(String(20))  # 'live', 'sample', 'cached'
    user_context = Column(Text)  # Future: who/what triggered this

    __table_args__ = (
        Index('idx_tool_executions_timestamp', 'timestamp', postgresql_ops={'timestamp': 'DESC'}),
        Index('idx_tool_executions_tool_name', 'tool_name', 'timestamp', postgresql_ops={'timestamp': 'DESC'}),
    )

    def __repr__(self) -> str:
        return f"<ToolExecution(id={self.id}, tool={self.tool_name}, status={self.status})>"


class APICall(Base):
    """
    Audit trail of all external API calls made by the MCP server.
    
    This helps with debugging, performance monitoring, and understanding
    rate limit usage patterns.
    """
    
    __tablename__ = "api_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    ecosystem = Column(String(50), nullable=False)  # 'gohighlevel', 'quickbooks', etc.
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    status_code = Column(Integer)
    latency_ms = Column(Integer)
    request_size_bytes = Column(Integer)
    response_size_bytes = Column(Integer)
    error = Column(Text)
    rate_limited = Column(Boolean, default=False)

    __table_args__ = (
        Index('idx_api_calls_ecosystem', 'ecosystem', 'timestamp', postgresql_ops={'timestamp': 'DESC'}),
        Index('idx_api_calls_timestamp', 'timestamp', postgresql_ops={'timestamp': 'DESC'}),
    )

    def __repr__(self) -> str:
        return f"<APICall(id={self.id}, ecosystem={self.ecosystem}, method={self.method}, status={self.status_code})>"


class Contact(Base):
    """
    Cached contact data from GoHighLevel.
    
    Caching reduces API calls and helps stay within rate limits.
    The expires_at field determines when the cache should be refreshed.
    """
    
    __tablename__ = "contacts"

    id = Column(String(100), primary_key=True)
    ecosystem = Column(String(50), default='gohighlevel', nullable=False)
    data = Column(JSON, nullable=False)  # Full contact data as JSON
    last_synced = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True))  # When this cache entry expires

    __table_args__ = (
        Index('idx_contacts_last_synced', 'last_synced', postgresql_ops={'last_synced': 'DESC'}),
    )

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, ecosystem={self.ecosystem})>"


class Invoice(Base):
    """
    Cached invoice data from QuickBooks.
    
    Caching reduces API calls and provides faster access to frequently
    accessed invoice information.
    """
    
    __tablename__ = "invoices"

    id = Column(String(100), primary_key=True)
    ecosystem = Column(String(50), default='quickbooks', nullable=False)
    data = Column(JSON, nullable=False)  # Full invoice data as JSON
    last_synced = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True))

    __table_args__ = (
        Index('idx_invoices_last_synced', 'last_synced', postgresql_ops={'last_synced': 'DESC'}),
    )

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, ecosystem={self.ecosystem})>"


class Order(Base):
    """
    Cached order data from Amazon Seller API.
    
    Amazon has strict rate limits, so caching is essential to provide
    responsive queries without hitting limits.
    """
    
    __tablename__ = "orders"

    id = Column(String(100), primary_key=True)
    ecosystem = Column(String(50), default='amazon', nullable=False)
    data = Column(JSON, nullable=False)  # Full order data as JSON
    last_synced = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True))

    __table_args__ = (
        Index('idx_orders_last_synced', 'last_synced', postgresql_ops={'last_synced': 'DESC'}),
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, ecosystem={self.ecosystem})>"


class ContactContext(Base):
    """
    Context and intelligence layer for natural language contact interactions.

    This table stores:
    - Nicknames ("medical glove guy", "John from MedSupply")
    - Personal notes and relationship info
    - Interaction patterns for building intelligence
    - Custom tags and importance scoring

    This enables natural language queries like:
    - "Show me the medical supply guy"
    - "Who haven't we talked to in a while?"
    - "My most important customers"
    """

    __tablename__ = "contact_context"

    contact_id = Column(String(100), primary_key=True)
    contact_name = Column(String(200))  # Denormalized for faster search
    nicknames = Column(ARRAY(Text))  # ["medical guy", "John", "glove supplier"]
    personal_notes = Column(Text)  # Free-form notes about the contact
    company_info = Column(Text)  # Company background, industry, etc.
    relationship_notes = Column(Text)  # How we know them, history
    last_interaction = Column(TIMESTAMP(timezone=True))
    interaction_count = Column(Integer, default=0)
    importance_score = Column(Integer, default=5)  # 1-10 scale
    custom_tags = Column(JSON)  # Flexible key-value pairs
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_contact_context_nicknames', 'nicknames', postgresql_using='gin'),
        Index('idx_contact_context_name', 'contact_name'),
        Index('idx_contact_context_importance', 'importance_score'),
    )

    def __repr__(self) -> str:
        return f"<ContactContext(id={self.contact_id}, name={self.contact_name})>"


class InteractionHistory(Base):
    """
    Complete history of all interactions with contacts.

    Tracks:
    - When contacts were viewed, updated, contacted
    - Communication history (calls, emails, SMS via GHL)
    - Pattern analysis for recommendations

    This powers features like:
    - "Who haven't I contacted this week?"
    - "When did I last talk to John?"
    - "Contacts that need follow-up"
    """

    __tablename__ = "interaction_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(String(100), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # 'viewed', 'updated', 'called', 'emailed', 'sms'
    description = Column(Text)  # Human-readable description
    extra_data = Column(JSON)  # Additional context as needed

    __table_args__ = (
        Index('idx_interaction_history_contact', 'contact_id', 'timestamp', postgresql_ops={'timestamp': 'DESC'}),
        Index('idx_interaction_history_type', 'interaction_type', 'timestamp', postgresql_ops={'timestamp': 'DESC'}),
    )

    def __repr__(self) -> str:
        return f"<InteractionHistory(id={self.id}, contact={self.contact_id}, type={self.interaction_type})>"


# =============================================================================
# GODADDY CLOUD ENVIRONMENT MODELS
# =============================================================================

class GoDaddyDomain(Base):
    """Core domain registration information from GoDaddy."""

    __tablename__ = "godaddy_domains"

    domain_id = Column(Integer, primary_key=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    expires = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    renew_deadline = Column(TIMESTAMP(timezone=True))
    registrar_created_at = Column(TIMESTAMP(timezone=True))
    deleted_at = Column(TIMESTAMP(timezone=True))

    # Renewal & Protection Settings
    renew_auto = Column(Boolean, default=False)
    renewable = Column(Boolean, default=False)
    expiration_protected = Column(Boolean, default=False)
    transfer_protected = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)
    privacy = Column(Boolean, default=False)

    # Nameservers (stored as JSON array)
    nameservers = Column(JSON)

    # Metadata
    last_synced_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    raw_data = Column(JSON)

    __table_args__ = (
        Index('idx_godaddy_domains_status', 'status'),
        Index('idx_godaddy_domains_expires', 'expires'),
        Index('idx_godaddy_domains_last_synced', 'last_synced_at'),
    )

    def __repr__(self) -> str:
        return f"<GoDaddyDomain(domain='{self.domain}', status='{self.status}')>"


class GoDaddyDnsRecord(Base):
    """DNS records (A, CNAME, MX, TXT, etc.) for each domain."""

    __tablename__ = "godaddy_dns_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, index=True)
    record_type = Column(String(10), nullable=False)
    name = Column(String(255), nullable=False)
    data = Column(Text, nullable=False)
    ttl = Column(Integer, default=3600)
    priority = Column(Integer)

    # Metadata
    last_synced_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_godaddy_dns_records_domain', 'domain'),
        Index('idx_godaddy_dns_records_type', 'domain', 'record_type'),
        Index('idx_godaddy_dns_records_name', 'domain', 'name'),
    )

    def __repr__(self) -> str:
        return f"<GoDaddyDnsRecord(domain='{self.domain}', type='{self.record_type}')>"


class GoDaddySubdomain(Base):
    """Subdomains derived from DNS records, showing email availability."""

    __tablename__ = "godaddy_subdomains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, index=True)
    subdomain = Column(String(255), nullable=False)
    record_types = Column(ARRAY(String(50)))
    available_for_email = Column(Boolean, default=True, index=True)

    # Metadata
    last_synced_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_godaddy_subdomains_domain', 'domain'),
    )

    def __repr__(self) -> str:
        return f"<GoDaddySubdomain(domain='{self.domain}', subdomain='{self.subdomain}')>"


class GoDaddyMxRecord(Base):
    """Email routing configuration per domain."""

    __tablename__ = "godaddy_mx_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, index=True)
    mail_server = Column(String(255), nullable=False)
    priority = Column(Integer, nullable=False)
    ttl = Column(Integer, default=3600)

    # Email Provider Detection
    provider = Column(String(100), index=True)

    # Metadata
    last_synced_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_godaddy_mx_records_domain', 'domain'),
        Index('idx_godaddy_mx_records_provider', 'provider'),
    )

    def __repr__(self) -> str:
        return f"<GoDaddyMxRecord(domain='{self.domain}', server='{self.mail_server}')>"


class GoDaddyDomainContact(Base):
    """Registration and administrative contact information."""

    __tablename__ = "godaddy_domain_contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)

    # Contact Information (stored as JSON for flexibility)
    contact_registrant = Column(JSON)
    contact_admin = Column(JSON)
    contact_tech = Column(JSON)
    contact_billing = Column(JSON)

    # Auth Code (for transfers)
    auth_code = Column(String(255))

    # Metadata
    last_synced_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<GoDaddyDomainContact(domain='{self.domain}')>"


class GoDaddySyncHistory(Base):
    """Track weekly sync operations and health monitoring."""

    __tablename__ = "godaddy_sync_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_started_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    sync_completed_at = Column(TIMESTAMP(timezone=True))
    sync_status = Column(String(20), nullable=False, index=True)

    # Statistics
    domains_synced = Column(Integer, default=0)
    dns_records_synced = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Error Details
    error_message = Column(Text)
    error_details = Column(JSON)

    # Metadata
    duration_seconds = Column(Integer)

    __table_args__ = (
        Index('idx_godaddy_sync_history_started', 'sync_started_at'),
        Index('idx_godaddy_sync_history_status', 'sync_status'),
    )

    def __repr__(self) -> str:
        return f"<GoDaddySyncHistory(started='{self.sync_started_at}', status='{self.sync_status}')>"


# Helper function to detect email provider from MX records
def detect_email_provider(mail_server: str) -> Optional[str]:
    """Detect email provider based on mail server hostname."""
    mail_server_lower = mail_server.lower()

    if 'secureserver.net' in mail_server_lower or 'godaddy' in mail_server_lower:
        return 'godaddy'
    elif 'google.com' in mail_server_lower or 'googlemail.com' in mail_server_lower:
        return 'google'
    elif 'outlook.com' in mail_server_lower or 'microsoft.com' in mail_server_lower or 'office365' in mail_server_lower:
        return 'microsoft'
    elif 'zoho.com' in mail_server_lower:
        return 'zoho'
    elif 'protonmail' in mail_server_lower or 'proton.me' in mail_server_lower:
        return 'protonmail'
    elif 'fastmail' in mail_server_lower:
        return 'fastmail'
    else:
        return 'custom'
