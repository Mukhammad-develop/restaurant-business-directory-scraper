"""Interactive map generator for business locations."""

import folium
from folium import plugins
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

from src.models import Business
from src.config import config
from src.utils.logger import get_logger

class MapGenerator:
    """Generates interactive maps for business locations."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.viz_config = self.config.visualization
        
    def generate_business_map(self, businesses: List[Business], output_path: str = None) -> str:
        """Generate interactive map with business locations."""
        if not businesses:
            raise ValueError("No businesses provided for map generation")
        
        self.logger.info(f"Generating map for {len(businesses)} businesses")
        
        # Filter businesses with valid coordinates
        mapped_businesses = [b for b in businesses if b.latitude and b.longitude]
        
        if not mapped_businesses:
            self.logger.warning("No businesses have valid coordinates for mapping")
            # Try to use default coordinates or geocode addresses
            mapped_businesses = self._geocode_businesses(businesses)
        
        if not mapped_businesses:
            raise ValueError("No businesses could be mapped")
        
        # Calculate map center
        center_lat, center_lng = self._calculate_map_center(mapped_businesses)
        
        # Create base map
        business_map = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=self.viz_config.get('map_zoom', 12),
            tiles='OpenStreetMap'
        )
        
        # Add different tile layers
        folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(business_map)
        folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(business_map)
        
        # Group businesses by cuisine type for color coding
        cuisine_groups = self._group_by_cuisine(mapped_businesses)
        colors = self._get_color_palette(len(cuisine_groups))
        
        # Add markers for each cuisine group
        for i, (cuisine, businesses_list) in enumerate(cuisine_groups.items()):
            color = colors[i % len(colors)]
            feature_group = folium.FeatureGroup(name=f"{cuisine} ({len(businesses_list)})")
            
            for business in businesses_list:
                self._add_business_marker(feature_group, business, color)
            
            feature_group.add_to(business_map)
        
        # Add clustering if enabled
        if self.viz_config.get('enable_clustering', True):
            self._add_marker_clustering(business_map, mapped_businesses)
        
        # Add heatmap layer
        self._add_heatmap_layer(business_map, mapped_businesses)
        
        # Add search functionality
        self._add_search_functionality(business_map, mapped_businesses)
        
        # Add layer control
        folium.LayerControl().add_to(business_map)
        
        # Add legend
        self._add_legend(business_map, cuisine_groups, colors)
        
        # Add statistics panel
        self._add_statistics_panel(business_map, mapped_businesses)
        
        # Save map
        output_file = output_path or self._get_default_map_path()
        business_map.save(output_file)
        
        self.logger.info(f"✅ Interactive map generated: {output_file}")
        return output_file
    
    def _geocode_businesses(self, businesses: List[Business]) -> List[Business]:
        """Attempt to geocode businesses without coordinates."""
        # This is a placeholder for geocoding functionality
        # In a real implementation, you would use a geocoding service like Google Maps API
        self.logger.info("Geocoding not implemented - using default coordinates")
        return []
    
    def _calculate_map_center(self, businesses: List[Business]) -> tuple:
        """Calculate the center point for the map."""
        if not businesses:
            # Use default center from config
            return (
                self.viz_config.get('map_center_lat', 40.7128),
                self.viz_config.get('map_center_lng', -74.0060)
            )
        
        # Calculate average coordinates
        total_lat = sum(b.latitude for b in businesses)
        total_lng = sum(b.longitude for b in businesses)
        
        center_lat = total_lat / len(businesses)
        center_lng = total_lng / len(businesses)
        
        return center_lat, center_lng
    
    def _group_by_cuisine(self, businesses: List[Business]) -> Dict[str, List[Business]]:
        """Group businesses by cuisine type."""
        groups = {}
        
        for business in businesses:
            cuisine = business.cuisine_type or 'Unknown'
            if cuisine not in groups:
                groups[cuisine] = []
            groups[cuisine].append(business)
        
        return groups
    
    def _get_color_palette(self, num_colors: int) -> List[str]:
        """Get color palette for different cuisine types."""
        colors = [
            'red', 'blue', 'green', 'purple', 'orange', 'darkred',
            'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
            'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen',
            'gray', 'black', 'lightgray'
        ]
        
        # Repeat colors if we have more cuisine types than colors
        return colors * ((num_colors // len(colors)) + 1)
    
    def _add_business_marker(self, feature_group: folium.FeatureGroup, business: Business, color: str):
        """Add a marker for a single business."""
        # Create popup content
        popup_html = self._create_popup_content(business)
        
        # Create tooltip
        tooltip = f"{business.name}"
        if business.rating:
            tooltip += f" - {business.rating}⭐"
        
        # Choose icon based on rating
        icon_name = self._get_icon_for_business(business)
        
        # Create marker
        marker = folium.Marker(
            location=[business.latitude, business.longitude],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=tooltip,
            icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
        )
        
        marker.add_to(feature_group)
    
    def _create_popup_content(self, business: Business) -> str:
        """Create HTML content for business popup."""
        html = f"""
        <div style="font-family: Arial, sans-serif; width: 280px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">{business.name}</h4>
            
            <div style="margin-bottom: 8px;">
                <strong>Address:</strong><br>
                {business.full_address}
            </div>
            
            {f'<div style="margin-bottom: 8px;"><strong>Phone:</strong> {business.phone}</div>' if business.phone else ''}
            
            {f'<div style="margin-bottom: 8px;"><strong>Website:</strong> <a href="{business.website}" target="_blank">Visit</a></div>' if business.website else ''}
            
            <div style="margin-bottom: 8px;">
                <strong>Cuisine:</strong> {business.cuisine_type or 'N/A'}
            </div>
            
            {f'<div style="margin-bottom: 8px;"><strong>Price:</strong> {business.price_level}</div>' if business.price_level else ''}
            
            <div style="margin-bottom: 8px;">
                <strong>Rating:</strong> 
                {'⭐' * int(business.rating) if business.rating else 'N/A'}
                {f' ({business.rating}/5)' if business.rating else ''}
            </div>
            
            <div style="margin-bottom: 8px;">
                <strong>Reviews:</strong> {business.review_count}
            </div>
            
            {f'<div style="margin-bottom: 8px;"><strong>Features:</strong> {", ".join(business.features[:3])}</div>' if business.features else ''}
            
            <div style="margin-top: 10px; font-size: 12px; color: #666;">
                Data from: {", ".join(business.data_sources)}
            </div>
        </div>
        """
        
        return html
    
    def _get_icon_for_business(self, business: Business) -> str:
        """Get appropriate icon based on business type and rating."""
        if business.rating:
            if business.rating >= 4.5:
                return 'star'
            elif business.rating >= 4.0:
                return 'thumbs-up'
            elif business.rating < 3.0:
                return 'thumbs-down'
        
        return 'cutlery'  # Default restaurant icon
    
    def _add_marker_clustering(self, business_map: folium.Map, businesses: List[Business]):
        """Add marker clustering to the map."""
        # Create marker cluster
        marker_cluster = plugins.MarkerCluster(
            name="All Businesses (Clustered)",
            show=False  # Hidden by default since we have cuisine groups
        ).add_to(business_map)
        
        # Add all businesses to cluster
        for business in businesses:
            popup_html = self._create_popup_content(business)
            
            folium.Marker(
                location=[business.latitude, business.longitude],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=business.name
            ).add_to(marker_cluster)
    
    def _add_heatmap_layer(self, business_map: folium.Map, businesses: List[Business]):
        """Add heatmap layer based on business density."""
        # Create heatmap data (lat, lng, weight)
        heat_data = []
        for business in businesses:
            # Use rating as weight, or 1 if no rating
            weight = business.rating if business.rating else 1
            heat_data.append([business.latitude, business.longitude, weight])
        
        # Add heatmap
        if heat_data:
            heatmap = plugins.HeatMap(
                heat_data,
                name="Business Density Heatmap",
                show=False,  # Hidden by default
                radius=15,
                blur=10
            )
            heatmap.add_to(business_map)
    
    def _add_search_functionality(self, business_map: folium.Map, businesses: List[Business]):
        """Add search functionality to the map."""
        # Create search data
        search_data = []
        for business in businesses:
            search_data.append({
                'name': business.name,
                'cuisine': business.cuisine_type or 'Unknown',
                'lat': business.latitude,
                'lng': business.longitude
            })
        
        # Add search plugin (simplified version)
        # In a real implementation, you might use a more sophisticated search plugin
        pass
    
    def _add_legend(self, business_map: folium.Map, cuisine_groups: Dict, colors: List[str]):
        """Add legend to the map."""
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; width: 200px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4 style="margin-top:0;">Cuisine Types</h4>
        '''
        
        for i, (cuisine, businesses_list) in enumerate(cuisine_groups.items()):
            color = colors[i % len(colors)]
            legend_html += f'''
            <p><span style="color:{color};">●</span> {cuisine} ({len(businesses_list)})</p>
            '''
        
        legend_html += '</div>'
        business_map.get_root().html.add_child(folium.Element(legend_html))
    
    def _add_statistics_panel(self, business_map: folium.Map, businesses: List[Business]):
        """Add statistics panel to the map."""
        total_businesses = len(businesses)
        avg_rating = sum(b.rating for b in businesses if b.rating) / len([b for b in businesses if b.rating])
        total_reviews = sum(b.review_count for b in businesses)
        
        stats_html = f'''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 250px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px">
        <h4 style="margin-top:0;">Statistics</h4>
        <p><strong>Total Businesses:</strong> {total_businesses}</p>
        <p><strong>Average Rating:</strong> {avg_rating:.1f}⭐</p>
        <p><strong>Total Reviews:</strong> {total_reviews:,}</p>
        <p><strong>Unique Cuisines:</strong> {len(set(b.cuisine_type for b in businesses if b.cuisine_type))}</p>
        </div>
        '''
        
        business_map.get_root().html.add_child(folium.Element(stats_html))
    
    def _get_default_map_path(self) -> str:
        """Get default path for saving the map."""
        output_dir = Path("data/exports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(output_dir / f"business_map_{timestamp}.html")
    
    def generate_cuisine_comparison_map(self, businesses: List[Business], cuisines: List[str]) -> str:
        """Generate map comparing specific cuisine types."""
        filtered_businesses = [
            b for b in businesses 
            if b.latitude and b.longitude and b.cuisine_type in cuisines
        ]
        
        if not filtered_businesses:
            raise ValueError("No businesses found for specified cuisines")
        
        return self.generate_business_map(filtered_businesses)
    
    def generate_rating_based_map(self, businesses: List[Business], min_rating: float = 4.0) -> str:
        """Generate map showing only highly-rated businesses."""
        high_rated_businesses = [
            b for b in businesses 
            if b.latitude and b.longitude and b.rating and b.rating >= min_rating
        ]
        
        if not high_rated_businesses:
            raise ValueError(f"No businesses found with rating >= {min_rating}")
        
        return self.generate_business_map(high_rated_businesses) 