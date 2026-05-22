#!/usr/bin/env node
/**
 * Reads the current tunnel URL from VM docker logs and pushes it to
 * the shared edge-gateway Worker admin endpoint.
 *
 * Usage: node sync-tunnel-url.js
 *
 * Required env vars:
 *   WORKER_URL   — edge-gateway Worker URL (e.g. https://bing-edge-gateway.workers.dev)
 *   ADMIN_TOKEN  — X-Admin-Token for the admin endpoint
 */

const { execSync } = require('child_process');
const https = require('https');

const WORKER_URL = process.env.WORKER_URL || process.env.npm_package_config_worker_url;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || process.env.npm_package_config_admin_token;

const SSH_KEY = require('path').join(process.env.USERPROFILE || '/home/ubuntu', '.ssh/id_rsa_oci');

let lastUrl = null;
const cacheFile = require('path').join(__dirname, '..', 'nocturne-proxy', '.last-url');
const fs = require('fs');
if (fs.existsSync(cacheFile)) {
  lastUrl = fs.readFileSync(cacheFile, 'utf8').trim();
}

function getTunnelUrl() {
  try {
    const cmd = `ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no ubuntu@129.213.35.8 "docker logs bing-cloudflared-1 --tail 50 2>&1"`;
    const out = execSync(cmd, { encoding: 'utf8', timeout: 10000 });
    const match = out.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/);
    return match ? match[0] : null;
  } catch {
    return null;
  }
}

function updateWorker(url) {
  if (!WORKER_URL || !ADMIN_TOKEN) {
    console.error('Missing WORKER_URL or ADMIN_TOKEN');
    return false;
  }
  const parsed = new URL('/admin/backend-url', WORKER_URL);
  const body = JSON.stringify({ url });

  return new Promise((resolve) => {
    const req = https.request(parsed, {
      method: 'POST',
      headers: {
        'X-Admin-Token': ADMIN_TOKEN,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          resolve(true);
        } else {
          console.error(`Worker returned ${res.statusCode}: ${data}`);
          resolve(false);
        }
      });
    });
    req.on('error', (err) => {
      console.error('Request failed:', err.message);
      resolve(false);
    });
    req.write(body);
    req.end();
  });
}

async function check() {
  const url = getTunnelUrl();
  if (!url) {
    console.log('[tunnel-sync] No tunnel URL found, skipping...');
    return;
  }
  if (url !== lastUrl && url.startsWith('https://')) {
    console.log(`[${new Date().toISOString()}] Tunnel URL changed: ${url}`);
    const ok = await updateWorker(url);
    if (ok) {
      console.log('  ✓ Worker updated');
      lastUrl = url;
      fs.writeFileSync(cacheFile, url);
    } else {
      console.log('  ✗ Failed');
    }
  }
}

console.log(`[tunnel-sync] Watching for changes (last: ${lastUrl || 'none'})`);
check();
setInterval(check, 30000);
