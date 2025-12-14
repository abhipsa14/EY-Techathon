"""
NPI Registry Service - Validates providers against the National Provider Identifier Registry.
This is the most authoritative data source (government database).
"""

import asyncio
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
import re

from models import (
    Provider, SourceValidation, DataSource, Discrepancy,
    DiscrepancyType, Priority
)
from config import NPI_REGISTRY_BASE_URL, REQUEST_TIMEOUT


class NPIRegistryService:
    """Service for validating providers against NPI Registry."""
    
    def __init__(self):
        self.base_url = NPI_REGISTRY_BASE_URL
        self.timeout = REQUEST_TIMEOUT
        
    async def validate_provider(self, provider: Provider) -> SourceValidation:
        """
        Validate a provider against the NPI Registry.
        
        Args:
            provider: Provider to validate
            
        Returns:
            SourceValidation with results
        """
        try:
            # Query NPI Registry
            npi_data = await self._query_npi(provider.npi)
            
            if not npi_data:
                return SourceValidation(
                    source=DataSource.NPI_REGISTRY,
                    success=False,
                    confidence=0.0,
                    error_message=f"NPI {provider.npi} not found in registry"
                )
            
            # Compare and find discrepancies
            discrepancies = self._compare_data(provider, npi_data)
            
            # Calculate confidence based on matches
            confidence = self._calculate_confidence(provider, npi_data, discrepancies)
            
            return SourceValidation(
                source=DataSource.NPI_REGISTRY,
                success=True,
                confidence=confidence,
                data=npi_data,
                discrepancies=discrepancies
            )
            
        except Exception as e:
            return SourceValidation(
                source=DataSource.NPI_REGISTRY,
                success=False,
                confidence=0.0,
                error_message=str(e)
            )
    
    async def _query_npi(self, npi: str) -> Optional[Dict[str, Any]]:
        """
        Query the NPI Registry API.
        
        In production, this would call the actual CMS NPI Registry API.
        For demo, we simulate realistic responses.
        """
        # Simulate API call delay
        await asyncio.sleep(0.1)
        
        # Validate NPI format (10 digits)
        if not self._is_valid_npi_format(npi):
            return None
        
        # For demo purposes, simulate NPI Registry response
        # In production, this would be: 
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"{self.base_url}?number={npi}&version=2.1"
        #     )
        #     return response.json()
        
        # Simulated response structure (matches real NPI Registry format)
        return self._generate_simulated_response(npi)
    
    def _is_valid_npi_format(self, npi: str) -> bool:
        """Check if NPI has valid format (10 digits, Luhn check)."""
        if not npi or len(npi) != 10 or not npi.isdigit():
            return False
        
        # Luhn algorithm check (NPI uses modified Luhn with prefix 80840)
        # Simplified for demo
        return True
    
    def _generate_simulated_response(self, npi: str) -> Dict[str, Any]:
        """Generate simulated NPI Registry response for demo."""
        # Use NPI to create deterministic but varied responses
        seed = int(npi) % 1000
        
        return {
            "result_count": 1,
            "results": [{
                "enumeration_type": "NPI-1",  # Individual
                "number": npi,
                "basic": {
                    "first_name": f"Provider{seed}",
                    "last_name": f"Name{seed}",
                    "credential": "MD",
                    "status": "A",  # Active
                    "enumeration_date": "2015-01-15"
                },
                "addresses": [{
                    "address_purpose": "LOCATION",
                    "address_1": f"{100 + seed} Medical Center Dr",
                    "city": "Boston",
                    "state": "MA",
                    "postal_code": "02115",
                    "telephone_number": f"617-555-{seed:04d}"
                }],
                "taxonomies": [{
                    "code": "207R00000X",
                    "desc": "Internal Medicine",
                    "primary": True,
                    "state": "MA",
                    "license": f"MA{seed:06d}"
                }]
            }]
        }
    
    def _compare_data(self, provider: Provider, npi_data: Dict[str, Any]) -> list[Discrepancy]:
        """Compare provider data with NPI Registry data and find discrepancies."""
        discrepancies = []
        
        if not npi_data.get("results"):
            return discrepancies
        
        result = npi_data["results"][0]
        basic = result.get("basic", {})
        addresses = result.get("addresses", [])
        taxonomies = result.get("taxonomies", [])
        
        # Get location address
        location_addr = next(
            (a for a in addresses if a.get("address_purpose") == "LOCATION"),
            addresses[0] if addresses else {}
        )
        
        # Check name match
        npi_first = basic.get("first_name", "").upper()
        npi_last = basic.get("last_name", "").upper()
        
        if npi_first and provider.first_name.upper() != npi_first:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.NAME_MISMATCH,
                field_name="first_name",
                current_value=provider.first_name,
                validated_value=basic.get("first_name", ""),
                source=DataSource.NPI_REGISTRY,
                priority=Priority.MEDIUM,
                confidence=95.0
            ))
        
        if npi_last and provider.last_name.upper() != npi_last:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.NAME_MISMATCH,
                field_name="last_name",
                current_value=provider.last_name,
                validated_value=basic.get("last_name", ""),
                source=DataSource.NPI_REGISTRY,
                priority=Priority.MEDIUM,
                confidence=95.0
            ))
        
        # Check phone match
        npi_phone = self._normalize_phone(location_addr.get("telephone_number", ""))
        provider_phone = self._normalize_phone(provider.contact.phone)
        
        if npi_phone and npi_phone != provider_phone:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.PHONE_MISMATCH,
                field_name="phone",
                current_value=provider.contact.phone,
                validated_value=location_addr.get("telephone_number", ""),
                source=DataSource.NPI_REGISTRY,
                priority=Priority.MEDIUM,
                confidence=90.0
            ))
        
        # Check address match
        npi_street = location_addr.get("address_1", "").upper()
        npi_city = location_addr.get("city", "").upper()
        npi_state = location_addr.get("state", "").upper()
        
        if npi_city and provider.address.city.upper() != npi_city:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.ADDRESS_MISMATCH,
                field_name="city",
                current_value=provider.address.city,
                validated_value=location_addr.get("city", ""),
                source=DataSource.NPI_REGISTRY,
                priority=Priority.MEDIUM,
                confidence=90.0
            ))
        
        if npi_state and provider.address.state.upper() != npi_state:
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.ADDRESS_MISMATCH,
                field_name="state",
                current_value=provider.address.state,
                validated_value=location_addr.get("state", ""),
                source=DataSource.NPI_REGISTRY,
                priority=Priority.HIGH,
                confidence=95.0
            ))
        
        # Check license status
        if basic.get("status") == "D":  # Deactivated
            discrepancies.append(Discrepancy(
                provider_id=provider.id,
                type=DiscrepancyType.LICENSE_ISSUE,
                field_name="npi_status",
                current_value="Active",
                validated_value="Deactivated",
                source=DataSource.NPI_REGISTRY,
                priority=Priority.HIGH,
                confidence=100.0
            ))
        
        return discrepancies
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison."""
        if not phone:
            return ""
        return re.sub(r'\D', '', phone)[-10:]  # Last 10 digits
    
    def _calculate_confidence(
        self, 
        provider: Provider, 
        npi_data: Dict[str, Any],
        discrepancies: list[Discrepancy]
    ) -> float:
        """Calculate confidence score based on NPI data match."""
        base_confidence = 100.0
        
        # Deduct points for each discrepancy
        for disc in discrepancies:
            if disc.priority == Priority.HIGH:
                base_confidence -= 20
            elif disc.priority == Priority.MEDIUM:
                base_confidence -= 10
            else:
                base_confidence -= 5
        
        return max(0.0, min(100.0, base_confidence))


# Singleton instance
npi_service = NPIRegistryService()
