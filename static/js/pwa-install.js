/**
 * ApexRML PWA Installation Handler
 * Manages app installation on iOS and Android devices
 * Version: 1.0.0
 */

class PWAInstaller {
  constructor() {
    this.deferredPrompt = null;
    this.installButton = document.getElementById('install-btn');
    this.isIOSPWA = this.checkIOSPWA();
    this.isAndroidPWA = this.checkAndroidPWA();
    this.isInstalled = this.checkIfInstalled();
    
    this.init();
  }
  
  /**
   * Initialize PWA installation handling
   */
  init() {
    console.log('Initializing PWA...');
    
    // Register service worker
    this.registerServiceWorker();
    
    // Handle beforeinstallprompt for Android Chrome
    window.addEventListener('beforeinstallprompt', (e) => {
      console.log('beforeinstallprompt fired');
      e.preventDefault();
      this.deferredPrompt = e;
      this.showInstallButton();
    });
    
    // Handle app installed event
    window.addEventListener('appinstalled', () => {
      console.log('PWA was installed');
      this.hideInstallButton();
      this.showInstalledNotification();
    });
    
    // Handle display mode change
    window.addEventListener('orientationchange', () => {
      this.handleOrientationChange();
    });
    
    // Check if already installed
    if (this.isInstalled || window.matchMedia('(display-mode: standalone)').matches) {
      this.hideInstallButton();
      console.log('App already installed');
    }
    
    // iOS specific handling
    if (this.isIOSPWA) {
      this.handleIOSInstallation();
    }
    
    // Handle install button click
    if (this.installButton) {
      this.installButton.addEventListener('click', () => this.promptInstall());
    }
  }
  
  /**
   * Register service worker
   */
  async registerServiceWorker() {
    if (!('serviceWorker' in navigator)) {
      console.log('Service Worker not supported');
      return;
    }
    
    try {
      const registration = await navigator.serviceWorker.register('/static/service-worker.js', {
        scope: '/',
      });
      
      console.log('Service Worker registered:', registration.scope);
      
      // Check for updates periodically
      setInterval(() => {
        registration.update();
      }, 3600000); // Every hour
      
      // Listen for controller change (new SW activated)
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        this.showUpdateNotification();
      });
      
