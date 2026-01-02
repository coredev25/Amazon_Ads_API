#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SYSTEMD_DIR="$SCRIPT_DIR/systemd"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Amazon Ads API - Systemd Services Setup"
echo "==========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️  This script requires sudo privileges${NC}"
    echo "Please run: sudo ./scripts/setup_systemd.sh"
    exit 1
fi

# Update paths in service files
update_service_paths() {
    local service_file=$1
    local project_path=$(realpath "$PROJECT_ROOT")
    
    # Replace placeholder paths with actual project path
    sed -i "s|/home/vip/Desktop/Amazon_Ads_API|$project_path|g" "$service_file"
    echo -e "${GREEN}✓ Updated paths in $(basename $service_file)${NC}"
}

# Install services
install_service() {
    local service_name=$1
    local service_file="$SYSTEMD_DIR/$service_name.service"
    
    if [ ! -f "$service_file" ]; then
        echo -e "${RED}✗ Service file not found: $service_file${NC}"
        return 1
    fi
    
    # Update paths
    update_service_paths "$service_file"
    
    # Copy to systemd directory
    cp "$service_file" "/etc/systemd/system/"
    echo -e "${GREEN}✓ Installed $service_name${NC}"
}

# Install all services
echo -e "${BLUE}Installing systemd services...${NC}"
echo ""

install_service "amazon-ads-api"
install_service "amazon-ads-frontend"
install_service "amazon-ads-sync"

# Reload systemd
echo ""
echo -e "${BLUE}Reloading systemd daemon...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

# Enable services (but don't start yet)
echo ""
echo -e "${BLUE}Enabling services...${NC}"
systemctl enable amazon-ads-api.service
systemctl enable amazon-ads-frontend.service
systemctl enable amazon-ads-sync.service
echo -e "${GREEN}✓ Services enabled${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "✓ Systemd services setup completed!"
echo "==========================================${NC}"
echo ""
echo "Services installed:"
echo "  - amazon-ads-api.service (Dashboard API)"
echo "  - amazon-ads-frontend.service (Dashboard Frontend)"
echo "  - amazon-ads-sync.service (Sync Service)"
echo ""
echo "Useful commands:"
echo "  Start all:    sudo systemctl start amazon-ads-api amazon-ads-frontend amazon-ads-sync"
echo "  Stop all:     sudo systemctl stop amazon-ads-api amazon-ads-frontend amazon-ads-sync"
echo "  Status:       sudo systemctl status amazon-ads-api"
echo "  View logs:    sudo journalctl -u amazon-ads-api -f"
echo "  Restart:      sudo systemctl restart amazon-ads-api"
echo ""
echo -e "${YELLOW}Note: Update service files with correct paths and user before starting${NC}"
echo ""

