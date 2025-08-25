"""Data processor for validation, filtering, and duplicate removal."""

import re
import hashlib
from typing import List, Set, Dict, Any, Optional
from email_validator import validate_email, EmailNotValidError
from difflib import SequenceMatcher

from src.models import Business, SearchFilter
from src.config import config
from src.utils.logger import get_logger

class DataProcessor:
    """Processes and validates business data."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.duplicate_threshold = 0.85  # Similarity threshold for duplicate detection
        
    def process_businesses(self, businesses: List[Business], search_filter: SearchFilter = None) -> List[Business]:
        """Process list of businesses with validation, filtering, and deduplication."""
        self.logger.info(f"Processing {len(businesses)} businesses")
        
        # Step 1: Apply filters
        if search_filter:
            businesses = self.apply_filters(businesses, search_filter)
            self.logger.info(f"After filtering: {len(businesses)} businesses")
        
        # Step 2: Validate and clean data
        businesses = self.validate_and_clean(businesses)
        self.logger.info(f"After validation: {len(businesses)} businesses")
        
        # Step 3: Remove duplicates
        businesses = self.remove_duplicates(businesses)
        self.logger.info(f"After deduplication: {len(businesses)} businesses")
        
        # Step 4: Validate emails if enabled
        if self.config.get('email_validation.enabled', True):
            businesses = self.validate_emails(businesses)
            self.logger.info(f"Email validation completed")
        
        self.logger.info(f"✅ Data processing completed: {len(businesses)} businesses")
        return businesses
    
    def apply_filters(self, businesses: List[Business], search_filter: SearchFilter) -> List[Business]:
        """Apply search filters to business list."""
        filtered_businesses = []
        
        for business in businesses:
            if self._passes_filters(business, search_filter):
                filtered_businesses.append(business)
        
        return filtered_businesses
    
    def _passes_filters(self, business: Business, search_filter: SearchFilter) -> bool:
        """Check if business passes all filter criteria."""
        
        # Rating filters
        if search_filter.min_rating and business.rating:
            if business.rating < search_filter.min_rating:
                return False
        
        if search_filter.max_rating and business.rating:
            if business.rating > search_filter.max_rating:
                return False
        
        # Review count filter
        if search_filter.min_reviews:
            if business.review_count < search_filter.min_reviews:
                return False
        
        # Cuisine type filter
        if search_filter.cuisine_type:
            if business.cuisine_type:
                if search_filter.cuisine_type.lower() not in business.cuisine_type.lower():
                    return False
            else:
                return False
        
        # Keywords filter
        if search_filter.keywords:
            keywords = search_filter.keywords.lower()
            searchable_text = f"{business.name} {business.category} {business.cuisine_type}".lower()
            if keywords not in searchable_text:
                return False
        
        # Price level filter
        if search_filter.price_levels:
            if business.price_level not in search_filter.price_levels:
                return False
        
        # Features filter
        if search_filter.features:
            business_features = [f.lower() for f in business.features]
            for required_feature in search_filter.features:
                if required_feature.lower() not in business_features:
                    return False
        
        return True
    
    def validate_and_clean(self, businesses: List[Business]) -> List[Business]:
        """Validate and clean business data."""
        cleaned_businesses = []
        
        for business in businesses:
            # Skip businesses without essential data
            if not business.name or not business.name.strip():
                self.logger.debug(f"Skipping business without name")
                continue
            
            # Clean and validate data
            business = self._clean_business_data(business)
            
            # Validate required fields
            if self._is_valid_business(business):
                cleaned_businesses.append(business)
            else:
                self.logger.debug(f"Skipping invalid business: {business.name}")
        
        return cleaned_businesses
    
    def _clean_business_data(self, business: Business) -> Business:
        """Clean and normalize business data."""
        
        # Clean name
        business.name = self._clean_text(business.name)
        
        # Clean address components
        business.address = self._clean_text(business.address) if business.address else ""
        business.city = self._clean_text(business.city) if business.city else ""
        business.state = self._clean_text(business.state) if business.state else ""
        business.zip_code = self._clean_zip_code(business.zip_code) if business.zip_code else ""
        
        # Clean phone number
        if business.phone:
            business.phone = self._clean_phone_number(business.phone)
        
        # Clean website URL
        if business.website:
            business.website = self._clean_url(business.website)
        
        # Clean email
        if business.email:
            business.email = self._clean_email(business.email)
        
        # Clean category and cuisine type
        business.category = self._clean_text(business.category) if business.category else None
        business.cuisine_type = self._clean_text(business.cuisine_type) if business.cuisine_type else None
        
        return business
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\-\.\,\&\'\(\)\/]', '', text)
        
        return text
    
    def _clean_phone_number(self, phone: str) -> str:
        """Clean and normalize phone number."""
        # Remove all non-digit characters except +
        phone = re.sub(r'[^\d\+]', '', phone)
        
        # Format US phone numbers
        if len(phone) == 10:
            phone = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
        elif len(phone) == 11 and phone.startswith('1'):
            phone = f"({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
        
        return phone
    
    def _clean_zip_code(self, zip_code: str) -> str:
        """Clean and normalize ZIP code."""
        # Extract 5-digit ZIP code
        zip_match = re.search(r'(\d{5})', zip_code)
        return zip_match.group(1) if zip_match else zip_code
    
    def _clean_url(self, url: str) -> str:
        """Clean and normalize URL."""
        url = url.strip()
        
        # Add http:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        return url
    
    def _clean_email(self, email: str) -> str:
        """Clean and normalize email."""
        return email.strip().lower()
    
    def _is_valid_business(self, business: Business) -> bool:
        """Check if business has valid essential data."""
        
        # Must have name
        if not business.name or len(business.name.strip()) < 2:
            return False
        
        # Must have some location information
        if not any([business.address, business.city, business.state]):
            return False
        
        # Validate rating if present
        if business.rating is not None:
            if not (0 <= business.rating <= 5):
                return False
        
        # Validate review count
        if business.review_count < 0:
            return False
        
        return True
    
    def remove_duplicates(self, businesses: List[Business]) -> List[Business]:
        """Remove duplicate businesses based on name and location similarity."""
        unique_businesses = []
        seen_signatures = set()
        
        for business in businesses:
            # Create a signature for quick duplicate detection
            signature = self._create_business_signature(business)
            
            if signature in seen_signatures:
                business.is_duplicate = True
                continue
            
            # Check for similar businesses (more comprehensive)
            is_duplicate = False
            for existing_business in unique_businesses:
                if self._are_duplicates(business, existing_business):
                    business.is_duplicate = True
                    is_duplicate = True
                    
                    # Merge data from duplicate into existing business
                    self._merge_duplicate_data(existing_business, business)
                    break
            
            if not is_duplicate:
                seen_signatures.add(signature)
                unique_businesses.append(business)
        
        duplicates_removed = len(businesses) - len(unique_businesses)
        if duplicates_removed > 0:
            self.logger.info(f"Removed {duplicates_removed} duplicate businesses")
        
        return unique_businesses
    
    def _create_business_signature(self, business: Business) -> str:
        """Create a signature for quick duplicate detection."""
        # Normalize name and address for comparison
        name = re.sub(r'[^\w]', '', business.name.lower()) if business.name else ""
        address = re.sub(r'[^\w]', '', business.address.lower()) if business.address else ""
        city = business.city.lower() if business.city else ""
        
        signature_text = f"{name}_{address}_{city}"
        return hashlib.md5(signature_text.encode()).hexdigest()
    
    def _are_duplicates(self, business1: Business, business2: Business) -> bool:
        """Check if two businesses are duplicates based on similarity."""
        
        # Compare names
        name_similarity = self._calculate_similarity(business1.name, business2.name)
        if name_similarity < 0.8:  # Names must be very similar
            return False
        
        # Compare addresses if available
        if business1.address and business2.address:
            address_similarity = self._calculate_similarity(business1.address, business2.address)
            if address_similarity < 0.7:
                return False
        
        # Compare cities
        if business1.city and business2.city:
            city_similarity = self._calculate_similarity(business1.city, business2.city)
            if city_similarity < 0.8:
                return False
        
        # If we get here, they're likely duplicates
        return True
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _merge_duplicate_data(self, primary: Business, duplicate: Business):
        """Merge data from duplicate business into primary business."""
        
        # Merge contact information
        if not primary.phone and duplicate.phone:
            primary.phone = duplicate.phone
        
        if not primary.website and duplicate.website:
            primary.website = duplicate.website
        
        if not primary.email and duplicate.email:
            primary.email = duplicate.email
        
        # Merge platform URLs
        if duplicate.yelp_url and not primary.yelp_url:
            primary.yelp_url = duplicate.yelp_url
            primary.yelp_id = duplicate.yelp_id
        
        if duplicate.google_url and not primary.google_url:
            primary.google_url = duplicate.google_url
            primary.google_place_id = duplicate.google_place_id
        
        # Merge data sources
        for source in duplicate.data_sources:
            if source not in primary.data_sources:
                primary.data_sources.append(source)
        
        # Use better rating if available
        if duplicate.rating and (not primary.rating or duplicate.review_count > primary.review_count):
            primary.rating = duplicate.rating
        
        # Use higher review count
        if duplicate.review_count > primary.review_count:
            primary.review_count = duplicate.review_count
        
        # Merge features
        for feature in duplicate.features:
            if feature not in primary.features:
                primary.features.append(feature)
        
        # Merge photos
        for photo in duplicate.photos:
            if photo not in primary.photos:
                primary.photos.append(photo)
    
    def validate_emails(self, businesses: List[Business]) -> List[Business]:
        """Validate email addresses for businesses."""
        validated_count = 0
        
        for business in businesses:
            if business.email:
                try:
                    # Basic email validation
                    valid = validate_email(business.email)
                    business.email = valid.email  # Normalized email
                    business.email_validated = True
                    validated_count += 1
                    
                except EmailNotValidError:
                    self.logger.debug(f"Invalid email for {business.name}: {business.email}")
                    business.email = None
                    business.email_validated = False
        
        self.logger.info(f"Validated {validated_count} email addresses")
        return businesses
    
    def extract_emails_from_websites(self, businesses: List[Business]) -> List[Business]:
        """Extract email addresses from business websites (optional enhancement)."""
        # This could be implemented to scrape emails from websites
        # For now, it's a placeholder
        return businesses
    
    def enrich_business_data(self, businesses: List[Business]) -> List[Business]:
        """Enrich business data with additional information."""
        # This could include geocoding addresses, extracting additional data, etc.
        return businesses 