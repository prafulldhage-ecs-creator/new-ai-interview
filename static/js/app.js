/**
 * InterviewIQ - Global App Utilities
 */

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const CSRF_TOKEN = getCookie('csrftoken') || '';

// Toast / Notification helper
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:10px;max-width:380px;';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `alert alert-${type}`;
  toast.style.cssText = 'margin-bottom:0;box-shadow:var(--shadow-md);animation:fadeIn 0.2s ease;';
  toast.innerHTML = `<span>${message}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss Django messages after 5s
  const djangoAlerts = document.querySelectorAll('.alert');
  djangoAlerts.forEach(al => {
    setTimeout(() => {
      al.style.opacity = '0';
      al.style.transition = 'opacity 0.4s ease';
      setTimeout(() => al.remove(), 400);
    }, 5000);
  });
});
