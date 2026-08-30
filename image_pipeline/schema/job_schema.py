"""
Strict Structured Schema for Image Job Extraction.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CompanyResult(BaseModel):
    name: Optional[str] = None
    confidence: float = 0.0
    canonical: Optional[str] = None
    detection_method: Optional[str] = None  # dictionary, legal_suffix, bounding_box, ai


class RoleResult(BaseModel):
    name: str
    canonical: Optional[str] = None
    category: Optional[str] = None
    sector: Optional[str] = None
    confidence: float = 0.0


class LocationResult(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    locality: Optional[str] = None
    venue: Optional[str] = None
    pincode: Optional[str] = None
    confidence: float = 0.0


class TimeWindow(BaseModel):
    start: Optional[str] = None  # e.g., "09:30 AM" or "09:30"
    end: Optional[str] = None    # e.g., "03:30 PM" or "15:30"


class QRCodeResult(BaseModel):
    found: bool = False
    payload_type: Optional[str] = None  # url, phone, email, text, wifi, vcard
    raw_data: Optional[str] = None
    url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class OCRBoundingBox(BaseModel):
    text: str
    confidence: float
    box: List[List[float]]       # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    rect: List[float]            # [x_min, y_min, x_max, y_max]
    relative_top: float = 0.0    # y_min / image_height (0.0 at top, 1.0 at bottom)


class JobExtractionResult(BaseModel):
    is_job: bool = False
    job_type: str = "walk_in_interview"  # walk_in_interview, direct_hiring, job_fair, referral
    title: Optional[str] = None
    company: CompanyResult = Field(default_factory=CompanyResult)
    roles: List[RoleResult] = Field(default_factory=list)
    location: LocationResult = Field(default_factory=LocationResult)
    
    # Dates and timings
    date: Optional[str] = None           # ISO Date e.g. "2026-08-29" or "29 Aug 2026"
    end_date: Optional[str] = None       # If date range
    time: TimeWindow = Field(default_factory=TimeWindow)
    
    # Contacts
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    apply_url: Optional[str] = None
    
    # QR & Verification Details
    qr: QRCodeResult = Field(default_factory=QRCodeResult)
    confidence: float = 0.0              # Overall extraction confidence (0.0 to 1.0)
    signal_score: int = 0
    signal_details: List[str] = Field(default_factory=list)
    
    # Metadata
    image_path: Optional[str] = None
    image_hash: Optional[str] = None
    source_url: Optional[str] = None
    raw_ocr_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
