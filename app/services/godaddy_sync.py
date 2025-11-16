"""
GoDaddy Cloud Environment Sync Service

Syncs domain, DNS, and email information from GoDaddy API to local database.
Designed to run weekly to keep cloud environment data up to date.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.mcp.ecosystems.godaddy.client import GoDaddyClient
from app.db.session import SessionLocal
from app.db.models import (
    GoDaddyDomain,
    GoDaddyDnsRecord,
    GoDaddySubdomain,
    GoDaddyMxRecord,
    GoDaddyDomainContact,
    GoDaddySyncHistory,
    detect_email_provider
)
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class GoDaddySyncService:
    """Service to sync GoDaddy cloud environment data to local database."""

    def __init__(self, client: GoDaddyClient = None):
        """
        Initialize sync service.

        Args:
            client: Optional GoDaddyClient instance. Creates new if not provided.
        """
        self.client = client or GoDaddyClient()

    def sync_all(self) -> GoDaddySyncHistory:
        """
        Perform a complete sync of all GoDaddy data.

        This is the main entry point for the sync operation.
        It will:
        1. Sync all domains
        2. For each active domain, sync DNS records, MX records, subdomains, and contacts
        3. Track sync progress and errors

        Returns:
            GoDaddySyncHistory record with sync results
        """
        with get_db() as db:
            # Create sync history record
            sync_history = GoDaddySyncHistory(
                sync_status='running',
                sync_started_at=datetime.utcnow()
            )
            db.add(sync_history)
            db.commit()
            db.refresh(sync_history)

            try:
                # Sync domains
                logger.info("Starting GoDaddy sync: fetching domains")
                domains = self._sync_domains(db)
                sync_history.domains_synced = len(domains)

                # Sync DNS records for active domains
                total_dns_records = 0
                for domain in domains:
                    if domain.status == 'ACTIVE':
                        try:
                            dns_count = self._sync_domain_dns(db, domain.domain)
                            total_dns_records += dns_count

                            self._sync_domain_mx_records(db, domain.domain)
                            self._sync_domain_subdomains(db, domain.domain)
                            self._sync_domain_contacts(db, domain.domain)

                        except Exception as e:
                            logger.error(f"Error syncing domain {domain.domain}: {e}")
                            sync_history.errors_count += 1

                sync_history.dns_records_synced = total_dns_records

                # Mark sync as completed
                sync_history.sync_status = 'completed'
                sync_history.sync_completed_at = datetime.utcnow()
                sync_history.duration_seconds = int(
                    (sync_history.sync_completed_at - sync_history.sync_started_at).total_seconds()
                )

                db.commit()
                logger.info(
                    f"GoDaddy sync completed: {sync_history.domains_synced} domains, "
                    f"{sync_history.dns_records_synced} DNS records, "
                    f"{sync_history.errors_count} errors"
                )

                return sync_history

            except Exception as e:
                # Mark sync as failed
                sync_history.sync_status = 'failed'
                sync_history.error_message = str(e)
                sync_history.sync_completed_at = datetime.utcnow()
                db.commit()
                logger.error(f"GoDaddy sync failed: {e}", exc_info=True)
                raise

    def _sync_domains(self, db: Session) -> List[GoDaddyDomain]:
        """
        Sync all domains from GoDaddy API to database.

        Args:
            db: Database session

        Returns:
            List of synced domain objects
        """
        # Fetch domains from GoDaddy
        domains_data = self.client.list_domains()

        synced_domains = []
        for domain_data in domains_data:
            # Update or create domain record
            domain = db.query(GoDaddyDomain).filter_by(
                domain_id=domain_data['domainId']
            ).first()

            if not domain:
                domain = GoDaddyDomain(
                    domain_id=domain_data['domainId'],
                    domain=domain_data['domain']
                )
                db.add(domain)

            # Update domain fields
            domain.status = domain_data.get('status', 'UNKNOWN')
            domain.created_at = self._parse_datetime(domain_data.get('createdAt'))
            domain.expires = self._parse_datetime(domain_data.get('expires'))
            domain.renew_deadline = self._parse_datetime(domain_data.get('renewDeadline'))
            domain.registrar_created_at = self._parse_datetime(domain_data.get('registrarCreatedAt'))
            domain.deleted_at = self._parse_datetime(domain_data.get('deletedAt'))

            domain.renew_auto = domain_data.get('renewAuto', False)
            domain.renewable = domain_data.get('renewable', False)
            domain.expiration_protected = domain_data.get('expirationProtected', False)
            domain.transfer_protected = domain_data.get('transferProtected', False)
            domain.locked = domain_data.get('locked', False)
            domain.privacy = domain_data.get('privacy', False)

            domain.nameservers = domain_data.get('nameServers')
            domain.raw_data = domain_data
            domain.last_synced_at = datetime.utcnow()

            synced_domains.append(domain)

        db.commit()
        return synced_domains

    def _sync_domain_dns(self, db: Session, domain: str) -> int:
        """
        Sync DNS records for a domain.

        Args:
            db: Database session
            domain: Domain name

        Returns:
            Number of DNS records synced
        """
        # Delete existing DNS records for this domain
        db.query(GoDaddyDnsRecord).filter_by(domain=domain).delete()

        # Fetch DNS records from GoDaddy
        dns_records = self.client.get_dns_records(domain)

        for record_data in dns_records:
            dns_record = GoDaddyDnsRecord(
                domain=domain,
                record_type=record_data.get('type'),
                name=record_data.get('name', '@'),
                data=record_data.get('data'),
                ttl=record_data.get('ttl', 3600),
                priority=record_data.get('priority'),
                last_synced_at=datetime.utcnow()
            )
            db.add(dns_record)

        db.commit()
        return len(dns_records)

    def _sync_domain_mx_records(self, db: Session, domain: str) -> int:
        """
        Sync MX (email) records for a domain.

        Args:
            db: Database session
            domain: Domain name

        Returns:
            Number of MX records synced
        """
        # Delete existing MX records for this domain
        db.query(GoDaddyMxRecord).filter_by(domain=domain).delete()

        # Fetch MX records from GoDaddy
        mx_records = self.client.get_dns_records(domain, record_type='MX')

        for record_data in mx_records:
            mail_server = record_data.get('data')
            mx_record = GoDaddyMxRecord(
                domain=domain,
                mail_server=mail_server,
                priority=record_data.get('priority', 10),
                ttl=record_data.get('ttl', 3600),
                provider=detect_email_provider(mail_server),
                last_synced_at=datetime.utcnow()
            )
            db.add(mx_record)

        db.commit()
        return len(mx_records)

    def _sync_domain_subdomains(self, db: Session, domain: str) -> int:
        """
        Sync subdomains for a domain by analyzing DNS records.

        Args:
            db: Database session
            domain: Domain name

        Returns:
            Number of subdomains synced
        """
        # Delete existing subdomains for this domain
        db.query(GoDaddySubdomain).filter_by(domain=domain).delete()

        # Get all DNS records to extract subdomains
        all_records = self.client.get_dns_records(domain)

        # Extract unique subdomains
        subdomains_map: Dict[str, List[str]] = {}
        for record in all_records:
            name = record.get('name', '')
            record_type = record.get('type', '')

            # Include A, AAAA, CNAME, MX records
            if record_type in ['A', 'AAAA', 'CNAME', 'MX'] and name not in ['@', '']:
                if name not in subdomains_map:
                    subdomains_map[name] = []
                subdomains_map[name].append(record_type)

        # Create subdomain records
        for subdomain_name, record_types in subdomains_map.items():
            subdomain = GoDaddySubdomain(
                domain=domain,
                subdomain=subdomain_name,
                record_types=list(set(record_types)),  # Unique record types
                available_for_email=True,  # All subdomains can potentially be used for email
                last_synced_at=datetime.utcnow()
            )
            db.add(subdomain)

        db.commit()
        return len(subdomains_map)

    def _sync_domain_contacts(self, db: Session, domain: str) -> None:
        """
        Sync contact information for a domain.

        Args:
            db: Database session
            domain: Domain name
        """
        try:
            # Fetch domain details which include contact info
            domain_details = self.client.get_domain(domain)

            # Delete existing contacts for this domain
            db.query(GoDaddyDomainContact).filter_by(domain=domain).delete()

            # Create contacts record
            contacts = GoDaddyDomainContact(
                domain=domain,
                contact_registrant=domain_details.get('contactRegistrant'),
                contact_admin=domain_details.get('contactAdmin'),
                contact_tech=domain_details.get('contactTech'),
                contact_billing=domain_details.get('contactBilling'),
                auth_code=domain_details.get('authCode'),
                last_synced_at=datetime.utcnow()
            )
            db.add(contacts)
            db.commit()

        except Exception as e:
            logger.warning(f"Could not sync contacts for {domain}: {e}")

    @staticmethod
    def _parse_datetime(date_string: str | None) -> datetime | None:
        """
        Parse ISO 8601 datetime string to datetime object.

        Args:
            date_string: ISO 8601 formatted date string

        Returns:
            Datetime object or None if parsing fails
        """
        if not date_string:
            return None

        try:
            # Remove 'Z' suffix and parse
            if date_string.endswith('Z'):
                date_string = date_string[:-1] + '+00:00'
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Could not parse datetime: {date_string} - {e}")
            return None


def run_weekly_sync() -> GoDaddySyncHistory:
    """
    Convenience function to run weekly sync.

    This should be called by a scheduler (e.g., cron, APScheduler, Celery).

    Returns:
        Sync history record
    """
    logger.info("Starting weekly GoDaddy sync")
    service = GoDaddySyncService()
    return service.sync_all()