      return registration;
    } catch (error) {
      console.error('Service Worker registration failed:', error);
    }
  }
  
  /**
   * Show install button
   */
  showInstallButton() {
    if (this.installButton) {
      this.installButton.classList.remove('hidden');
      this.animateInstallButton();
    }
  }
  
  /**
   * Hide install button
   */
  hideInstallButton() {
    if (this.installButton) {
      this.installButton.classList.add('hidden');
    }
  }
  
  /**
   * Prompt user to install
   */
  async promptInstall() {
    if (!this.deferredPrompt) {
      console.log('Install prompt not available');
      return;
    }
    
    // Show the install prompt
    this.deferredPrompt.prompt();
    
    // Wait for user response
    const { outcome } = await this.deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      console.log('User accepted installation');
      this.hideInstallButton();
    } else {
      console.log('User rejected installation');
    }
    
    this.deferredPrompt = null;
  }
  
  /**
   * Check if running as iOS PWA
   */
  checkIOSPWA() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) &&
           !window.MSStream;
  }
  
  /**
   * Check if running as Android PWA
   */
  checkAndroidPWA() {
    return /Android/.test(navigator.userAgent);
  }
  
  /**
   * Check if app is installed
   */
  checkIfInstalled() {
    // Check display mode
    if (window.matchMedia('(display-mode: standalone)').matches) {
      return true;
    }
    
    // Check if running as PWA on iOS
    if (this.isIOSPWA && window.navigator.standalone === true) {
      return true;
    }
    
    // Check localStorage
    if (localStorage.getItem('pwa-installed')) {
      return true;
    }
    
    return false;
  }
  
  /**
   * Handle iOS installation instructions
   */
  handleIOSInstallation() {
    console.log('Handling iOS PWA installation');
    
    // Check if installed
    if (window.navigator.standalone === false) {
      // Show iOS installation instructions
      this.showIOSInstallInstructions();
    } else if (window.navigator.standalone === true) {
      // App is running in standalone mode
      localStorage.setItem('pwa-installed', 'true');
      console.log('iOS PWA running in standalone mode');
    }
  }
  
  /**
   * Show iOS installation instructions
   */
  showIOSInstallInstructions() {
    const message = `
      To install ApexRML on your iPhone:
      1. Tap the Share button
      2. Scroll and tap "Add to Home Screen"
      3. Tap "Add"
    `;
    
    if (confirm(message)) {
      localStorage.setItem('ios-install-prompt-shown', 'true');
    }
  }
  
  /**
   * Show install button with animation
   */
  animateInstallButton() {
    if (!this.installButton) return;
    
    this.installButton.style.animation = 'slideInUp 0.5s ease-out';
  }
  
  /**
   * Show installed notification
   */
  showInstalledNotification() {
    if (!('Notification' in window)) return;
    
    if (Notification.permission === 'granted') {
      new Notification('ApexRML Installed', {
        body: 'App installed successfully. You can now use it offline.',
        icon: '/static/images/icons/icon-192x192.png',
        tag: 'app-installed',
        requireInteraction: false,
      });
    }
  }
  
  /**
   * Show update available notification
   */
  showUpdateNotification() {
    if (!('Notification' in window)) return;
    
    if (Notification.permission === 'granted') {
      const notification = new Notification('ApexRML Update Available', {
        body: 'A new version is ready. Refresh the page to update.',
        icon: '/static/images/icons/icon-192x192.png',
        tag: 'app-update',
        requireInteraction: true,
      });
      
      notification.addEventListener('click', () => {
        window.location.reload();
      });
    }
  }
  
  /**
   * Handle orientation change
   */
  handleOrientationChange() {
    console.log('Orientation changed');
    // Adjust layout based on new orientation
  }
  
  /**
   * Request notification permissions
   */
  async requestNotificationPermission() {
    if (!('Notification' in window)) {
      console.log('Notifications not supported');
      return false;
    }
    
    if (Notification.permission === 'granted') {
      return true;
    }
    
    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }
    
    return false;
  }
  
  /**
   * Enable background sync
   */
  async enableBackgroundSync() {
    if (!('serviceWorker' in navigator) || !('SyncManager' in window)) {
      console.log('Background Sync not supported');
      return false;
    }
    
    try {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register('sync-leads');
      console.log('Background sync registered');
      return true;
    } catch (error) {
      console.error('Background sync registration failed:', error);
      return false;
    }
  }
  
  /**
   * Check if online
   */
  isOnline() {
    return navigator.onLine;
  }
  
  /**
   * Share functionality (Web Share API)
   */
  async share(title, text, url) {
    if (!navigator.share) {
      // Fallback
      console.log(`${title}: ${text} ${url}`);
      return;
    }
    
    try {
      await navigator.share({
        title,
        text,
        url,
      });
      console.log('Share successful');
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Share failed:', error);
      }
    }
  }
}

// Initialize PWA installer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.pwaInstaller = new PWAInstaller();
});

// Handle offline/online events
window.addEventListener('offline', () => {
  console.log('App went offline');
  showOfflineNotice();
});

window.addEventListener('online', () => {
  console.log('App went online');
  hideOfflineNotice();
  syncPendingData();
});

/**
 * Show offline notice
 */
function showOfflineNotice() {
  const notice = document.getElementById('offline-notice');
  if (notice) {
    notice.classList.remove('hidden');
  }
}

/**
 * Hide offline notice
 */
function hideOfflineNotice() {
  const notice = document.getElementById('offline-notice');
  if (notice) {
    notice.classList.add('hidden');
  }
}

/**
 * Sync pending data when back online
 */
function syncPendingData() {
  if ('serviceWorker' in navigator && 'SyncManager' in window) {
    navigator.serviceWorker.ready.then((registration) => {
      registration.sync.register('sync-leads')
        .then(() => console.log('Background sync triggered'))
        .catch((error) => console.error('Sync failed:', error));
    });
  }
}

// Detect if running as installed PWA
if (window.matchMedia('(display-mode: standalone)').matches) {
  document.body.classList.add('pwa-installed');
}

console.log('PWA installer loaded');
