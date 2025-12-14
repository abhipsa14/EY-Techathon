"""
Directory Management Agent - Handles updates, review tickets, and notifications.
Final agent in the pipeline that takes action based on validation results.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from models import (
    Provider, ValidationResult, ReviewTicket, ValidationReport,
    ValidationStatus, Priority, Discrepancy
)
from services.notification_service import notification_service
from services.report_generator import report_generator
from config import REPORTS_DIR


class DirectoryManagementAgent:
    """
    Agent responsible for managing the provider directory based on validation results.
    
    Capabilities:
    - Auto-updates provider records with high-confidence data
    - Creates review tickets for providers needing attention
    - Sends notifications for urgent issues
    - Generates reports and exports
    - Maintains audit trail of all changes
    
    This agent is the final decision executor, implementing the actions
    determined by the Quality Assurance Agent.
    """
    
    def __init__(self):
        self.name = "Directory Management Agent"
        self.notification_service = notification_service
        self.report_generator = report_generator
        
        # In-memory storage for demo (use database in production)
        self.review_tickets: Dict[str, ReviewTicket] = {}
        self.update_log: List[Dict[str, Any]] = []
        self.provider_store: Dict[str, Provider] = {}
        
        # Statistics
        self.stats = {
            "providers_updated": 0,
            "tickets_created": 0,
            "notifications_sent": 0,
            "reports_generated": 0
        }
    
    async def process_validation_result(
        self,
        provider: Provider,
        result: ValidationResult
    ) -> Dict[str, Any]:
        """
        Process a validation result and take appropriate action.
        
        Args:
            provider: The validated provider
            result: The validation result
            
        Returns:
            Dictionary describing actions taken
        """
        actions = {
            "provider_id": provider.id,
            "provider_name": provider.full_name(),
            "status": result.status.value,
            "confidence": result.overall_confidence,
            "actions_taken": []
        }
        
        if result.auto_updated:
            # Auto-update the provider record
            update_result = await self._auto_update_provider(provider, result)
            actions["actions_taken"].append({
                "type": "auto_update",
                "details": update_result
            })
            
        elif result.urgent_review:
            # Create urgent ticket and send notification
            ticket = await self._create_review_ticket(provider, result, Priority.HIGH)
            actions["actions_taken"].append({
                "type": "urgent_ticket_created",
                "ticket_id": ticket.id
            })
            
            # Send urgent notification
            notif_result = await self._send_urgent_notification(provider, result)
            actions["actions_taken"].append({
                "type": "notification_sent",
                "details": notif_result
            })
            
        else:
            # Create review ticket for manual review
            ticket = await self._create_review_ticket(provider, result, Priority.MEDIUM)
            actions["actions_taken"].append({
                "type": "review_ticket_created",
                "ticket_id": ticket.id
            })
        
        return actions
    
    async def process_batch(
        self,
        providers: List[Provider],
        validation_results: Dict[str, ValidationResult],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process multiple validation results.
        
        Args:
            providers: List of providers
            validation_results: Validation results keyed by provider ID
            progress_callback: Optional progress callback
            
        Returns:
            Summary of all actions taken
        """
        summary = {
            "total_processed": 0,
            "auto_updated": 0,
            "tickets_created": 0,
            "urgent_notifications": 0,
            "provider_actions": []
        }
        
        total = len(providers)
        
        for i, provider in enumerate(providers):
            result = validation_results.get(provider.id)
            if result:
                actions = await self.process_validation_result(provider, result)
                summary["provider_actions"].append(actions)
                summary["total_processed"] += 1
                
                for action in actions["actions_taken"]:
                    if action["type"] == "auto_update":
                        summary["auto_updated"] += 1
                    elif "ticket" in action["type"]:
                        summary["tickets_created"] += 1
                    elif action["type"] == "notification_sent":
                        summary["urgent_notifications"] += 1
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return summary
    
    async def _auto_update_provider(
        self,
        provider: Provider,
        result: ValidationResult
    ) -> Dict[str, Any]:
        """
        Auto-update provider with validated data.
        
        Returns details of fields updated.
        """
        updates = []
        
        # Apply updates from discrepancies with high confidence
        for disc in result.discrepancies:
            if disc.confidence >= 85:
                # In production, this would update the database
                updates.append({
                    "field": disc.field_name,
                    "old_value": disc.current_value,
                    "new_value": disc.validated_value,
                    "confidence": disc.confidence,
                    "source": disc.source.value
                })
        
        # Update provider status
        provider.status = ValidationStatus.VALIDATED
        provider.confidence_score = result.overall_confidence
        provider.last_validated = datetime.now()
        
        # Store updated provider
        self.provider_store[provider.id] = provider
        
        # Log the update
        self.update_log.append({
            "provider_id": provider.id,
            "timestamp": datetime.now().isoformat(),
            "updates": updates,
            "confidence": result.overall_confidence
        })
        
        self.stats["providers_updated"] += 1
        
        return {
            "fields_updated": len(updates),
            "updates": updates,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _create_review_ticket(
        self,
        provider: Provider,
        result: ValidationResult,
        priority: Priority
    ) -> ReviewTicket:
        """
        Create a review ticket for manual review.
        """
        ticket = ReviewTicket(
            provider_id=provider.id,
            validation_result_id=result.id,
            priority=priority,
            status="open",
            discrepancies=result.discrepancies,
            notes=[f"Auto-generated ticket for {result.status.value} validation"]
        )
        
        self.review_tickets[ticket.id] = ticket
        self.stats["tickets_created"] += 1
        
        return ticket
    
    async def _send_urgent_notification(
        self,
        provider: Provider,
        result: ValidationResult
    ) -> Dict[str, Any]:
        """
        Send urgent notification for provider requiring immediate attention.
        """
        notif_result = await self.notification_service.send_urgent_review_alert(
            provider, result
        )
        
        if notif_result.get("success"):
            self.stats["notifications_sent"] += 1
        
        return notif_result
    
    async def generate_validation_report(
        self,
        providers: List[Provider],
        validation_results: Dict[str, ValidationResult],
        processing_time: float
    ) -> ValidationReport:
        """
        Generate a comprehensive validation report.
        """
        # Calculate statistics
        total = len(providers)
        auto_updated = sum(1 for r in validation_results.values() if r.auto_updated)
        needs_review = sum(1 for r in validation_results.values() if r.needs_review)
        urgent = sum(1 for r in validation_results.values() if r.urgent_review)
        errors = total - (auto_updated + needs_review + urgent)
        
        confidences = [r.overall_confidence for r in validation_results.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Count discrepancy types
        disc_counts = {}
        for result in validation_results.values():
            for disc in result.discrepancies:
                dtype = disc.type.value
                disc_counts[dtype] = disc_counts.get(dtype, 0) + 1
        
        report = ValidationReport(
            total_providers=total,
            validated=auto_updated + needs_review + urgent,
            auto_updated=auto_updated,
            needs_review=needs_review,
            urgent=urgent,
            errors=errors,
            average_confidence=avg_confidence,
            processing_time_seconds=processing_time,
            discrepancy_counts=disc_counts,
            completed_at=datetime.now()
        )
        
        self.stats["reports_generated"] += 1
        
        return report
    
    async def export_results(
        self,
        providers: List[Provider],
        validation_results: Dict[str, ValidationResult],
        format: str = "csv"
    ) -> str:
        """
        Export validation results to file.
        
        Args:
            providers: List of providers
            validation_results: Validation results
            format: Export format ('csv', 'excel', 'pdf')
            
        Returns:
            Path to exported file
        """
        if format == "excel":
            return self.report_generator.export_to_excel(
                providers, validation_results
            )
        elif format == "pdf":
            report = await self.generate_validation_report(
                providers, validation_results, 0
            )
            return self.report_generator.generate_pdf_report(
                providers, validation_results, report
            )
        else:
            return self.report_generator.generate_csv_report(
                providers, validation_results
            )
    
    def get_review_tickets(
        self,
        status: Optional[str] = None,
        priority: Optional[Priority] = None
    ) -> List[ReviewTicket]:
        """
        Get review tickets with optional filtering.
        """
        tickets = list(self.review_tickets.values())
        
        if status:
            tickets = [t for t in tickets if t.status == status]
        
        if priority:
            tickets = [t for t in tickets if t.priority == priority]
        
        # Sort by priority and creation date
        priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        tickets.sort(key=lambda t: (priority_order[t.priority], t.created_at))
        
        return tickets
    
    def resolve_ticket(
        self,
        ticket_id: str,
        resolution_notes: str,
        resolved_by: str
    ) -> Optional[ReviewTicket]:
        """
        Resolve a review ticket.
        """
        ticket = self.review_tickets.get(ticket_id)
        if ticket:
            ticket.status = "resolved"
            ticket.resolved_at = datetime.now()
            ticket.notes.append(f"Resolved: {resolution_notes}")
            
            # Mark discrepancies as resolved
            for disc in ticket.discrepancies:
                disc.resolved = True
                disc.resolved_at = datetime.now()
                disc.resolved_by = resolved_by
                disc.resolution_notes = resolution_notes
        
        return ticket
    
    def get_update_history(
        self,
        provider_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get update history, optionally filtered by provider.
        """
        history = self.update_log
        
        if provider_id:
            history = [h for h in history if h["provider_id"] == provider_id]
        
        return history[-limit:]
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get statistics for dashboard display.
        """
        tickets = list(self.review_tickets.values())
        
        return {
            "providers_in_system": len(self.provider_store),
            "providers_updated": self.stats["providers_updated"],
            "open_tickets": sum(1 for t in tickets if t.status == "open"),
            "urgent_tickets": sum(1 for t in tickets if t.priority == Priority.HIGH and t.status == "open"),
            "resolved_tickets": sum(1 for t in tickets if t.status == "resolved"),
            "notifications_sent": self.stats["notifications_sent"],
            "reports_generated": self.stats["reports_generated"],
            "recent_updates": len(self.update_log)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset agent statistics."""
        self.stats = {
            "providers_updated": 0,
            "tickets_created": 0,
            "notifications_sent": 0,
            "reports_generated": 0
        }
        self.review_tickets.clear()
        self.update_log.clear()


# Singleton instance
directory_management_agent = DirectoryManagementAgent()
