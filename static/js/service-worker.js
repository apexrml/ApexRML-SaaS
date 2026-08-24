/**
 * ApexRML Service Worker
 * Offline support, caching, and push notifications
 * Version: 1.0.0
 */

const CACHE_VERSION = 'apexrml-v1-20240101';
const ASSETS_CACHE = `${CACHE_VERSION}-assets`;
const API_CACHE = `${CACHE_VERSION}-api`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;

// Files to precache on installation
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/offline.html',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/garage-finder.js',
  '/static/js/parts-finder.js',
  '/static/manifest.json'
];

// ============================================================================
// INSTALLATION - Precache static assets
// ============================================================================

self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(ASSETS_CACHE)
      .then((cache) => {
        console.log(`Precaching ${PRECACHE_URLS.length} assets`);
        return cache.addAll(PRECACHE_URLS);
      })
      .then(() => {
        console.log('Service Worker installed');
        return self.skipWaiting(); // Activate immediately
      })
      .catch((error) => {
        console.error('Installation failed:', error);
      })
  );
});

// ============================================================================
// ACTIVATION - Cleanup old caches
// ============================================================================

self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              // Delete old versioned caches
              return cacheName.startsWith('apexrml-v1-') && 
                     cacheName !== ASSETS_CACHE &&
                     cacheName !== API_CACHE &&
                     cacheName !== IMAGE_CACHE;
            })
            .map((cacheName) => {
              console.log(`Deleting old cache: ${cacheName}`);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('Service Worker activated');
        return self.clients.claim(); // Take control of all pages
      })
  );
});

// ============================================================================
// FETCH - Request handling with caching strategies
// ============================================================================

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip external domains
  if (url.origin !== location.origin) {
    return;
  }
  
  // API endpoints - Network first, then cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstStrategy(request, API_CACHE, 5000));
    return;
  }
  
  // Images - Cache first
  if (request.destination === 'image') {
    event.respondWith(cacheFirstStrategy(request, IMAGE_CACHE));
    return;
  }
  
  // Static assets - Cache first with network fallback
  if (shouldCacheAsset(url.pathname)) {
    event.respondWith(cacheFirstStrategy(request, ASSETS_CACHE));
    return;
  }
  
  // HTML pages - Network first with cache fallback
  if (request.destination === '' || request.destination === 'document') {
    event.respondWith(networkFirstStrategy(request, ASSETS_CACHE, 3000));
    return;
  }
});

// ============================================================================
// CACHING STRATEGIES
// ============================================================================

/**
 * Network first - try network, fall back to cache
 * Used for API calls and dynamic content
 */
async function networkFirstStrategy(request, cacheName, timeoutMs = 5000) {
  const cache = await caches.open(cacheName);
  
  try {
    // Race between network and timeout
    const response = await Promise.race([
      fetch(request),
      new Promise((resolve, reject) =>
        setTimeout(() => reject(new Error('Network request timeout')), timeoutMs)
      )
    ]);
    
    // Cache successful response
    if (response.ok) {
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    // Network failed or timed out, try cache
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      console.log(`Serving from cache: ${request.url}`);
      return cachedResponse;
    }
    
    // No cache, return offline page for navigation requests
    if (request.destination === 'document') {
      return cache.match('/offline.html');
    }
    
    // Return error response
    return new Response(
      JSON.stringify({ error: 'Network request failed' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Cache first - use cache, fall back to network
 * Used for static assets and images
 */
async function cacheFirstStrategy(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    console.log(`Serving from cache: ${request.url}`);
    // Update cache in background
    fetch(request)
      .then((response) => {
        if (response.ok) {
          cache.put(request, response);
        }
      })
      .catch(() => {}); // Ignore errors
    
    return cachedResponse;
  }
  
  try {
    const response = await fetch(request);
    
    if (response.ok) {
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.error(`Fetch failed: ${request.url}`, error);
    
    // Return error response
    return new Response(
      JSON.stringify({ error: 'Request failed' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Determine if a URL path should be cached as static asset
 */
function shouldCacheAsset(pathname) {
  const staticExtensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2', '.ttf'];
  return staticExtensions.some(ext => pathname.endsWith(ext));
}

// ============================================================================
// BACKGROUND SYNC
// ============================================================================

/**
 * Sync pending requests when back online
 */
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-leads') {
    event.waitUntil(
      syncPendingLeads()
        .then(() => {
          // Notify all clients that sync is complete
          return self.clients.matchAll();
        })
        .then((clients) => {
          clients.forEach((client) => {
            client.postMessage({ type: 'SYNC_COMPLETE', tag: 'sync-leads' });
          });
        })
    );
  }
});

/**
 * Sync pending lead submissions
 */
async function syncPendingLeads() {
  const db = await openDatabase();
  const pendingLeads = await getAllFromStore(db, 'pending_leads');
  
  for (const lead of pendingLeads) {
    try {
      const response = await fetch('/api/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lead.data)
      });
      
      if (response.ok) {
        await deleteFromStore(db, 'pending_leads', lead.id);
      }
    } catch (error) {
      console.error(`Failed to sync lead ${lead.id}:`, error);
    }
  }
}

// ============================================================================
// PUSH NOTIFICATIONS
// ============================================================================

/**
 * Handle push notifications
 */
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const options = {
    body: data.body || 'ApexRML notification',
    icon: '/static/images/icons/icon-192x192.png',
    badge: '/static/images/icons/badge-72x72.png',
    tag: data.tag || 'notification',
    requireInteraction: data.requireInteraction || false,
    data: {
      dateOfArrival: Date.now(),
      primaryKey: data.id,
      ...data
    }
  };
  
  // Add image if available
  if (data.image) {
    options.image = data.image;
  }
  
  // Add actions for interactive notifications
  if (data.actions) {
    options.actions = data.actions;
  }
  
  event.waitUntil(
    self.registration.showNotification(data.title || 'ApexRML', options)
  );
});

/**
 * Handle notification clicks
 */
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  const data = event.notification.data;
  const url = data.url || '/';
  
  event.waitUntil(
    // Find existing window/tab
    clients.matchAll({ type: 'window' })
      .then((clientList) => {
        // Check if already open
        for (let i = 0; i < clientList.length; i++) {
          const client = clientList[i];
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Open new window if not already open
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});

// ============================================================================
// INDEXED DB HELPER FUNCTIONS
// ============================================================================

/**
 * Open IndexedDB database
 */
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('apexrml-db', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      // Create object stores
      if (!db.objectStoreNames.contains('pending_leads')) {
        db.createObjectStore('pending_leads', { keyPath: 'id', autoIncrement: true });
      }
      
      if (!db.objectStoreNames.contains('offline_cache')) {
        db.createObjectStore('offline_cache', { keyPath: 'url' });
      }
    };
  });
}

/**
 * Get all items from IndexedDB store
 */
function getAllFromStore(db, storeName) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([storeName], 'readonly');
    const store = transaction.objectStore(storeName);
    const request = store.getAll();
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

/**
 * Delete item from IndexedDB store
 */
function deleteFromStore(db, storeName, key) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([storeName], 'readwrite');
    const store = transaction.objectStore(storeName);
    const request = store.delete(key);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

// ============================================================================
// MESSAGE HANDLING
// ============================================================================

/**
 * Handle messages from clients
 */
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'REGISTER_SYNC') {
    self.registration.sync.register('sync-leads')
      .then(() => {
        event.ports[0].postMessage({ status: 'sync registered' });
      })
      .catch((error) => {
        event.ports[0].postMessage({ status: 'sync failed', error: error.message });
      });
  }
});

console.log('Service Worker initialized');
