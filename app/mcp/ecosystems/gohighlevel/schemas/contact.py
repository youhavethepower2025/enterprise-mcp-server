"""GoHighLevel contact schemas validated against real API responses.

Schema Version: 1.0
Last Validated: 2025-11-12
API Version: V1 (rest.gohighlevel.com/v1)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class GHLContact(BaseModel):
    """
    GoHighLevel contact schema.

    Validated against real API response from /v1/contacts/
    """

    # Identity
    id: str = Field(..., description="Unique contact ID")
    locationId: str = Field(..., description="Location/Sub-account ID")

    # Name
    contactName: Optional[str] = Field(None, description="Full name")
    firstName: Optional[str] = Field(None, description="First name")
    lastName: Optional[str] = Field(None, description="Last name")

    # Company
    companyName: Optional[str] = Field(None, description="Company name")

    # Contact Info
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    dnd: bool = Field(False, description="Do not disturb flag")

    # Type & Source
    type: Optional[str] = Field(None, description="Contact type (vendor, lead, etc.)")
    source: Optional[str] = Field(None, description="Source of contact")

    # Assignment
    assignedTo: Optional[str] = Field(None, description="User ID contact is assigned to")

    # Address
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    postalCode: Optional[str] = Field(None, description="Postal/ZIP code")
    address1: Optional[str] = Field(None, description="Street address")
    country: Optional[str] = Field(None, description="Country code")

    # Dates
    dateAdded: str = Field(..., description="Date contact was added (ISO 8601)")
    dateUpdated: str = Field(..., description="Date contact was last updated (ISO 8601)")
    dateOfBirth: Optional[str] = Field(None, description="Date of birth (ISO 8601)")

    # Categorization
    tags: List[str] = Field(default_factory=list, description="Array of tag strings")

    # Web
    website: Optional[str] = Field(None, description="Website URL")

    # Settings
    timezone: Optional[str] = Field(None, description="Timezone (e.g., America/Los_Angeles)")

    # Activity
    lastActivity: Optional[int] = Field(None, description="Last activity timestamp (milliseconds)")

    # Custom Fields
    customField: List[dict] = Field(default_factory=list, description="Array of custom field objects")

    class Config:
        """Pydantic config."""

        # Allow extra fields in case API adds new ones
        extra = "allow"


class GHLContactList(BaseModel):
    """Response schema for /v1/contacts/ list endpoint."""

    contacts: List[GHLContact] = Field(..., description="Array of contact objects")
    meta: "GHLPaginationMeta" = Field(..., description="Pagination metadata")


class GHLPaginationMeta(BaseModel):
    """Pagination metadata from GoHighLevel API."""

    total: int = Field(..., description="Total number of contacts")
    nextPageUrl: Optional[str] = Field(None, description="URL for next page")
    startAfterId: Optional[str] = Field(None, description="ID to start after for pagination")
    startAfter: Optional[int] = Field(None, description="Timestamp to start after")
    currentPage: int = Field(..., description="Current page number")
    nextPage: Optional[int] = Field(None, description="Next page number")
    prevPage: Optional[int] = Field(None, description="Previous page number")


# For forward reference
GHLContactList.update_forward_refs()
