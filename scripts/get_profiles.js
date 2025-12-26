#!/usr/bin/env node

/**
 * Helper script to retrieve available Amazon Advertising API profiles
 * This will help you find the correct AMAZON_PROFILE_ID to use
 */

const axios = require('axios');
const config = require('../src/config/config');

async function refreshAccessToken() {
  try {
    console.log('🔄 Refreshing access token...');
    
    const response = await axios.post(
      config.amazon.tokenEndpoint,
      new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: config.amazon.refreshToken,
        client_id: config.amazon.clientId,
        client_secret: config.amazon.clientSecret
      }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );

    console.log('✅ Access token refreshed successfully\n');
    return response.data.access_token;
  } catch (error) {
    console.error('❌ Error refreshing access token:', error.response?.data || error.message);
    throw error;
  }
}

async function getProfiles() {
  try {
    const token = await refreshAccessToken();

    console.log('📋 Fetching available profiles...\n');

    const response = await axios.get(
      `${config.amazon.endpoint}/v2/profiles`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Amazon-Advertising-API-ClientId': config.amazon.clientId,
          'Content-Type': 'application/json'
        }
      }
    );

    const profiles = response.data;

    if (!profiles || profiles.length === 0) {
      console.log('⚠️  No profiles found for your account.');
      return;
    }

    console.log('✅ Found', profiles.length, 'profile(s):\n');
    console.log('═══════════════════════════════════════════════════════════════');

    profiles.forEach((profile, index) => {
      console.log(`\n📍 Profile ${index + 1}:`);
      console.log('   Profile ID:', profile.profileId);
      console.log('   Country Code:', profile.countryCode);
      console.log('   Currency Code:', profile.currencyCode);
      console.log('   Timezone:', profile.timezone);
      console.log('   Account Info:', profile.accountInfo?.name || 'N/A');
      console.log('   Account Type:', profile.accountInfo?.type || 'N/A');
      console.log('   Marketplace:', profile.accountInfo?.marketplaceStringId || 'N/A');
    });

    console.log('\n═══════════════════════════════════════════════════════════════');
    console.log('\n💡 To use a profile, update your .env file with:');
    console.log('   AMAZON_PROFILE_ID=<profile_id_from_above>');
    console.log('\n📝 Example:');
    console.log(`   AMAZON_PROFILE_ID=${profiles[0].profileId}`);
    console.log('\n');

  } catch (error) {
    if (error.response) {
      console.error('❌ API Error:', error.response.status);
      console.error('   Details:', JSON.stringify(error.response.data, null, 2));
    } else {
      console.error('❌ Error:', error.message);
    }
    process.exit(1);
  }
}

// Run the script
getProfiles().catch(error => {
  console.error('❌ Fatal error:', error.message);
  process.exit(1);
});

