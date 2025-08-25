"""Sentiment analysis for business reviews."""

from typing import List, Dict, Any, Tuple
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.models import Business, Review
from src.utils.logger import get_logger

class SentimentAnalyzer:
    """Analyzes sentiment of business reviews."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.vader_analyzer = SentimentIntensityAnalyzer()
    
    def analyze_businesses(self, businesses: List[Business]) -> List[Business]:
        """Analyze sentiment for all reviews in business list."""
        self.logger.info(f"Analyzing sentiment for {len(businesses)} businesses")
        
        total_reviews = 0
        for business in businesses:
            if business.reviews:
                business.reviews = self.analyze_reviews(business.reviews)
                total_reviews += len(business.reviews)
        
        self.logger.info(f"✅ Sentiment analysis completed for {total_reviews} reviews")
        return businesses
    
    def analyze_reviews(self, reviews: List[Review]) -> List[Review]:
        """Analyze sentiment for a list of reviews."""
        for review in reviews:
            if review.text:
                sentiment_score, sentiment_label = self.analyze_text(review.text)
                review.sentiment_score = sentiment_score
                review.sentiment_label = sentiment_label
        
        return reviews
    
    def analyze_text(self, text: str) -> Tuple[float, str]:
        """Analyze sentiment of a single text."""
        if not text or not text.strip():
            return 0.0, 'neutral'
        
        try:
            # Use VADER sentiment analyzer (better for social media text)
            vader_scores = self.vader_analyzer.polarity_scores(text)
            compound_score = vader_scores['compound']
            
            # Use TextBlob as backup
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity
            
            # Combine scores (weighted average)
            combined_score = (compound_score * 0.7) + (textblob_polarity * 0.3)
            
            # Determine sentiment label
            if combined_score >= 0.05:
                sentiment_label = 'positive'
            elif combined_score <= -0.05:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
            
            return combined_score, sentiment_label
            
        except Exception as e:
            self.logger.debug(f"Error analyzing sentiment: {str(e)}")
            return 0.0, 'neutral'
    
    def get_business_sentiment_summary(self, business: Business) -> Dict[str, Any]:
        """Get sentiment summary for a business."""
        if not business.reviews:
            return {
                'average_sentiment': None,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'total_reviews': 0
            }
        
        positive_count = len([r for r in business.reviews if r.sentiment_label == 'positive'])
        negative_count = len([r for r in business.reviews if r.sentiment_label == 'negative'])
        neutral_count = len([r for r in business.reviews if r.sentiment_label == 'neutral'])
        
        sentiment_scores = [r.sentiment_score for r in business.reviews if r.sentiment_score is not None]
        average_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None
        
        return {
            'average_sentiment': average_sentiment,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'total_reviews': len(business.reviews),
            'positive_percentage': (positive_count / len(business.reviews)) * 100,
            'negative_percentage': (negative_count / len(business.reviews)) * 100,
            'neutral_percentage': (neutral_count / len(business.reviews)) * 100
        }
    
    def get_trending_sentiments(self, businesses: List[Business], top_n: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Get businesses with trending positive/negative sentiments."""
        business_sentiments = []
        
        for business in businesses:
            summary = self.get_business_sentiment_summary(business)
            if summary['total_reviews'] >= 5:  # Minimum reviews threshold
                business_sentiments.append({
                    'business': business,
                    'summary': summary
                })
        
        # Sort by positive percentage
        most_positive = sorted(
            business_sentiments,
            key=lambda x: x['summary']['positive_percentage'],
            reverse=True
        )[:top_n]
        
        # Sort by negative percentage
        most_negative = sorted(
            business_sentiments,
            key=lambda x: x['summary']['negative_percentage'],
            reverse=True
        )[:top_n]
        
        return {
            'most_positive': [
                {
                    'name': item['business'].name,
                    'positive_percentage': item['summary']['positive_percentage'],
                    'total_reviews': item['summary']['total_reviews'],
                    'average_sentiment': item['summary']['average_sentiment']
                }
                for item in most_positive
            ],
            'most_negative': [
                {
                    'name': item['business'].name,
                    'negative_percentage': item['summary']['negative_percentage'],
                    'total_reviews': item['summary']['total_reviews'],
                    'average_sentiment': item['summary']['average_sentiment']
                }
                for item in most_negative
            ]
        } 