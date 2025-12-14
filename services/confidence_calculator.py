"""
Confidence Calculator Service - Calculates overall confidence scores for provider validation.
Implements weighted multi-source validation algorithm.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

from models import (
    Provider, SourceValidation, ValidationResult, ValidationStatus,
    DataSource, Discrepancy, Priority
)
from config import CONFIDENCE_THRESHOLDS, SOURCE_WEIGHTS


class ConfidenceCalculator:
    """
    Calculates confidence scores using weighted multi-source validation.
    
    Formula:
    confidence = Σ(source_reliability * source_confidence * data_freshness_factor)
    
    Where:
    - source_reliability: Weight assigned to each data source (NPI > Google > Website)
    - source_confidence: Confidence from individual source validation
    - data_freshness_factor: Bonus/penalty based on data age
    """
    
    def __init__(self):
        self.source_weights = SOURCE_WEIGHTS
        self.thresholds = CONFIDENCE_THRESHOLDS
        
    def calculate_overall_confidence(
        self, 
        source_validations: List[SourceValidation]
    ) -> float:
        """
        Calculate overall confidence score from multiple source validations.
        
        Args:
            source_validations: List of validation results from different sources
            
        Returns:
            Overall confidence score (0-100)
        """
        if not source_validations:
            return 0.0
        
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for validation in source_validations:
            weight = self.source_weights.get(validation.source.value, 0.1)
            
            if validation.success:
                # Apply freshness factor
                freshness = self._calculate_freshness_factor(validation.timestamp)
                adjusted_confidence = validation.confidence * freshness
                
                weighted_confidence += weight * adjusted_confidence
                total_weight += weight
            else:
                # Failed validation reduces confidence, but doesn't zero it
                weighted_confidence -= weight * 10  # Penalty for failed validation
        
        if total_weight == 0:
            return 0.0
        
        overall = weighted_confidence / total_weight
        return max(0.0, min(100.0, overall))
    
    def _calculate_freshness_factor(self, timestamp: datetime) -> float:
        """
        Calculate data freshness factor.
        
        More recent data gets higher weight.
        Data older than 30 days gets slight penalty.
        """
        age = datetime.now() - timestamp
        
        if age < timedelta(hours=24):
            return 1.05  # 5% bonus for very fresh data
        elif age < timedelta(days=7):
            return 1.02  # 2% bonus for recent data
        elif age < timedelta(days=30):
            return 1.0   # No adjustment
        elif age < timedelta(days=90):
            return 0.95  # 5% penalty
        else:
            return 0.90  # 10% penalty for old data
    
    def determine_validation_status(self, confidence: float) -> ValidationStatus:
        """
        Determine validation status based on confidence score.
        
        Returns:
            ValidationStatus enum value
        """
        if confidence >= self.thresholds["auto_update"]:
            return ValidationStatus.VALIDATED
        elif confidence >= self.thresholds["needs_review"]:
            return ValidationStatus.NEEDS_REVIEW
        else:
            return ValidationStatus.URGENT
    
    def calculate_discrepancy_impact(
        self, 
        discrepancies: List[Discrepancy]
    ) -> Dict[str, Any]:
        """
        Calculate the impact of discrepancies on overall confidence.
        
        Returns:
            Dictionary with impact analysis
        """
        if not discrepancies:
            return {
                "total_impact": 0,
                "high_priority_count": 0,
                "medium_priority_count": 0,
                "low_priority_count": 0,
                "impact_breakdown": {}
            }
        
        impact_breakdown = {}
        total_impact = 0
        priority_counts = {Priority.HIGH: 0, Priority.MEDIUM: 0, Priority.LOW: 0}
        
        impact_values = {
            Priority.HIGH: 20,
            Priority.MEDIUM: 10,
            Priority.LOW: 5
        }
        
        for disc in discrepancies:
            impact = impact_values[disc.priority]
            total_impact += impact
            priority_counts[disc.priority] += 1
            
            disc_type = disc.type.value
            if disc_type not in impact_breakdown:
                impact_breakdown[disc_type] = {"count": 0, "total_impact": 0}
            impact_breakdown[disc_type]["count"] += 1
            impact_breakdown[disc_type]["total_impact"] += impact
        
        return {
            "total_impact": total_impact,
            "high_priority_count": priority_counts[Priority.HIGH],
            "medium_priority_count": priority_counts[Priority.MEDIUM],
            "low_priority_count": priority_counts[Priority.LOW],
            "impact_breakdown": impact_breakdown
        }
    
    def calculate_source_agreement(
        self, 
        source_validations: List[SourceValidation],
        field_name: str
    ) -> Dict[str, Any]:
        """
        Calculate how well different sources agree on a specific field.
        
        Args:
            source_validations: List of source validations
            field_name: Field to check agreement on
            
        Returns:
            Agreement analysis
        """
        values = []
        sources = []
        
        for validation in source_validations:
            if validation.success and field_name in validation.data:
                values.append(str(validation.data[field_name]).lower())
                sources.append(validation.source.value)
        
        if not values:
            return {
                "field": field_name,
                "sources_checked": 0,
                "agreement_rate": 0.0,
                "values": {}
            }
        
        # Count unique values
        value_counts = {}
        for i, val in enumerate(values):
            if val not in value_counts:
                value_counts[val] = {"count": 0, "sources": []}
            value_counts[val]["count"] += 1
            value_counts[val]["sources"].append(sources[i])
        
        # Calculate agreement (percentage of sources agreeing on most common value)
        max_count = max(v["count"] for v in value_counts.values())
        agreement_rate = max_count / len(values) * 100
        
        return {
            "field": field_name,
            "sources_checked": len(values),
            "agreement_rate": agreement_rate,
            "values": value_counts,
            "consensus_reached": agreement_rate >= 66.7  # 2/3 majority
        }
    
    def generate_confidence_breakdown(
        self,
        source_validations: List[SourceValidation]
    ) -> Dict[str, Any]:
        """
        Generate detailed breakdown of confidence calculation.
        
        Useful for explaining to users why a certain score was assigned.
        """
        breakdown = {
            "sources": [],
            "weights_applied": {},
            "adjustments": [],
            "final_score": 0.0
        }
        
        for validation in source_validations:
            source_name = validation.source.value
            weight = self.source_weights.get(source_name, 0.1)
            freshness = self._calculate_freshness_factor(validation.timestamp)
            
            source_detail = {
                "source": source_name,
                "raw_confidence": validation.confidence,
                "weight": weight,
                "freshness_factor": freshness,
                "success": validation.success,
                "discrepancies_found": len(validation.discrepancies),
                "contribution": weight * validation.confidence * freshness if validation.success else 0
            }
            breakdown["sources"].append(source_detail)
            breakdown["weights_applied"][source_name] = weight
        
        breakdown["final_score"] = self.calculate_overall_confidence(source_validations)
        
        return breakdown
    
    def should_auto_update(
        self, 
        confidence: float,
        discrepancies: List[Discrepancy]
    ) -> bool:
        """
        Determine if provider data should be auto-updated.
        
        Rules:
        1. Confidence must be >= 80%
        2. No HIGH priority discrepancies
        3. All discrepancies must have confidence >= 75%
        """
        if confidence < self.thresholds["auto_update"]:
            return False
        
        # Check for high priority discrepancies
        high_priority = [d for d in discrepancies if d.priority == Priority.HIGH]
        if high_priority:
            return False
        
        # Check individual discrepancy confidence
        low_confidence_discs = [d for d in discrepancies if d.confidence < 75]
        if low_confidence_discs:
            return False
        
        return True
    
    def needs_urgent_review(
        self, 
        confidence: float,
        discrepancies: List[Discrepancy]
    ) -> bool:
        """
        Determine if provider needs urgent human review.
        
        Criteria:
        1. Confidence < 60%
        2. OR has license issues
        3. OR has NPI issues
        4. OR has multiple HIGH priority discrepancies
        """
        if confidence < self.thresholds["needs_review"]:
            return True
        
        # Check for critical discrepancy types
        critical_types = ["license_issue", "npi_invalid", "status_change"]
        for disc in discrepancies:
            if disc.type.value in critical_types:
                return True
        
        # Check for multiple high priority issues
        high_priority = [d for d in discrepancies if d.priority == Priority.HIGH]
        if len(high_priority) >= 2:
            return True
        
        return False
    
    def calculate_validation_result(
        self,
        provider: Provider,
        source_validations: List[SourceValidation],
        processing_time_ms: float = 0.0
    ) -> ValidationResult:
        """
        Create complete validation result from source validations.
        """
        # Gather all discrepancies
        all_discrepancies = []
        for sv in source_validations:
            all_discrepancies.extend(sv.discrepancies)
        
        # Calculate overall confidence
        overall_confidence = self.calculate_overall_confidence(source_validations)
        
        # Determine status
        status = self.determine_validation_status(overall_confidence)
        
        # Determine actions
        auto_updated = self.should_auto_update(overall_confidence, all_discrepancies)
        urgent_review = self.needs_urgent_review(overall_confidence, all_discrepancies)
        needs_review = not auto_updated and not urgent_review
        
        # Generate summary
        summary = self._generate_summary(
            provider, overall_confidence, all_discrepancies, 
            auto_updated, needs_review, urgent_review
        )
        
        return ValidationResult(
            provider_id=provider.id,
            status=status,
            overall_confidence=overall_confidence,
            source_validations=source_validations,
            discrepancies=all_discrepancies,
            total_discrepancies=len(all_discrepancies),
            auto_updated=auto_updated,
            needs_review=needs_review,
            urgent_review=urgent_review,
            processing_time_ms=processing_time_ms,
            summary=summary
        )
    
    def _generate_summary(
        self,
        provider: Provider,
        confidence: float,
        discrepancies: List[Discrepancy],
        auto_updated: bool,
        needs_review: bool,
        urgent_review: bool
    ) -> str:
        """Generate human-readable summary of validation."""
        parts = []
        
        parts.append(f"Provider {provider.full_name()} ({provider.npi})")
        parts.append(f"Confidence: {confidence:.1f}%")
        
        if auto_updated:
            parts.append("Status: Auto-updated ✓")
        elif urgent_review:
            parts.append("Status: URGENT REVIEW REQUIRED ✗")
        else:
            parts.append("Status: Needs Review ⚠")
        
        if discrepancies:
            disc_types = set(d.type.value for d in discrepancies)
            parts.append(f"Issues: {', '.join(disc_types)}")
        else:
            parts.append("No discrepancies found")
        
        return " | ".join(parts)


# Singleton instance
confidence_calculator = ConfidenceCalculator()
