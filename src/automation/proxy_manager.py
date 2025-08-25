"""Proxy manager for anti-bot protection and IP rotation."""

import random
import requests
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import time
from urllib.parse import urlparse

from src.config import config
from src.utils.logger import get_logger

class ProxyManager:
    """Manages proxy rotation for anti-bot protection."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.proxies = []
        self.working_proxies = []
        self.current_proxy_index = 0
        self.proxy_test_url = "http://httpbin.org/ip"
        
        # Load proxies from configuration
        self._load_proxies()
        
    def _load_proxies(self):
        """Load proxies from configuration or file."""
        proxy_list_file = self.config.get('anti_bot.proxy_list', 'proxies/proxy_list.txt')
        
        if Path(proxy_list_file).exists():
            self._load_proxies_from_file(proxy_list_file)
        else:
            self.logger.warning(f"Proxy list file not found: {proxy_list_file}")
            # Use environment variables if available
            self._load_proxies_from_env()
    
    def _load_proxies_from_file(self, file_path: str):
        """Load proxies from text file."""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxy_info = self._parse_proxy_line(line)
                    if proxy_info:
                        self.proxies.append(proxy_info)
            
            self.logger.info(f"Loaded {len(self.proxies)} proxies from file")
            
        except Exception as e:
            self.logger.error(f"Error loading proxies from file: {str(e)}")
    
    def _load_proxies_from_env(self):
        """Load proxy from environment variables."""
        import os
        
        proxy_host = os.getenv('PROXY_HOST')
        proxy_port = os.getenv('PROXY_PORT')
        proxy_username = os.getenv('PROXY_USERNAME')
        proxy_password = os.getenv('PROXY_PASSWORD')
        
        if proxy_host and proxy_port:
            proxy_info = {
                'host': proxy_host,
                'port': int(proxy_port),
                'username': proxy_username,
                'password': proxy_password,
                'protocol': 'http'
            }
            self.proxies.append(proxy_info)
            self.logger.info("Loaded proxy from environment variables")
    
    def _parse_proxy_line(self, line: str) -> Optional[Dict]:
        """Parse a proxy line in various formats."""
        try:
            # Format: protocol://username:password@host:port
            if '://' in line:
                parsed = urlparse(line)
                return {
                    'protocol': parsed.scheme,
                    'host': parsed.hostname,
                    'port': parsed.port,
                    'username': parsed.username,
                    'password': parsed.password
                }
            
            # Format: host:port:username:password
            elif line.count(':') == 3:
                parts = line.split(':')
                return {
                    'protocol': 'http',
                    'host': parts[0],
                    'port': int(parts[1]),
                    'username': parts[2],
                    'password': parts[3]
                }
            
            # Format: host:port
            elif line.count(':') == 1:
                parts = line.split(':')
                return {
                    'protocol': 'http',
                    'host': parts[0],
                    'port': int(parts[1]),
                    'username': None,
                    'password': None
                }
            
        except Exception as e:
            self.logger.debug(f"Error parsing proxy line '{line}': {str(e)}")
        
        return None
    
    def test_proxies(self) -> int:
        """Test all proxies and keep only working ones."""
        self.logger.info(f"Testing {len(self.proxies)} proxies...")
        self.working_proxies = []
        
        for i, proxy_info in enumerate(self.proxies):
            if self._test_single_proxy(proxy_info):
                self.working_proxies.append(proxy_info)
                self.logger.debug(f"Proxy {i+1} working: {proxy_info['host']}:{proxy_info['port']}")
            else:
                self.logger.debug(f"Proxy {i+1} failed: {proxy_info['host']}:{proxy_info['port']}")
            
            # Small delay between tests
            time.sleep(0.5)
        
        self.logger.info(f"✅ {len(self.working_proxies)} working proxies found")
        return len(self.working_proxies)
    
    def _test_single_proxy(self, proxy_info: Dict, timeout: int = 10) -> bool:
        """Test a single proxy."""
        try:
            proxy_dict = self._format_proxy_for_requests(proxy_info)
            
            response = requests.get(
                self.proxy_test_url,
                proxies=proxy_dict,
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            if response.status_code == 200:
                # Verify the IP changed
                response_data = response.json()
                proxy_ip = response_data.get('origin', '').split(',')[0].strip()
                return proxy_ip == proxy_info['host']
            
        except Exception:
            pass
        
        return False
    
    def _format_proxy_for_requests(self, proxy_info: Dict) -> Dict[str, str]:
        """Format proxy info for requests library."""
        protocol = proxy_info.get('protocol', 'http')
        host = proxy_info['host']
        port = proxy_info['port']
        username = proxy_info.get('username')
        password = proxy_info.get('password')
        
        if username and password:
            proxy_url = f"{protocol}://{username}:{password}@{host}:{port}"
        else:
            proxy_url = f"{protocol}://{host}:{port}"
        
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Get a random working proxy."""
        if not self.working_proxies:
            return None
        
        proxy_info = random.choice(self.working_proxies)
        return self._format_proxy_for_requests(proxy_info)
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get next proxy in rotation."""
        if not self.working_proxies:
            return None
        
        proxy_info = self.working_proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.working_proxies)
        
        return self._format_proxy_for_requests(proxy_info)
    
    def get_proxy_for_selenium(self) -> Optional[str]:
        """Get proxy string for Selenium WebDriver."""
        if not self.working_proxies:
            return None
        
        proxy_info = random.choice(self.working_proxies)
        host = proxy_info['host']
        port = proxy_info['port']
        username = proxy_info.get('username')
        password = proxy_info.get('password')
        
        if username and password:
            return f"{username}:{password}@{host}:{port}"
        else:
            return f"{host}:{port}"
    
    def is_proxy_enabled(self) -> bool:
        """Check if proxy usage is enabled."""
        return self.config.get('anti_bot.use_proxies', False) and len(self.working_proxies) > 0
    
    def get_proxy_stats(self) -> Dict[str, int]:
        """Get proxy statistics."""
        return {
            'total_proxies': len(self.proxies),
            'working_proxies': len(self.working_proxies),
            'current_index': self.current_proxy_index
        }
    
    def refresh_proxies(self):
        """Refresh and retest all proxies."""
        self.logger.info("Refreshing proxy list...")
        self._load_proxies()
        self.test_proxies()
    
    def create_proxy_list_template(self, file_path: str = "proxies/proxy_list.txt"):
        """Create a template proxy list file."""
        template_content = """# Proxy List Template
# Format options:
# 1. protocol://username:password@host:port
# 2. host:port:username:password  
# 3. host:port (no authentication)
#
# Examples:
# http://user:pass@proxy1.example.com:8080
# https://user:pass@proxy2.example.com:3128
# 192.168.1.100:8080:username:password
# 203.0.113.1:3128
#
# Add your proxies below (one per line):

"""
        
        # Create directory if it doesn't exist
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write template
        with open(file_path, 'w') as f:
            f.write(template_content)
        
        self.logger.info(f"Created proxy list template: {file_path}")

class UserAgentManager:
    """Manages user agent rotation."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            
            # Chrome on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            
            # Firefox on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            
            # Safari on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            
            # Chrome on Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(self.user_agents)
    
    def get_user_agents_list(self) -> List[str]:
        """Get list of all user agents."""
        return self.user_agents.copy()

# Global instances
proxy_manager = ProxyManager()
user_agent_manager = UserAgentManager() 