"""Analytics dashboard for business data visualization."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from src.models import Business
from src.processors.sentiment_analyzer import SentimentAnalyzer
from src.config import config
from src.utils.logger import get_logger

class AnalyticsDashboard:
    """Generates analytics dashboard and visualizations."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.sentiment_analyzer = SentimentAnalyzer()
        
    def generate_analytics_report(self, businesses: List[Business], output_path: str = None) -> str:
        """Generate comprehensive analytics report."""
        if not businesses:
            raise ValueError("No businesses provided for analytics")
        
        self.logger.info(f"Generating analytics for {len(businesses)} businesses")
        
        # Create output directory
        output_dir = Path(output_path) if output_path else Path("data/exports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate individual charts
        charts = {}
        
        # 1. Cuisine Distribution
        charts['cuisine_distribution'] = self._create_cuisine_distribution_chart(businesses)
        
        # 2. Rating Distribution
        charts['rating_distribution'] = self._create_rating_distribution_chart(businesses)
        
        # 3. Price Level Analysis
        charts['price_analysis'] = self._create_price_level_chart(businesses)
        
        # 4. Geographic Distribution
        charts['geographic_distribution'] = self._create_geographic_chart(businesses)
        
        # 5. Review Count Analysis
        charts['review_analysis'] = self._create_review_count_chart(businesses)
        
        # 6. Sentiment Analysis
        if any(business.reviews for business in businesses):
            charts['sentiment_analysis'] = self._create_sentiment_analysis_chart(businesses)
        
        # 7. Top Businesses
        charts['top_businesses'] = self._create_top_businesses_chart(businesses)
        
        # 8. Data Source Comparison
        charts['data_sources'] = self._create_data_source_chart(businesses)
        
        # Generate HTML report
        report_path = self._generate_html_report(businesses, charts, output_dir)
        
        self.logger.info(f"✅ Analytics report generated: {report_path}")
        return report_path
    
    def _create_cuisine_distribution_chart(self, businesses: List[Business]) -> go.Figure:
        """Create cuisine type distribution chart."""
        cuisine_counts = {}
        for business in businesses:
            cuisine = business.cuisine_type or 'Unknown'
            cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1
        
        # Sort by count
        sorted_cuisines = sorted(cuisine_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Take top 15 to avoid overcrowding
        top_cuisines = sorted_cuisines[:15]
        
        fig = go.Figure(data=[
            go.Bar(
                x=[item[1] for item in top_cuisines],
                y=[item[0] for item in top_cuisines],
                orientation='h',
                marker=dict(
                    color=px.colors.qualitative.Set3[:len(top_cuisines)],
                    line=dict(color='black', width=0.5)
                )
            )
        ])
        
        fig.update_layout(
            title="Top Cuisine Types by Number of Businesses",
            xaxis_title="Number of Businesses",
            yaxis_title="Cuisine Type",
            height=600,
            margin=dict(l=150)
        )
        
        return fig
    
    def _create_rating_distribution_chart(self, businesses: List[Business]) -> go.Figure:
        """Create rating distribution chart."""
        ratings = [b.rating for b in businesses if b.rating is not None]
        
        if not ratings:
            # Create empty chart
            fig = go.Figure()
            fig.add_annotation(text="No rating data available", 
                             xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Create histogram
        fig = go.Figure(data=[
            go.Histogram(
                x=ratings,
                nbinsx=20,
                marker=dict(color='skyblue', line=dict(color='black', width=1))
            )
        ])
        
        fig.update_layout(
            title="Rating Distribution",
            xaxis_title="Rating",
            yaxis_title="Number of Businesses",
            height=400
        )
        
        # Add average line
        avg_rating = sum(ratings) / len(ratings)
        fig.add_vline(x=avg_rating, line_dash="dash", line_color="red",
                     annotation_text=f"Avg: {avg_rating:.2f}")
        
        return fig
    
    def _create_price_level_chart(self, businesses: List[Business]) -> go.Figure:
        """Create price level distribution chart."""
        price_counts = {}
        for business in businesses:
            price = business.price_level or 'Unknown'
            price_counts[price] = price_counts.get(price, 0) + 1
        
        # Define order for price levels
        price_order = ['$', '$$', '$$$', '$$$$', 'Unknown']
        ordered_prices = [(price, price_counts.get(price, 0)) for price in price_order if price_counts.get(price, 0) > 0]
        
        fig = go.Figure(data=[
            go.Pie(
                labels=[item[0] for item in ordered_prices],
                values=[item[1] for item in ordered_prices],
                hole=0.3,
                marker=dict(colors=px.colors.qualitative.Set2)
            )
        ])
        
        fig.update_layout(
            title="Price Level Distribution",
            height=400
        )
        
        return fig
    
    def _create_geographic_chart(self, businesses: List[Business]) -> go.Figure:
        """Create geographic distribution chart."""
        city_counts = {}
        for business in businesses:
            city = business.city or 'Unknown'
            city_counts[city] = city_counts.get(city, 0) + 1
        
        # Sort and take top 10 cities
        sorted_cities = sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        fig = go.Figure(data=[
            go.Bar(
                x=[item[0] for item in sorted_cities],
                y=[item[1] for item in sorted_cities],
                marker=dict(color='lightcoral')
            )
        ])
        
        fig.update_layout(
            title="Top Cities by Number of Businesses",
            xaxis_title="City",
            yaxis_title="Number of Businesses",
            height=400,
            xaxis=dict(tickangle=45)
        )
        
        return fig
    
    def _create_review_count_chart(self, businesses: List[Business]) -> go.Figure:
        """Create review count analysis chart."""
        review_counts = [b.review_count for b in businesses if b.review_count > 0]
        
        if not review_counts:
            fig = go.Figure()
            fig.add_annotation(text="No review data available", 
                             xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Create box plot
        fig = go.Figure(data=[
            go.Box(
                y=review_counts,
                name="Review Counts",
                marker=dict(color='lightgreen')
            )
        ])
        
        fig.update_layout(
            title="Review Count Distribution",
            yaxis_title="Number of Reviews",
            height=400
        )
        
        return fig
    
    def _create_sentiment_analysis_chart(self, businesses: List[Business]) -> go.Figure:
        """Create sentiment analysis chart."""
        # Analyze sentiment for all businesses
        businesses_with_sentiment = self.sentiment_analyzer.analyze_businesses(businesses.copy())
        
        # Collect sentiment data
        sentiment_data = []
        for business in businesses_with_sentiment:
            if business.reviews:
                summary = self.sentiment_analyzer.get_business_sentiment_summary(business)
                sentiment_data.append({
                    'business': business.name,
                    'positive': summary['positive_percentage'],
                    'negative': summary['negative_percentage'],
                    'neutral': summary['neutral_percentage'],
                    'total_reviews': summary['total_reviews']
                })
        
        if not sentiment_data:
            fig = go.Figure()
            fig.add_annotation(text="No sentiment data available", 
                             xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Sort by positive sentiment
        sentiment_data.sort(key=lambda x: x['positive'], reverse=True)
        
        # Take top 10 for readability
        top_sentiment = sentiment_data[:10]
        
        fig = go.Figure()
        
        # Add bars for each sentiment
        fig.add_trace(go.Bar(
            name='Positive',
            x=[item['business'] for item in top_sentiment],
            y=[item['positive'] for item in top_sentiment],
            marker_color='green'
        ))
        
        fig.add_trace(go.Bar(
            name='Neutral',
            x=[item['business'] for item in top_sentiment],
            y=[item['neutral'] for item in top_sentiment],
            marker_color='yellow'
        ))
        
        fig.add_trace(go.Bar(
            name='Negative',
            x=[item['business'] for item in top_sentiment],
            y=[item['negative'] for item in top_sentiment],
            marker_color='red'
        ))
        
        fig.update_layout(
            title="Sentiment Analysis - Top 10 Businesses by Positive Sentiment",
            xaxis_title="Business",
            yaxis_title="Percentage",
            barmode='stack',
            height=500,
            xaxis=dict(tickangle=45)
        )
        
        return fig
    
    def _create_top_businesses_chart(self, businesses: List[Business]) -> go.Figure:
        """Create top-rated businesses chart."""
        # Filter businesses with ratings and sort
        rated_businesses = [b for b in businesses if b.rating is not None]
        rated_businesses.sort(key=lambda x: (x.rating, x.review_count), reverse=True)
        
        # Take top 15
        top_businesses = rated_businesses[:15]
        
        fig = go.Figure()
        
        # Add rating bars
        fig.add_trace(go.Bar(
            name='Rating',
            x=[b.name for b in top_businesses],
            y=[b.rating for b in top_businesses],
            yaxis='y',
            marker=dict(color='gold')
        ))
        
        # Add review count on secondary y-axis
        fig.add_trace(go.Scatter(
            name='Review Count',
            x=[b.name for b in top_businesses],
            y=[b.review_count for b in top_businesses],
            yaxis='y2',
            mode='markers+lines',
            marker=dict(color='red', size=8),
            line=dict(color='red')
        ))
        
        fig.update_layout(
            title="Top Rated Businesses",
            xaxis_title="Business",
            yaxis=dict(title="Rating", side="left"),
            yaxis2=dict(title="Review Count", side="right", overlaying="y"),
            height=500,
            xaxis=dict(tickangle=45)
        )
        
        return fig
    
    def _create_data_source_chart(self, businesses: List[Business]) -> go.Figure:
        """Create data source comparison chart."""
        source_counts = {}
        for business in businesses:
            for source in business.data_sources:
                source_counts[source] = source_counts.get(source, 0) + 1
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(source_counts.keys()),
                values=list(source_counts.values()),
                hole=0.3,
                marker=dict(colors=px.colors.qualitative.Pastel)
            )
        ])
        
        fig.update_layout(
            title="Data Sources Distribution",
            height=400
        )
        
        return fig
    
    def _generate_html_report(self, businesses: List[Business], charts: Dict[str, go.Figure], output_dir: Path) -> str:
        """Generate HTML report with all charts and statistics."""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"analytics_report_{timestamp}.html"
        
        # Calculate summary statistics
        total_businesses = len(businesses)
        avg_rating = sum(b.rating for b in businesses if b.rating) / len([b for b in businesses if b.rating]) if any(b.rating for b in businesses) else 0
        total_reviews = sum(b.review_count for b in businesses)
        unique_cuisines = len(set(b.cuisine_type for b in businesses if b.cuisine_type))
        unique_cities = len(set(b.city for b in businesses if b.city))
        
        # Start HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Restaurant Business Directory - Analytics Report</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
                .stat-card {{ background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }}
                .stat-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
                .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
                .chart-container {{ background-color: white; margin-bottom: 30px; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .chart {{ width: 100%; height: 500px; }}
                .footer {{ background-color: #34495e; color: white; padding: 15px; border-radius: 10px; text-align: center; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🍽️ Restaurant Business Directory - Analytics Report</h1>
                <p>Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{total_businesses:,}</div>
                    <div class="stat-label">Total Businesses</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{avg_rating:.1f}⭐</div>
                    <div class="stat-label">Average Rating</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{total_reviews:,}</div>
                    <div class="stat-label">Total Reviews</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{unique_cuisines}</div>
                    <div class="stat-label">Cuisine Types</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{unique_cities}</div>
                    <div class="stat-label">Cities Covered</div>
                </div>
            </div>
        """
        
        # Add charts
        chart_counter = 0
        for chart_name, fig in charts.items():
            chart_counter += 1
            chart_div_id = f"chart_{chart_counter}"
            
            html_content += f"""
            <div class="chart-container">
                <div id="{chart_div_id}" class="chart"></div>
            </div>
            """
        
        # Add JavaScript to render charts
        html_content += """
        <script>
        """
        
        chart_counter = 0
        for chart_name, fig in charts.items():
            chart_counter += 1
            chart_div_id = f"chart_{chart_counter}"
            chart_json = fig.to_json()
            
            html_content += f"""
            Plotly.newPlot('{chart_div_id}', {chart_json});
            """
        
        html_content += """
        </script>
        
        <div class="footer">
            <p>📊 Analytics powered by Restaurant Business Directory Scraper</p>
            <p>Data sources: Yelp, Google Maps | Processing: Email validation, Sentiment analysis, Duplicate removal</p>
        </div>
        
        </body>
        </html>
        """
        
        # Write HTML file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(report_path)
    
    def generate_summary_statistics(self, businesses: List[Business]) -> Dict[str, Any]:
        """Generate summary statistics for businesses."""
        stats = {
            'total_businesses': len(businesses),
            'businesses_with_rating': len([b for b in businesses if b.rating]),
            'businesses_with_phone': len([b for b in businesses if b.phone]),
            'businesses_with_website': len([b for b in businesses if b.website]),
            'businesses_with_email': len([b for b in businesses if b.email]),
            'average_rating': 0,
            'median_rating': 0,
            'total_reviews': sum(b.review_count for b in businesses),
            'average_reviews': 0,
            'unique_cuisines': len(set(b.cuisine_type for b in businesses if b.cuisine_type)),
            'unique_cities': len(set(b.city for b in businesses if b.city)),
            'unique_states': len(set(b.state for b in businesses if b.state)),
            'price_distribution': {},
            'cuisine_distribution': {},
            'rating_distribution': {},
            'data_source_distribution': {}
        }
        
        # Calculate rating statistics
        ratings = [b.rating for b in businesses if b.rating]
        if ratings:
            stats['average_rating'] = sum(ratings) / len(ratings)
            stats['median_rating'] = sorted(ratings)[len(ratings) // 2]
        
        # Calculate review statistics
        review_counts = [b.review_count for b in businesses if b.review_count > 0]
        if review_counts:
            stats['average_reviews'] = sum(review_counts) / len(review_counts)
        
        # Price distribution
        for business in businesses:
            price = business.price_level or 'Unknown'
            stats['price_distribution'][price] = stats['price_distribution'].get(price, 0) + 1
        
        # Cuisine distribution
        for business in businesses:
            cuisine = business.cuisine_type or 'Unknown'
            stats['cuisine_distribution'][cuisine] = stats['cuisine_distribution'].get(cuisine, 0) + 1
        
        # Rating distribution
        for business in businesses:
            if business.rating:
                rating_range = f"{int(business.rating)}.0-{int(business.rating)}.9"
                stats['rating_distribution'][rating_range] = stats['rating_distribution'].get(rating_range, 0) + 1
        
        # Data source distribution
        for business in businesses:
            for source in business.data_sources:
                stats['data_source_distribution'][source] = stats['data_source_distribution'].get(source, 0) + 1
        
        return stats 