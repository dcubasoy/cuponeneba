import logging
import requests
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from cache import Cache

logger = logging.getLogger(__name__)

class CouponService:
    """Service to fetch, cache, and serve coupon codes from GG.deals API."""
    
    def __init__(self, cache_file="coupons_cache.json", cache_ttl=3600):
        """
        Initialize the coupon service.
        
        Args:
            cache_file (str): The file to use for caching coupon data.
            cache_ttl (int): Cache time-to-live in seconds (default: 1 hour).
        """
        self.url = "https://gg.deals/vouchers/?maxDiscount=5&minDiscount=5&store=60"
        self.cache = Cache(cache_file, cache_ttl)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml'
        }
    
    def fetch_coupons_from_api(self):
        """
        Fetch coupon codes from GG.deals website using web scraping.
        
        Returns:
            list: List of coupon dictionaries.
            
        Raises:
            Exception: If there is an error fetching coupons.
        """
        try:
            logger.debug("Fetching coupons from GG.deals website")
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Process and format the coupon data
            coupons = []
            
            # Find all coupon cards
            coupon_cards = soup.select('.voucher-item')
            
            for card in coupon_cards:
                # Extract coupon information
                code_element = card.select_one('.voucher-code .code')
                title_element = card.select_one('.info-title .title')
                store_element = card.select_one('.shop-image')
                
                # Get the code text and remove 'copy' if present
                code = code_element.get_text(strip=True) if code_element else 'N/A'
                code = code.replace('copy', '')
                
                # Get title/discount information
                discount = title_element.get_text(strip=True) if title_element else 'Unknown Discount'
                
                # Get store name
                store_name = 'GG.deals'
                if store_element and store_element.get('title'):
                    store_name = store_element.get('title')
                
                # Get description from the title as well
                description = discount
                
                # Try to find expiration date from the timer element
                valid_until = 'Unknown'
                expiry_element = card.select_one('.expiry.timer time')
                
                if expiry_element and expiry_element.has_attr('datetime'):
                    # Extract the datetime attribute which has the exact expiration time
                    valid_until = expiry_element['datetime']
                    
                    # If we also need to add the remaining time
                    if expiry_element.get_text(strip=True):
                        remaining_time = expiry_element.get_text(strip=True)
                        valid_until = f"{valid_until} ({remaining_time})"
                
                # Create coupon dictionary with only code and valid_until
                coupon = {
                    'code': code,
                    'valid_until': valid_until
                }
                
                coupons.append(coupon)
            
            logger.debug(f"Successfully fetched {len(coupons)} coupons")
            return coupons
            
        except requests.RequestException as e:
            logger.error(f"Error fetching coupons from website: {str(e)}")
            raise Exception(f"Failed to fetch coupon data: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing website response: {str(e)}")
            raise Exception(f"Failed to parse coupon data: {str(e)}")
    
    def get_coupons(self, force_refresh=False):
        """
        Get coupon codes, either from cache or by fetching from the API.
        
        Args:
            force_refresh (bool): Whether to force a refresh from the API.
            
        Returns:
            list: List of coupon dictionaries.
        """
        # Check if we need to refresh the cache
        if force_refresh or not self.cache.is_valid():
            try:
                # Fetch fresh data from the API
                coupons = self.fetch_coupons_from_api()
                
                # Update the cache
                self.cache.update({
                    'coupons': coupons,
                    'timestamp': time.time()
                })
                
                return coupons
            except Exception as e:
                # If force refresh fails, try to use cached data as fallback
                if not force_refresh and self.cache.exists():
                    logger.warning(f"Using cached data as fallback after API error: {str(e)}")
                    cached_data = self.cache.get()
                    if cached_data and 'coupons' in cached_data:
                        return cached_data['coupons']
                
                # Re-raise the exception if we can't fallback
                raise
        else:
            # Use cached data
            cached_data = self.cache.get()
            if cached_data and 'coupons' in cached_data:
                logger.debug("Using cached coupon data")
                return cached_data['coupons']
            else:
                # Cache exists but is invalid/empty, fetch new data
                logger.warning("Cache exists but data is invalid, fetching new data")
                coupons = self.fetch_coupons_from_api()
                self.cache.update({
                    'coupons': coupons,
                    'timestamp': time.time()
                })
                return coupons
    
    def get_cache_status(self):
        """
        Get information about the current cache status.
        
        Returns:
            dict: Cache status information.
        """
        if not self.cache.exists():
            return {
                'status': 'no_cache',
                'message': 'No cache file exists yet'
            }
        
        cached_data = self.cache.get()
        timestamp = cached_data.get('timestamp', 0)
        coupons_count = len(cached_data.get('coupons', []))
        
        time_diff = time.time() - timestamp
        cache_age = round(time_diff)
        is_valid = time_diff < self.cache.ttl
        
        next_refresh = self.cache.ttl - cache_age if is_valid else 0
        
        return {
            'status': 'valid' if is_valid else 'expired',
            'cache_age_seconds': cache_age,
            'next_refresh_seconds': max(0, next_refresh),
            'last_updated': datetime.fromtimestamp(timestamp).isoformat(),
            'coupon_count': coupons_count
        }
