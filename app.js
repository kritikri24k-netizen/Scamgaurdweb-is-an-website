// ScamGuard Dynamic Interactive Behaviors
document.addEventListener('DOMContentLoaded', () => {
  
  // 1. ChatGPT/Gemini Style Onboarding Splash Sequence
  const overlay = document.getElementById('welcomeScreenOverlay');
  const phase1 = document.getElementById('splashPhase1');
  const phase2 = document.getElementById('splashPhase2');

  // Check persistent login state or already dismissed state
  const localSavedEmail = localStorage.getItem('scamguard_saved_user');
  const isServerLoggedIn = overlay ? overlay.getAttribute('data-logged-in') === 'true' : false;
  const isWelcomeDismissed = sessionStorage.getItem('scamguard_welcome_dismissed') === 'true';

  if (overlay) {
    // If user is already logged in, has a saved account, OR has already dismissed/skipped the welcome screen in this session:
    // COMPLETELY BYPASS THE WELCOME SCREEN (prevents re-opening on language changes or reloads!)
    if (isServerLoggedIn || localSavedEmail || isWelcomeDismissed) {
      overlay.style.display = 'none';
      if (!isServerLoggedIn && localSavedEmail) {
        // Auto-reconnect session in background
        fetch('/auto-login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({email: localSavedEmail})
        });
      }
    } else {
      // First time visiting: Show Logo exclusively for 1.5 seconds, then reveal Sign In card
      setTimeout(() => {
        if (phase1) phase1.style.display = 'none';
        if (phase2) phase2.style.display = 'block';
      }, 1500);
    }
  }

  // Dismiss Splash Screen (Skip for later)
  window.skipWelcomeSplash = function() {
    sessionStorage.setItem('scamguard_welcome_dismissed', 'true');
    if (overlay) {
      overlay.classList.add('dismissed');
      setTimeout(() => {
        overlay.style.display = 'none';
      }, 800);
    }
  };

  // Remember credentials upon sign in form submission
  const authForms = document.querySelectorAll('form[action*="login"]');
  authForms.forEach(f => {
    f.addEventListener('submit', () => {
      sessionStorage.setItem('scamguard_welcome_dismissed', 'true');
      const emailInput = f.querySelector('input[type="email"]');
      if (emailInput && emailInput.value) {
        localStorage.setItem('scamguard_saved_user', emailInput.value.trim());
      }
    });
  });

  // 2. Modality Selection (Radio cards)
  const modalityOptions = document.querySelectorAll('.modality-choice');
  const workspaces = document.querySelectorAll('.scanner-workspace');

  modalityOptions.forEach(opt => {
    opt.addEventListener('click', () => {
      const targetId = opt.getAttribute('data-target');
      const radio = opt.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;

      modalityOptions.forEach(o => o.classList.remove('active'));
      opt.classList.add('active');

      workspaces.forEach(w => w.classList.remove('active'));
      const activeWs = document.getElementById(targetId);
      if (activeWs) {
        activeWs.classList.add('active');
      }
    });
  });

  // 3. Collapsible Rating Drawer Toggle
  const ratingDrawerHeader = document.getElementById('ratingDrawerHeader');
  const ratingDrawerBody = document.getElementById('ratingDrawerBody');
  if (ratingDrawerHeader && ratingDrawerBody) {
    ratingDrawerHeader.addEventListener('click', () => {
      ratingDrawerBody.classList.toggle('open');
      const icon = document.getElementById('ratingChevron');
      if (icon) {
        icon.innerText = ratingDrawerBody.classList.contains('open') ? '▲' : '▼';
      }
    });
  }

  // 4. Modal Handlers
  window.openModal = function(id) {
    const m = document.getElementById(id);
    if (m) m.classList.add('open');
  };

  window.closeModal = function(id) {
    const m = document.getElementById(id);
    if (m) m.classList.remove('open');
  };

  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.classList.remove('open');
      }
    });
  });
});
