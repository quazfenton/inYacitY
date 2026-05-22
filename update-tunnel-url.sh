#!/bin/bash
# Auto-update Cloudflare Worker KV with current tunnel URL
NEW_URL=$(sudo docker logs bing-cloudflared-1 --tail 50 2>&1 | grep -oP 'https://[a-z-]+\.trycloudflare\.com' | tail -1)
if [ -n "$NEW_URL" ]; then
  echo "$(date): Tunnel URL: $NEW_URL"
  echo "$NEW_URL" > /opt/nocturne/current-tunnel-url.txt
fi
