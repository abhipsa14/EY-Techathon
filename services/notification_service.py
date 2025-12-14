"""
Notification Service - Handles email notifications and alerts.
Sends alerts for urgent reviews, daily summaries, and status updates.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from models import (
    Provider, ValidationResult, Priority, NotificationRequest,
    ReviewTicket, ValidationReport
)
from config import SENDGRID_API_KEY, EMAIL_FROM, EMAIL_TO


class NotificationService:
    """Service for sending email notifications and alerts."""
    
    def __init__(self):
        self.api_key = SENDGRID_API_KEY
        self.from_email = EMAIL_FROM
        self.default_to = EMAIL_TO
        self.enabled = bool(self.api_key)
        
    async def send_urgent_review_alert(
        self, 
        provider: Provider,
        validation_result: ValidationResult,
        recipient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send urgent review alert for a provider requiring immediate attention.
        """
        to_email = recipient or self.default_to
        
        subject = f"🚨 URGENT: Provider Review Required - {provider.full_name()}"
        
        html_content = self._generate_urgent_alert_html(provider, validation_result)
        
        return await self._send_email(to_email, subject, html_content)
    
    async def send_daily_summary(
        self, 
        report: ValidationReport,
        recipient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send daily validation summary report.
        """
        to_email = recipient or self.default_to
        
        subject = f"📊 Daily Validation Summary - {datetime.now().strftime('%Y-%m-%d')}"
        
        html_content = self._generate_daily_summary_html(report)
        
        return await self._send_email(to_email, subject, html_content)
    
    async def send_review_ticket_notification(
        self, 
        ticket: ReviewTicket,
        provider: Provider,
        recipient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification about new review ticket.
        """
        to_email = recipient or self.default_to
        
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(ticket.priority.value, "⚪")
        subject = f"{priority_emoji} New Review Ticket - {provider.practice_name}"
        
        html_content = self._generate_ticket_html(ticket, provider)
        
        return await self._send_email(to_email, subject, html_content)
    
    async def send_batch_notification(
        self, 
        providers: List[Provider],
        validation_results: List[ValidationResult],
        recipient: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send batch notification for multiple providers.
        """
        to_email = recipient or self.default_to
        
        urgent_count = sum(1 for r in validation_results if r.urgent_review)
        review_count = sum(1 for r in validation_results if r.needs_review)
        auto_count = sum(1 for r in validation_results if r.auto_updated)
        
        subject = f"📋 Batch Validation Complete - {len(providers)} Providers Processed"
        
        html_content = self._generate_batch_html(providers, validation_results, urgent_count, review_count, auto_count)
        
        return await self._send_email(to_email, subject, html_content)
    
    async def _send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str
    ) -> Dict[str, Any]:
        """
        Send email via SendGrid or simulate for demo.
        
        In production, this would use the SendGrid API.
        For demo, we simulate the email sending.
        """
        # Simulate sending delay
        await asyncio.sleep(0.1)
        
        # For demo purposes, we simulate success
        # In production:
        # from sendgrid import SendGridAPIClient
        # from sendgrid.helpers.mail import Mail
        #
        # message = Mail(
        #     from_email=self.from_email,
        #     to_emails=to_email,
        #     subject=subject,
        #     html_content=html_content
        # )
        # 
        # try:
        #     sg = SendGridAPIClient(self.api_key)
        #     response = sg.send(message)
        #     return {"success": True, "status_code": response.status_code}
        # except Exception as e:
        #     return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "simulated": True,
            "to": to_email,
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            "message": "Email notification simulated (API key not configured)"
        }
    
    def _generate_urgent_alert_html(
        self, 
        provider: Provider,
        result: ValidationResult
    ) -> str:
        """Generate HTML content for urgent alert email."""
        discrepancy_rows = ""
        for disc in result.discrepancies:
            priority_color = {"high": "#dc3545", "medium": "#ffc107", "low": "#28a745"}.get(disc.priority.value, "#6c757d")
            discrepancy_rows += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{disc.type.value.replace('_', ' ').title()}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{disc.field_name}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{disc.current_value}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{disc.validated_value}</td>
                <td style="padding: 8px; border: 1px solid #ddd; background-color: {priority_color}; color: white;">{disc.priority.value.upper()}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .info-box {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th {{ background-color: #343a40; color: white; padding: 10px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 Urgent Review Required</h1>
            </div>
            <div class="content">
                <h2>Provider Information</h2>
                <div class="info-box">
                    <strong>Name:</strong> {provider.full_name()}<br>
                    <strong>NPI:</strong> {provider.npi}<br>
                    <strong>Practice:</strong> {provider.practice_name}<br>
                    <strong>Specialty:</strong> {provider.specialty}<br>
                    <strong>Confidence Score:</strong> {result.overall_confidence:.1f}%
                </div>
                
                <h2>Issues Found ({len(result.discrepancies)})</h2>
                <table>
                    <tr>
                        <th>Type</th>
                        <th>Field</th>
                        <th>Current Value</th>
                        <th>Validated Value</th>
                        <th>Priority</th>
                    </tr>
                    {discrepancy_rows}
                </table>
                
                <p style="margin-top: 20px;">
                    <a href="#" class="btn">Review in Dashboard</a>
                </p>
                
                <p style="color: #6c757d; font-size: 12px; margin-top: 30px;">
                    This is an automated notification from the Provider Data Validation System.<br>
                    Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </body>
        </html>
        """
    
    def _generate_daily_summary_html(self, report: ValidationReport) -> str:
        """Generate HTML content for daily summary email."""
        discrepancy_breakdown = ""
        for disc_type, count in report.discrepancy_counts.items():
            discrepancy_breakdown += f"<li>{disc_type.replace('_', ' ').title()}: {count}</li>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .stats-grid {{ display: flex; gap: 15px; flex-wrap: wrap; }}
                .stat-box {{ flex: 1; min-width: 150px; padding: 20px; text-align: center; border-radius: 10px; }}
                .stat-value {{ font-size: 36px; font-weight: bold; }}
                .green {{ background-color: #d4edda; color: #155724; }}
                .yellow {{ background-color: #fff3cd; color: #856404; }}
                .red {{ background-color: #f8d7da; color: #721c24; }}
                .blue {{ background-color: #d1ecf1; color: #0c5460; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Daily Validation Summary</h1>
                <p>{datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            <div class="content">
                <div class="stats-grid">
                    <div class="stat-box blue">
                        <div class="stat-value">{report.total_providers}</div>
                        <div>Total Providers</div>
                    </div>
                    <div class="stat-box green">
                        <div class="stat-value">{report.auto_updated}</div>
                        <div>Auto-Updated ✓</div>
                    </div>
                    <div class="stat-box yellow">
                        <div class="stat-value">{report.needs_review}</div>
                        <div>Needs Review ⚠</div>
                    </div>
                    <div class="stat-box red">
                        <div class="stat-value">{report.urgent}</div>
                        <div>Urgent ✗</div>
                    </div>
                </div>
                
                <h2 style="margin-top: 30px;">Key Metrics</h2>
                <ul>
                    <li><strong>Average Confidence:</strong> {report.average_confidence:.1f}%</li>
                    <li><strong>Processing Time:</strong> {report.processing_time_seconds:.1f} seconds</li>
                    <li><strong>Validation Rate:</strong> {(report.validated / report.total_providers * 100):.1f}%</li>
                    <li><strong>Error Rate:</strong> {(report.errors / report.total_providers * 100):.1f}%</li>
                </ul>
                
                <h2>Discrepancy Breakdown</h2>
                <ul>
                    {discrepancy_breakdown if discrepancy_breakdown else "<li>No discrepancies found</li>"}
                </ul>
                
                <p style="color: #6c757d; font-size: 12px; margin-top: 30px;">
                    Provider Data Validation System - Automated Report<br>
                    Report ID: {report.id}
                </p>
            </div>
        </body>
        </html>
        """
    
    def _generate_ticket_html(self, ticket: ReviewTicket, provider: Provider) -> str:
        """Generate HTML content for ticket notification."""
        priority_color = {"high": "#dc3545", "medium": "#ffc107", "low": "#28a745"}.get(ticket.priority.value, "#6c757d")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: {priority_color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .info-box {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>New Review Ticket Created</h1>
                <p>Priority: {ticket.priority.value.upper()}</p>
            </div>
            <div class="content">
                <h2>Ticket #{ticket.id[:8]}</h2>
                <div class="info-box">
                    <strong>Provider:</strong> {provider.full_name()}<br>
                    <strong>Practice:</strong> {provider.practice_name}<br>
                    <strong>NPI:</strong> {provider.npi}<br>
                    <strong>Discrepancies:</strong> {len(ticket.discrepancies)}
                </div>
                
                <p>Please review this provider's information in the validation dashboard.</p>
                
                <p style="color: #6c757d; font-size: 12px; margin-top: 30px;">
                    Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </body>
        </html>
        """
    
    def _generate_batch_html(
        self, 
        providers: List[Provider],
        results: List[ValidationResult],
        urgent: int,
        review: int,
        auto: int
    ) -> str:
        """Generate HTML content for batch notification."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #17a2b8; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .stats {{ display: flex; gap: 20px; justify-content: center; }}
                .stat {{ text-align: center; padding: 15px 30px; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✓ Batch Validation Complete</h1>
            </div>
            <div class="content">
                <h2>{len(providers)} Providers Processed</h2>
                
                <div class="stats">
                    <div class="stat" style="background-color: #d4edda;">
                        <h3 style="margin: 0; color: #155724;">{auto}</h3>
                        <p style="margin: 5px 0;">Auto-Updated</p>
                    </div>
                    <div class="stat" style="background-color: #fff3cd;">
                        <h3 style="margin: 0; color: #856404;">{review}</h3>
                        <p style="margin: 5px 0;">Needs Review</p>
                    </div>
                    <div class="stat" style="background-color: #f8d7da;">
                        <h3 style="margin: 0; color: #721c24;">{urgent}</h3>
                        <p style="margin: 5px 0;">Urgent</p>
                    </div>
                </div>
                
                <p style="text-align: center; margin-top: 20px;">
                    View detailed results in the Provider Validation Dashboard.
                </p>
            </div>
        </body>
        </html>
        """


# Singleton instance
notification_service = NotificationService()
