"""Configuration management for the restaurant directory scraper."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration manager for the scraper."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            
        # Override with environment variables where applicable
        self._override_with_env_vars(config)
        return config
    
    def _override_with_env_vars(self, config: Dict[str, Any]) -> None:
        """Override configuration values with environment variables."""
        # API Keys
        if os.getenv('YELP_API_KEY'):
            config['platforms']['yelp']['api_key'] = os.getenv('YELP_API_KEY')
        if os.getenv('GOOGLE_MAPS_API_KEY'):
            config['platforms']['google_maps']['api_key'] = os.getenv('GOOGLE_MAPS_API_KEY')
            
        # Database
        if os.getenv('DATABASE_URL'):
            config['database']['url'] = os.getenv('DATABASE_URL')
            
        # Logging
        if os.getenv('LOG_LEVEL'):
            config['logging']['level'] = os.getenv('LOG_LEVEL')
        if os.getenv('LOG_FILE'):
            config['logging']['log_file'] = os.getenv('LOG_FILE')
            
        # Scraping settings
        if os.getenv('MAX_CONCURRENT_REQUESTS'):
            config['scraping']['concurrent_requests'] = int(os.getenv('MAX_CONCURRENT_REQUESTS'))
        if os.getenv('REQUEST_DELAY'):
            config['scraping']['delay_between_requests'] = float(os.getenv('REQUEST_DELAY'))
        if os.getenv('HEADLESS_BROWSER'):
            config['anti_bot']['headless_browser'] = os.getenv('HEADLESS_BROWSER').lower() == 'true'
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        return self._config.get(section, {})
    
    @property
    def scraping(self) -> Dict[str, Any]:
        """Get scraping configuration."""
        return self.get_section('scraping')
    
    @property
    def search(self) -> Dict[str, Any]:
        """Get search configuration."""
        return self.get_section('search')
    
    @property
    def platforms(self) -> Dict[str, Any]:
        """Get platforms configuration."""
        return self.get_section('platforms')
    
    @property
    def filters(self) -> Dict[str, Any]:
        """Get filters configuration."""
        return self.get_section('filters')
    
    @property
    def export(self) -> Dict[str, Any]:
        """Get export configuration."""
        return self.get_section('export')
    
    @property
    def anti_bot(self) -> Dict[str, Any]:
        """Get anti-bot configuration."""
        return self.get_section('anti_bot')
    
    @property
    def logging(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get_section('logging')
    
    @property
    def database(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self.get_section('database')
    
    @property
    def visualization(self) -> Dict[str, Any]:
        """Get visualization configuration."""
        return self.get_section('visualization')
    
    @property
    def analytics(self) -> Dict[str, Any]:
        """Get analytics configuration."""
        return self.get_section('analytics')

# Global configuration instance
config = Config() 