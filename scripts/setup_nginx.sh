#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Amazon Ads API - Nginx Setup"
echo "==========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️  This script requires sudo privileges${NC}"
    echo "Please run: sudo ./scripts/setup_nginx.sh"
    exit 1
fi

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Nginx is not installed. Installing...${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y nginx
    elif command -v yum &> /dev/null; then
        yum install -y nginx
    else
        echo -e "${RED}✗ Cannot install nginx automatically. Please install it manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Nginx installed${NC}"
fi

# Create nginx configuration directory if it doesn't exist
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"

mkdir -p "$NGINX_SITES_AVAILABLE"
mkdir -p "$NGINX_SITES_ENABLED"

# Copy configuration file
CONFIG_FILE="$PROJECT_ROOT/nginx/amazon-ads-api.conf"
TARGET_CONFIG="$NGINX_SITES_AVAILABLE/amazon-ads-api"

if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$TARGET_CONFIG"
    echo -e "${GREEN}✓ Configuration file copied${NC}"
else
    echo -e "${RED}✗ Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Create symlink to enable site
if [ -L "$NGINX_SITES_ENABLED/amazon-ads-api" ]; then
    rm "$NGINX_SITES_ENABLED/amazon-ads-api"
fi
ln -s "$TARGET_CONFIG" "$NGINX_SITES_ENABLED/amazon-ads-api"
echo -e "${GREEN}✓ Site enabled${NC}"

# Remove default nginx site if it exists
if [ -L "$NGINX_SITES_ENABLED/default" ]; then
    rm "$NGINX_SITES_ENABLED/default"
    echo -e "${YELLOW}⚠️  Removed default nginx site${NC}"
fi

# Test nginx configuration
echo ""
echo -e "${BLUE}Testing nginx configuration...${NC}"
if nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
    exit 1
fi

# Create log directory
mkdir -p /var/log/nginx
chown -R www-data:www-data /var/log/nginx 2>/dev/null || true

# Restart nginx
echo ""
echo -e "${BLUE}Restarting nginx...${NC}"
systemctl restart nginx || service nginx restart

# Check nginx status
if systemctl is-active --quiet nginx || service nginx status &> /dev/null; then
    echo -e "${GREEN}✓ Nginx is running${NC}"
else
    echo -e "${RED}✗ Nginx failed to start${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================="
echo "✓ Nginx setup completed successfully!"
echo "==========================================${NC}"
echo ""
echo "Configuration:"
echo "  Config file: $TARGET_CONFIG"
echo "  Enabled link: $NGINX_SITES_ENABLED/amazon-ads-api"
echo ""
echo "Next steps:"
echo "1. Update server_name in $TARGET_CONFIG with your domain"
echo "2. For HTTPS, uncomment SSL section and configure certificates"
echo "3. Ensure services are running on:"
echo "   - Frontend: localhost:3000"
echo "   - API: localhost:8000"
echo "   - Node.js API: localhost:3001 (if used)"
echo ""
echo "Useful commands:"
echo "  - Test config: sudo nginx -t"
echo "  - Reload nginx: sudo systemctl reload nginx"
echo "  - View logs: sudo tail -f /var/log/nginx/amazon-ads-api-*.log"
echo ""

