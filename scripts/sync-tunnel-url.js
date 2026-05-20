#!/usr/bin/env node
/**
 * Reads the current tunnel URL from the VM and updates Cloudflare Worker KV.
 * Run this locally (or on any machine with wrangler installed).
 * Usage: node sync-tunnel-url.js
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const SSH_KEY = path.join(process.env.USERPROFILE, '.ssh', 'id_rsa_oci');
const SSH_CMD = `ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no ubuntu@129.213.35.8 "cat /opt/nocturne/current-tunnel-url.txt"`;
const KV_NAMESPACE_ID = '4dc5d2076ba9407796473017879587be';
const WORKER_DIR = path.join(__dirname, '..', 'nocturne-proxy');

let lastUrl = null;

// Try to load last known URL from cache
const cacheFile = path.join(WORKER_DIR, '.last-url');
if (fs.existsSync(cacheFile)) {
  lastUrl = fs.readFileSync(cacheFile, 'utf8').trim();
}

function getVmUrl() {
  try {
    return execSync(SSH_CMD, { encoding: 'utf8', timeout: 10000 }).trim();
  } catch {
    return null;
  }
}

function updateKv(url) {
  try {
    execSync(
      `cd "${WORKER_DIR}" && wrangler kv key put url "${url}" --namespace-id=${KV_NAMESPACE_ID} --remote`,
      { encoding: 'utf8', stdio: 'inherit', timeout: 30000 }
    );
    return true;
  } catch (e) {
    console.error('KV update failed:', e.message);
    return false;
  }
}

function check() {
  const url = getVmUrl();
  if (url && url !== lastUrl && url.startsWith('https://')) {
    console.log(`[${new Date().toISOString()}] Tunnel URL changed: ${url}`);
    if (updateKv(url)) {
      console.log(`  KV updated successfully`);
      lastUrl = url;
      fs.writeFileSync(cacheFile, url);
    }
  }
}

console.log(`Watching for tunnel URL changes... (last: ${lastUrl || 'none'})`);
check();
setInterval(check, 30000);
