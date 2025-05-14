import os
import json
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Cache:
    """Simple file-based cache for storing data."""
    
    def __init__(self, cache_file, ttl=3600):
        """
        Initialize the cache.
        
        Args:
            cache_file (str): The file to use for caching.
            ttl (int): Cache time-to-live in seconds (default: 1 hour).
        """
        self.cache_file = cache_file
        self.ttl = ttl
    
    def exists(self):
        """
        Check if the cache file exists.
        
        Returns:
            bool: True if the cache file exists, False otherwise.
        """
        return os.path.exists(self.cache_file)
    
    def is_valid(self):
        """
        Check if the cache is valid (exists and not expired).
        
        Returns:
            bool: True if the cache is valid, False otherwise.
        """
        if not self.exists():
            return False
        
        try:
            cached_data = self.get()
            timestamp = cached_data.get('timestamp', 0)
            return time.time() - timestamp < self.ttl
        except Exception as e:
            logger.error(f"Error checking cache validity: {str(e)}")
            return False
    
    def get(self):
        """
        Get data from the cache.
        
        Returns:
            dict: The cached data, or an empty dict if there's an error.
        """
        if not self.exists():
            return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading cache file: {str(e)}")
            return {}
    
    def update(self, data):
        """
        Update the cache with new data.
        
        Args:
            data (dict): The data to cache.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Add metadata if not present
            if 'timestamp' not in data:
                data['timestamp'] = time.time()
            
            # Ensure cache directory exists
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            
            # Write cache to file
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Cache updated at {datetime.now().isoformat()}")
            return True
        except Exception as e:
            logger.error(f"Error updating cache: {str(e)}")
            return False
    
    def clear(self):
        """
        Clear the cache by removing the cache file.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.exists():
            return True
        
        try:
            os.remove(self.cache_file)
            logger.debug("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False
