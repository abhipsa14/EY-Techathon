"""
Configuration settings for the Provider Data Validation System.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
for dir_path in [DATA_DIR, REPORTS_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/providers.db")

# API Keys (set these in .env file)
NPI_REGISTRY_BASE_URL = "https://npiregistry.cms.hhs.gov/api/"
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Email Configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@providervalidation.com")
EMAIL_TO = os.getenv("EMAIL_TO", "admin@providervalidation.com")

# Validation Thresholds
CONFIDENCE_THRESHOLDS = {
    "auto_update": 80,     # >= 80% confidence: auto-update
    "needs_review": 60,    # 60-79% confidence: needs review
    "urgent": 0            # < 60% confidence: urgent review
}

# Source Reliability Weights
SOURCE_WEIGHTS = {
    "npi_registry": 0.35,      # Most reliable (government source)
    "google_places": 0.25,     # Reliable (verified business info)
    "practice_website": 0.20,  # Semi-reliable (self-reported)
    "state_license": 0.15,     # Reliable but may be outdated
    "pdf_document": 0.05       # Least reliable (potentially old)
}

# Processing Settings
BATCH_SIZE = 50
MAX_CONCURRENT_REQUESTS = 10
REQUEST_TIMEOUT = 30  # seconds
RATE_LIMIT_DELAY = 0.5  # seconds between API calls

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Provider Specialties (common medical specialties)
MEDICAL_SPECIALTIES = [
    "Family Medicine",
    "Internal Medicine",
    "Pediatrics",
    "Cardiology",
    "Dermatology",
    "Emergency Medicine",
    "Gastroenterology",
    "Neurology",
    "Obstetrics & Gynecology",
    "Oncology",
    "Ophthalmology",
    "Orthopedics",
    "Psychiatry",
    "Pulmonology",
    "Radiology",
    "Surgery",
    "Urology",
    "Anesthesiology",
    "Endocrinology",
    "Rheumatology"
]

# US States for validation
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
]

# Credentials
CREDENTIAL_TYPES = ["MD", "DO", "NP", "PA", "DPM", "DC", "DDS", "DMD", "OD", "PhD"]
