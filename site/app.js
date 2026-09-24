const installPwaButton = document.getElementById('installPwaButton');

let deferredPrompt = null;

if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      await navigator.serviceWorker.register('sw.js');
    } catch (error) {
      console.warn('Service worker registration failed:', error);
    }
  });
}

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredPrompt = event;
  installPwaButton.style.display = 'inline-flex';
});

installPwaButton.addEventListener('click', async () => {
  if (!deferredPrompt) {
    alert('This browser cannot install the app from here yet. You can still download the Windows EXE from the release page.');
    return;
  }

  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  if (outcome === 'accepted') {
    console.log('PWA install accepted');
  }
  deferredPrompt = null;
  installPwaButton.style.display = 'none';
});
