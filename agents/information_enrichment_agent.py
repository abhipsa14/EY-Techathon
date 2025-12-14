"""
Information Enrichment Agent - Enriches provider data with additional information.
Adds credentials, education, hospital affiliations, and other supplementary data.
"""

import asyncio
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from models import Provider, DataSource
from config import MEDICAL_SPECIALTIES


class InformationEnrichmentAgent:
    """
    Agent responsible for enriching provider profiles with additional data.
    
    Capabilities:
    - Adds education and training information
    - Identifies hospital affiliations
    - Discovers board certifications
    - Finds additional practice locations
    - Enriches service offerings
    - Adds quality metrics and ratings
    
    This agent enhances provider profiles beyond basic validation,
    making directory data more comprehensive and valuable.
    """
    
    def __init__(self):
        self.name = "Information Enrichment Agent"
        
        # Enrichment data sources (simulated for demo)
        self.hospital_database = self._load_hospital_database()
        self.certification_boards = self._load_certification_boards()
        self.medical_schools = self._load_medical_schools()
        
        # Statistics
        self.stats = {
            "providers_enriched": 0,
            "fields_added": 0,
            "enrichment_rate": 0.0
        }
    
    def _load_hospital_database(self) -> Dict[str, List[str]]:
        """Load hospital data by state (simulated)."""
        return {
            "MA": ["Massachusetts General Hospital", "Brigham and Women's Hospital", 
                   "Beth Israel Deaconess Medical Center", "Boston Children's Hospital"],
            "NY": ["NewYork-Presbyterian Hospital", "Mount Sinai Hospital", 
                   "NYU Langone Medical Center", "Memorial Sloan Kettering"],
            "CA": ["Cedars-Sinai Medical Center", "UCLA Medical Center",
                   "Stanford Health Care", "UCSF Medical Center"],
            "TX": ["Houston Methodist Hospital", "MD Anderson Cancer Center",
                   "Baylor University Medical Center", "UT Southwestern Medical Center"],
            "FL": ["Cleveland Clinic Florida", "Mayo Clinic Jacksonville",
                   "Tampa General Hospital", "Baptist Health South Florida"]
        }
    
    def _load_certification_boards(self) -> Dict[str, str]:
        """Load certification board mappings."""
        return {
            "Internal Medicine": "American Board of Internal Medicine (ABIM)",
            "Family Medicine": "American Board of Family Medicine (ABFM)",
            "Pediatrics": "American Board of Pediatrics (ABP)",
            "Cardiology": "American Board of Internal Medicine (ABIM) - Cardiovascular Disease",
            "Dermatology": "American Board of Dermatology (ABD)",
            "Surgery": "American Board of Surgery (ABS)",
            "Orthopedics": "American Board of Orthopaedic Surgery (ABOS)",
            "Psychiatry": "American Board of Psychiatry and Neurology (ABPN)",
            "Neurology": "American Board of Psychiatry and Neurology (ABPN)",
            "Oncology": "American Board of Internal Medicine (ABIM) - Medical Oncology"
        }
    
    def _load_medical_schools(self) -> List[str]:
        """Load medical school list."""
        return [
            "Harvard Medical School",
            "Johns Hopkins School of Medicine",
            "Stanford University School of Medicine",
            "Yale School of Medicine",
            "Columbia University Vagelos College of Physicians and Surgeons",
            "University of Pennsylvania Perelman School of Medicine",
            "Duke University School of Medicine",
            "NYU Grossman School of Medicine",
            "University of Michigan Medical School",
            "UCLA David Geffen School of Medicine",
            "University of Washington School of Medicine",
            "University of Chicago Pritzker School of Medicine"
        ]
    
    async def enrich_provider(self, provider: Provider) -> Dict[str, Any]:
        """
        Enrich a single provider's profile with additional data.
        
        Args:
            provider: Provider to enrich
            
        Returns:
            Dictionary of enriched/added fields
        """
        # Simulate API call delay
        await asyncio.sleep(0.05)
        
        enrichments = {}
        
        # Enrich hospital affiliations
        if not provider.hospital_affiliations or len(provider.hospital_affiliations) < 2:
            new_affiliations = self._find_hospital_affiliations(provider)
            if new_affiliations:
                enrichments["hospital_affiliations"] = new_affiliations
                provider.hospital_affiliations = new_affiliations
        
        # Enrich education
        if not provider.education:
            education = self._find_education(provider)
            if education:
                enrichments["education"] = education
                provider.education = education
        
        # Enrich certifications
        if not provider.certifications:
            certifications = self._find_certifications(provider)
            if certifications:
                enrichments["certifications"] = certifications
                provider.certifications = certifications
        
        # Add quality metrics (simulated)
        quality_metrics = self._generate_quality_metrics(provider)
        enrichments["quality_metrics"] = quality_metrics
        
        # Add patient satisfaction scores (simulated)
        satisfaction = self._generate_satisfaction_scores(provider)
        enrichments["patient_satisfaction"] = satisfaction
        
        # Add availability information
        availability = self._generate_availability(provider)
        enrichments["availability"] = availability
        
        # Update statistics
        self.stats["providers_enriched"] += 1
        self.stats["fields_added"] += len(enrichments)
        
        return enrichments
    
    async def enrich_batch(
        self, 
        providers: List[Provider],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich multiple providers efficiently.
        
        Args:
            providers: List of providers to enrich
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping provider IDs to their enrichments
        """
        all_enrichments = {}
        total = len(providers)
        
        # Process providers with concurrency limit
        batch_size = 20
        for i in range(0, total, batch_size):
            batch = providers[i:i + batch_size]
            tasks = [self.enrich_provider(p) for p in batch]
            results = await asyncio.gather(*tasks)
            
            for j, enrichment in enumerate(results):
                all_enrichments[batch[j].id] = enrichment
            
            if progress_callback:
                progress_callback(min(i + batch_size, total), total)
        
        # Calculate enrichment rate
        if self.stats["providers_enriched"] > 0:
            self.stats["enrichment_rate"] = (
                self.stats["fields_added"] / self.stats["providers_enriched"]
            )
        
        return all_enrichments
    
    def _find_hospital_affiliations(self, provider: Provider) -> List[str]:
        """Find hospital affiliations for a provider."""
        state = provider.address.state
        state_hospitals = self.hospital_database.get(state, [])
        
        if not state_hospitals:
            # Use generic hospitals if state not in database
            state_hospitals = [
                f"{provider.address.city} General Hospital",
                f"{provider.address.city} Medical Center"
            ]
        
        # Randomly select 1-3 affiliations
        num_affiliations = min(random.randint(1, 3), len(state_hospitals))
        return random.sample(state_hospitals, num_affiliations)
    
    def _find_education(self, provider: Provider) -> List[str]:
        """Find education information for a provider."""
        # Simulate education discovery
        school = random.choice(self.medical_schools)
        graduation_year = random.randint(1990, 2020)
        
        education = [f"MD, {school}, {graduation_year}"]
        
        # Add residency
        residency_hospital = random.choice(
            self.hospital_database.get("MA", ["Teaching Hospital"])
        )
        education.append(f"Residency in {provider.specialty}, {residency_hospital}")
        
        return education
    
    def _find_certifications(self, provider: Provider) -> List[str]:
        """Find board certifications for a provider."""
        certifications = []
        
        # Match specialty to certification board
        for specialty, board in self.certification_boards.items():
            if specialty.lower() in provider.specialty.lower():
                cert_year = random.randint(2010, 2023)
                certifications.append(f"Board Certified by {board} ({cert_year})")
                break
        
        if not certifications:
            certifications.append(f"Board Certified in {provider.specialty}")
        
        return certifications
    
    def _generate_quality_metrics(self, provider: Provider) -> Dict[str, Any]:
        """Generate simulated quality metrics."""
        return {
            "overall_rating": round(random.uniform(3.5, 5.0), 1),
            "patient_reviews": random.randint(20, 500),
            "years_of_experience": random.randint(5, 35),
            "successful_outcomes_rate": round(random.uniform(85, 99), 1),
            "readmission_rate": round(random.uniform(1, 10), 1),
            "complications_rate": round(random.uniform(0.5, 5), 1)
        }
    
    def _generate_satisfaction_scores(self, provider: Provider) -> Dict[str, float]:
        """Generate simulated patient satisfaction scores."""
        base_score = random.uniform(3.5, 5.0)
        
        return {
            "overall": round(base_score, 1),
            "communication": round(base_score + random.uniform(-0.3, 0.3), 1),
            "wait_time": round(base_score + random.uniform(-0.5, 0.2), 1),
            "staff_friendliness": round(base_score + random.uniform(-0.2, 0.3), 1),
            "office_environment": round(base_score + random.uniform(-0.2, 0.2), 1),
            "would_recommend": round(min(5.0, base_score + random.uniform(0, 0.5)), 1)
        }
    
    def _generate_availability(self, provider: Provider) -> Dict[str, Any]:
        """Generate availability information."""
        return {
            "accepting_new_patients": provider.accepting_patients,
            "next_available_appointment": self._get_next_available(),
            "telehealth_available": random.random() > 0.3,
            "evening_hours": random.random() > 0.6,
            "weekend_hours": random.random() > 0.7,
            "languages": provider.languages
        }
    
    def _get_next_available(self) -> str:
        """Generate next available appointment time."""
        days_out = random.randint(1, 21)
        if days_out <= 3:
            return f"Within {days_out} days"
        elif days_out <= 7:
            return "This week"
        elif days_out <= 14:
            return "Next week"
        else:
            return "2-3 weeks"
    
    def get_enrichment_summary(
        self, 
        enrichments: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary of enrichment operations."""
        total_providers = len(enrichments)
        
        fields_enriched = {
            "hospital_affiliations": 0,
            "education": 0,
            "certifications": 0,
            "quality_metrics": 0,
            "patient_satisfaction": 0,
            "availability": 0
        }
        
        for provider_enrichment in enrichments.values():
            for field in fields_enriched:
                if field in provider_enrichment:
                    fields_enriched[field] += 1
        
        return {
            "total_providers_enriched": total_providers,
            "fields_enriched": fields_enriched,
            "enrichment_rates": {
                field: count / total_providers * 100 if total_providers > 0 else 0
                for field, count in fields_enriched.items()
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset agent statistics."""
        self.stats = {
            "providers_enriched": 0,
            "fields_added": 0,
            "enrichment_rate": 0.0
        }


# Singleton instance
information_enrichment_agent = InformationEnrichmentAgent()
