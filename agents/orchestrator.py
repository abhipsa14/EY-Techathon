"""
Validation Orchestrator - Coordinates all agents in the validation pipeline.
Manages the end-to-end validation workflow.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from models import (
    Provider, ValidationResult, ValidationReport, ValidationStatus
)
from agents.data_validation_agent import data_validation_agent
from agents.information_enrichment_agent import information_enrichment_agent
from agents.quality_assurance_agent import quality_assurance_agent
from agents.directory_management_agent import directory_management_agent


class ValidationOrchestrator:
    """
    Orchestrates the multi-agent validation pipeline.
    
    Pipeline Flow:
    1. Data Validation Agent - Gathers data from all sources
    2. Information Enrichment Agent - Enriches provider profiles
    3. Quality Assurance Agent - Assesses quality and calculates confidence
    4. Directory Management Agent - Takes appropriate actions
    
    The orchestrator manages:
    - Sequential and parallel execution of agents
    - Progress reporting
    - Error handling and recovery
    - Pipeline configuration
    """
    
    def __init__(self):
        self.name = "Validation Orchestrator"
        
        # Agents
        self.data_validation = data_validation_agent
        self.enrichment = information_enrichment_agent
        self.qa = quality_assurance_agent
        self.directory = directory_management_agent
        
        # Pipeline state
        self.is_running = False
        self.current_stage = None
        self.progress = 0.0
        self.start_time = None
        
        # Configuration
        self.config = {
            "enable_enrichment": True,
            "enable_notifications": True,
            "auto_export_results": False,
            "export_format": "csv"
        }
        
        # Results storage
        self.last_run_results = None
    
    async def run_full_validation(
        self,
        providers: List[Provider],
        progress_callback: Optional[Callable[[str, float, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Run the complete validation pipeline on a list of providers.
        
        Args:
            providers: List of providers to validate
            progress_callback: Optional callback(stage, progress, message)
            
        Returns:
            Complete validation results and report
        """
        self.is_running = True
        self.start_time = time.time()
        
        results = {
            "providers": {},
            "validation_results": {},
            "enrichments": {},
            "actions": {},
            "report": None,
            "errors": [],
            "timing": {}
        }
        
        total_providers = len(providers)
        
        try:
            # Stage 1: Data Validation
            self.current_stage = "data_validation"
            self._report_progress(progress_callback, "Validating Data", 0.0,
                                 f"Checking {total_providers} providers against external sources...")
            
            stage_start = time.time()
            
            def validation_progress(current, total):
                pct = current / total * 25  # 25% of total progress
                self._report_progress(progress_callback, "Validating Data", pct,
                                     f"Validated {current}/{total} providers")
            
            source_validations = await self.data_validation.validate_batch(
                providers, progress_callback=validation_progress
            )
            
            results["timing"]["data_validation"] = time.time() - stage_start
            
            # Stage 2: Information Enrichment (if enabled)
            if self.config["enable_enrichment"]:
                self.current_stage = "enrichment"
                self._report_progress(progress_callback, "Enriching Data", 25.0,
                                     "Adding additional information to provider profiles...")
                
                stage_start = time.time()
                
                def enrichment_progress(current, total):
                    pct = 25 + (current / total * 25)  # 25-50% of total progress
                    self._report_progress(progress_callback, "Enriching Data", pct,
                                         f"Enriched {current}/{total} providers")
                
                enrichments = await self.enrichment.enrich_batch(
                    providers, progress_callback=enrichment_progress
                )
                results["enrichments"] = enrichments
                
                results["timing"]["enrichment"] = time.time() - stage_start
            
            # Stage 3: Quality Assessment
            self.current_stage = "quality_assessment"
            self._report_progress(progress_callback, "Quality Assessment", 50.0,
                                 "Calculating confidence scores and prioritizing issues...")
            
            stage_start = time.time()
            
            def qa_progress(current, total):
                pct = 50 + (current / total * 25)  # 50-75% of total progress
                self._report_progress(progress_callback, "Quality Assessment", pct,
                                     f"Assessed {current}/{total} providers")
            
            validation_results = await self.qa.assess_batch(
                providers, source_validations, progress_callback=qa_progress
            )
            results["validation_results"] = validation_results
            
            results["timing"]["quality_assessment"] = time.time() - stage_start
            
            # Stage 4: Directory Management
            self.current_stage = "directory_management"
            self._report_progress(progress_callback, "Processing Results", 75.0,
                                 "Updating directory, creating tickets, sending notifications...")
            
            stage_start = time.time()
            
            def directory_progress(current, total):
                pct = 75 + (current / total * 20)  # 75-95% of total progress
                self._report_progress(progress_callback, "Processing Results", pct,
                                     f"Processed {current}/{total} providers")
            
            actions = await self.directory.process_batch(
                providers, validation_results, progress_callback=directory_progress
            )
            results["actions"] = actions
            
            results["timing"]["directory_management"] = time.time() - stage_start
            
            # Stage 5: Generate Report
            self.current_stage = "reporting"
            self._report_progress(progress_callback, "Generating Report", 95.0,
                                 "Creating validation report...")
            
            stage_start = time.time()
            
            total_time = time.time() - self.start_time
            report = await self.directory.generate_validation_report(
                providers, validation_results, total_time
            )
            results["report"] = report
            
            results["timing"]["reporting"] = time.time() - stage_start
            
            # Export results if configured
            if self.config["auto_export_results"]:
                export_path = await self.directory.export_results(
                    providers, validation_results, self.config["export_format"]
                )
                results["export_path"] = export_path
            
            # Store providers with updated statuses
            results["providers"] = {p.id: p for p in providers}
            
            # Finalize
            self._report_progress(progress_callback, "Complete", 100.0,
                                 f"Validation complete! Processed {total_providers} providers in {total_time:.1f}s")
            
            results["timing"]["total"] = total_time
            
            # Store for reference
            self.last_run_results = results
            
        except Exception as e:
            results["errors"].append({
                "stage": self.current_stage,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            self._report_progress(progress_callback, "Error", self.progress,
                                 f"Error in {self.current_stage}: {str(e)}")
        
        finally:
            self.is_running = False
            self.current_stage = None
        
        return results
    
    def _report_progress(
        self,
        callback: Optional[Callable],
        stage: str,
        progress: float,
        message: str
    ):
        """Report progress to callback if provided."""
        self.progress = progress
        if callback:
            callback(stage, progress, message)
    
    async def run_quick_validation(
        self,
        provider: Provider
    ) -> ValidationResult:
        """
        Run quick validation on a single provider.
        
        Simplified pipeline for individual provider validation.
        """
        # Validate against sources
        source_validations = await self.data_validation.validate_provider(provider)
        
        # Assess quality
        result = await self.qa.assess_provider(provider, source_validations)
        
        return result
    
    def configure(self, **kwargs):
        """
        Configure the orchestrator.
        
        Args:
            enable_enrichment: Whether to run enrichment (default: True)
            enable_notifications: Whether to send notifications (default: True)
            auto_export_results: Whether to auto-export results (default: False)
            export_format: Export format - 'csv', 'excel', 'pdf' (default: 'csv')
        """
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        return {
            "is_running": self.is_running,
            "current_stage": self.current_stage,
            "progress": self.progress,
            "elapsed_seconds": elapsed,
            "config": self.config
        }
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics from all agents."""
        return {
            "data_validation": self.data_validation.get_stats(),
            "enrichment": self.enrichment.get_stats(),
            "quality_assurance": self.qa.get_stats(),
            "directory_management": self.directory.get_stats()
        }
    
    def reset_all_stats(self):
        """Reset statistics for all agents."""
        self.data_validation.reset_stats()
        self.enrichment.reset_stats()
        self.qa.reset_stats()
        self.directory.reset_stats()
    
    def get_quality_insights(self) -> Dict[str, Any]:
        """Get quality insights from the last run."""
        if not self.last_run_results or not self.last_run_results.get("validation_results"):
            return {"error": "No validation results available"}
        
        return self.qa.analyze_quality_trends(
            self.last_run_results["validation_results"]
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of the last validation run."""
        if not self.last_run_results:
            return {"error": "No validation run completed yet"}
        
        report = self.last_run_results.get("report")
        timing = self.last_run_results.get("timing", {})
        
        return {
            "total_providers": report.total_providers if report else 0,
            "auto_updated": report.auto_updated if report else 0,
            "needs_review": report.needs_review if report else 0,
            "urgent": report.urgent if report else 0,
            "average_confidence": report.average_confidence if report else 0,
            "processing_time": timing.get("total", 0),
            "errors": len(self.last_run_results.get("errors", [])),
            "completed_at": report.completed_at.isoformat() if report and report.completed_at else None
        }


# Singleton instance
orchestrator = ValidationOrchestrator()
