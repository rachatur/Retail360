import logging
from django.core.cache import cache
from IDENTITY.models import Domain

logger = logging.getLogger(__name__)

def get_allowed_hosts():
    """
    Fetches and caches allowed hosts (domains) from the database.
    """
    domains = cache.get('allowed_hosts')
    
    if not domains:
        # Fetch domains from the database if not found in the cache
        domains = list(Domain.objects.values_list('domain', flat=True))
        
        # Log domains before deduplication
        logger.debug(f"Fetched domains from DB: {domains}")
        
        # Remove duplicates using set (ensure unique domains)
        domains = list(set(domains))
        
        # Log domains after deduplication
        logger.debug(f"Unique domains: {domains}")
        
        # Cache the domains for 1 day (86400 seconds)
        # cache.set('allowed_hosts', domains, 3600)
        cache.set('allowed_hosts', domains, 60)
    
    return domains
