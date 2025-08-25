"""Yelp scraper implementation."""

import re
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus, urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from src.scrapers.base_scraper import BaseScraper
from src.models import Business, Review, BusinessHours, SearchFilter
from src.utils.logger import get_logger

class YelpScraper(BaseScraper):
    """Yelp scraper for restaurant and business data."""
    
    def __init__(self):
        super().__init__("yelp")
        self.base_url = "https://www.yelp.com"
        self.search_url = f"{self.base_url}/search"
        
    def search_businesses(self, search_filter: SearchFilter) -> List[Business]:
        """Search for businesses on Yelp based on filter criteria."""
        businesses = []
        
        try:
            # Build search URL
            search_url = self._build_search_url(search_filter)
            self.logger.info(f"Searching Yelp with URL: {search_url}")
            
            # Navigate to search page
            self.driver.get(search_url)
            self.random_delay()
            
            # Handle potential popups
            self.handle_popup()
            
            # Get business listings
            page_num = 1
            max_pages = 10  # Limit to prevent infinite scrolling
            
            while page_num <= max_pages:
                self.logger.info(f"Scraping Yelp page {page_num}")
                
                # Extract businesses from current page
                page_businesses = self._extract_businesses_from_page()
                if not page_businesses:
                    self.logger.info("No more businesses found")
                    break
                
                businesses.extend(page_businesses)
                self.logger.info(f"Found {len(page_businesses)} businesses on page {page_num}")
                
                # Check if we have enough results
                max_results = search_filter.min_reviews or 100  # Use as max results if set
                if len(businesses) >= max_results:
                    businesses = businesses[:max_results]
                    break
                
                # Try to go to next page
                if not self._go_to_next_page():
                    break
                    
                page_num += 1
                self.random_delay()
            
            self.logger.info(f"Total businesses found on Yelp: {len(businesses)}")
            
        except Exception as e:
            self.logger.error(f"Error searching Yelp: {str(e)}")
            
        return businesses
    
    def _build_search_url(self, search_filter: SearchFilter) -> str:
        """Build Yelp search URL from filter parameters."""
        params = []
        
        # Location
        if search_filter.city:
            params.append(f"find_loc={quote_plus(search_filter.city)}")
        
        # Search term/keywords
        search_term = "restaurants"
        if search_filter.keywords:
            search_term = search_filter.keywords
        elif search_filter.cuisine_type:
            search_term = f"{search_filter.cuisine_type} restaurants"
        
        params.append(f"find_desc={quote_plus(search_term)}")
        
        # Radius (Yelp uses different values)
        if search_filter.radius:
            # Convert miles to Yelp's radius values
            radius_map = {
                1: "1610",    # ~1 mile
                5: "8047",    # ~5 miles  
                10: "16093",  # ~10 miles
                25: "40234",  # ~25 miles
            }
            closest_radius = min(radius_map.keys(), key=lambda x: abs(x - search_filter.radius))
            params.append(f"l=g:{closest_radius}")
        
        url = f"{self.search_url}?" + "&".join(params)
        return url
    
    def _extract_businesses_from_page(self) -> List[Business]:
        """Extract business information from current search results page."""
        businesses = []
        
        try:
            # Find business containers
            business_containers = self.safe_find_elements(
                By.CSS_SELECTOR, 
                '[data-testid="serp-ia-card"], .businessName, .result, .search-result'
            )
            
            if not business_containers:
                # Try alternative selectors
                business_containers = self.safe_find_elements(By.CSS_SELECTOR, 'li[data-ad-logging-uid]')
            
            self.logger.debug(f"Found {len(business_containers)} business containers")
            
            for container in business_containers:
                try:
                    business = self._extract_business_from_container(container)
                    if business:
                        businesses.append(business)
                except Exception as e:
                    self.logger.debug(f"Error extracting business from container: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error extracting businesses from page: {str(e)}")
            
        return businesses
    
    def _extract_business_from_container(self, container) -> Optional[Business]:
        """Extract business information from a single container element."""
        try:
            # Business name and URL
            name_element = container.find_element(By.CSS_SELECTOR, 'a[data-analytics-label="biz-name"]')
            if not name_element:
                name_element = container.find_element(By.CSS_SELECTOR, '.businessName a, h3 a, h4 a')
            
            if not name_element:
                return None
                
            name = self.safe_get_text(name_element)
            business_url = self.safe_get_attribute(name_element, 'href')
            
            if not name:
                return None
            
            # Make URL absolute
            if business_url and not business_url.startswith('http'):
                business_url = urljoin(self.base_url, business_url)
            
            # Rating
            rating = None
            rating_element = container.find_element(By.CSS_SELECTOR, '[role="img"][aria-label*="star"]')
            if rating_element:
                aria_label = self.safe_get_attribute(rating_element, 'aria-label')
                rating_match = re.search(r'(\d+\.?\d*)\s*star', aria_label)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Review count
            review_count = 0
            review_element = container.find_element(By.CSS_SELECTOR, '[href*="reviews"]')
            if review_element:
                review_text = self.safe_get_text(review_element)
                review_match = re.search(r'(\d+)', review_text)
                if review_match:
                    review_count = int(review_match.group(1))
            
            # Price level
            price_level = None
            price_element = container.find_element(By.CSS_SELECTOR, '.priceRange')
            if price_element:
                price_level = self.safe_get_text(price_element)
            
            # Categories/Cuisine
            category = None
            cuisine_type = None
            category_elements = container.find_elements(By.CSS_SELECTOR, '.categoryLink')
            if category_elements:
                categories = [self.safe_get_text(el) for el in category_elements]
                category = categories[0] if categories else None
                cuisine_type = category  # Use first category as cuisine type
            
            # Address (basic from search results)
            address = ""
            city = ""
            state = ""
            zip_code = ""
            
            address_element = container.find_element(By.CSS_SELECTOR, '.secondaryAttributes')
            if address_element:
                address_text = self.safe_get_text(address_element)
                # Try to parse address components
                if address_text:
                    parts = address_text.split(',')
                    if len(parts) >= 2:
                        address = parts[0].strip()
                        location_part = parts[1].strip()
                        # Try to extract city, state, zip
                        location_match = re.match(r'(.+?)\s+([A-Z]{2})\s+(\d{5})', location_part)
                        if location_match:
                            city = location_match.group(1)
                            state = location_match.group(2)
                            zip_code = location_match.group(3)
                        else:
                            city = location_part
            
            # Create business object
            business = Business(
                name=name,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                rating=rating,
                review_count=review_count,
                category=category,
                cuisine_type=cuisine_type,
                price_level=price_level,
                yelp_url=business_url,
                data_sources=["yelp"]
            )
            
            return business
            
        except Exception as e:
            self.logger.debug(f"Error extracting business data: {str(e)}")
            return None
    
    def get_business_details(self, business_url: str) -> Optional[Business]:
        """Get detailed information about a specific business."""
        try:
            self.logger.info(f"Getting Yelp business details from: {business_url}")
            self.driver.get(business_url)
            self.random_delay()
            
            # Handle popups
            self.handle_popup()
            
            # Extract detailed information
            business_data = {}
            
            # Basic info
            business_data['name'] = self._get_business_name()
            business_data['rating'] = self._get_business_rating()
            business_data['review_count'] = self._get_review_count()
            business_data['price_level'] = self._get_price_level()
            
            # Contact info
            business_data['phone'] = self._get_phone_number()
            business_data['website'] = self._get_website()
            
            # Address
            address_info = self._get_address_info()
            business_data.update(address_info)
            
            # Categories
            business_data['category'], business_data['cuisine_type'] = self._get_categories()
            
            # Hours
            business_data['hours'] = self._get_business_hours()
            
            # Features/amenities
            business_data['features'] = self._get_features()
            
            # Photos
            business_data['photos'] = self._get_photo_urls()
            
            # Create Business object
            business = Business(
                name=business_data.get('name', ''),
                address=business_data.get('address', ''),
                city=business_data.get('city', ''),
                state=business_data.get('state', ''),
                zip_code=business_data.get('zip_code', ''),
                phone=business_data.get('phone'),
                website=business_data.get('website'),
                category=business_data.get('category'),
                cuisine_type=business_data.get('cuisine_type'),
                price_level=business_data.get('price_level'),
                rating=business_data.get('rating'),
                review_count=business_data.get('review_count', 0),
                hours=business_data.get('hours'),
                features=business_data.get('features', []),
                photos=business_data.get('photos', []),
                yelp_url=business_url,
                data_sources=["yelp"]
            )
            
            return business
            
        except Exception as e:
            self.logger.error(f"Error getting business details: {str(e)}")
            return None
    
    def get_reviews(self, business_url: str, max_reviews: int = 50) -> List[Dict[str, Any]]:
        """Get reviews for a specific business."""
        reviews = []
        
        try:
            # Navigate to reviews page
            reviews_url = business_url.rstrip('/') + '/reviews'
            self.logger.info(f"Getting Yelp reviews from: {reviews_url}")
            
            self.driver.get(reviews_url)
            self.random_delay()
            
            # Handle popups
            self.handle_popup()
            
            # Extract reviews
            reviews = self._extract_reviews_from_page(max_reviews)
            
        except Exception as e:
            self.logger.error(f"Error getting reviews: {str(e)}")
            
        return reviews
    
    def _get_business_name(self) -> str:
        """Extract business name."""
        selectors = [
            'h1[data-testid="page-title"]',
            'h1.page-title',
            'h1'
        ]
        
        for selector in selectors:
            element = self.safe_find_element(By.CSS_SELECTOR, selector)
            if element:
                return self.safe_get_text(element)
        
        return ""
    
    def _get_business_rating(self) -> Optional[float]:
        """Extract business rating."""
        rating_element = self.safe_find_element(By.CSS_SELECTOR, '[role="img"][aria-label*="star rating"]')
        if rating_element:
            aria_label = self.safe_get_attribute(rating_element, 'aria-label')
            rating_match = re.search(r'(\d+\.?\d*)\s*star', aria_label)
            if rating_match:
                return float(rating_match.group(1))
        return None
    
    def _get_review_count(self) -> int:
        """Extract review count."""
        review_element = self.safe_find_element(By.CSS_SELECTOR, '[href*="reviews"]')
        if review_element:
            review_text = self.safe_get_text(review_element)
            review_match = re.search(r'(\d+)', review_text)
            if review_match:
                return int(review_match.group(1))
        return 0
    
    def _get_price_level(self) -> Optional[str]:
        """Extract price level."""
        price_element = self.safe_find_element(By.CSS_SELECTOR, '.priceRange')
        if price_element:
            return self.safe_get_text(price_element)
        return None
    
    def _get_phone_number(self) -> Optional[str]:
        """Extract phone number."""
        phone_element = self.safe_find_element(By.CSS_SELECTOR, '[href^="tel:"]')
        if phone_element:
            return self.safe_get_text(phone_element)
        return None
    
    def _get_website(self) -> Optional[str]:
        """Extract website URL."""
        website_element = self.safe_find_element(By.CSS_SELECTOR, 'a[href*="biz_redir"]')
        if website_element:
            return self.safe_get_attribute(website_element, 'href')
        return None
    
    def _get_address_info(self) -> Dict[str, str]:
        """Extract address information."""
        address_info = {
            'address': '',
            'city': '',
            'state': '',
            'zip_code': ''
        }
        
        address_element = self.safe_find_element(By.CSS_SELECTOR, '[data-testid="business-address"]')
        if address_element:
            address_text = self.safe_get_text(address_element)
            # Parse address components
            lines = address_text.split('\n')
            if len(lines) >= 2:
                address_info['address'] = lines[0]
                location_line = lines[1]
                # Extract city, state, zip
                location_match = re.match(r'(.+?),\s*([A-Z]{2})\s+(\d{5})', location_line)
                if location_match:
                    address_info['city'] = location_match.group(1)
                    address_info['state'] = location_match.group(2)
                    address_info['zip_code'] = location_match.group(3)
        
        return address_info
    
    def _get_categories(self) -> tuple:
        """Extract categories and cuisine type."""
        category_elements = self.safe_find_elements(By.CSS_SELECTOR, '.categoryLink')
        if category_elements:
            categories = [self.safe_get_text(el) for el in category_elements]
            category = categories[0] if categories else None
            cuisine_type = category  # Use first category as cuisine type
            return category, cuisine_type
        return None, None
    
    def _get_business_hours(self) -> Optional[BusinessHours]:
        """Extract business hours."""
        # Implementation for extracting hours would go here
        # This is a simplified version
        return None
    
    def _get_features(self) -> List[str]:
        """Extract business features/amenities."""
        features = []
        # Implementation for extracting features would go here
        return features
    
    def _get_photo_urls(self) -> List[str]:
        """Extract photo URLs."""
        photos = []
        # Implementation for extracting photos would go here
        return photos
    
    def _extract_reviews_from_page(self, max_reviews: int) -> List[Dict[str, Any]]:
        """Extract reviews from current page."""
        reviews = []
        # Implementation for extracting reviews would go here
        return reviews
    
    def _go_to_next_page(self) -> bool:
        """Navigate to next page of search results."""
        try:
            next_button = self.safe_find_element(By.CSS_SELECTOR, '[aria-label="Next"]')
            if next_button and next_button.is_enabled():
                next_button.click()
                self.random_delay()
                return True
        except Exception as e:
            self.logger.debug(f"Error going to next page: {str(e)}")
        
        return False 