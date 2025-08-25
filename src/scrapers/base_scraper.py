"""Base scraper class with common functionality."""

import time
import random
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from fake_useragent import UserAgent
import undetected_chromedriver as uc

from src.config import config
from src.models import Business, SearchFilter
from src.utils.logger import get_logger

class BaseScraper(ABC):
    """Base class for all scrapers."""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = get_logger(f"scraper.{platform_name}")
        self.config = config
        self.driver = None
        self.user_agent = UserAgent()
        
        # Scraping configuration
        self.delay_min = self.config.scraping.get('delay_between_requests', 2)
        self.delay_max = self.delay_min * 2
        self.timeout = self.config.scraping.get('timeout', 30)
        self.max_retries = self.config.scraping.get('max_retries', 3)
        
    def setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome driver with anti-detection options."""
        try:
            chrome_options = Options()
            
            # Anti-detection options
            if self.config.anti_bot.get('headless_browser', True):
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Random user agent
            if self.config.anti_bot.get('rotate_user_agents', True):
                chrome_options.add_argument(f'--user-agent={self.user_agent.random}')
            
            # Window size
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Use undetected-chromedriver for better anti-detection
            self.driver = uc.Chrome(options=chrome_options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info(f"Chrome driver initialized for {self.platform_name}")
            return self.driver
            
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {str(e)}")
            raise
    
    def random_delay(self, min_delay: Optional[float] = None, max_delay: Optional[float] = None):
        """Add random delay between requests."""
        min_d = min_delay or self.delay_min
        max_d = max_delay or self.delay_max
        delay = random.uniform(min_d, max_d)
        time.sleep(delay)
        self.logger.debug(f"Delayed for {delay:.2f} seconds")
    
    def safe_find_element(self, by: By, value: str, timeout: int = None) -> Optional[Any]:
        """Safely find element with timeout."""
        try:
            wait_time = timeout or self.timeout
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.debug(f"Element not found: {by}={value}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding element {by}={value}: {str(e)}")
            return None
    
    def safe_find_elements(self, by: By, value: str, timeout: int = None) -> List[Any]:
        """Safely find multiple elements with timeout."""
        try:
            wait_time = timeout or self.timeout
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except TimeoutException:
            self.logger.debug(f"Elements not found: {by}={value}")
            return []
        except Exception as e:
            self.logger.error(f"Error finding elements {by}={value}: {str(e)}")
            return []
    
    def safe_get_text(self, element) -> str:
        """Safely get text from element."""
        try:
            return element.text.strip() if element else ""
        except Exception as e:
            self.logger.debug(f"Error getting text from element: {str(e)}")
            return ""
    
    def safe_get_attribute(self, element, attribute: str) -> str:
        """Safely get attribute from element."""
        try:
            return element.get_attribute(attribute) if element else ""
        except Exception as e:
            self.logger.debug(f"Error getting attribute {attribute}: {str(e)}")
            return ""
    
    def retry_operation(self, operation, max_retries: int = None, *args, **kwargs):
        """Retry operation with exponential backoff."""
        retries = max_retries or self.max_retries
        
        for attempt in range(retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                if attempt == retries - 1:
                    self.logger.error(f"Operation failed after {retries} attempts: {str(e)}")
                    raise
                
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f}s: {str(e)}")
                time.sleep(wait_time)
    
    def scroll_to_element(self, element):
        """Scroll to element to make it visible."""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
        except Exception as e:
            self.logger.debug(f"Error scrolling to element: {str(e)}")
    
    def handle_popup(self):
        """Handle common popups and overlays."""
        try:
            # Common popup selectors
            popup_selectors = [
                '[data-testid="close-button"]',
                '.close-button',
                '.modal-close',
                '[aria-label="Close"]',
                '.popup-close'
            ]
            
            for selector in popup_selectors:
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if close_btn.is_displayed():
                        close_btn.click()
                        self.logger.debug("Closed popup")
                        time.sleep(1)
                        break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Error handling popup: {str(e)}")
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info(f"Driver cleanup completed for {self.platform_name}")
            except Exception as e:
                self.logger.error(f"Error during driver cleanup: {str(e)}")
    
    def __enter__(self):
        """Context manager entry."""
        self.setup_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
    
    @abstractmethod
    def search_businesses(self, search_filter: SearchFilter) -> List[Business]:
        """Search for businesses based on filter criteria."""
        pass
    
    @abstractmethod
    def get_business_details(self, business_url: str) -> Optional[Business]:
        """Get detailed information about a specific business."""
        pass
    
    @abstractmethod
    def get_reviews(self, business_url: str, max_reviews: int = 50) -> List[Dict[str, Any]]:
        """Get reviews for a specific business."""
        pass 