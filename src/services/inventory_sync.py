"""
Inventory Synchronization Service
Handles periodic sync of Amazon inventory to local database
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class InventorySyncService:
    """
    Service to sync Amazon inventory data to database
    Scheduled to run periodically
    """

    def __init__(self, db_connector, sp_api_client, cache=None):
        """
        Initialize inventory sync service
        
        Args:
            db_connector: Database connection
            sp_api_client: SP-API client instance
            cache: Optional caching layer
        """
        self.db = db_connector
        self.sp_api = sp_api_client
        self.cache = cache
        self.is_syncing = False
        self.last_sync: Optional[datetime] = None

    async def sync_inventory_for_asins(
        self,
        asins: List[str],
        marketplace_id: str
    ) -> Dict[str, Any]:
        """
        Sync inventory data for given ASINs
        
        Returns:
            {
                "success": bool,
                "synced_count": int,
                "failed_count": int,
                "inventory_data": {...}
            }
        """
        if self.is_syncing:
            logger.warning("Inventory sync already in progress")
            return {"success": False, "error": "Sync already in progress"}

        try:
            self.is_syncing = True
            logger.info(f"Starting inventory sync for {len(asins)} ASINs")

            # Get inventory from SP-API
            inventory_data = await self.sp_api.batch_get_inventory_summary(
                marketplace_id=marketplace_id,
                asins=asins
            )

            # Update database
            synced_count = 0
            failed_count = 0

            for asin, inv_info in inventory_data.items():
                try:
                    self.db.execute(
                        """
                        INSERT INTO inventory_health 
                        (asin, current_inventory, status, last_updated)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(asin) DO UPDATE SET
                        current_inventory = excluded.current_inventory,
                        status = excluded.status,
                        last_updated = excluded.last_updated
                        """,
                        (
                            asin,
                            inv_info.get("quantity", 0),
                            inv_info.get("status", "unknown"),
                            datetime.now().isoformat()
                        )
                    )
                    synced_count += 1

                except Exception as e:
                    logger.error(f"Failed to sync inventory for {asin}: {e}")
                    failed_count += 1

            self.last_sync = datetime.now()
            
            result = {
                "success": True,
                "synced_count": synced_count,
                "failed_count": failed_count,
                "inventory_data": inventory_data,
                "sync_time": self.last_sync.isoformat()
            }

            logger.info(f"Inventory sync completed: {synced_count} synced, {failed_count} failed")
            return result

        except Exception as e:
            logger.error(f"Inventory sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0,
                "failed_count": len(asins)
            }

        finally:
            self.is_syncing = False

    async def get_stock_status(
        self,
        asin: str,
        marketplace_id: str,
        force_refresh: bool = False
    ) -> str:
        """
        Get current stock status for an ASIN
        Uses cache to minimize API calls
        
        Returns: 'in_stock', 'low_stock', 'out_of_stock', 'unknown'
        """
        cache_key = f"inventory:{asin}:{marketplace_id}"

        # Check cache first
        if not force_refresh and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached.get("status", "unknown")

        # Check database
        try:
            cursor = self.db.connection.execute(
                "SELECT status FROM inventory_health WHERE asin = ?",
                (asin,)
            )
            result = cursor.fetchone()
            if result:
                status = result[0]
                if self.cache:
                    self.cache.set(cache_key, {"status": status})
                return status
        except Exception as e:
            logger.warning(f"Failed to get inventory from DB for {asin}: {e}")

        # Fallback to SP-API
        try:
            status = await self.sp_api.check_stock_status(asin, marketplace_id)
            if self.cache:
                self.cache.set(cache_key, {"status": status})
            return status
        except Exception as e:
            logger.error(f"Failed to check stock status for {asin}: {e}")
            return "unknown"

    async def setup_scheduled_sync(
        self,
        interval_minutes: int = 60
    ):
        """
        Start periodic inventory sync
        Runs in background as async task
        """
        logger.info(f"Starting scheduled inventory sync (interval: {interval_minutes} min)")
        
        while True:
            try:
                # Get all active campaigns with products
                campaigns = self.db.get_campaigns_with_performance()
                
                # Collect unique ASINs
                asins = set()
                for campaign in campaigns:
                    if campaign.get("product_asin"):
                        asins.add(campaign["product_asin"])

                if asins:
                    await self.sync_inventory_for_asins(
                        list(asins),
                        marketplace_id="ATVPDKIKX0DER"  # US marketplace
                    )

                # Clear expired cache entries
                if self.cache:
                    self.cache.clear_expired()

                # Sleep until next sync
                await asyncio.sleep(interval_minutes * 60)

            except Exception as e:
                logger.error(f"Scheduled inventory sync failed: {e}")
                # Continue trying even on failure
                await asyncio.sleep(60)  # Wait a minute before retrying

    def get_low_stock_warnings(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """
        Get list of products with low stock
        """
        try:
            cursor = self.db.connection.execute(
                """
                SELECT asin, current_inventory, status, last_updated
                FROM inventory_health
                WHERE current_inventory <= ? AND status != 'out_of_stock'
                ORDER BY current_inventory ASC
                """,
                (threshold,)
            )
            
            warnings = []
            for row in cursor.fetchall():
                warnings.append({
                    "asin": row[0],
                    "quantity": row[1],
                    "status": row[2],
                    "last_updated": row[3]
                })
            
            return warnings

        except Exception as e:
            logger.error(f"Failed to get low stock warnings: {e}")
            return []

    def get_out_of_stock_asins(self) -> List[str]:
        """
        Get list of out-of-stock ASINs
        """
        try:
            cursor = self.db.connection.execute(
                "SELECT asin FROM inventory_health WHERE status = 'out_of_stock'"
            )
            return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get out of stock ASINs: {e}")
            return []
