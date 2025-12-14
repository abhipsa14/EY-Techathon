"""
Synthetic Data Generator - Creates realistic provider data with intentional errors.
Used for demonstrations and testing of the validation system.
"""

import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from models import Provider, Address, ContactInfo, ValidationStatus
from config import MEDICAL_SPECIALTIES, US_STATES, CREDENTIAL_TYPES


class SyntheticDataGenerator:
    """
    Generates realistic synthetic provider data for testing and demos.
    
    Includes intentional errors to demonstrate validation capabilities:
    - ~20% phone number errors
    - ~15% address errors
    - ~10% specialty mismatches
    - ~5% license issues
    - ~5% NPI format errors
    """
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
        
        # Name components for realistic generation
        self.first_names = [
            "James", "John", "Robert", "Michael", "William", "David", "Richard",
            "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
            "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew",
            "Sarah", "Karen", "Nancy", "Lisa", "Margaret", "Betty", "Sandra",
            "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua",
            "Michelle", "Emily", "Ashley", "Amanda", "Melissa", "Stephanie", "Nicole"
        ]
        
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
            "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
            "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
            "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
            "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
            "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green"
        ]
        
        self.practice_prefixes = [
            "Advanced", "Premier", "Elite", "Family", "Community", "Regional",
            "Metro", "City", "Valley", "Coastal", "Mountain", "Central",
            "Professional", "Comprehensive", "Integrated", "Wellness"
        ]
        
        self.practice_suffixes = [
            "Medical Center", "Health Group", "Medical Associates", "Healthcare",
            "Medical Practice", "Physicians", "Clinic", "Medical Group",
            "Care Center", "Health Services", "Medical Partners", "Specialists"
        ]
        
        self.street_names = [
            "Main St", "Oak Ave", "Medical Center Dr", "Healthcare Blvd",
            "Hospital Way", "Wellness Rd", "Professional Plaza", "Doctor's Row",
            "Health Park Dr", "Campus Dr", "University Ave", "Research Blvd",
            "Commerce St", "Market St", "Park Ave", "Broadway"
        ]
        
        self.cities = {
            "MA": ["Boston", "Cambridge", "Worcester", "Springfield", "Lowell"],
            "NY": ["New York", "Buffalo", "Rochester", "Albany", "Syracuse"],
            "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento", "San Jose"],
            "TX": ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth"],
            "FL": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale"],
            "IL": ["Chicago", "Aurora", "Naperville", "Rockford", "Springfield"],
            "PA": ["Philadelphia", "Pittsburgh", "Allentown", "Erie", "Reading"],
            "OH": ["Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron"],
            "GA": ["Atlanta", "Augusta", "Savannah", "Athens", "Macon"],
            "NC": ["Charlotte", "Raleigh", "Durham", "Greensboro", "Winston-Salem"]
        }
        
        self.hospitals = [
            "General Hospital", "Medical Center", "University Hospital",
            "Regional Medical Center", "Community Hospital", "Memorial Hospital",
            "Children's Hospital", "Heart Institute", "Cancer Center"
        ]
        
        self.medical_schools = [
            "Harvard Medical School", "Johns Hopkins School of Medicine",
            "Stanford University School of Medicine", "Yale School of Medicine",
            "Columbia University Vagelos College of Physicians and Surgeons",
            "University of Pennsylvania Perelman School of Medicine",
            "Duke University School of Medicine", "NYU Grossman School of Medicine",
            "University of Michigan Medical School", "UCLA David Geffen School of Medicine"
        ]
    
    def generate_providers(self, count: int = 200, error_rate: float = 0.25) -> List[Provider]:
        """
        Generate a list of synthetic providers with realistic data and intentional errors.
        
        Args:
            count: Number of providers to generate
            error_rate: Percentage of providers with some form of error (0.0 to 1.0)
            
        Returns:
            List of Provider objects
        """
        providers = []
        
        for i in range(count):
            provider = self._generate_single_provider(i)
            
            # Introduce errors for some providers
            if random.random() < error_rate:
                provider = self._introduce_errors(provider)
            
            providers.append(provider)
        
        return providers
    
    def _generate_single_provider(self, index: int) -> Provider:
        """Generate a single provider with complete data."""
        # Basic demographics
        first_name = random.choice(self.first_names)
        last_name = random.choice(self.last_names)
        specialty = random.choice(MEDICAL_SPECIALTIES)
        credentials = self._generate_credentials(specialty)
        
        # Location
        state = random.choice(list(self.cities.keys()))
        city = random.choice(self.cities[state])
        
        # Generate NPI (10-digit, starts with 1 or 2)
        npi = f"{random.choice([1, 2])}{random.randint(100000000, 999999999)}"
        
        # Contact info
        area_code = self._get_area_code(state)
        phone = f"({area_code}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
        
        # Practice name
        practice_name = f"{random.choice(self.practice_prefixes)} {specialty} {random.choice(self.practice_suffixes)}"
        
        # Address
        address = Address(
            street1=f"{random.randint(100, 9999)} {random.choice(self.street_names)}",
            street2=f"Suite {random.randint(100, 999)}" if random.random() > 0.5 else None,
            city=city,
            state=state,
            zip_code=self._generate_zip(state)
        )
        
        # Contact
        email_domain = practice_name.lower().replace(" ", "").replace("&", "")[:20]
        contact = ContactInfo(
            phone=phone,
            fax=phone.replace(str(random.randint(0, 9)), str(random.randint(0, 9))),
            email=f"{first_name.lower()}.{last_name.lower()}@{email_domain}.com",
            website=f"https://www.{email_domain}.com"
        )
        
        # Professional info
        license_number = f"{state}{random.randint(100000, 999999)}"
        
        return Provider(
            npi=npi,
            first_name=first_name,
            last_name=last_name,
            credentials=credentials,
            specialty=specialty,
            practice_name=practice_name,
            address=address,
            contact=contact,
            license_number=license_number,
            license_state=state,
            license_status="Active",
            accepting_patients=random.random() > 0.1,
            languages=self._generate_languages(),
            office_hours=self._generate_office_hours(),
            hospital_affiliations=self._generate_affiliations(city),
            education=self._generate_education(),
            certifications=self._generate_certifications(specialty),
            status=ValidationStatus.PENDING,
            confidence_score=0.0
        )
    
    def _generate_credentials(self, specialty: str) -> List[str]:
        """Generate appropriate credentials based on specialty."""
        base_creds = ["MD"] if random.random() > 0.2 else ["DO"]
        
        # Add board certification abbreviations
        if random.random() > 0.3:
            if "Surgery" in specialty:
                base_creds.append("FACS")
            elif "Cardiology" in specialty:
                base_creds.append("FACC")
            elif "Internal" in specialty:
                base_creds.append("FACP")
        
        return base_creds
    
    def _get_area_code(self, state: str) -> str:
        """Get realistic area code for state."""
        area_codes = {
            "MA": ["617", "508", "781", "857"],
            "NY": ["212", "718", "516", "914"],
            "CA": ["310", "415", "619", "818"],
            "TX": ["214", "713", "512", "210"],
            "FL": ["305", "407", "813", "954"],
            "IL": ["312", "773", "847", "630"],
            "PA": ["215", "412", "610", "717"],
            "OH": ["614", "216", "513", "419"],
            "GA": ["404", "770", "678", "912"],
            "NC": ["704", "919", "336", "252"]
        }
        return random.choice(area_codes.get(state, ["555"]))
    
    def _generate_zip(self, state: str) -> str:
        """Generate realistic ZIP code for state."""
        zip_ranges = {
            "MA": (1000, 2799),
            "NY": (10000, 14999),
            "CA": (90000, 96199),
            "TX": (75000, 79999),
            "FL": (32000, 34999),
            "IL": (60000, 62999),
            "PA": (15000, 19699),
            "OH": (43000, 45999),
            "GA": (30000, 31999),
            "NC": (27000, 28999)
        }
        range_start, range_end = zip_ranges.get(state, (10000, 99999))
        return str(random.randint(range_start, range_end)).zfill(5)
    
    def _generate_languages(self) -> List[str]:
        """Generate list of languages spoken."""
        languages = ["English"]
        additional = ["Spanish", "Mandarin", "French", "German", "Portuguese", 
                      "Italian", "Russian", "Arabic", "Hindi", "Korean"]
        
        if random.random() > 0.6:
            languages.append(random.choice(additional))
        
        return languages
    
    def _generate_office_hours(self) -> Dict[str, str]:
        """Generate realistic office hours."""
        return {
            "Monday": "8:00 AM - 5:00 PM",
            "Tuesday": "8:00 AM - 5:00 PM",
            "Wednesday": "8:00 AM - 5:00 PM",
            "Thursday": "8:00 AM - 5:00 PM",
            "Friday": "8:00 AM - 4:00 PM",
            "Saturday": "Closed" if random.random() > 0.3 else "9:00 AM - 12:00 PM",
            "Sunday": "Closed"
        }
    
    def _generate_affiliations(self, city: str) -> List[str]:
        """Generate hospital affiliations."""
        num_affiliations = random.randint(1, 3)
        affiliations = []
        
        for _ in range(num_affiliations):
            hospital = f"{city} {random.choice(self.hospitals)}"
            if hospital not in affiliations:
                affiliations.append(hospital)
        
        return affiliations
    
    def _generate_education(self) -> List[str]:
        """Generate education history."""
        school = random.choice(self.medical_schools)
        year = random.randint(1985, 2020)
        return [f"{school}, {year}"]
    
    def _generate_certifications(self, specialty: str) -> List[str]:
        """Generate board certifications."""
        certs = []
        if random.random() > 0.2:
            certs.append(f"Board Certified in {specialty}")
        return certs
    
    def _introduce_errors(self, provider: Provider) -> Provider:
        """Introduce realistic errors into provider data."""
        error_types = ["phone", "address", "specialty", "license", "npi", "name"]
        error_type = random.choice(error_types)
        
        if error_type == "phone":
            # Wrong phone number
            new_phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
            provider.contact.phone = new_phone
            
        elif error_type == "address":
            # Old/wrong address
            provider.address.street1 = f"{random.randint(1, 999)} Old Location St"
            if random.random() > 0.5:
                provider.address.city = random.choice(["Oldtown", "Former City", "Previous Location"])
            
        elif error_type == "specialty":
            # Specialty mismatch
            other_specialties = [s for s in MEDICAL_SPECIALTIES if s != provider.specialty]
            provider.specialty = random.choice(other_specialties)
            
        elif error_type == "license":
            # License issues
            if random.random() > 0.5:
                provider.license_status = random.choice(["Expired", "Suspended", "Inactive"])
            else:
                provider.license_number = f"INVALID{random.randint(100, 999)}"
            
        elif error_type == "npi":
            # Invalid NPI format
            if random.random() > 0.5:
                provider.npi = str(random.randint(10000000, 99999999))  # 8 digits instead of 10
            else:
                provider.npi = f"999{random.randint(1000000, 9999999)}"  # Invalid prefix
        
        elif error_type == "name":
            # Name variation/typo
            typos = {
                "Michael": "Micheal",
                "Jennifer": "Jenifer",
                "Christopher": "Cristopher",
                "Elizabeth": "Elisabeth",
                "Matthew": "Mathew"
            }
            if provider.first_name in typos:
                provider.first_name = typos[provider.first_name]
        
        return provider
    
    def generate_summary(self, providers: List[Provider]) -> Dict[str, Any]:
        """Generate summary statistics for generated data."""
        specialties = {}
        states = {}
        
        for p in providers:
            specialties[p.specialty] = specialties.get(p.specialty, 0) + 1
            states[p.address.state] = states.get(p.address.state, 0) + 1
        
        return {
            "total_providers": len(providers),
            "specialties_distribution": dict(sorted(specialties.items(), key=lambda x: x[1], reverse=True)),
            "states_distribution": dict(sorted(states.items(), key=lambda x: x[1], reverse=True)),
            "accepting_patients": sum(1 for p in providers if p.accepting_patients),
            "generated_at": datetime.now().isoformat()
        }


# Singleton instance
data_generator = SyntheticDataGenerator()
