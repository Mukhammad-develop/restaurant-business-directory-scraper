#!/usr/bin/env python3
"""
Restaurant Business Directory Scraper
Main entry point for the application.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import config
from src.utils.logger import get_logger
from src.models import SearchFilter

logger = get_logger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Restaurant Business Directory Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --city "New York, NY" --cuisine Italian --min-rating 4.0
  python main.py --city "Los Angeles, CA" --radius 15 --keywords "pizza"
  python main.py --config custom_config.yaml --export csv,google_sheets
        """
    )
    
    # Configuration
    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Configuration file path (default: config.yaml)'
    )
    
    # Search parameters
    parser.add_argument(
        '--city',
        help='City to search in (e.g., "New York, NY")'
    )
    
    parser.add_argument(
        '--radius', '-r',
        type=float,
        help='Search radius in miles'
    )
    
    parser.add_argument(
        '--cuisine',
        help='Cuisine type to filter by'
    )
    
    parser.add_argument(
        '--keywords', '-k',
        help='Keywords to search for'
    )
    
    parser.add_argument(
        '--min-rating',
        type=float,
        help='Minimum rating threshold'
    )
    
    parser.add_argument(
        '--max-rating',
        type=float,
        help='Maximum rating threshold'
    )
    
    parser.add_argument(
        '--min-reviews',
        type=int,
        help='Minimum number of reviews'
    )
    
    # Export options
    parser.add_argument(
        '--export', '-e',
        default='csv',
        help='Export formats (comma-separated): csv, excel, google_sheets'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file path (without extension)'
    )
    
    # Platforms
    parser.add_argument(
        '--platforms', '-p',
        default='yelp,google',
        help='Platforms to scrape (comma-separated): yelp, google'
    )
    
    # Options
    parser.add_argument(
        '--max-results',
        type=int,
        help='Maximum number of results to collect'
    )
    
    parser.add_argument(
        '--with-reviews',
        action='store_true',
        help='Include reviews in the scraping'
    )
    
    parser.add_argument(
        '--validate-emails',
        action='store_true',
        help='Validate email addresses'
    )
    
    parser.add_argument(
        '--remove-duplicates',
        action='store_true',
        default=True,
        help='Remove duplicate entries'
    )
    
    parser.add_argument(
        '--generate-map',
        action='store_true',
        help='Generate interactive map'
    )
    
    parser.add_argument(
        '--generate-analytics',
        action='store_true',
        help='Generate analytics report'
    )
    
    # Verbose output
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be scraped without actually scraping'
    )
    
    return parser.parse_args()

def create_search_filter(args) -> SearchFilter:
    """Create SearchFilter from command line arguments."""
    return SearchFilter(
        city=args.city or config.get('search.default_city'),
        radius=args.radius or config.get('search.default_radius'),
        cuisine_type=args.cuisine,
        min_rating=getattr(args, 'min_rating', None),
        max_rating=getattr(args, 'max_rating', None),
        min_reviews=getattr(args, 'min_reviews', None),
        keywords=args.keywords
    )

def main():
    """Main application entry point."""
    try:
        args = parse_arguments()
        
        # Update logging level if verbose
        if args.verbose:
            logger.info("Verbose logging enabled")
        
        logger.info("🍽️  Restaurant Business Directory Scraper Starting")
        logger.info(f"Configuration loaded from: {args.config}")
        
        # Create search filter
        search_filter = create_search_filter(args)
        logger.info(f"Search parameters: {search_filter.to_dict()}")
        
        # Parse platforms and export formats
        platforms = [p.strip() for p in args.platforms.split(',')]
        export_formats = [f.strip() for f in args.export.split(',')]
        
        logger.info(f"Enabled platforms: {platforms}")
        logger.info(f"Export formats: {export_formats}")
        
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No actual scraping will be performed")
            logger.info("Search would be performed with the above parameters")
            return
        
        # Initialize scraper manager and run scrapers
        from src.scraper_manager import ScraperManager
        
        scraper_manager = ScraperManager()
        
        logger.info("🔍 Starting scraping process...")
        businesses = scraper_manager.search_all_platforms(search_filter, platforms)
        
        if not businesses:
            logger.warning("No businesses found matching the search criteria")
            return
        
        logger.info(f"✅ Found {len(businesses)} businesses total")
        
        # Process and validate data
        from src.processors.data_processor import DataProcessor
        from src.exporters.data_exporter import DataExporter
        
        processor = DataProcessor()
        exporter = DataExporter()
        
        logger.info("🔧 Processing and validating data...")
        processed_businesses = processor.process_businesses(businesses, search_filter)
        
        if not processed_businesses:
            logger.warning("No valid businesses after processing")
            return
        
        logger.info(f"📊 Data processing completed: {len(processed_businesses)} valid businesses")
        
        # Export data
        logger.info("💾 Exporting data...")
        export_results = exporter.export_businesses(processed_businesses, export_formats, args.output)
        
        # Display export results
        for format_type, result in export_results.items():
            logger.info(f"✅ {format_type.upper()} export: {result}")
        
        # Export reviews if requested
        if args.with_reviews:
            logger.info("📝 Exporting reviews...")
            reviews_file = exporter.export_reviews(processed_businesses)
            if reviews_file:
                logger.info(f"✅ Reviews exported: {reviews_file}")
        
        # Generate visualizations and analytics
        if args.generate_map:
            from src.visualizers.map_generator import MapGenerator
            
            logger.info("🗺️  Generating interactive map...")
            map_generator = MapGenerator()
            try:
                map_file = map_generator.generate_business_map(processed_businesses)
                logger.info(f"✅ Interactive map generated: {map_file}")
            except Exception as e:
                logger.warning(f"Map generation failed: {str(e)}")
            
        if args.generate_analytics:
            from src.visualizers.analytics_dashboard import AnalyticsDashboard
            
            logger.info("📊 Generating analytics dashboard...")
            analytics = AnalyticsDashboard()
            try:
                analytics_file = analytics.generate_analytics_report(processed_businesses)
                logger.info(f"✅ Analytics dashboard generated: {analytics_file}")
            except Exception as e:
                logger.warning(f"Analytics generation failed: {str(e)}")
        
        logger.info("✅ Application completed successfully")
        
    except KeyboardInterrupt:
        logger.info("⚠️  Application interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Application failed: {str(e)}")
        if args.verbose if 'args' in locals() else False:
            logger.exception("Full error details:")
        sys.exit(1)

if __name__ == "__main__":
    main() 