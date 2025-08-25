"""Data models for restaurant and business information."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

@dataclass
class BusinessHours:
    """Business operating hours."""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert to dictionary."""
        return {
            'monday': self.monday,
            'tuesday': self.tuesday,
            'wednesday': self.wednesday,
            'thursday': self.thursday,
            'friday': self.friday,
            'saturday': self.saturday,
            'sunday': self.sunday
        }

@dataclass
class Review:
    """Individual review data."""
    id: str
    author_name: str
    rating: float
    text: str
    date: datetime
    platform: str  # 'yelp' or 'google'
    helpful_votes: int = 0
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None  # 'positive', 'negative', 'neutral'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'author_name': self.author_name,
            'rating': self.rating,
            'text': self.text,
            'date': self.date.isoformat() if self.date else None,
            'platform': self.platform,
            'helpful_votes': self.helpful_votes,
            'sentiment_score': self.sentiment_score,
            'sentiment_label': self.sentiment_label
        }

@dataclass
class Business:
    """Business/restaurant data model."""
    # Basic Information
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    
    # Contact Information
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    
    # Business Details
    category: Optional[str] = None
    cuisine_type: Optional[str] = None
    price_level: Optional[str] = None  # $, $$, $$$, $$$$
    
    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Ratings and Reviews
    rating: Optional[float] = None
    review_count: int = 0
    reviews: List[Review] = field(default_factory=list)
    
    # Hours
    hours: Optional[BusinessHours] = None
    
    # Platform Information
    yelp_id: Optional[str] = None
    yelp_url: Optional[str] = None
    google_place_id: Optional[str] = None
    google_url: Optional[str] = None
    
    # Additional Data
    features: List[str] = field(default_factory=list)  # e.g., ['delivery', 'takeout', 'outdoor_seating']
    photos: List[str] = field(default_factory=list)  # URLs to photos
    
    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    data_sources: List[str] = field(default_factory=list)  # ['yelp', 'google']
    
    # Validation flags
    email_validated: bool = False
    is_duplicate: bool = False
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure data_sources is a list
        if not self.data_sources:
            self.data_sources = []
    
    @property
    def full_address(self) -> str:
        """Get full formatted address."""
        parts = [self.address, self.city, self.state, self.zip_code]
        return ", ".join([part for part in parts if part])
    
    @property
    def average_sentiment(self) -> Optional[float]:
        """Calculate average sentiment score from reviews."""
        if not self.reviews:
            return None
        
        sentiment_scores = [r.sentiment_score for r in self.reviews if r.sentiment_score is not None]
        if not sentiment_scores:
            return None
            
        return sum(sentiment_scores) / len(sentiment_scores)
    
    @property
    def sentiment_distribution(self) -> Dict[str, int]:
        """Get distribution of sentiment labels."""
        distribution = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for review in self.reviews:
            if review.sentiment_label in distribution:
                distribution[review.sentiment_label] += 1
                
        return distribution
    
    def add_review(self, review: Review) -> None:
        """Add a review to the business."""
        self.reviews.append(review)
        self.review_count = len(self.reviews)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert business to dictionary for export."""
        return {
            # Basic Information
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'country': self.country,
            'full_address': self.full_address,
            
            # Contact Information
            'phone': self.phone,
            'website': self.website,
            'email': self.email,
            'email_validated': self.email_validated,
            
            # Business Details
            'category': self.category,
            'cuisine_type': self.cuisine_type,
            'price_level': self.price_level,
            
            # Location
            'latitude': self.latitude,
            'longitude': self.longitude,
            
            # Ratings and Reviews
            'rating': self.rating,
            'review_count': self.review_count,
            'average_sentiment': self.average_sentiment,
            'sentiment_positive': self.sentiment_distribution['positive'],
            'sentiment_negative': self.sentiment_distribution['negative'],
            'sentiment_neutral': self.sentiment_distribution['neutral'],
            
            # Hours (flattened)
            'hours_monday': self.hours.monday if self.hours else None,
            'hours_tuesday': self.hours.tuesday if self.hours else None,
            'hours_wednesday': self.hours.wednesday if self.hours else None,
            'hours_thursday': self.hours.thursday if self.hours else None,
            'hours_friday': self.hours.friday if self.hours else None,
            'hours_saturday': self.hours.saturday if self.hours else None,
            'hours_sunday': self.hours.sunday if self.hours else None,
            
            # Platform Information
            'yelp_id': self.yelp_id,
            'yelp_url': self.yelp_url,
            'google_place_id': self.google_place_id,
            'google_url': self.google_url,
            
            # Additional Data
            'features': ', '.join(self.features),
            'photo_count': len(self.photos),
            
            # Metadata
            'scraped_at': self.scraped_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'data_sources': ', '.join(self.data_sources),
            'is_duplicate': self.is_duplicate
        }
    
    def to_json(self) -> str:
        """Convert business to JSON string."""
        data = self.to_dict()
        # Convert reviews to dict format
        data['reviews'] = [review.to_dict() for review in self.reviews]
        data['hours'] = self.hours.to_dict() if self.hours else None
        return json.dumps(data, default=str, indent=2)

@dataclass
class SearchFilter:
    """Search filter parameters."""
    city: Optional[str] = None
    radius: Optional[float] = None  # in miles
    cuisine_type: Optional[str] = None
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    min_reviews: Optional[int] = None
    keywords: Optional[str] = None
    price_levels: List[str] = field(default_factory=list)  # ['$', '$$', '$$$', '$$$$']
    features: List[str] = field(default_factory=list)  # ['delivery', 'takeout', etc.]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary."""
        return {
            'city': self.city,
            'radius': self.radius,
            'cuisine_type': self.cuisine_type,
            'min_rating': self.min_rating,
            'max_rating': self.max_rating,
            'min_reviews': self.min_reviews,
            'keywords': self.keywords,
            'price_levels': self.price_levels,
            'features': self.features
        } 