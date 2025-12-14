"""
Quality Assurance Agent - Analyzes validation results and calculates confidence scores.
Flags discrepancies and prioritizes issues for review.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from models import (
    Provider, SourceValidation, ValidationResult, Discrepancy,
    ValidationStatus, Priority, DataSource
)
from services.confidence_calculator import confidence_calculator
from config import CONFIDENCE_THRESHOLDS


class QualityAssuranceAgent:
    """
    Agent responsible for quality assurance of validation results.
    
    Capabilities:
    - Calculates confidence scores from multiple sources
    - Identifies and prioritizes discrepancies
    - Determines validation status
    - Flags providers for appropriate action
    - Generates quality metrics and insights
    
    This agent acts as the decision maker, determining what action
    should be taken for each provider based on validation results.
    """
    
    def __init__(self):
        self.name = "Quality Assurance Agent"
        self.calculator = confidence_calculator
        
        # Quality thresholds
        self.thresholds = CONFIDENCE_THRESHOLDS
        
        # Statistics
        self.stats = {
            "providers_assessed": 0,
            "auto_approved": 0,
            "flagged_for_review": 0,
            "flagged_urgent": 0,
            "average_confidence": 0.0,
            "total_discrepancies": 0
        }
    
    async def assess_provider(
        self, 
        provider: Provider,
        source_validations: Dict[str, SourceValidation]
    ) -> ValidationResult:
        """
        Perform quality assessment on provider validation results.
        
        Args:
            provider: The provider being validated
            source_validations: Results from different validation sources
            
        Returns:
            Complete ValidationResult with confidence score and status
        """
        start_time = datetime.now()
        
        # Convert dict to list of SourceValidations
        validations = list(source_validations.values())
        
        # Calculate overall confidence
        overall_confidence = self.calculator.calculate_overall_confidence(validations)
        
        # Gather all discrepancies
        all_discrepancies = []
        for validation in validations:
            all_discrepancies.extend(validation.discrepancies)
        
        # Prioritize discrepancies
        prioritized_discrepancies = self._prioritize_discrepancies(all_discrepancies)
        
        # Determine status
        status = self.calculator.determine_validation_status(overall_confidence)
        
        # Determine actions
        should_auto_update = self.calculator.should_auto_update(
            overall_confidence, prioritized_discrepancies
        )
        needs_urgent = self.calculator.needs_urgent_review(
            overall_confidence, prioritized_discrepancies
        )
        needs_review = not should_auto_update and not needs_urgent
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Generate summary
        summary = self._generate_assessment_summary(
            provider, overall_confidence, prioritized_discrepancies,
            should_auto_update, needs_review, needs_urgent
        )
        
        # Update statistics
        self._update_stats(overall_confidence, prioritized_discrepancies,
                          should_auto_update, needs_review, needs_urgent)
        
        return ValidationResult(
            provider_id=provider.id,
            status=status,
            overall_confidence=overall_confidence,
            source_validations=validations,
            discrepancies=prioritized_discrepancies,
            total_discrepancies=len(prioritized_discrepancies),
            auto_updated=should_auto_update,
            needs_review=needs_review,
            urgent_review=needs_urgent,
            processing_time_ms=processing_time,
            summary=summary
        )
    
    async def assess_batch(
        self,
        providers: List[Provider],
        validation_results: Dict[str, Dict[str, SourceValidation]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, ValidationResult]:
        """
        Assess multiple providers efficiently.
        
        Args:
            providers: List of providers to assess
            validation_results: Validation results keyed by provider ID
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary mapping provider IDs to ValidationResults
        """
        assessments = {}
        total = len(providers)
        
        for i, provider in enumerate(providers):
            source_validations = validation_results.get(provider.id, {})
            result = await self.assess_provider(provider, source_validations)
            assessments[provider.id] = result
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return assessments
    
    def _prioritize_discrepancies(
        self, 
        discrepancies: List[Discrepancy]
    ) -> List[Discrepancy]:
        """
        Prioritize and deduplicate discrepancies.
        
        Higher priority issues come first. Duplicate issues (same field, same type)
        are consolidated, keeping the one with highest confidence.
        """
        # Deduplicate by field and type, keeping highest confidence
        deduped = {}
        for disc in discrepancies:
            key = f"{disc.field_name}_{disc.type.value}"
            if key not in deduped or disc.confidence > deduped[key].confidence:
                deduped[key] = disc
        
        # Sort by priority (HIGH first) then by confidence (highest first)
        priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        sorted_discs = sorted(
            deduped.values(),
            key=lambda d: (priority_order[d.priority], -d.confidence)
        )
        
        return sorted_discs
    
    def _generate_assessment_summary(
        self,
        provider: Provider,
        confidence: float,
        discrepancies: List[Discrepancy],
        auto_updated: bool,
        needs_review: bool,
        urgent_review: bool
    ) -> str:
        """Generate human-readable assessment summary."""
        parts = [f"Provider: {provider.full_name()} (NPI: {provider.npi})"]
        parts.append(f"Confidence: {confidence:.1f}%")
        
        if auto_updated:
            parts.append("Decision: ✓ AUTO-APPROVED for update")
        elif urgent_review:
            parts.append("Decision: ✗ URGENT REVIEW REQUIRED")
        else:
            parts.append("Decision: ⚠ Needs manual review")
        
        if discrepancies:
            disc_summary = []
            for disc in discrepancies[:3]:  # Top 3 issues
                disc_summary.append(
                    f"- {disc.type.value}: {disc.field_name} "
                    f"('{disc.current_value}' → '{disc.validated_value}')"
                )
            parts.append("Issues Found:\n" + "\n".join(disc_summary))
            
            if len(discrepancies) > 3:
                parts.append(f"... and {len(discrepancies) - 3} more issues")
        else:
            parts.append("No discrepancies detected")
        
        return "\n".join(parts)
    
    def _update_stats(
        self,
        confidence: float,
        discrepancies: List[Discrepancy],
        auto_updated: bool,
        needs_review: bool,
        urgent_review: bool
    ):
        """Update agent statistics."""
        self.stats["providers_assessed"] += 1
        self.stats["total_discrepancies"] += len(discrepancies)
        
        if auto_updated:
            self.stats["auto_approved"] += 1
        elif urgent_review:
            self.stats["flagged_urgent"] += 1
        else:
            self.stats["flagged_for_review"] += 1
        
        # Update running average confidence
        n = self.stats["providers_assessed"]
        prev_avg = self.stats["average_confidence"]
        self.stats["average_confidence"] = prev_avg + (confidence - prev_avg) / n
    
    def analyze_quality_trends(
        self,
        validation_results: Dict[str, ValidationResult]
    ) -> Dict[str, Any]:
        """
        Analyze quality trends across all validation results.
        
        Returns insights about common issues, confidence distribution, etc.
        """
        if not validation_results:
            return {"error": "No validation results to analyze"}
        
        confidences = [r.overall_confidence for r in validation_results.values()]
        
        # Discrepancy type analysis
        disc_types = {}
        disc_by_priority = {Priority.HIGH: 0, Priority.MEDIUM: 0, Priority.LOW: 0}
        
        for result in validation_results.values():
            for disc in result.discrepancies:
                disc_type = disc.type.value
                disc_types[disc_type] = disc_types.get(disc_type, 0) + 1
                disc_by_priority[disc.priority] += 1
        
        # Source reliability analysis
        source_success = {}
        source_confidence = {}
        
        for result in validation_results.values():
            for sv in result.source_validations:
                source = sv.source.value
                if source not in source_success:
                    source_success[source] = {"success": 0, "total": 0}
                    source_confidence[source] = []
                
                source_success[source]["total"] += 1
                if sv.success:
                    source_success[source]["success"] += 1
                    source_confidence[source].append(sv.confidence)
        
        # Calculate source metrics
        source_metrics = {}
        for source, counts in source_success.items():
            success_rate = counts["success"] / counts["total"] * 100 if counts["total"] > 0 else 0
            avg_conf = sum(source_confidence[source]) / len(source_confidence[source]) if source_confidence[source] else 0
            source_metrics[source] = {
                "success_rate": success_rate,
                "average_confidence": avg_conf,
                "total_checks": counts["total"]
            }
        
        return {
            "total_providers": len(validation_results),
            "confidence_stats": {
                "average": sum(confidences) / len(confidences),
                "min": min(confidences),
                "max": max(confidences),
                "std_dev": self._calculate_std_dev(confidences)
            },
            "confidence_distribution": {
                "high_80_plus": sum(1 for c in confidences if c >= 80),
                "medium_60_79": sum(1 for c in confidences if 60 <= c < 80),
                "low_under_60": sum(1 for c in confidences if c < 60)
            },
            "status_breakdown": {
                "auto_approved": sum(1 for r in validation_results.values() if r.auto_updated),
                "needs_review": sum(1 for r in validation_results.values() if r.needs_review),
                "urgent": sum(1 for r in validation_results.values() if r.urgent_review)
            },
            "discrepancy_analysis": {
                "total": sum(disc_types.values()),
                "by_type": dict(sorted(disc_types.items(), key=lambda x: x[1], reverse=True)),
                "by_priority": {p.value: c for p, c in disc_by_priority.items()}
            },
            "source_reliability": source_metrics,
            "insights": self._generate_insights(confidences, disc_types, disc_by_priority)
        }
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        return variance ** 0.5
    
    def _generate_insights(
        self,
        confidences: List[float],
        disc_types: Dict[str, int],
        disc_by_priority: Dict[Priority, int]
    ) -> List[str]:
        """Generate actionable insights from quality analysis."""
        insights = []
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        if avg_confidence < 70:
            insights.append(
                "⚠️ Average confidence is below 70%. Consider reviewing data sources "
                "and provider data quality."
            )
        elif avg_confidence >= 85:
            insights.append(
                "✅ High average confidence indicates good data quality across providers."
            )
        
        # Most common issue
        if disc_types:
            top_issue = max(disc_types.items(), key=lambda x: x[1])
            insights.append(
                f"📊 Most common discrepancy: {top_issue[0].replace('_', ' ').title()} "
                f"({top_issue[1]} occurrences)"
            )
        
        # High priority issues
        high_priority = disc_by_priority.get(Priority.HIGH, 0)
        if high_priority > 0:
            insights.append(
                f"🔴 {high_priority} high-priority issues require immediate attention."
            )
        
        # Auto-approval rate
        high_conf = sum(1 for c in confidences if c >= 80)
        auto_rate = high_conf / len(confidences) * 100 if confidences else 0
        insights.append(
            f"🤖 Auto-approval rate: {auto_rate:.1f}% of providers can be "
            f"automatically updated."
        )
        
        return insights
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset agent statistics."""
        self.stats = {
            "providers_assessed": 0,
            "auto_approved": 0,
            "flagged_for_review": 0,
            "flagged_urgent": 0,
            "average_confidence": 0.0,
            "total_discrepancies": 0
        }


# Singleton instance
quality_assurance_agent = QualityAssuranceAgent()
