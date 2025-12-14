"""
Google Places Service - Validates provider business information using Google Places API.
Provides business hours, contact info, reviews, and location verification.
"""

import asyncio
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
import re

from models import (
    Provider, SourceValidation, DataSource, Discrepancy,
    DiscrepancyType, Priority
)
from config import GOOGLE_PLACES_API_KEY, REQUEST_TIMEOUT


class GooglePlacesService:
    """Service for validating providers against Google Places/Business data."""
    
    def __init__(self):
        self.api_key = GOOGLE_PLACES_API_KEY
        self.timeout = REQUEST_TIMEOUT
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        
    async def validate_provider(self, provider: Provider) -> SourceValidation:
        """
        Validate a provider's business information using Google Places.
        
        Args:
            provider: Provider to validate
            
        Returns:
            SourceValidation with results
        """
        try:
            # Search for the practice
            place_data = await self._find_place(provider)
            
            if not place_data:
                return SourceValidation(
                    source=DataSource.GOOGLE_PLACES,
                    success=False,
                    confidence=50.0,  # Not found doesn't mean invalid
                    error_message=f"Practice '{provider.practice_name}' not found on Google"
                )
            
            # Get detailed place information
            details = await self._get_place_details(place_data.get("place_id"))
            
            if details:
                place_data.update(details)
            
            # Compare and find discrepancies
            discrepancies = self._compare_data(provider, place_data)
            
            # Calculate confidence based on matches
            confidence = self._calculate_confidence(provider, place_data, discrepancies)
            
            return SourceValidation(
                source=DataSource.GOOGLE_PLACES,
                success=True,
                confidence=confidence,
                data=place_data,
                discrepancies=discrepancies
            )
            
        except Exception as e:
            return SourceValidation(
                source=DataSource.GOOGLE_PLACES,
                success=False,
                confidence=0.0,
                error_message=str(e)
            )
    
    async def _find_place(self, provider: Provider) -> Optional[Dict[str, Any]]:
        """
        Search for a place on Google Maps.
        
        In production, this would call Google Places API.
        For demo, we simulate realistic responses.
        """
        # Simulate API call delay
        await asyncio.sleep(0.15)
        
        # For demo purposes, simulate Google Places response
        # In production:
        # query = f"{provider.practice_name} {provider.address.city} {provider.address.state}"
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"{self.base_url}/findplacefromtext/json",
        #         params={
        #             "input": query,
        #             "inputtype": "textquery",
        #             "key": self.api_key,
        #             "fields": "place_id,name,formatted_address,geometry"
        #         }
        #     )
        
        return self._generate_simulated_place(provider)
    
    async def _get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a place."""
        if not place_id:
            return None
            
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        # Simulated details
        return {
            "business_status": "OPERATIONAL",
            "rating": 4.5,
            "user_ratings_total": 127,
            "price_level": 2
        }
    
    def _generate_simulated_place(self, provider: Provider) -> Dict[str, Any]:
        """Generate simulated Google Places response for demo."""
        # Use provider ID to create deterministic but varied responses
        seed = hash(provider.id) % 1000
        
        # Simulate some variations (30% chance of different phone/address)
        phone_variation = seed % 10 < 3
        address_variation = seed % 10 < 2
        
        phone = provider.contact.phone
        if phone_variation:
            # Generate slightly different phone
            phone = f"({provider.address.state[:2]}5) 555-{seed:04d}"
        
        street = provider.address.street1
        if address_variation:
            street = f"{seed + 200} New Location Blvd"
        
        return {
            "place_id": f"ChIJ{provider.id[:20]}",
            "name": provider.practice_name,
            "formatted_address": f"{street}, {provider.address.city}, {provider.address.state} {provider.address.zip_code}",
            "formatted_phone_number": phone,
            "international_phone_number": f"+1 {phone}",
            "website": provider.contact.website or f"https://www.{provider.practice_name.lower().replace(' ', '')}.com",
            "opening_hours": {
                "open_now": True,
                "weekday_text": [
                    "Monday: 8:00 AM – 5:00 PM",
                    "Tuesday: 8:00 AM – 5:00 PM",
                    "Wednesday: 8:00 AM – 5:00 PM",
                    "Thursday: 8:00 AM – 5:00 PM",
                    "Friday: 8:00 AM – 4:00 PM",
                    "Saturday: Closed",
                    "Sunday: Closed"
                ]
            },
            "geometry": {
                "location": {
                    "lat": 42.3601 + (seed / 10000),
                    "lng": -71.0589 + (seed / 10000)
                }
            },
            "types": ["doctor", "health", "point_of_interest", "establishment"],
            "url": f"https://maps.google.com/?cid={seed}12345678901234"
        }
    
    def _compare_data(self, provider: Provider, place_data: Dict[str, Any]) -> List[Discrepancy]:
        """Compare provider data with Google Places data."""
        discrepancies = []
        
        # Check phone match
        google_phone = self._normalize_phone(place_data.get("formatted_phone_number", ""))
        provider_phone = self._normalize_phone(provider.contact.phone)
        
        if google_phone and google_phone != provider_phone:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.PHONE_MISMATCH,
                field_name="phone",
                current_value=provider.contact.phone,
                validated_value=place_data.get("formatted_phone_number", ""),
                source=DataSource.GOOGLE_PLACES,
                priority=Priority.MEDIUM,
                confidence=85.0
            ))
        
        # Check address match (simplified comparison)
        google_address = place_data.get("formatted_address", "").upper()
        provider_street = provider.address.street1.upper()
        
        if provider_street and provider_street not in google_address:
            # Potential address mismatch
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.ADDRESS_MISMATCH,
                field_name="street",
                current_value=provider.address.street1,
                validated_value=place_data.get("formatted_address", "").split(",")[0],
                source=DataSource.GOOGLE_PLACES,
                priority=Priority.MEDIUM,
                confidence=80.0
            ))
        
        # Check website match
        google_website = place_data.get("website", "").lower()
        provider_website = (provider.contact.website or "").lower()
        
        if google_website and provider_website and google_website != provider_website:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.WEBSITE_ISSUE,
                field_name="website",
                current_value=provider.contact.website or "",
                validated_value=place_data.get("website", ""),
                source=DataSource.GOOGLE_PLACES,
                priority=Priority.LOW,
                confidence=75.0
            ))
        
        # Check business status
        if place_data.get("business_status") == "CLOSED_PERMANENTLY":
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.STATUS_CHANGE,
                field_name="practice_status",
                current_value="Active",
                validated_value="Permanently Closed",
                source=DataSource.GOOGLE_PLACES,
                priority=Priority.HIGH,
                confidence=95.0
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
        place_data: Dict[str, Any],
        discrepancies: List[Discrepancy]
    ) -> float:
        """Calculate confidence score based on Google Places match."""
        base_confidence = 90.0  # Start slightly lower than NPI (less authoritative)
        
        # Deduct points for discrepancies
        for disc in discrepancies:
            if disc.priority == Priority.HIGH:
                base_confidence -= 25
            elif disc.priority == Priority.MEDIUM:
                base_confidence -= 12
            else:
                base_confidence -= 5
        
        # Bonus for verified data
        if place_data.get("business_status") == "OPERATIONAL":
            base_confidence += 5
        
        if place_data.get("user_ratings_total", 0) > 50:
            base_confidence += 3  # More reviews = more reliable
        
        return max(0.0, min(100.0, base_confidence))


# Singleton instance
google_places_service = GooglePlacesService()
