"""
Web Scraper Service - Extracts provider information from practice websites.
Handles semi-structured data extraction from various website formats.
"""

import asyncio
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
import re
from bs4 import BeautifulSoup

from models import (
    Provider, SourceValidation, DataSource, Discrepancy,
    DiscrepancyType, Priority
)
from config import REQUEST_TIMEOUT


class WebScraperService:
    """Service for scraping and validating provider data from practice websites."""
    
    def __init__(self):
        self.timeout = REQUEST_TIMEOUT
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
    async def validate_provider(self, provider: Provider) -> SourceValidation:
        """
        Validate provider data by scraping their practice website.
        
        Args:
            provider: Provider to validate
            
        Returns:
            SourceValidation with results
        """
        try:
            # Check if website exists
            website = provider.contact.website
            if not website:
                return SourceValidation(
                    source=DataSource.PRACTICE_WEBSITE,
                    success=False,
                    confidence=0.0,
                    error_message="No website URL provided"
                )
            
            # Scrape website data
            scraped_data = await self._scrape_website(website, provider)
            
            if not scraped_data or not scraped_data.get("accessible"):
                return SourceValidation(
                    source=DataSource.PRACTICE_WEBSITE,
                    success=False,
                    confidence=30.0,
                    error_message="Website not accessible or data extraction failed"
                )
            
            # Compare and find discrepancies
            discrepancies = self._compare_data(provider, scraped_data)
            
            # Calculate confidence
            confidence = self._calculate_confidence(provider, scraped_data, discrepancies)
            
            return SourceValidation(
                source=DataSource.PRACTICE_WEBSITE,
                success=True,
                confidence=confidence,
                data=scraped_data,
                discrepancies=discrepancies
            )
            
        except Exception as e:
            return SourceValidation(
                source=DataSource.PRACTICE_WEBSITE,
                success=False,
                confidence=0.0,
                error_message=str(e)
            )
    
    async def _scrape_website(self, url: str, provider: Provider) -> Optional[Dict[str, Any]]:
        """
        Scrape data from practice website.
        
        In production, this would actually fetch and parse the website.
        For demo, we simulate realistic scraped data.
        """
        # Simulate scraping delay
        await asyncio.sleep(0.2)
        
        # For demo purposes, simulate scraped data
        # In production:
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(url, headers=self.headers, timeout=self.timeout)
        #     if response.status_code == 200:
        #         return self._parse_html(response.text, provider)
        
        return self._generate_simulated_scraped_data(url, provider)
    
    def _parse_html(self, html: str, provider: Provider) -> Dict[str, Any]:
        """Parse HTML content to extract provider information."""
        soup = BeautifulSoup(html, 'html.parser')
        
        data = {
            "accessible": True,
            "title": "",
            "phones": [],
            "addresses": [],
            "emails": [],
            "providers_mentioned": [],
            "services": [],
            "hours": []
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            data["title"] = title_tag.get_text(strip=True)
        
        # Extract phone numbers (common patterns)
        text = soup.get_text()
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        data["phones"] = list(set(re.findall(phone_pattern, text)))
        
        # Extract emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        data["emails"] = list(set(re.findall(email_pattern, text)))
        
        # Look for provider name mentions
        provider_name = f"{provider.first_name} {provider.last_name}"
        if provider_name.lower() in text.lower():
            data["providers_mentioned"].append(provider_name)
        
        # Extract common medical terms/services
        common_services = [
            "primary care", "family medicine", "internal medicine", "pediatrics",
            "cardiology", "dermatology", "telehealth", "urgent care"
        ]
        text_lower = text.lower()
        data["services"] = [s for s in common_services if s in text_lower]
        
        return data
    
    def _generate_simulated_scraped_data(self, url: str, provider: Provider) -> Dict[str, Any]:
        """Generate simulated scraped data for demo."""
        seed = hash(provider.id) % 1000
        
        # Simulate variation (20% chance of phone mismatch from website)
        phone_variation = seed % 10 < 2
        name_found = seed % 10 > 1  # 80% chance name is found
        
        phone = provider.contact.phone
        if phone_variation:
            phone = f"(617) 555-{(seed + 100):04d}"
        
        return {
            "accessible": True,
            "url": url,
            "title": f"{provider.practice_name} - {provider.specialty}",
            "phones": [phone],
            "addresses": [provider.address.to_string()],
            "emails": [provider.contact.email] if provider.contact.email else [],
            "providers_mentioned": [f"Dr. {provider.first_name} {provider.last_name}"] if name_found else [],
            "services": self._get_services_for_specialty(provider.specialty),
            "hours": "Monday-Friday: 8AM-5PM",
            "accepting_patients": True,
            "last_updated": datetime.now().isoformat(),
            "specialties_mentioned": [provider.specialty],
            "certifications": provider.certifications if provider.certifications else []
        }
    
    def _get_services_for_specialty(self, specialty: str) -> List[str]:
        """Get typical services for a medical specialty."""
        specialty_services = {
            "Family Medicine": ["Primary Care", "Preventive Care", "Chronic Disease Management", "Immunizations"],
            "Internal Medicine": ["Adult Primary Care", "Chronic Disease Management", "Health Screenings"],
            "Pediatrics": ["Well-Child Visits", "Immunizations", "Developmental Screenings"],
            "Cardiology": ["Heart Disease", "EKG", "Echocardiogram", "Cardiac Stress Test"],
            "Dermatology": ["Skin Cancer Screening", "Acne Treatment", "Cosmetic Procedures"],
            "Orthopedics": ["Joint Replacement", "Sports Medicine", "Fracture Care"],
            "Psychiatry": ["Mental Health", "Medication Management", "Therapy"],
            "Neurology": ["Headache Treatment", "Stroke Care", "Epilepsy Management"],
        }
        return specialty_services.get(specialty, ["General Medical Services"])
    
    def _compare_data(self, provider: Provider, scraped_data: Dict[str, Any]) -> List[Discrepancy]:
        """Compare provider data with scraped website data."""
        discrepancies = []
        
        # Check phone numbers
        scraped_phones = [self._normalize_phone(p) for p in scraped_data.get("phones", [])]
        provider_phone = self._normalize_phone(provider.contact.phone)
        
        if scraped_phones and provider_phone not in scraped_phones:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.PHONE_MISMATCH,
                field_name="phone",
                current_value=provider.contact.phone,
                validated_value=scraped_data.get("phones", ["Unknown"])[0],
                source=DataSource.PRACTICE_WEBSITE,
                priority=Priority.MEDIUM,
                confidence=75.0
            ))
        
        # Check if provider name is on website
        provider_name = f"{provider.first_name} {provider.last_name}".lower()
        providers_mentioned = [p.lower() for p in scraped_data.get("providers_mentioned", [])]
        
        name_found = any(provider_name in p for p in providers_mentioned)
        if not name_found and providers_mentioned:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.NAME_MISMATCH,
                field_name="provider_presence",
                current_value=f"Dr. {provider.first_name} {provider.last_name}",
                validated_value="Not found on practice website",
                source=DataSource.PRACTICE_WEBSITE,
                priority=Priority.LOW,
                confidence=60.0
            ))
        
        # Check specialty match
        scraped_specialties = [s.lower() for s in scraped_data.get("specialties_mentioned", [])]
        if scraped_specialties and provider.specialty.lower() not in scraped_specialties:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.SPECIALTY_MISMATCH,
                field_name="specialty",
                current_value=provider.specialty,
                validated_value=", ".join(scraped_data.get("specialties_mentioned", [])),
                source=DataSource.PRACTICE_WEBSITE,
                priority=Priority.LOW,
                confidence=70.0
            ))
        
        return discrepancies
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison."""
        if not phone:
            return ""
        return re.sub(r'\D', '', phone)[-10:]
    
    def _calculate_confidence(
        self, 
        provider: Provider, 
        scraped_data: Dict[str, Any],
        discrepancies: List[Discrepancy]
    ) -> float:
        """Calculate confidence score based on website data."""
        # Website data is less reliable, start at 80%
        base_confidence = 80.0
        
        # Deduct for discrepancies
        for disc in discrepancies:
            if disc.priority == Priority.HIGH:
                base_confidence -= 20
            elif disc.priority == Priority.MEDIUM:
                base_confidence -= 10
            else:
                base_confidence -= 5
        
        # Bonus if provider name found
        if scraped_data.get("providers_mentioned"):
            base_confidence += 5
        
        # Bonus for recent update
        if scraped_data.get("last_updated"):
            base_confidence += 3
        
        return max(0.0, min(100.0, base_confidence))
    
    async def scrape_multiple(self, providers: List[Provider]) -> Dict[str, SourceValidation]:
        """Scrape multiple provider websites concurrently."""
        tasks = [self.validate_provider(p) for p in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            providers[i].id: results[i] if not isinstance(results[i], Exception) 
            else SourceValidation(
                source=DataSource.PRACTICE_WEBSITE,
                success=False,
                confidence=0.0,
                error_message=str(results[i])
            )
            for i in range(len(providers))
        }


# Singleton instance
web_scraper_service = WebScraperService()
