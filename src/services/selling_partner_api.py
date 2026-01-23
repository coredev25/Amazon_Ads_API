"""
Selling Partner API Service
Handles integration with Amazon Selling Partner API for inventory management
Documentation: https://developer.amazon.com/docs/sellers/
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json
from enum import Enum

logger = logging.getLogger(__name__)


class SPAPIRegion(Enum):
    """Selling Partner API endpoints by region"""
    NA = "https://sellingpartnerapi-na.amazon.com"  # North America
    EU = "https://sellingpartnerapi-eu.amazon.com"  # Europe
    FE = "https://sellingpartnerapi-fe.amazon.com"  # Far East (Japan)


class SellingPartnerAPIClient:
    """
    Client for Amazon Selling Partner API
    Handles authentication and data retrieval for inventory management
    """

    def __init__(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        region: str = "NA"
    ):
        """
        Initialize SP-API Client
        
        Args:
            refresh_token: LWA refresh token
            client_id: LWA client ID
            client_secret: LWA client secret
            region: AWS region (NA, EU, FE)
        """
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        
        # Set endpoint based on region
        self.endpoints = {
            "NA": SPAPIRegion.NA.value,
            "EU": SPAPIRegion.EU.value,
            "FE": SPAPIRegion.FE.value,
        }
        self.base_url = self.endpoints.get(region, SPAPIRegion.NA.value)

    async def get_access_token(self) -> str:
        """
        Get valid access token (refresh if needed)
        Uses LWA (Login with Amazon) tokens
        """
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        try:
            # Token endpoint for LWA
            token_url = "https://api.amazon.com/auth/o2/token"
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            self.access_token = result.get("access_token")
            
            # Set expiry (default 1 hour minus 5 minutes for safety)
            expires_in = result.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
            
            logger.info("SP-API access token refreshed successfully")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get SP-API access token: {e}")
            raise Exception(f"SP-API authentication failed: {str(e)}")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to SP-API
        """
        token = await self.get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "AmazonAdsDashboard/1.0",
        }

        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            
            return response.json() if response.text else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SP-API request failed: {method} {endpoint}: {e}")
            raise

    async def get_catalog_item(
        self,
        asin: str,
        marketplace_id: str
    ) -> Dict[str, Any]:
        """
        Get catalog item details including availability
        API v2022-04-01
        """
        try:
            endpoint = f"/catalog/2022-04-01/items/{asin}"
            params = {"marketplaceIds": marketplace_id}
            
            result = await self._make_request("GET", endpoint, params=params)
            
            logger.info(f"Retrieved catalog item for ASIN: {asin}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get catalog item {asin}: {e}")
            return {}

    async def get_inventory_summary(
        self,
        marketplace_id: str,
        asin: Optional[str] = None,
        skus: Optional[List[str]] = None,
        details: bool = True
    ) -> Dict[str, Any]:
        """
        Get inventory summary for SKUs or ASINs
        API v1
        
        Args:
            marketplace_id: Amazon marketplace ID
            asin: Optional ASIN filter
            skus: Optional list of SKUs
            details: Include detailed info
        """
        try:
            endpoint = "/fba/inventory/v1/summaries"
            
            params = {
                "marketplaceIds": marketplace_id,
                "details": str(details).lower(),
            }
            
            # Add ASIN or SKUs filter if provided
            if asin:
                params["filters"] = json.dumps({"asin": asin})
            elif skus:
                params["filters"] = json.dumps({"skus": skus})

            result = await self._make_request("GET", endpoint, params=params)
            
            logger.info(f"Retrieved FBA inventory summary for marketplace: {marketplace_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get inventory summary: {e}")
            return {"inventorySummaries": []}

    async def get_fba_item_details(
        self,
        asin: str,
        marketplace_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed FBA inventory information for an ASIN
        Includes stock levels, condition, etc.
        """
        try:
            # Try catalog v0 endpoint (most reliable)
            endpoint = f"/catalog/v0/items/{asin}"
            params = {"marketplaceIds": marketplace_id}
            
            result = await self._make_request("GET", endpoint, params=params)
            
            # Extract relevant fields
            if result and "item" in result:
                item = result["item"]
                return {
                    "asin": asin,
                    "sku": item.get("sku"),
                    "title": item.get("title"),
                    "available_quantity": item.get("standardProductDetails", {}).get("quantity", 0),
                    "condition": "New",  # Default to New for seller inventory
                    "active": True
                }
            
            return {"asin": asin, "available_quantity": 0, "active": False}
            
        except Exception as e:
            logger.error(f"Failed to get FBA item details for {asin}: {e}")
            return {"asin": asin, "available_quantity": 0, "active": False}

    async def batch_get_inventory_summary(
        self,
        marketplace_id: str,
        asins: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get inventory status for multiple ASINs
        Returns dict mapping ASIN -> {quantity, status, etc}
        """
        results = {}
        
        # Process in batches (SP-API limits)
        batch_size = 20
        for i in range(0, len(asins), batch_size):
            batch = asins[i:i + batch_size]
            
            try:
                inventory_data = await self.get_inventory_summary(
                    marketplace_id=marketplace_id,
                    skus=batch
                )
                
                # Parse results
                for item in inventory_data.get("inventorySummaries", []):
                    asin = item.get("asin")
                    quantity = item.get("totalSupplyQuantity", 0)
                    status = "in_stock" if quantity > 0 else "out_of_stock"
                    
                    if quantity < 5:
                        status = "low_stock"
                    
                    results[asin] = {
                        "quantity": quantity,
                        "status": status,
                        "updated_at": datetime.now().isoformat()
                    }
                    
            except Exception as e:
                logger.warning(f"Failed to get inventory for batch: {e}")
                # Mark as unknown status
                for asin in batch:
                    results[asin] = {
                        "quantity": 0,
                        "status": "unknown",
                        "error": str(e),
                        "updated_at": datetime.now().isoformat()
                    }

        return results

    async def get_product_performance(
        self,
        marketplace_id: str,
        asin: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get product performance metrics
        Note: Requires Business Reports API
        """
        try:
            # This endpoint requires special access
            endpoint = f"/reports/2021-06-30/documents"
            
            logger.warning("Product performance endpoint requires Business Reports API access")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get product performance: {e}")
            return {}

    async def check_stock_status(
        self,
        asin: str,
        marketplace_id: str
    ) -> str:
        """
        Quick check for stock status
        Returns: 'in_stock', 'low_stock', 'out_of_stock', 'unknown'
        """
        try:
            details = await self.get_fba_item_details(asin, marketplace_id)
            quantity = details.get("available_quantity", 0)
            
            if quantity == 0:
                return "out_of_stock"
            elif quantity < 5:
                return "low_stock"
            else:
                return "in_stock"
                
        except Exception as e:
            logger.warning(f"Failed to check stock status for {asin}: {e}")
            return "unknown"


class SPAPIInventoryCache:
    """
    Simple in-memory cache for inventory data to reduce API calls
    """
    
    def __init__(self, cache_ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = cache_ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value if not expired"""
        if key in self.cache:
            cached_value, timestamp = self.cache[key]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                return cached_value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Dict[str, Any]):
        """Cache a value with timestamp"""
        self.cache[key] = (value, datetime.now())

    def clear(self):
        """Clear all cache"""
        self.cache.clear()

    def clear_expired(self):
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if (now - timestamp).total_seconds() > self.cache_ttl
        ]
        for key in expired_keys:
            del self.cache[key]
