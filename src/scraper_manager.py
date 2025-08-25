"""Scraper manager to orchestrate multiple scrapers and combine results."""

from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.config import config
from src.models import Business, SearchFilter
from src.scrapers.yelp_scraper import YelpScraper
from src.scrapers.google_maps_scraper import GoogleMapsScraper
from src.utils.logger import get_logger

class ScraperManager:
    """Manages multiple scrapers and combines their results."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.scrapers = {}
        
        # Initialize scrapers based on configuration
        if self.config.platforms.get('yelp', {}).get('enabled', True):
            self.scrapers['yelp'] = YelpScraper
        
        if self.config.platforms.get('google_maps', {}).get('enabled', True):
            self.scrapers['google_maps'] = GoogleMapsScraper
    
    def search_all_platforms(self, search_filter: SearchFilter, platforms: List[str] = None) -> List[Business]:
        """Search all enabled platforms and combine results."""
        if platforms is None:
            platforms = list(self.scrapers.keys())
        
        self.logger.info(f"Starting search across platforms: {platforms}")
        all_businesses = []
        
        # Determine if we should run scrapers concurrently or sequentially
        concurrent_requests = self.config.scraping.get('concurrent_requests', 1)
        
        if concurrent_requests > 1 and len(platforms) > 1:
            # Run scrapers concurrently
            all_businesses = self._search_concurrent(search_filter, platforms)
        else:
            # Run scrapers sequentially
            all_businesses = self._search_sequential(search_filter, platforms)
        
        self.logger.info(f"Total businesses found across all platforms: {len(all_businesses)}")
        return all_businesses
    
    def _search_sequential(self, search_filter: SearchFilter, platforms: List[str]) -> List[Business]:
        """Search platforms sequentially."""
        all_businesses = []
        
        for platform in platforms:
            if platform not in self.scrapers:
                self.logger.warning(f"Scraper not available for platform: {platform}")
                continue
            
            try:
                self.logger.info(f"Starting search on {platform}")
                scraper_class = self.scrapers[platform]
                
                with scraper_class() as scraper:
                    businesses = scraper.search_businesses(search_filter)
                    self.logger.info(f"Found {len(businesses)} businesses on {platform}")
                    all_businesses.extend(businesses)
                
                # Add delay between platforms
                if len(platforms) > 1:
                    delay = self.config.scraping.get('delay_between_requests', 2)
                    self.logger.debug(f"Waiting {delay}s before next platform")
                    time.sleep(delay)
                    
            except Exception as e:
                self.logger.error(f"Error scraping {platform}: {str(e)}")
                continue
        
        return all_businesses
    
    def _search_concurrent(self, search_filter: SearchFilter, platforms: List[str]) -> List[Business]:
        """Search platforms concurrently using thread pool."""
        all_businesses = []
        max_workers = min(len(platforms), self.config.scraping.get('concurrent_requests', 2))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit scraping tasks
            future_to_platform = {}
            
            for platform in platforms:
                if platform in self.scrapers:
                    future = executor.submit(self._scrape_platform, platform, search_filter)
                    future_to_platform[future] = platform
            
            # Collect results as they complete
            for future in as_completed(future_to_platform):
                platform = future_to_platform[future]
                
                try:
                    businesses = future.result(timeout=300)  # 5 minute timeout per platform
                    self.logger.info(f"Found {len(businesses)} businesses on {platform}")
                    all_businesses.extend(businesses)
                    
                except Exception as e:
                    self.logger.error(f"Error scraping {platform}: {str(e)}")
        
        return all_businesses
    
    def _scrape_platform(self, platform: str, search_filter: SearchFilter) -> List[Business]:
        """Scrape a single platform (for use in concurrent execution)."""
        scraper_class = self.scrapers[platform]
        
        with scraper_class() as scraper:
            return scraper.search_businesses(search_filter)
    
    def get_business_details(self, business: Business, platforms: List[str] = None) -> Business:
        """Get detailed information for a business from specified platforms."""
        if platforms is None:
            platforms = business.data_sources
        
        enhanced_business = business
        
        for platform in platforms:
            if platform not in self.scrapers:
                continue
            
            try:
                scraper_class = self.scrapers[platform]
                business_url = getattr(business, f"{platform}_url")
                
                if not business_url:
                    self.logger.debug(f"No URL available for {platform}")
                    continue
                
                with scraper_class() as scraper:
                    detailed_business = scraper.get_business_details(business_url)
                    
                    if detailed_business:
                        enhanced_business = self._merge_business_data(enhanced_business, detailed_business)
                        
            except Exception as e:
                self.logger.error(f"Error getting details from {platform}: {str(e)}")
        
        return enhanced_business
    
    def get_reviews(self, business: Business, platforms: List[str] = None, max_reviews_per_platform: int = 25) -> List[Dict[str, Any]]:
        """Get reviews for a business from specified platforms."""
        if platforms is None:
            platforms = business.data_sources
        
        all_reviews = []
        
        for platform in platforms:
            if platform not in self.scrapers:
                continue
            
            try:
                scraper_class = self.scrapers[platform]
                business_url = getattr(business, f"{platform}_url")
                
                if not business_url:
                    continue
                
                with scraper_class() as scraper:
                    reviews = scraper.get_reviews(business_url, max_reviews_per_platform)
                    all_reviews.extend(reviews)
                    
            except Exception as e:
                self.logger.error(f"Error getting reviews from {platform}: {str(e)}")
        
        return all_reviews
    
    def _merge_business_data(self, base_business: Business, new_business: Business) -> Business:
        """Merge data from two business objects, preferring non-empty values."""
        
        # Helper function to choose better value
        def choose_value(base_val, new_val):
            if new_val and (not base_val or len(str(new_val)) > len(str(base_val))):
                return new_val
            return base_val
        
        # Update basic information
        base_business.name = choose_value(base_business.name, new_business.name)
        base_business.address = choose_value(base_business.address, new_business.address)
        base_business.city = choose_value(base_business.city, new_business.city)
        base_business.state = choose_value(base_business.state, new_business.state)
        base_business.zip_code = choose_value(base_business.zip_code, new_business.zip_code)
        
        # Update contact information
        base_business.phone = choose_value(base_business.phone, new_business.phone)
        base_business.website = choose_value(base_business.website, new_business.website)
        base_business.email = choose_value(base_business.email, new_business.email)
        
        # Update business details
        base_business.category = choose_value(base_business.category, new_business.category)
        base_business.cuisine_type = choose_value(base_business.cuisine_type, new_business.cuisine_type)
        base_business.price_level = choose_value(base_business.price_level, new_business.price_level)
        
        # Update location
        if new_business.latitude and new_business.longitude:
            base_business.latitude = new_business.latitude
            base_business.longitude = new_business.longitude
        
        # Update ratings (use average if both exist)
        if new_business.rating:
            if base_business.rating:
                base_business.rating = (base_business.rating + new_business.rating) / 2
            else:
                base_business.rating = new_business.rating
        
        # Update review count (use max)
        if new_business.review_count > base_business.review_count:
            base_business.review_count = new_business.review_count
        
        # Update hours
        if new_business.hours and not base_business.hours:
            base_business.hours = new_business.hours
        
        # Merge platform-specific URLs
        if new_business.yelp_url:
            base_business.yelp_url = new_business.yelp_url
        if new_business.yelp_id:
            base_business.yelp_id = new_business.yelp_id
        if new_business.google_url:
            base_business.google_url = new_business.google_url
        if new_business.google_place_id:
            base_business.google_place_id = new_business.google_place_id
        
        # Merge features (combine unique values)
        if new_business.features:
            combined_features = set(base_business.features + new_business.features)
            base_business.features = list(combined_features)
        
        # Merge photos (combine unique URLs)
        if new_business.photos:
            combined_photos = set(base_business.photos + new_business.photos)
            base_business.photos = list(combined_photos)
        
        # Merge data sources
        if new_business.data_sources:
            combined_sources = set(base_business.data_sources + new_business.data_sources)
            base_business.data_sources = list(combined_sources)
        
        # Merge reviews
        if new_business.reviews:
            # Combine reviews, avoiding duplicates based on review ID
            existing_review_ids = {review.id for review in base_business.reviews}
            for review in new_business.reviews:
                if review.id not in existing_review_ids:
                    base_business.reviews.append(review)
        
        # Update metadata
        base_business.last_updated = new_business.last_updated
        
        return base_business
    
    def get_available_platforms(self) -> List[str]:
        """Get list of available/enabled platforms."""
        return list(self.scrapers.keys())
    
    def is_platform_enabled(self, platform: str) -> bool:
        """Check if a platform is enabled."""
        return platform in self.scrapers 