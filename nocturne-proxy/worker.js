/**
 * Unified Proxy Worker — routes all 3 apps through one stable URL
 *
 * Routes:
 *   /copa/*      → CopaMundial (Next.js, port 3004)
 *   /nocturne/*  → Nocturne (FastAPI, port 8000)
 *   /api/*       → bing backend (Hono, port 3001)
 *   /health*     → bing health
 *
 * All requests proxy to the current cloudflared tunnel URL via KV.
 * KV key "tunnel_url" is updated by systemd timer on the VM every 60s.
 *
 * IMPORTANT: Does NOT strip prefixes. The full path goes to Caddy on the VM,
 * which already has route matchers for /copa/*, /nocturne/*, /api/*, etc.
 *
 * OPTIMIZATION: Uses in-memory counters with periodic KV sync to avoid
 * excessive KV writes (was doing a PUT on every request for rate limiting).
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, X-Auth-Token',
  'Access-Control-Max-Age': '86400',
};

// Rate limit: 100 requests per IP per 60s window
const RATE_LIMIT_WINDOW = 60;
const RATE_LIMIT_MAX = 100;
const KV_SYNC_INTERVAL = 10; // Sync to KV every 10 seconds (was every request)

// In-memory counters to reduce KV writes (same fix as edge-gateway)
const memoryCounters = new Map();
const lastSyncTimes = new Map();
const CLEANUP_INTERVAL = 60;
let lastCleanup = 0;

function getWindowKey(ip) {
  const windowNum = Math.floor(Date.now() / (RATE_LIMIT_WINDOW * 1000));
  return `rl:${ip}:${windowNum}`;
}

function cleanupOldEntries() {
  const now = Date.now();
  if (now - lastCleanup < CLEANUP_INTERVAL * 1000) return;
  lastCleanup = now;
  const currentWindow = Math.floor(now / (RATE_LIMIT_WINDOW * 1000));
  for (const key of memoryCounters.keys()) {
    const keyWindow = parseInt(key.split(':').pop() || '0', 10);
    if (keyWindow < currentWindow - 1) {
      memoryCounters.delete(key);
      lastSyncTimes.delete(key);
    }
  }
}

async function syncToKV(env, ip, count) {
  const windowKey = getWindowKey(ip);
  try {
    await env.TUNNEL_KV.put(windowKey, String(count), { expirationTtl: RATE_LIMIT_WINDOW + 1 });
  } catch { /* silent fail - local counter still tracks */ }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // ─── Health Check ────────────────────────────────────────────────
    if (path === '/health') {
      return jsonResponse({
        status: 'healthy',
        service: 'unified-proxy',
        timestamp: new Date().toISOString(),
      });
    }

    // ─── CORS Preflight ──────────────────────────────────────────────
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // ─── Rate Limiting (optimized to reduce KV writes) ───────────────
    if (env.TUNNEL_KV) {
      const ip = request.headers.get('cf-connecting-ip') || 'unknown';
      const windowKey = getWindowKey(ip);

      // Get or create counter
      let counter = memoryCounters.get(windowKey);
      if (!counter) {
        const stored = await env.TUNNEL_KV.get(windowKey);
        counter = stored ? parseInt(stored, 10) : 0;
      }

      if (counter >= RATE_LIMIT_MAX) {
        return jsonResponse(
          { error: 'Too many requests', retryAfter: RATE_LIMIT_WINDOW },
          { status: 429, headers: { 'Retry-After': String(RATE_LIMIT_WINDOW) } }
        );
      }

      // Increment and periodically sync to KV
      counter++;
      memoryCounters.set(windowKey, counter);
      cleanupOldEntries();

      const lastSync = lastSyncTimes.get(windowKey) || 0;
      if (Date.now() - lastSync >= KV_SYNC_INTERVAL * 1000) {
        await syncToKV(env, ip, counter);
        lastSyncTimes.set(windowKey, Date.now());
      }
    }

    // ─── Get Tunnel URL ──────────────────────────────────────────────
    const tunnelUrl = await env.TUNNEL_KV.get('tunnel_url');
    if (!tunnelUrl) {
      return jsonResponse(
        { error: 'Tunnel URL not set', hint: 'Run: wrangler kv:key put --binding=TUNNEL_KV tunnel_url "https://xxx.trycloudflare.com"' },
        { status: 503 }
      );
    }

    // ─── Proxy to Tunnel (full path, no stripping) ───────────────────
    const target = new URL(path + url.search, tunnelUrl);

    try {
      const proxyHeaders = new Headers(request.headers);

      // Remove hop-by-hop headers
      for (const h of ['transfer-encoding', 'connection', 'keep-alive', 'upgrade']) {
        proxyHeaders.delete(h);
      }

      // Set forwarded headers
      proxyHeaders.set('X-Forwarded-For', request.headers.get('cf-connecting-ip') || url.hostname);
      proxyHeaders.set('X-Forwarded-Proto', url.protocol.replace(':', ''));
      proxyHeaders.set('X-Forwarded-Host', url.hostname);

      const proxyResponse = await fetch(target.toString(), {
        method: request.method,
        headers: proxyHeaders,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : undefined,
        redirect: 'follow',
      });

      // ─── Build Response ────────────────────────────────────────────
      const responseHeaders = new Headers(proxyResponse.headers);

      // Apply CORS
      for (const [key, value] of Object.entries(CORS_HEADERS)) {
        responseHeaders.set(key, value);
      }

      // Security headers
      responseHeaders.set('X-Content-Type-Options', 'nosniff');
      responseHeaders.set('X-Frame-Options', 'DENY');

      // Cache static assets
      if (/\.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?|ttf|eot|webp)$/i.test(path)) {
        responseHeaders.set('Cache-Control', 'public, max-age=86400');
      }

      return new Response(proxyResponse.body, {
        status: proxyResponse.status,
        statusText: proxyResponse.statusText,
        headers: responseHeaders,
      });
    } catch (error) {
      return jsonResponse(
        { error: 'Backend unavailable', detail: error?.message || 'Unknown error' },
        { status: 502 }
      );
    }
  },
};

function jsonResponse(data, { status = 200, headers = {} } = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS, ...headers },
  });
}
