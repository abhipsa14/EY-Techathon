"""
Data Validation Agent - Validates provider data against multiple external sources.
This is the first agent in the pipeline that gathers data from all sources.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from models import (
    Provider, SourceValidation, DataSource, ValidationResult,
    Discrepancy, ValidationStatus
)
from services.npi_service import npi_service
from services.google_places_service import google_places_service
from services.web_scraper_service import web_scraper_service
from services.pdf_processor_service import pdf_processor_service
from config import BATCH_SIZE, MAX_CONCURRENT_REQUESTS


class DataValidationAgent:
    """
    Agent responsible for validating provider data against multiple sources.
    
    Capabilities:
    - Validates against NPI Registry (structured API)
    - Validates against Google Places (structured API)
    - Scrapes practice websites (semi-structured)
    - Processes PDF documents (unstructured)
    
    The agent runs validations in parallel for efficiency while
    respecting rate limits on external APIs.
    """
    
    def __init__(self):
        self.name = "Data Validation Agent"
        self.npi_service = npi_service
        self.google_service = google_places_service
        self.web_scraper = web_scraper_service
        self.pdf_processor = pdf_processor_service
        
        # Track validation statistics
        self.stats = {
            "total_validated": 0,
            "successful": 0,
            "failed": 0,
            "total_time_ms": 0
        }
    
    async def validate_provider(
        self, 
        provider: Provider,
        sources: Optional[List[DataSource]] = None
    ) -> Dict[str, SourceValidation]:
        """
        Validate a single provider against specified sources.
        
        Args:
            provider: Provider to validate
            sources: List of sources to check (default: all available)
            
        Returns:
            Dictionary mapping source names to validation results
        """
        start_time = time.time()
        
        if sources is None:
            sources = [
                DataSource.NPI_REGISTRY,
                DataSource.GOOGLE_PLACES,
                DataSource.PRACTICE_WEBSITE
            ]
        
        results = {}
        tasks = []
        source_names = []
        
        # Create validation tasks for each source
        for source in sources:
            if source == DataSource.NPI_REGISTRY:
                tasks.append(self.npi_service.validate_provider(provider))
                source_names.append(DataSource.NPI_REGISTRY.value)
                
            elif source == DataSource.GOOGLE_PLACES:
                tasks.append(self.google_service.validate_provider(provider))
                source_names.append(DataSource.GOOGLE_PLACES.value)
                
            elif source == DataSource.PRACTICE_WEBSITE:
                tasks.append(self.web_scraper.validate_provider(provider))
                source_names.append(DataSource.PRACTICE_WEBSITE.value)
        
        # Run all validations in parallel
        validation_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(validation_results):
            source_name = source_names[i]
            
            if isinstance(result, Exception):
                results[source_name] = SourceValidation(
                    source=DataSource(source_name),
                    success=False,
                    confidence=0.0,
                    error_message=str(result)
                )
            else:
                results[source_name] = result
        
        # Update statistics
        elapsed_ms = (time.time() - start_time) * 1000
        self.stats["total_validated"] += 1
        self.stats["total_time_ms"] += elapsed_ms
        
        if all(r.success for r in results.values()):
            self.stats["successful"] += 1
        else:
            self.stats["failed"] += 1
        
        return results
    
    async def validate_batch(
        self, 
        providers: List[Provider],
        sources: Optional[List[DataSource]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Dict[str, SourceValidation]]:
        """
        Validate multiple providers efficiently.
        
        Args:
            providers: List of providers to validate
            sources: Sources to check for each provider
            progress_callback: Optional callback(current, total) for progress updates
            
        Returns:
            Dictionary mapping provider IDs to their validation results
        """
        all_results = {}
        total = len(providers)
        
        # Process in batches to manage memory and rate limits
        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch = providers[batch_start:batch_end]
            
            # Validate batch concurrently
            tasks = [self.validate_provider(p, sources) for p in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Store results
            for i, result in enumerate(batch_results):
                provider = batch[i]
                if isinstance(result, Exception):
                    all_results[provider.id] = {
                        "error": SourceValidation(
                            source=DataSource.NPI_REGISTRY,
                            success=False,
                            confidence=0.0,
                            error_message=str(result)
                        )
                    }
                else:
                    all_results[provider.id] = result
            
            # Report progress
            if progress_callback:
                progress_callback(batch_end, total)
            
            # Small delay between batches for rate limiting
            if batch_end < total:
                await asyncio.sleep(0.1)
        
        return all_results
    
    async def validate_with_pdf(
        self, 
        provider: Provider,
        pdf_path: str
    ) -> Dict[str, SourceValidation]:
        """
        Validate a provider including PDF document processing.
        
        Args:
            provider: Provider to validate
            pdf_path: Path to PDF document to process
            
        Returns:
            Validation results including PDF data
        """
        # Get standard validations
        results = await self.validate_provider(provider)
        
        # Add PDF validation
        pdf_result = await self.pdf_processor.process_document(pdf_path, provider)
        results[DataSource.PDF_DOCUMENT.value] = pdf_result
        
        return results
    
    def get_all_discrepancies(
        self, 
        validation_results: Dict[str, SourceValidation]
    ) -> List[Discrepancy]:
        """
        Extract all discrepancies from validation results.
        """
        discrepancies = []
        for source_name, result in validation_results.items():
            if result.success:
                discrepancies.extend(result.discrepancies)
        return discrepancies
    
    def get_source_summary(
        self, 
        validation_results: Dict[str, SourceValidation]
    ) -> Dict[str, Any]:
        """
        Generate a summary of validation results by source.
        """
        summary = {
            "sources_checked": len(validation_results),
            "sources_successful": 0,
            "sources_failed": 0,
            "total_discrepancies": 0,
            "by_source": {}
        }
        
        for source_name, result in validation_results.items():
            if result.success:
                summary["sources_successful"] += 1
            else:
                summary["sources_failed"] += 1
            
            summary["total_discrepancies"] += len(result.discrepancies)
            
            summary["by_source"][source_name] = {
                "success": result.success,
                "confidence": result.confidence,
                "discrepancies": len(result.discrepancies),
                "error": result.error_message if not result.success else None
            }
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        avg_time = 0
        if self.stats["total_validated"] > 0:
            avg_time = self.stats["total_time_ms"] / self.stats["total_validated"]
        
        return {
            **self.stats,
            "average_time_ms": avg_time,
            "success_rate": (
                self.stats["successful"] / self.stats["total_validated"] * 100
                if self.stats["total_validated"] > 0 else 0
            )
        }
    
    def reset_stats(self):
        """Reset agent statistics."""
        self.stats = {
            "total_validated": 0,
            "successful": 0,
            "failed": 0,
            "total_time_ms": 0
        }


# Singleton instance
data_validation_agent = DataValidationAgent()
