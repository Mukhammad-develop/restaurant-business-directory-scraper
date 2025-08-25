"""Data exporter for CSV, Excel, and Google Sheets export."""

import os
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

from src.models import Business
from src.config import config
from src.utils.logger import get_logger

class DataExporter:
    """Exports business data to various formats."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.output_dir = Path(self.config.export.get('output_directory', 'data/exports'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def export_businesses(self, businesses: List[Business], formats: List[str], filename_prefix: str = None) -> Dict[str, str]:
        """Export businesses to specified formats."""
        if not businesses:
            self.logger.warning("No businesses to export")
            return {}
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = filename_prefix or self.config.export.get('filename_prefix', 'restaurant_directory')
        filename = f"{base_filename}_{timestamp}"
        
        results = {}
        
        for format_type in formats:
            try:
                if format_type.lower() == 'csv':
                    filepath = self.export_to_csv(businesses, filename)
                    results['csv'] = filepath
                    
                elif format_type.lower() == 'excel':
                    filepath = self.export_to_excel(businesses, filename)
                    results['excel'] = filepath
                    
                elif format_type.lower() == 'google_sheets':
                    sheet_url = self.export_to_google_sheets(businesses, filename)
                    results['google_sheets'] = sheet_url
                    
                else:
                    self.logger.warning(f"Unsupported export format: {format_type}")
                    
            except Exception as e:
                self.logger.error(f"Error exporting to {format_type}: {str(e)}")
        
        return results
    
    def export_to_csv(self, businesses: List[Business], filename: str) -> str:
        """Export businesses to CSV file."""
        filepath = self.output_dir / f"{filename}.csv"
        
        self.logger.info(f"Exporting {len(businesses)} businesses to CSV: {filepath}")
        
        # Convert businesses to dictionaries
        business_dicts = [business.to_dict() for business in businesses]
        
        if not business_dicts:
            raise ValueError("No business data to export")
        
        # Get all possible field names
        all_fields = set()
        for business_dict in business_dicts:
            all_fields.update(business_dict.keys())
        
        # Sort fields for consistent column order
        fieldnames = self._get_ordered_fieldnames(all_fields)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for business_dict in business_dicts:
                # Ensure all fields are present
                row = {field: business_dict.get(field, '') for field in fieldnames}
                writer.writerow(row)
        
        self.logger.info(f"✅ CSV export completed: {filepath}")
        return str(filepath)
    
    def export_to_excel(self, businesses: List[Business], filename: str) -> str:
        """Export businesses to Excel file."""
        filepath = self.output_dir / f"{filename}.xlsx"
        
        self.logger.info(f"Exporting {len(businesses)} businesses to Excel: {filepath}")
        
        # Convert to DataFrame
        business_dicts = [business.to_dict() for business in businesses]
        df = pd.DataFrame(business_dicts)
        
        # Create Excel writer with multiple sheets
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main businesses sheet
            df.to_excel(writer, sheet_name='Businesses', index=False)
            
            # Summary sheet
            summary_data = self._create_summary_data(businesses)
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Statistics sheet
            stats_data = self._create_statistics_data(businesses)
            stats_df = pd.DataFrame(stats_data, index=[0])
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)
        
        self.logger.info(f"✅ Excel export completed: {filepath}")
        return str(filepath)
    
    def export_to_google_sheets(self, businesses: List[Business], filename: str) -> str:
        """Export businesses to Google Sheets."""
        try:
            # Set up Google Sheets credentials
            gc = self._setup_google_sheets_client()
            
            # Create or open spreadsheet
            spreadsheet_name = f"{filename}"
            try:
                spreadsheet = gc.create(spreadsheet_name)
                self.logger.info(f"Created new Google Sheet: {spreadsheet_name}")
            except Exception:
                # If creation fails, try to open existing
                spreadsheet = gc.open(spreadsheet_name)
                self.logger.info(f"Opened existing Google Sheet: {spreadsheet_name}")
            
            # Get the main worksheet
            worksheet = spreadsheet.sheet1
            worksheet.update_title("Businesses")
            
            # Convert businesses to list of lists for bulk update
            business_dicts = [business.to_dict() for business in businesses]
            
            if not business_dicts:
                raise ValueError("No business data to export")
            
            # Get headers
            headers = list(business_dicts[0].keys())
            
            # Prepare data
            data = [headers]
            for business_dict in business_dicts:
                row = [str(business_dict.get(header, '')) for header in headers]
                data.append(row)
            
            # Clear existing data and update
            worksheet.clear()
            worksheet.update('A1', data)
            
            # Format headers
            worksheet.format('A1:Z1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}
            })
            
            # Add summary sheet
            try:
                summary_sheet = spreadsheet.add_worksheet("Summary", 100, 10)
                summary_data = self._create_summary_data(businesses)
                if summary_data:
                    summary_headers = list(summary_data[0].keys())
                    summary_rows = [summary_headers]
                    for item in summary_data:
                        row = [str(item.get(header, '')) for header in summary_headers]
                        summary_rows.append(row)
                    summary_sheet.update('A1', summary_rows)
            except Exception as e:
                self.logger.warning(f"Could not create summary sheet: {str(e)}")
            
            # Share the spreadsheet (make it accessible)
            spreadsheet.share('', perm_type='anyone', role='reader')
            
            sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}"
            self.logger.info(f"✅ Google Sheets export completed: {sheet_url}")
            
            return sheet_url
            
        except Exception as e:
            self.logger.error(f"Google Sheets export failed: {str(e)}")
            raise
    
    def _setup_google_sheets_client(self):
        """Set up Google Sheets API client."""
        credentials_path = self.config.get('google_sheets.credentials_file', 'credentials/google_credentials.json')
        
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")
        
        # Define the scope
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Load credentials
        credentials = Credentials.from_service_account_file(credentials_path, scopes=scope)
        
        # Create client
        gc = gspread.authorize(credentials)
        return gc
    
    def _get_ordered_fieldnames(self, all_fields: set) -> List[str]:
        """Get ordered list of field names for consistent CSV/Excel columns."""
        # Define preferred order for common fields
        preferred_order = [
            'name', 'address', 'city', 'state', 'zip_code', 'country', 'full_address',
            'phone', 'website', 'email', 'email_validated',
            'category', 'cuisine_type', 'price_level',
            'latitude', 'longitude',
            'rating', 'review_count', 'average_sentiment',
            'sentiment_positive', 'sentiment_negative', 'sentiment_neutral',
            'hours_monday', 'hours_tuesday', 'hours_wednesday', 'hours_thursday',
            'hours_friday', 'hours_saturday', 'hours_sunday',
            'yelp_id', 'yelp_url', 'google_place_id', 'google_url',
            'features', 'photo_count',
            'scraped_at', 'last_updated', 'data_sources', 'is_duplicate'
        ]
        
        # Start with preferred fields that exist
        ordered_fields = [field for field in preferred_order if field in all_fields]
        
        # Add remaining fields
        remaining_fields = sorted(all_fields - set(ordered_fields))
        ordered_fields.extend(remaining_fields)
        
        return ordered_fields
    
    def _create_summary_data(self, businesses: List[Business]) -> List[Dict[str, Any]]:
        """Create summary data for export."""
        summary = []
        
        # Group by cuisine type
        cuisine_counts = {}
        rating_sum = 0
        rating_count = 0
        total_reviews = 0
        
        for business in businesses:
            # Count by cuisine type
            cuisine = business.cuisine_type or 'Unknown'
            cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1
            
            # Calculate averages
            if business.rating:
                rating_sum += business.rating
                rating_count += 1
            
            total_reviews += business.review_count
        
        # Create cuisine summary
        for cuisine, count in sorted(cuisine_counts.items(), key=lambda x: x[1], reverse=True):
            summary.append({
                'Category': 'Cuisine Type',
                'Name': cuisine,
                'Count': count,
                'Percentage': f"{(count/len(businesses)*100):.1f}%"
            })
        
        return summary
    
    def _create_statistics_data(self, businesses: List[Business]) -> Dict[str, Any]:
        """Create statistics data for export."""
        stats = {
            'total_businesses': len(businesses),
            'businesses_with_phone': len([b for b in businesses if b.phone]),
            'businesses_with_website': len([b for b in businesses if b.website]),
            'businesses_with_email': len([b for b in businesses if b.email]),
            'businesses_with_rating': len([b for b in businesses if b.rating]),
            'average_rating': 0,
            'total_reviews': sum(b.review_count for b in businesses),
            'unique_cities': len(set(b.city for b in businesses if b.city)),
            'unique_cuisines': len(set(b.cuisine_type for b in businesses if b.cuisine_type)),
        }
        
        # Calculate average rating
        rated_businesses = [b for b in businesses if b.rating]
        if rated_businesses:
            stats['average_rating'] = sum(b.rating for b in rated_businesses) / len(rated_businesses)
        
        return stats
    
    def export_reviews(self, businesses: List[Business], filename: str = None) -> str:
        """Export reviews to separate CSV file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"reviews_{timestamp}"
        filepath = self.output_dir / f"{filename}.csv"
        
        self.logger.info(f"Exporting reviews to CSV: {filepath}")
        
        reviews_data = []
        for business in businesses:
            for review in business.reviews:
                review_dict = review.to_dict()
                review_dict['business_name'] = business.name
                review_dict['business_address'] = business.full_address
                reviews_data.append(review_dict)
        
        if not reviews_data:
            self.logger.warning("No reviews to export")
            return ""
        
        # Write to CSV
        fieldnames = list(reviews_data[0].keys())
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reviews_data)
        
        self.logger.info(f"✅ Reviews export completed: {filepath}")
        return str(filepath) 