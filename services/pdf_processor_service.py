"""
PDF Processor Service - Extracts provider information from PDF documents.
Handles scanned documents, credentials, and license certificates.
"""

import asyncio
import io
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from models import (
    Provider, SourceValidation, DataSource, Discrepancy,
    DiscrepancyType, Priority
)
from config import DATA_DIR


class PDFProcessorService:
    """Service for processing and extracting data from PDF documents."""
    
    def __init__(self):
        self.supported_formats = [".pdf", ".PDF"]
        
    async def process_document(
        self, 
        file_path: str, 
        provider: Optional[Provider] = None
    ) -> SourceValidation:
        """
        Process a PDF document and extract provider information.
        
        Args:
            file_path: Path to the PDF file
            provider: Optional provider to validate against
            
        Returns:
            SourceValidation with extracted data
        """
        try:
            # Simulate PDF processing
            extracted_data = await self._extract_pdf_data(file_path)
            
            if not extracted_data:
                return SourceValidation(
                    source=DataSource.PDF_DOCUMENT,
                    success=False,
                    confidence=0.0,
                    error_message="Failed to extract data from PDF"
                )
            
            # If provider is provided, compare data
            discrepancies = []
            if provider:
                discrepancies = self._compare_data(provider, extracted_data)
            
            confidence = self._calculate_confidence(extracted_data, discrepancies)
            
            return SourceValidation(
                source=DataSource.PDF_DOCUMENT,
                success=True,
                confidence=confidence,
                data=extracted_data,
                discrepancies=discrepancies
            )
            
        except Exception as e:
            return SourceValidation(
                source=DataSource.PDF_DOCUMENT,
                success=False,
                confidence=0.0,
                error_message=str(e)
            )
    
    async def _extract_pdf_data(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract data from PDF file.
        
        In production, this would use PyPDF2, pdfplumber, or pytesseract for OCR.
        For demo, we simulate extraction results.
        """
        # Simulate processing delay
        await asyncio.sleep(0.3)
        
        # In production:
        # import pdfplumber
        # with pdfplumber.open(file_path) as pdf:
        #     text = ""
        #     for page in pdf.pages:
        #         text += page.extract_text() or ""
        #     return self._parse_extracted_text(text)
        
        # Simulated extraction
        return self._generate_simulated_extraction(file_path)
    
    def _generate_simulated_extraction(self, file_path: str) -> Dict[str, Any]:
        """Generate simulated PDF extraction results for demo."""
        seed = hash(file_path) % 1000
        
        # Simulate different document types
        doc_types = ["license", "credential", "insurance_form", "application"]
        doc_type = doc_types[seed % len(doc_types)]
        
        base_data = {
            "document_type": doc_type,
            "extraction_quality": 0.85 + (seed % 15) / 100,  # 85-99%
            "pages_processed": 1 + seed % 5,
            "extracted_at": datetime.now().isoformat(),
            "raw_text_length": 1000 + seed * 10
        }
        
        if doc_type == "license":
            base_data.update({
                "license_number": f"MA{seed:06d}",
                "license_state": "MA",
                "issue_date": "2020-01-15",
                "expiration_date": "2025-01-15",
                "status": "Active",
                "holder_name": f"Provider{seed} Name{seed}, MD"
            })
        elif doc_type == "credential":
            base_data.update({
                "credential_type": "Board Certification",
                "specialty": "Internal Medicine",
                "board": "American Board of Internal Medicine",
                "certification_date": "2018-06-20",
                "holder_name": f"Provider{seed} Name{seed}, MD"
            })
        elif doc_type == "insurance_form":
            base_data.update({
                "npi": f"1{seed:09d}",
                "tax_id": f"XX-{seed:07d}",
                "practice_name": f"Medical Practice {seed}",
                "address": f"{seed} Medical Center Dr, Boston, MA 02115",
                "phone": f"(617) 555-{seed:04d}"
            })
        else:  # application
            base_data.update({
                "applicant_name": f"Dr. Provider{seed} Name{seed}",
                "application_type": "New Provider Enrollment",
                "submitted_date": "2024-01-10",
                "status": "Pending Review"
            })
        
        return base_data
    
    def _parse_extracted_text(self, text: str) -> Dict[str, Any]:
        """Parse extracted text to find structured data."""
        data = {
            "raw_text": text[:500],  # First 500 chars for reference
            "extraction_quality": 0.0,
        }
        
        # Extract NPI (10 digit number)
        npi_match = re.search(r'\b\d{10}\b', text)
        if npi_match:
            data["npi"] = npi_match.group()
        
        # Extract license number patterns
        license_match = re.search(r'License\s*#?\s*:?\s*([A-Z]{2}\d{6,8})', text, re.IGNORECASE)
        if license_match:
            data["license_number"] = license_match.group(1)
        
        # Extract phone numbers
        phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone_matches:
            data["phones"] = list(set(phone_matches))
        
        # Extract email addresses
        email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_matches:
            data["emails"] = list(set(email_matches))
        
        # Extract dates
        date_matches = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
        if date_matches:
            data["dates_found"] = date_matches[:5]  # First 5 dates
        
        # Calculate extraction quality based on found elements
        found_elements = sum([
            bool(data.get("npi")),
            bool(data.get("license_number")),
            bool(data.get("phones")),
            bool(data.get("emails")),
            bool(data.get("dates_found"))
        ])
        data["extraction_quality"] = found_elements / 5.0
        
        return data
    
    def _compare_data(self, provider: Provider, extracted_data: Dict[str, Any]) -> List[Discrepancy]:
        """Compare provider data with extracted PDF data."""
        discrepancies = []
        
        # Check NPI match
        if extracted_data.get("npi"):
            if extracted_data["npi"] != provider.npi:
                discrepancies.append(Discrepancy(
                    provider_id=provider.id,
                    type=DiscrepancyType.NPI_INVALID,
                    field_name="npi",
                    current_value=provider.npi,
                    validated_value=extracted_data["npi"],
                    source=DataSource.PDF_DOCUMENT,
                    priority=Priority.HIGH,
                    confidence=70.0  # Lower confidence for PDF data
                ))
        
        # Check license number match
        if extracted_data.get("license_number") and provider.license_number:
            if extracted_data["license_number"] != provider.license_number:
                discrepancies.append(Discrepancy(
                    provider_id=provider.id,
                    type=DiscrepancyType.LICENSE_ISSUE,
                    field_name="license_number",
                    current_value=provider.license_number,
                    validated_value=extracted_data["license_number"],
                    source=DataSource.PDF_DOCUMENT,
                    priority=Priority.MEDIUM,
                    confidence=65.0
                ))
        
        # Check license expiration
        if extracted_data.get("expiration_date"):
            try:
                exp_date = datetime.strptime(extracted_data["expiration_date"], "%Y-%m-%d")
                if exp_date < datetime.now():
                    discrepancies.append(Discrepancy(
                        provider_id=provider.id,
                        type=DiscrepancyType.LICENSE_ISSUE,
                        field_name="license_status",
                        current_value="Active",
                        validated_value="Expired",
                        source=DataSource.PDF_DOCUMENT,
                        priority=Priority.HIGH,
                        confidence=80.0
                    ))
            except ValueError:
                pass
        
        return discrepancies
    
    def _calculate_confidence(
        self, 
        extracted_data: Dict[str, Any],
        discrepancies: List[Discrepancy]
    ) -> float:
        """Calculate confidence score for PDF extraction."""
        # Base confidence from extraction quality
        extraction_quality = extracted_data.get("extraction_quality", 0.5)
        base_confidence = extraction_quality * 80  # Max 80% from extraction
        
        # Deduct for discrepancies
        for disc in discrepancies:
            if disc.priority == Priority.HIGH:
                base_confidence -= 15
            elif disc.priority == Priority.MEDIUM:
                base_confidence -= 8
            else:
                base_confidence -= 3
        
        return max(0.0, min(100.0, base_confidence))
    
    async def batch_process(
        self, 
        file_paths: List[str],
        providers: Optional[List[Provider]] = None
    ) -> List[SourceValidation]:
        """Process multiple PDF documents."""
        if providers and len(providers) != len(file_paths):
            raise ValueError("Number of providers must match number of files")
        
        tasks = []
        for i, path in enumerate(file_paths):
            provider = providers[i] if providers else None
            tasks.append(self.process_document(path, provider))
        
        return await asyncio.gather(*tasks)
    
    def get_document_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic information about a PDF document without full processing."""
        path = Path(file_path)
        
        if not path.exists():
            return {"error": "File not found"}
        
        if path.suffix.lower() not in self.supported_formats:
            return {"error": f"Unsupported format: {path.suffix}"}
        
        return {
            "file_name": path.name,
            "file_size_bytes": path.stat().st_size,
            "file_size_kb": round(path.stat().st_size / 1024, 2),
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "format": path.suffix.lower()
        }


# Singleton instance
pdf_processor_service = PDFProcessorService()
