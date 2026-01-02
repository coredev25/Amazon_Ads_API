# Nginx Configuration for Amazon Ads API

This directory contains nginx configuration files for running all project services behind a reverse proxy.

## Services

- **Dashboard Frontend** (Next.js): Port 3000
- **Dashboard API** (FastAPI): Port 8000
- **Node.js API** (Express): Port 3001 (optional)

## Quick Setup

### 1. Install and Configure Nginx

```bash
sudo ./scripts/setup_nginx.sh
```

This will:
- Install nginx if not present
- Copy configuration to `/etc/nginx/sites-available/`
- Enable the site
- Test and restart nginx

### 2. Manual Setup

```bash
# Copy configuration
sudo cp nginx/amazon-ads-api.conf /etc/nginx/sites-available/amazon-ads-api

# Create symlink to enable
sudo ln -s /etc/nginx/sites-available/amazon-ads-api /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Configuration Details

### Main Features

- **Reverse Proxy**: Routes requests to appropriate backend services
- **Rate Limiting**: Protects API endpoints from abuse
- **WebSocket Support**: For Next.js hot reload and real-time features
- **Gzip Compression**: Reduces bandwidth usage
- **Security Headers**: XSS protection, frame options, etc.
- **SSL Ready**: HTTPS configuration template included

### Location Blocks

- `/` - Frontend (Next.js on port 3000)
- `/api/` - Dashboard API (FastAPI on port 8000)
- `/docs`, `/openapi.json`, `/redoc` - API documentation
- `/v1/` - Node.js API (port 3001, if used)
- `/health` - Health check endpoint

### Rate Limiting

- **API Limit**: 100 requests/minute per IP
- **Auth Limit**: 10 requests/minute per IP (login/signup)

## SSL/HTTPS Setup

1. Install Certbot:
```bash
sudo apt-get install certbot python3-certbot-nginx
```

2. Get certificate:
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

3. Uncomment HTTPS server block in configuration

4. Update SSL certificate paths

5. Reload nginx:
```bash
sudo systemctl reload nginx
```

## Production Checklist

- [ ] Update `server_name` with your domain
- [ ] Configure SSL certificates
- [ ] Uncomment HTTPS server block
- [ ] Set up firewall rules (allow 80, 443)
- [ ] Configure log rotation
- [ ] Set up monitoring
- [ ] Review security headers
- [ ] Test rate limiting
- [ ] Verify all services are running

## Troubleshooting

### Check nginx status
```bash
sudo systemctl status nginx
```

### Test configuration
```bash
sudo nginx -t
```

### View logs
```bash
# Access logs
sudo tail -f /var/log/nginx/amazon-ads-api-access.log

# Error logs
sudo tail -f /var/log/nginx/amazon-ads-api-error.log
```

### Check if services are running
```bash
# Frontend
curl http://localhost:3000

# API
curl http://localhost:8000/api/health
```

### Reload nginx after changes
```bash
sudo systemctl reload nginx
```

## Customization

### Change Ports

Edit `amazon-ads-api.conf` and update upstream definitions:

```nginx
upstream dashboard_frontend {
    server 127.0.0.1:3000;  # Change port here
}

upstream dashboard_api {
    server 127.0.0.1:8000;  # Change port here
}
```

### Adjust Rate Limits

Modify limit zones:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
```

### Add Additional Services

Add new upstream and location block:

```nginx
upstream new_service {
    server 127.0.0.1:PORT;
}

location /new-service/ {
    proxy_pass http://new_service;
    # ... proxy settings
}
```

## Security Notes

- Keep nginx updated: `sudo apt-get update && sudo apt-get upgrade nginx`
- Review and adjust rate limits based on your needs
- Enable fail2ban for additional protection
- Regularly check access logs for suspicious activity
- Use strong SSL/TLS configuration in production

