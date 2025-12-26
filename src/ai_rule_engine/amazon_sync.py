"""
Amazon SP-API Sync Module
Handles downloading reports from Amazon SP-API and uploading bid/budget changes
"""

import os
import logging
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests

# Import database connector
from .database import DatabaseConnector


@dataclass
class SyncResult:
    """Result of a sync operation"""
    success: bool
    records_processed: int
    error_message: Optional[str] = None
    sync_type: str = 'unknown'
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class AmazonSPAPIClient:
    """
    Amazon SP-API Client for Advertising API
    Handles authentication and API requests
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SP-API client
        
        Args:
            config: Configuration dictionary with API credentials
        """
        self.logger = logging.getLogger(__name__)
        
        # Load credentials from environment or config
        self.client_id = os.getenv('AMAZON_CLIENT_ID') or config.get('amazon_client_id')
        self.client_secret = os.getenv('AMAZON_CLIENT_SECRET') or config.get('amazon_client_secret')
        self.refresh_token = os.getenv('AMAZON_REFRESH_TOKEN') or config.get('amazon_refresh_token')
        self.profile_id = os.getenv('AMAZON_PROFILE_ID') or config.get('amazon_profile_id')
        
        # API endpoints
        self.api_base_url = config.get('amazon_api_base_url', 'https://advertising-api.amazon.com')
        self.token_url = 'https://api.amazon.com/auth/o2/token'
        
        # Access token (will be obtained on first request)
        self.access_token = None
        self.token_expiry = None
        
        # Validate credentials
        if not all([self.client_id, self.client_secret, self.refresh_token, self.profile_id]):
            raise ValueError(
                "Missing required Amazon API credentials. Set environment variables: "
                "AMAZON_CLIENT_ID, AMAZON_CLIENT_SECRET, AMAZON_REFRESH_TOKEN, AMAZON_PROFILE_ID"
            )
    
    def _get_access_token(self) -> str:
        """
        Get or refresh access token
        
        Returns:
            Access token string
        """
        # Check if we have a valid token
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        # Request new access token
        self.logger.info("Requesting new Amazon API access token")
        
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = requests.post(self.token_url, data=payload, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Set expiry to 1 hour from now (tokens typically last 1 hour)
            expires_in = token_data.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)  # 1 min buffer
            
            self.logger.info("Successfully obtained access token")
            return self.access_token
            
        except Exception as e:
            self.logger.error(f"Error obtaining access token: {e}")
            raise
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                     params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to Amazon Advertising API
        
        Args:
            method: HTTP method (GET, POST, PUT)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            Response JSON
        """
        access_token = self._get_access_token()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Amazon-Advertising-API-ClientId': self.client_id,
            'Amazon-Advertising-API-Scope': self.profile_id,
            'Content-Type': 'application/json'
        }
        
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error in API request: {e}")
            self.logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            raise
        except Exception as e:
            self.logger.error(f"Error making API request: {e}")
            raise
    
    def request_report(self, report_type: str, report_date: datetime) -> str:
        """
        Request a report from Amazon Advertising API
        
        Args:
            report_type: Type of report (e.g., 'spAdvertisedProduct')
            report_date: Date for the report
            
        Returns:
            Report ID
            
        WARNING: This method uses Amazon Advertising API v2 endpoints which are being
        deprecated by Amazon. Consider migrating to v3 Async Reporting API or
        Amazon Marketing Stream for long-term stability.
        
        See: https://advertising.amazon.com/API/docs/en-us/reference/migration-guide-v3
        """
        endpoint = f'/v2/sp/reports'
        
        self.logger.warning(
            "Using deprecated Amazon API v2 endpoint '/v2/sp/reports'. "
            "Amazon is phasing out v2 endpoints. Consider migrating to v3 Async Reporting API."
        )
        
        payload = {
            'reportDate': report_date.strftime('%Y%m%d'),
            'metrics': [
                'campaignId',
                'campaignName',
                'campaignStatus',
                'adGroupId',
                'adGroupName',
                'keywordId',
                'keywordText',
                'matchType',
                'impressions',
                'clicks',
                'cost',
                'attributedConversions1d',
                'attributedConversions7d',
                'attributedConversions14d',
                'attributedConversions30d',
                'attributedSales1d',
                'attributedSales7d',
                'attributedSales14d',
                'attributedSales30d'
            ]
        }
        
        if report_type == 'spAdvertisedProduct':
            payload['recordType'] = 'adGroups'
        elif report_type == 'spKeywords':
            payload['recordType'] = 'keywords'
        elif report_type == 'spCampaigns':
            payload['recordType'] = 'campaigns'
        else:
            raise ValueError(f"Unsupported report type: {report_type}")
        
        self.logger.info(f"Requesting {report_type} report for {report_date.strftime('%Y-%m-%d')}")
        
        try:
            response = self._make_request('POST', endpoint, data=payload)
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code in [400, 403, 410]:
                self.logger.error(
                    f"API v2 endpoint may be deprecated or disabled for your account. "
                    f"Status: {e.response.status_code}. "
                    f"Please migrate to Amazon Advertising API v3 or Amazon Marketing Stream. "
                    f"Response: {e.response.text}"
                )
                raise RuntimeError(
                    f"Amazon API v2 endpoint failure (HTTP {e.response.status_code}). "
                    f"This endpoint may be deprecated. Please contact support or migrate to v3 API."
                ) from e
            raise
        
        report_id = response.get('reportId')
        
        if not report_id:
            raise ValueError(f"No report ID returned: {response}")
        
        self.logger.info(f"Report requested successfully: {report_id}")
        return report_id
    
    def check_report_status(self, report_id: str) -> Dict[str, Any]:
        """
        Check the status of a report
        
        Args:
            report_id: Report ID
            
        Returns:
            Report status information
            
        WARNING: Uses deprecated v2 endpoint. Consider migrating to v3 API.
        """
        endpoint = f'/v2/reports/{report_id}'
        return self._make_request('GET', endpoint)
    
    def download_report(self, report_id: str, max_wait_seconds: int = 300) -> List[Dict[str, Any]]:
        """
        Download a report (waits for report to be ready)
        
        Args:
            report_id: Report ID
            max_wait_seconds: Maximum time to wait for report
            
        Returns:
            List of report records
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            status_info = self.check_report_status(report_id)
            status = status_info.get('status')
            
            if status == 'SUCCESS':
                download_url = status_info.get('location')
                if not download_url:
                    raise ValueError(f"No download URL in report status: {status_info}")
                
                self.logger.info(f"Report ready, downloading from: {download_url}")
                
                # Download report data
                response = requests.get(download_url, timeout=60)
                response.raise_for_status()
                
                # Parse JSON lines format
                records = []
                for line in response.text.strip().split('\n'):
                    if line:
                        records.append(json.loads(line))
                
                self.logger.info(f"Downloaded {len(records)} records from report")
                return records
                
            elif status == 'FAILURE':
                raise ValueError(f"Report generation failed: {status_info}")
            
            # Still processing, wait and retry
            self.logger.debug(f"Report status: {status}, waiting...")
            time.sleep(10)
        
        raise TimeoutError(f"Report {report_id} did not complete within {max_wait_seconds} seconds")
    
    def update_keyword_bids(self, keyword_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update keyword bids
        
        Args:
            keyword_updates: List of keyword updates with keywordId and bid
            
        Returns:
            Update response
            
        WARNING: Uses deprecated v2 endpoint. Consider migrating to v3 API.
        """
        endpoint = '/v2/sp/keywords'
        self.logger.debug("Using v2 endpoint for keyword updates")
        
        # Format updates for API
        formatted_updates = []
        for update in keyword_updates:
            formatted_updates.append({
                'keywordId': update['keyword_id'],
                'state': update.get('state', 'enabled'),
                'bid': update['bid']
            })
        
        self.logger.info(f"Updating {len(formatted_updates)} keyword bids")
        
        response = self._make_request('PUT', endpoint, data=formatted_updates)
        
        self.logger.info(f"Keyword bid update response: {response}")
        return response
    
    def update_campaign_budgets(self, campaign_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update campaign budgets
        
        Args:
            campaign_updates: List of campaign updates with campaignId and dailyBudget
            
        Returns:
            Update response
            
        WARNING: Uses deprecated v2 endpoint. Consider migrating to v3 API.
        """
        endpoint = '/v2/sp/campaigns'
        self.logger.debug("Using v2 endpoint for campaign updates")
        
        # Format updates for API
        formatted_updates = []
        for update in campaign_updates:
            formatted_updates.append({
                'campaignId': update['campaign_id'],
                'state': update.get('state', 'enabled'),
                'dailyBudget': update['daily_budget']
            })
        
        self.logger.info(f"Updating {len(formatted_updates)} campaign budgets")
        
        response = self._make_request('PUT', endpoint, data=formatted_updates)
        
        self.logger.info(f"Campaign budget update response: {response}")
        return response


class AmazonSyncManager:
    """
    Manages syncing data between Amazon SP-API and local database
    """
    
    def __init__(self, config: Dict[str, Any], db_connector: DatabaseConnector):
        """
        Initialize sync manager
        
        Args:
            config: Configuration dictionary
            db_connector: Database connector
        """
        self.config = config
        self.db = db_connector
        self.logger = logging.getLogger(__name__)
        
        # Initialize SP-API client
        try:
            self.api_client = AmazonSPAPIClient(config)
        except Exception as e:
            self.logger.error(f"Failed to initialize Amazon API client: {e}")
            self.api_client = None
    
    def download_yesterday_performance(self) -> SyncResult:
        """
        Download performance data for yesterday (T-1) from Amazon SP-API
        
        Returns:
            SyncResult with download results
        """
        if not self.api_client:
            return SyncResult(
                success=False,
                records_processed=0,
                error_message="Amazon API client not initialized",
                sync_type='download'
            )
        
        start_time = datetime.now()
        yesterday = datetime.now() - timedelta(days=1)
        
        self.logger.info(f"Starting download of performance data for {yesterday.strftime('%Y-%m-%d')}")
        
        try:
            # Download keyword performance report
            report_id = self.api_client.request_report('spKeywords', yesterday)
            records = self.api_client.download_report(report_id)
            
            # Insert records into database
            records_processed = self._insert_performance_records(records, yesterday)
            
            end_time = datetime.now()
            
            # Log sync to database
            self._log_sync(
                sync_type='download_performance',
                start_time=start_time,
                end_time=end_time,
                status='success',
                records_processed=records_processed
            )
            
            return SyncResult(
                success=True,
                records_processed=records_processed,
                sync_type='download',
                start_time=start_time,
                end_time=end_time
            )
            
        except Exception as e:
            self.logger.error(f"Error downloading performance data: {e}")
            
            end_time = datetime.now()
            
            # Log failed sync
            self._log_sync(
                sync_type='download_performance',
                start_time=start_time,
                end_time=end_time,
                status='failed',
                records_processed=0,
                error_message=str(e)
            )
            
            return SyncResult(
                success=False,
                records_processed=0,
                error_message=str(e),
                sync_type='download',
                start_time=start_time,
                end_time=end_time
            )
    
    def _insert_performance_records(self, records: List[Dict[str, Any]], report_date: datetime) -> int:
        """
        Insert performance records into database
        
        Args:
            records: List of performance records
            report_date: Date of the report
            
        Returns:
            Number of records inserted
        """
        inserted_count = 0
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                for record in records:
                    try:
                        # Determine entity type and insert into appropriate table
                        if record.get('keywordId'):
                            # Keyword performance
                            query = """
                            INSERT INTO keyword_performance (
                                campaign_id, ad_group_id, keyword_id, report_date,
                                impressions, clicks, cost,
                                attributed_conversions_1d, attributed_conversions_7d,
                                attributed_sales_1d, attributed_sales_7d
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (keyword_id, report_date) DO UPDATE SET
                                impressions = EXCLUDED.impressions,
                                clicks = EXCLUDED.clicks,
                                cost = EXCLUDED.cost,
                                attributed_conversions_1d = EXCLUDED.attributed_conversions_1d,
                                attributed_conversions_7d = EXCLUDED.attributed_conversions_7d,
                                attributed_sales_1d = EXCLUDED.attributed_sales_1d,
                                attributed_sales_7d = EXCLUDED.attributed_sales_7d,
                                updated_at = CURRENT_TIMESTAMP
                            """
                            
                            cursor.execute(query, (
                                record.get('campaignId'),
                                record.get('adGroupId'),
                                record.get('keywordId'),
                                report_date.date(),
                                record.get('impressions', 0),
                                record.get('clicks', 0),
                                record.get('cost', 0),
                                record.get('attributedConversions1d', 0),
                                record.get('attributedConversions7d', 0),
                                record.get('attributedSales1d', 0),
                                record.get('attributedSales7d', 0)
                            ))
                            
                        elif record.get('adGroupId'):
                            # Ad group performance
                            query = """
                            INSERT INTO ad_group_performance (
                                campaign_id, ad_group_id, report_date,
                                impressions, clicks, cost,
                                attributed_conversions_1d, attributed_conversions_7d,
                                attributed_sales_1d, attributed_sales_7d
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (ad_group_id, report_date) DO UPDATE SET
                                impressions = EXCLUDED.impressions,
                                clicks = EXCLUDED.clicks,
                                cost = EXCLUDED.cost,
                                attributed_conversions_1d = EXCLUDED.attributed_conversions_1d,
                                attributed_conversions_7d = EXCLUDED.attributed_conversions_7d,
                                attributed_sales_1d = EXCLUDED.attributed_sales_1d,
                                attributed_sales_7d = EXCLUDED.attributed_sales_7d,
                                updated_at = CURRENT_TIMESTAMP
                            """
                            
                            cursor.execute(query, (
                                record.get('campaignId'),
                                record.get('adGroupId'),
                                report_date.date(),
                                record.get('impressions', 0),
                                record.get('clicks', 0),
                                record.get('cost', 0),
                                record.get('attributedConversions1d', 0),
                                record.get('attributedConversions7d', 0),
                                record.get('attributedSales1d', 0),
                                record.get('attributedSales7d', 0)
                            ))
                            
                        elif record.get('campaignId'):
                            # Campaign performance
                            query = """
                            INSERT INTO campaign_performance (
                                campaign_id, report_date,
                                impressions, clicks, cost,
                                attributed_conversions_1d, attributed_conversions_7d,
                                attributed_sales_1d, attributed_sales_7d
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (campaign_id, report_date) DO UPDATE SET
                                impressions = EXCLUDED.impressions,
                                clicks = EXCLUDED.clicks,
                                cost = EXCLUDED.cost,
                                attributed_conversions_1d = EXCLUDED.attributed_conversions_1d,
                                attributed_conversions_7d = EXCLUDED.attributed_conversions_7d,
                                attributed_sales_1d = EXCLUDED.attributed_sales_1d,
                                attributed_sales_7d = EXCLUDED.attributed_sales_7d,
                                updated_at = CURRENT_TIMESTAMP
                            """
                            
                            cursor.execute(query, (
                                record.get('campaignId'),
                                report_date.date(),
                                record.get('impressions', 0),
                                record.get('clicks', 0),
                                record.get('cost', 0),
                                record.get('attributedConversions1d', 0),
                                record.get('attributedConversions7d', 0),
                                record.get('attributedSales1d', 0),
                                record.get('attributedSales7d', 0)
                            ))
                        
                        inserted_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error inserting record: {e}")
                        self.logger.error(f"Record: {record}")
                
                conn.commit()
        
        self.logger.info(f"Inserted {inserted_count} performance records")
        return inserted_count
    
    def upload_approved_recommendations(self) -> SyncResult:
        """
        Upload approved recommendations from database to Amazon SP-API
        
        Returns:
            SyncResult with upload results
        """
        if not self.api_client:
            return SyncResult(
                success=False,
                records_processed=0,
                error_message="Amazon API client not initialized",
                sync_type='upload'
            )
        
        start_time = datetime.now()
        
        self.logger.info("Starting upload of approved recommendations")
        
        try:
            # Get approved recommendations from database
            approved_recs = self._get_approved_recommendations()
            
            if not approved_recs:
                self.logger.info("No approved recommendations to upload")
                return SyncResult(
                    success=True,
                    records_processed=0,
                    sync_type='upload',
                    start_time=start_time,
                    end_time=datetime.now()
                )
            
            # Separate by type
            keyword_updates = []
            campaign_updates = []
            
            for rec in approved_recs:
                if rec['entity_type'] == 'keyword' and rec['adjustment_type'] == 'bid':
                    keyword_updates.append({
                        'keyword_id': rec['entity_id'],
                        'bid': rec['recommended_value']
                    })
                elif rec['entity_type'] == 'campaign' and rec['adjustment_type'] == 'budget':
                    campaign_updates.append({
                        'campaign_id': rec['entity_id'],
                        'daily_budget': rec['recommended_value']
                    })
            
            # Upload keyword bid updates
            if keyword_updates:
                self.api_client.update_keyword_bids(keyword_updates)
                self.logger.info(f"Uploaded {len(keyword_updates)} keyword bid updates")
            
            # Upload campaign budget updates
            if campaign_updates:
                self.api_client.update_campaign_budgets(campaign_updates)
                self.logger.info(f"Uploaded {len(campaign_updates)} campaign budget updates")
            
            # Mark recommendations as applied
            self._mark_recommendations_applied([rec['recommendation_id'] for rec in approved_recs])
            
            end_time = datetime.now()
            total_processed = len(keyword_updates) + len(campaign_updates)
            
            # Log sync to database
            self._log_sync(
                sync_type='upload_recommendations',
                start_time=start_time,
                end_time=end_time,
                status='success',
                records_processed=total_processed
            )
            
            return SyncResult(
                success=True,
                records_processed=total_processed,
                sync_type='upload',
                start_time=start_time,
                end_time=end_time
            )
            
        except Exception as e:
            self.logger.error(f"Error uploading recommendations: {e}")
            
            end_time = datetime.now()
            
            # Log failed sync
            self._log_sync(
                sync_type='upload_recommendations',
                start_time=start_time,
                end_time=end_time,
                status='failed',
                records_processed=0,
                error_message=str(e)
            )
            
            return SyncResult(
                success=False,
                records_processed=0,
                error_message=str(e),
                sync_type='upload',
                start_time=start_time,
                end_time=end_time
            )
    
    def _get_approved_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get approved recommendations from database that haven't been applied yet
        
        Returns:
            List of approved recommendations
        """
        query = """
        SELECT 
            recommendation_id,
            entity_type,
            entity_id,
            adjustment_type,
            recommended_value,
            current_value
        FROM recommendation_tracking
        WHERE applied = TRUE
            AND applied_at IS NULL
        ORDER BY created_at ASC
        LIMIT 100
        """
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    results = []
                    for row in cursor.fetchall():
                        results.append(dict(zip(columns, row)))
                    return results
        except Exception as e:
            self.logger.error(f"Error fetching approved recommendations: {e}")
            return []
    
    def _mark_recommendations_applied(self, recommendation_ids: List[str]) -> None:
        """
        Mark recommendations as applied in database
        
        Args:
            recommendation_ids: List of recommendation IDs
        """
        if not recommendation_ids:
            return
        
        query = """
        UPDATE recommendation_tracking
        SET applied_at = CURRENT_TIMESTAMP
        WHERE recommendation_id = ANY(%s)
        """
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (recommendation_ids,))
                    conn.commit()
                    self.logger.info(f"Marked {len(recommendation_ids)} recommendations as applied")
        except Exception as e:
            self.logger.error(f"Error marking recommendations as applied: {e}")
    
    def _log_sync(self, sync_type: str, start_time: datetime, end_time: datetime,
                 status: str, records_processed: int, error_message: Optional[str] = None) -> None:
        """
        Log sync operation to database
        
        Args:
            sync_type: Type of sync operation
            start_time: Start time
            end_time: End time
            status: Status (success/failed)
            records_processed: Number of records processed
            error_message: Error message if failed
        """
        query = """
        INSERT INTO sync_logs (
            sync_type, start_time, end_time, status, records_processed, error_message
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        )
        """
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (
                        sync_type,
                        start_time,
                        end_time,
                        status,
                        records_processed,
                        error_message
                    ))
                    conn.commit()
        except Exception as e:
            self.logger.error(f"Error logging sync: {e}")


def run_daily_sync(config: Dict[str, Any], db_connector: DatabaseConnector) -> Dict[str, SyncResult]:
    """
    Run daily sync operations (download T-1 data and upload approved recommendations)
    
    Args:
        config: Configuration dictionary
        db_connector: Database connector
        
    Returns:
        Dictionary with sync results
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting daily Amazon sync")
    
    sync_manager = AmazonSyncManager(config, db_connector)
    
    results = {}
    
    # Download yesterday's performance data
    logger.info("Step 1: Downloading yesterday's performance data")
    results['download'] = sync_manager.download_yesterday_performance()
    
    # Upload approved recommendations
    logger.info("Step 2: Uploading approved recommendations")
    results['upload'] = sync_manager.upload_approved_recommendations()
    
    # Log summary
    logger.info("Daily sync completed")
    logger.info(f"Download: {results['download'].success}, {results['download'].records_processed} records")
    logger.info(f"Upload: {results['upload'].success}, {results['upload'].records_processed} records")
    
    return results


if __name__ == '__main__':
    """
    Run sync as standalone script
    """
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    from .config import RuleConfig
    config = RuleConfig()
    
    # Initialize database connector
    db = DatabaseConnector()
    
    # Run sync
    try:
        results = run_daily_sync(config.__dict__, db)
        
        # Exit with error code if any sync failed
        if not all(r.success for r in results.values()):
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        logging.error(f"Fatal error in sync: {e}")
        sys.exit(1)

