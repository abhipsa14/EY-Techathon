"""
Data models for the Provider Data Validation System.
Defines Provider, ValidationResult, Discrepancy, and other core entities.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
import uuid


class ValidationStatus(str, Enum):
    """Status of validation for a provider."""
    PENDING = "pending"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    URGENT = "urgent"
    ERROR = "error"


class DiscrepancyType(str, Enum):
    """Types of discrepancies that can be detected."""
    PHONE_MISMATCH = "phone_mismatch"
    ADDRESS_MISMATCH = "address_mismatch"
    NAME_MISMATCH = "name_mismatch"
    SPECIALTY_MISMATCH = "specialty_mismatch"
    LICENSE_ISSUE = "license_issue"
    NPI_INVALID = "npi_invalid"
    STATUS_CHANGE = "status_change"
    EMAIL_INVALID = "email_invalid"
    FAX_MISMATCH = "fax_mismatch"
    WEBSITE_ISSUE = "website_issue"
    HOURS_MISMATCH = "hours_mismatch"


class Priority(str, Enum):
    """Priority levels for issues."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataSource(str, Enum):
    """External data sources for validation."""
    NPI_REGISTRY = "npi_registry"
    GOOGLE_PLACES = "google_places"
    PRACTICE_WEBSITE = "practice_website"
    STATE_LICENSE = "state_license"
    PDF_DOCUMENT = "pdf_document"


class Address(BaseModel):
    """Address model."""
    street1: str
    street2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    
    def to_string(self) -> str:
        """Convert address to single string."""
        parts = [self.street1]
        if self.street2:
            parts.append(self.street2)
        parts.append(f"{self.city}, {self.state} {self.zip_code}")
        return ", ".join(parts)


class ContactInfo(BaseModel):
    """Contact information model."""
    phone: str
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class Provider(BaseModel):
    """Healthcare provider model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    npi: str  # National Provider Identifier
    
    # Basic Info
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    credentials: List[str] = []
    specialty: str
    
    # Practice Info
    practice_name: str
    address: Address
    contact: ContactInfo
    
    # Professional Info
    license_number: Optional[str] = None
    license_state: Optional[str] = None
    license_status: str = "Active"
    accepting_patients: bool = True
    
    # Languages & Hours
    languages: List[str] = ["English"]
    office_hours: Optional[Dict[str, str]] = None
    
    # Metadata
    status: ValidationStatus = ValidationStatus.PENDING
    confidence_score: float = 0.0
    last_validated: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Enrichment data
    hospital_affiliations: List[str] = []
    education: List[str] = []
    certifications: List[str] = []
    
    def full_name(self) -> str:
        """Get full name with credentials."""
        name = f"{self.first_name}"
        if self.middle_name:
            name += f" {self.middle_name}"
        name += f" {self.last_name}"
        if self.credentials:
            name += f", {', '.join(self.credentials)}"
        return name


class Discrepancy(BaseModel):
    """Model for data discrepancies found during validation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider_id: str
    type: DiscrepancyType
    field_name: str
    
    # Values
    current_value: str
    validated_value: str
    source: DataSource
    
    # Assessment
    priority: Priority
    confidence: float  # 0-100
    
    # Resolution
    resolved: bool = False
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    # Timestamps
    detected_at: datetime = Field(default_factory=datetime.now)


class SourceValidation(BaseModel):
    """Validation result from a single source."""
    source: DataSource
    success: bool
    confidence: float  # 0-100
    data: Dict[str, Any] = {}
    discrepancies: List[Discrepancy] = []
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ValidationResult(BaseModel):
    """Complete validation result for a provider."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider_id: str
    
    # Status
    status: ValidationStatus
    overall_confidence: float  # 0-100
    
    # Source validations
    source_validations: List[SourceValidation] = []
    
    # Discrepancies found
    discrepancies: List[Discrepancy] = []
    total_discrepancies: int = 0
    
    # Decision
    auto_updated: bool = False
    needs_review: bool = False
    urgent_review: bool = False
    
    # Processing info
    processing_time_ms: float = 0.0
    validated_at: datetime = Field(default_factory=datetime.now)
    
    # Summary
    summary: Optional[str] = None


class ReviewTicket(BaseModel):
    """Ticket for human review of provider data."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider_id: str
    validation_result_id: str
    
    # Ticket info
    priority: Priority
    status: str = "open"  # open, in_progress, resolved, closed
    
    # Assignment
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    
    # Details
    discrepancies: List[Discrepancy] = []
    notes: List[str] = []
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None


class ValidationReport(BaseModel):
    """Summary report of validation run."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Counts
    total_providers: int
    validated: int = 0
    auto_updated: int = 0
    needs_review: int = 0
    urgent: int = 0
    errors: int = 0
    
    # Statistics
    average_confidence: float = 0.0
    processing_time_seconds: float = 0.0
    
    # Discrepancy breakdown
    discrepancy_counts: Dict[str, int] = {}
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class NotificationRequest(BaseModel):
    """Request to send notification."""
    recipient_email: str
    subject: str
    message: str
    priority: Priority = Priority.MEDIUM
    provider_ids: List[str] = []
    attachment_path: Optional[str] = None
