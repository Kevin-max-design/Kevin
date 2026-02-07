"""
Data Exporter - Export application data to various formats.

Supports CSV, JSON, and Google Sheets export with customizable fields.
"""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from io import StringIO

from ..database import Database, Job, Application


class DataExporter:
    """
    Export job application data to various formats.
    
    Supports:
    - CSV export
    - JSON export
    - Google Sheets integration (requires credentials)
    """
    
    # Default fields to export
    DEFAULT_JOB_FIELDS = [
        "id", "title", "company", "location", "platform", 
        "job_type", "work_mode", "match_score", "status",
        "url", "posted_date", "scraped_at", "applied_at"
    ]
    
    DEFAULT_APPLICATION_FIELDS = [
        "id", "job_id", "status", "application_method",
        "created_at", "applied_at", "response_received"
    ]
    
    def __init__(self, db: Database, output_dir: str = "data/exports"):
        """
        Initialize exporter.
        
        Args:
            db: Database instance
            output_dir: Directory for export files
        """
        self.db = db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Google Sheets API client (initialized on demand)
        self._sheets_service = None
    
    def export_jobs_csv(
        self,
        filename: str = None,
        status_filter: str = None,
        fields: List[str] = None,
    ) -> str:
        """
        Export jobs to CSV file.
        
        Args:
            filename: Output filename (auto-generated if not provided)
            status_filter: Optional status filter
            fields: Fields to include (uses defaults if not specified)
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jobs_export_{timestamp}.csv"
        
        output_path = self.output_dir / filename
        fields = fields or self.DEFAULT_JOB_FIELDS
        
        with self.db.get_session() as session:
            query = session.query(Job)
            
            if status_filter:
                query = query.filter(Job.status == status_filter)
            
            jobs = query.order_by(Job.updated_at.desc()).all()
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
                writer.writeheader()
                
                for job in jobs:
                    row = job.to_dict()
                    writer.writerow(row)
        
        self.logger.info(f"Exported {len(jobs)} jobs to {output_path}")
        return str(output_path)
    
    def export_jobs_json(
        self,
        filename: str = None,
        status_filter: str = None,
        include_applications: bool = False,
    ) -> str:
        """
        Export jobs to JSON file.
        
        Args:
            filename: Output filename
            status_filter: Optional status filter
            include_applications: Include application data
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jobs_export_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        with self.db.get_session() as session:
            query = session.query(Job)
            
            if status_filter:
                query = query.filter(Job.status == status_filter)
            
            jobs = query.order_by(Job.updated_at.desc()).all()
            
            data = []
            for job in jobs:
                job_data = job.to_dict()
                
                if include_applications:
                    applications = session.query(Application).filter(
                        Application.job_id == job.id
                    ).all()
                    job_data["applications"] = [app.to_dict() for app in applications]
                
                data.append(job_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "exported_at": datetime.utcnow().isoformat(),
                    "total_jobs": len(data),
                    "jobs": data,
                }, f, indent=2, default=str)
        
        self.logger.info(f"Exported {len(data)} jobs to {output_path}")
        return str(output_path)
    
    def export_to_google_sheets(
        self,
        spreadsheet_id: str,
        sheet_name: str = "Applications",
        status_filter: str = None,
    ) -> bool:
        """
        Export jobs to Google Sheets.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the sheet to write to
            status_filter: Optional status filter
            
        Returns:
            True if successful
        """
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            self.logger.error(
                "Google API libraries not installed. "
                "Install with: pip install google-api-python-client google-auth"
            )
            return False
        
        # Check for credentials
        credentials_path = Path("config/google_credentials.json")
        if not credentials_path.exists():
            self.logger.error(f"Google credentials not found at {credentials_path}")
            return False
        
        try:
            # Authenticate
            credentials = Credentials.from_service_account_file(
                str(credentials_path),
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            service = build('sheets', 'v4', credentials=credentials)
            
            # Get job data
            with self.db.get_session() as session:
                query = session.query(Job)
                
                if status_filter:
                    query = query.filter(Job.status == status_filter)
                
                jobs = query.order_by(Job.updated_at.desc()).all()
                
                # Prepare data
                headers = self.DEFAULT_JOB_FIELDS
                rows = [headers]
                
                for job in jobs:
                    job_dict = job.to_dict()
                    row = [str(job_dict.get(field, "")) for field in headers]
                    rows.append(row)
            
            # Write to sheet
            body = {'values': rows}
            
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            self.logger.info(
                f"Exported {len(jobs)} jobs to Google Sheets. "
                f"Updated {result.get('updatedCells')} cells."
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Google Sheets export failed: {e}")
            return False
    
    def get_csv_string(
        self,
        status_filter: str = None,
        fields: List[str] = None,
    ) -> str:
        """
        Get CSV data as string (for API responses).
        
        Args:
            status_filter: Optional status filter
            fields: Fields to include
            
        Returns:
            CSV data as string
        """
        fields = fields or self.DEFAULT_JOB_FIELDS
        output = StringIO()
        
        with self.db.get_session() as session:
            query = session.query(Job)
            
            if status_filter:
                query = query.filter(Job.status == status_filter)
            
            jobs = query.order_by(Job.updated_at.desc()).all()
            
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            
            for job in jobs:
                writer.writerow(job.to_dict())
        
        return output.getvalue()
    
    def export_summary_report(
        self,
        filename: str = None,
        days: int = 30,
    ) -> str:
        """
        Export a summary report.
        
        Args:
            filename: Output filename
            days: Number of days to include
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_report_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        from sqlalchemy import func, and_
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.db.get_session() as session:
            # Status counts
            status_counts = dict(session.query(
                Job.status,
                func.count(Job.id)
            ).group_by(Job.status).all())
            
            # Platform counts
            platform_counts = dict(session.query(
                Job.platform,
                func.count(Job.id)
            ).group_by(Job.platform).all())
            
            # Recent applications
            recent_count = session.query(func.count(Job.id)).filter(
                and_(
                    Job.applied_at >= cutoff,
                    Job.status.in_(["applied", "interview", "offer"])
                )
            ).scalar() or 0
            
            # Top companies
            top_companies = session.query(
                Job.company,
                func.count(Job.id)
            ).group_by(Job.company).order_by(
                func.count(Job.id).desc()
            ).limit(10).all()
            
            # Average match score by platform
            avg_scores = session.query(
                Job.platform,
                func.avg(Job.match_score)
            ).filter(Job.match_score > 0).group_by(Job.platform).all()
            
            report = {
                "report_date": datetime.utcnow().isoformat(),
                "period_days": days,
                "summary": {
                    "total_jobs": session.query(func.count(Job.id)).scalar() or 0,
                    "recent_applications": recent_count,
                    "status_breakdown": status_counts,
                    "platform_breakdown": platform_counts,
                },
                "top_companies": [
                    {"company": c, "count": count} 
                    for c, count in top_companies
                ],
                "average_scores_by_platform": {
                    platform: round(score, 1) 
                    for platform, score in avg_scores
                },
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Summary report exported to {output_path}")
        return str(output_path)
    
    def export_for_visualization(
        self,
        filename: str = None,
    ) -> str:
        """
        Export data formatted for visualization tools.
        
        Args:
            filename: Output filename
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"viz_data_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        from sqlalchemy import func
        
        with self.db.get_session() as session:
            # Applications over time (by week)
            applications_timeline = session.query(
                func.strftime('%Y-%W', Job.applied_at).label('week'),
                func.count(Job.id)
            ).filter(Job.applied_at.isnot(None)).group_by('week').all()
            
            # Match score distribution
            score_ranges = [(0, 40), (40, 60), (60, 80), (80, 100)]
            score_distribution = []
            for low, high in score_ranges:
                count = session.query(func.count(Job.id)).filter(
                    and_(
                        Job.match_score >= low,
                        Job.match_score < high
                    )
                ).scalar() or 0
                score_distribution.append({
                    "range": f"{low}-{high}",
                    "count": count
                })
            
            viz_data = {
                "timeline": [
                    {"week": week, "count": count}
                    for week, count in applications_timeline
                ],
                "score_distribution": score_distribution,
                "generated_at": datetime.utcnow().isoformat(),
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(viz_data, f, indent=2, default=str)
        
        self.logger.info(f"Visualization data exported to {output_path}")
        return str(output_path)
