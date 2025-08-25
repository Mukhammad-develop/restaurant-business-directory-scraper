"""Google Maps scraper implementation."""

import re
import json
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.scrapers.base_scraper import BaseScraper
from src.models import Business, Review, BusinessHours, SearchFilter
from src.utils.logger import get_logger

class GoogleMapsScraper(BaseScraper):
    """Google Maps scraper for restaurant and business data."""
    
    def __init__(self):
        super().__init__("google_maps")
        self.base_url = "https://maps.google.com"
        
    def search_businesses(self, search_filter: SearchFilter) -> List[Business]:
        """Search for businesses on Google Maps based on filter criteria."""
        businesses = []
        
        try:
            # Build search query
            search_query = self._build_search_query(search_filter)
            self.logger.info(f"Searching Google Maps for: {search_query}")
            
            # Navigate to Google Maps
            self.driver.get(self.base_url)
            self.random_delay()
            
            # Handle potential popups/consent
            self._handle_consent_popup()
            
            # Perform search
            self._perform_search(search_query)
            
            # Wait for results to load
            self._wait_for_results()
            
            # Extract businesses from search results
            businesses = self._extract_businesses_from_results()
            
            self.logger.info(f"Total businesses found on Google Maps: {len(businesses)}")
            
        except Exception as e:
            self.logger.error(f"Error searching Google Maps: {str(e)}")
            
        return businesses
    
    def _build_search_query(self, search_filter: SearchFilter) -> str:
        """Build Google Maps search query from filter parameters."""
        query_parts = []
        
        # Base search term
        if search_filter.keywords:
            query_parts.append(search_filter.keywords)
        elif search_filter.cuisine_type:
            query_parts.append(f"{search_filter.cuisine_type} restaurants")
        else:
            query_parts.append("restaurants")
        
        # Location
        if search_filter.city:
            query_parts.append(f"in {search_filter.city}")
        
        return " ".join(query_parts)
    
    def _handle_consent_popup(self):
        """Handle Google's consent popup if it appears."""
        try:
            # Look for consent buttons
            consent_selectors = [
                '[data-testid="accept-all-button"]',
                'button[aria-label*="Accept"]',
                'button:contains("Accept all")',
                'button:contains("I agree")'
            ]
            
            for selector in consent_selectors:
                try:
                    consent_btn = self.safe_find_element(By.CSS_SELECTOR, selector, timeout=5)
                    if consent_btn:
                        consent_btn.click()
                        self.logger.debug("Accepted consent popup")
                        time.sleep(2)
                        return
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Error handling consent popup: {str(e)}")
    
    def _perform_search(self, query: str):
        """Perform search on Google Maps."""
        try:
            # Find search box
            search_box = self.safe_find_element(By.ID, "searchboxinput")
            if not search_box:
                search_box = self.safe_find_element(By.CSS_SELECTOR, 'input[data-testid="searchbox-input"]')
            
            if search_box:
                search_box.clear()
                search_box.send_keys(query)
                search_box.send_keys(Keys.RETURN)
                self.random_delay(2, 4)
            else:
                raise Exception("Could not find search box")
                
        except Exception as e:
            self.logger.error(f"Error performing search: {str(e)}")
            raise
    
    def _wait_for_results(self):
        """Wait for search results to load."""
        try:
            # Wait for results container to appear
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="main"]'))
            )
            
            # Additional wait for results to populate
            time.sleep(3)
            
        except Exception as e:
            self.logger.error(f"Error waiting for results: {str(e)}")
    
    def _extract_businesses_from_results(self) -> List[Business]:
        """Extract business information from search results."""
        businesses = []
        
        try:
            # Scroll to load more results
            self._scroll_results_panel()
            
            # Find business elements
            business_elements = self._find_business_elements()
            
            self.logger.info(f"Found {len(business_elements)} business elements")
            
            for element in business_elements:
                try:
                    business = self._extract_business_from_element(element)
                    if business:
                        businesses.append(business)
                except Exception as e:
                    self.logger.debug(f"Error extracting business: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error extracting businesses: {str(e)}")
            
        return businesses
    
    def _scroll_results_panel(self):
        """Scroll the results panel to load more businesses."""
        try:
            # Find the scrollable results container
            results_container = self.safe_find_element(
                By.CSS_SELECTOR, 
                '[role="main"] div[data-testid="results-container"], [role="main"] div[tabindex="-1"]'
            )
            
            if results_container:
                # Scroll multiple times to load more results
                for _ in range(5):
                    self.driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight", 
                        results_container
                    )
                    time.sleep(2)
                    
        except Exception as e:
            self.logger.debug(f"Error scrolling results panel: {str(e)}")
    
    def _find_business_elements(self) -> List:
        """Find business elements in the results."""
        selectors = [
            '[data-result-index]',
            '[role="article"]',
            'div[jsaction*="mouseover"]',
            'a[data-cid]'
        ]
        
        for selector in selectors:
            elements = self.safe_find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements
                
        return []
    
    def _extract_business_from_element(self, element) -> Optional[Business]:
        """Extract business information from a single element."""
        try:
            # Business name
            name_element = element.find_element(By.CSS_SELECTOR, 'div[role="button"] span, h3, .fontHeadlineSmall')
            if not name_element:
                return None
                
            name = self.safe_get_text(name_element)
            if not name:
                return None
            
            # Rating
            rating = None
            rating_element = element.find_element(By.CSS_SELECTOR, 'span[aria-label*="star"], .fontBodyMedium span')
            if rating_element:
                rating_text = self.safe_get_text(rating_element)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Review count
            review_count = 0
            review_elements = element.find_elements(By.CSS_SELECTOR, 'span[aria-label*="review"], .fontBodyMedium span')
            for review_element in review_elements:
                review_text = self.safe_get_text(review_element)
                review_match = re.search(r'(\d+)\s*review', review_text)
                if review_match:
                    review_count = int(review_match.group(1))
                    break
            
            # Price level
            price_level = None
            price_elements = element.find_elements(By.CSS_SELECTOR, 'span[aria-label*="Price"], span')
            for price_element in price_elements:
                price_text = self.safe_get_text(price_element)
                if re.match(r'^\$+$', price_text):
                    price_level = price_text
                    break
            
            # Category/Cuisine type
            category = None
            cuisine_type = None
            category_elements = element.find_elements(By.CSS_SELECTOR, '.fontBodyMedium span')
            for cat_element in category_elements:
                cat_text = self.safe_get_text(cat_element)
                if cat_text and not re.match(r'^\d+\.?\d*$', cat_text) and 'review' not in cat_text.lower():
                    category = cat_text
                    cuisine_type = cat_text
                    break
            
            # Address (basic)
            address = ""
            city = ""
            state = ""
            zip_code = ""
            
            address_elements = element.find_elements(By.CSS_SELECTOR, '.fontBodyMedium')
            for addr_element in address_elements:
                addr_text = self.safe_get_text(addr_element)
                if addr_text and ('st' in addr_text.lower() or 'ave' in addr_text.lower() or 'rd' in addr_text.lower()):
                    address = addr_text
                    break
            
            # Get business URL by clicking and extracting from URL
            business_url = None
            try:
                # Try to get the business URL
                element.click()
                time.sleep(2)
                current_url = self.driver.current_url
                if '/place/' in current_url:
                    business_url = current_url
            except:
                pass
            
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
                google_url=business_url,
                data_sources=["google"]
            )
            
            return business
            
        except Exception as e:
            self.logger.debug(f"Error extracting business data: {str(e)}")
            return None
    
    def get_business_details(self, business_url: str) -> Optional[Business]:
        """Get detailed information about a specific business."""
        try:
            self.logger.info(f"Getting Google Maps business details from: {business_url}")
            self.driver.get(business_url)
            self.random_delay(3, 5)
            
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
            
            # Features
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
                google_url=business_url,
                data_sources=["google"]
            )
            
            return business
            
        except Exception as e:
            self.logger.error(f"Error getting business details: {str(e)}")
            return None
    
    def get_reviews(self, business_url: str, max_reviews: int = 50) -> List[Dict[str, Any]]:
        """Get reviews for a specific business."""
        reviews = []
        
        try:
            self.logger.info(f"Getting Google Maps reviews from: {business_url}")
            self.driver.get(business_url)
            self.random_delay()
            
            # Click on reviews tab
            reviews_button = self.safe_find_element(
                By.CSS_SELECTOR, 
                'button[data-tab-index="1"], button:contains("Reviews")'
            )
            if reviews_button:
                reviews_button.click()
                self.random_delay()
            
            # Extract reviews
            reviews = self._extract_reviews_from_page(max_reviews)
            
        except Exception as e:
            self.logger.error(f"Error getting reviews: {str(e)}")
            
        return reviews
    
    def _get_business_name(self) -> str:
        """Extract business name."""
        selectors = [
            'h1[data-attrid="title"]',
            'h1.fontHeadlineLarge',
            'h1'
        ]
        
        for selector in selectors:
            element = self.safe_find_element(By.CSS_SELECTOR, selector)
            if element:
                return self.safe_get_text(element)
        
        return ""
    
    def _get_business_rating(self) -> Optional[float]:
        """Extract business rating."""
        rating_element = self.safe_find_element(By.CSS_SELECTOR, 'div.F7nice span[aria-hidden="true"]')
        if rating_element:
            rating_text = self.safe_get_text(rating_element)
            try:
                return float(rating_text)
            except ValueError:
                pass
        return None
    
    def _get_review_count(self) -> int:
        """Extract review count."""
        review_element = self.safe_find_element(By.CSS_SELECTOR, 'button[data-tab-index="1"] span')
        if review_element:
            review_text = self.safe_get_text(review_element)
            review_match = re.search(r'(\d+)', review_text.replace(',', ''))
            if review_match:
                return int(review_match.group(1))
        return 0
    
    def _get_price_level(self) -> Optional[str]:
        """Extract price level."""
        price_element = self.safe_find_element(By.CSS_SELECTOR, 'span[aria-label*="Price"]')
        if price_element:
            return self.safe_get_text(price_element)
        return None
    
    def _get_phone_number(self) -> Optional[str]:
        """Extract phone number."""
        phone_button = self.safe_find_element(
            By.CSS_SELECTOR, 
            'button[data-item-id*="phone"], button[aria-label*="phone"]'
        )
        if phone_button:
            return self.safe_get_text(phone_button)
        return None
    
    def _get_website(self) -> Optional[str]:
        """Extract website URL."""
        website_element = self.safe_find_element(
            By.CSS_SELECTOR, 
            'a[data-item-id*="authority"], a[aria-label*="Website"]'
        )
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
        
        address_button = self.safe_find_element(
            By.CSS_SELECTOR, 
            'button[data-item-id*="address"]'
        )
        if address_button:
            address_text = self.safe_get_text(address_button)
            if address_text:
                # Try to parse address components
                parts = address_text.split(',')
                if len(parts) >= 2:
                    address_info['address'] = parts[0].strip()
                    if len(parts) >= 3:
                        address_info['city'] = parts[1].strip()
                        location_part = parts[2].strip()
                        # Extract state and zip
                        location_match = re.match(r'([A-Z]{2})\s+(\d{5})', location_part)
                        if location_match:
                            address_info['state'] = location_match.group(1)
                            address_info['zip_code'] = location_match.group(2)
        
        return address_info
    
    def _get_categories(self) -> tuple:
        """Extract categories and cuisine type."""
        category_element = self.safe_find_element(By.CSS_SELECTOR, 'button[jsaction*="category"]')
        if category_element:
            category_text = self.safe_get_text(category_element)
            return category_text, category_text
        return None, None
    
    def _get_business_hours(self) -> Optional[BusinessHours]:
        """Extract business hours."""
        # Implementation for extracting hours would go here
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