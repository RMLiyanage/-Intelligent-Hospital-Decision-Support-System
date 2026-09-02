/**
 * MediRoute DSS — Main JavaScript
 * =================================
 * Provides:
 *  - Sidebar collapse/toggle
 *  - Bootstrap toast helpers
 *  - Auto-dismiss flash alerts
 *  - Theme utilities
 */

'use strict';

// ── Sidebar toggle ──
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');

if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
        // Mobile: slide in/out
        if (window.innerWidth <= 991) {
            document.body.classList.toggle('sidebar-open');
        } else {
            // Desktop: collapse to icon-only
            document.body.classList.toggle('sidebar-collapsed');
            localStorage.setItem(
                'sidebarCollapsed',
                document.body.classList.contains('sidebar-collapsed') ? '1' : '0'
            );
        }
    });

    // Restore collapse preference on desktop
    if (window.innerWidth > 991 && localStorage.getItem('sidebarCollapsed') === '1') {
        document.body.classList.add('sidebar-collapsed');
    }
}

// ── Close sidebar on mobile backdrop click ──
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 991
        && document.body.classList.contains('sidebar-open')
        && !sidebar?.contains(e.target)
        && e.target !== sidebarToggle) {
        document.body.classList.remove('sidebar-open');
    }
});

// ── Auto-dismiss Bootstrap alerts after 5s ──
document.querySelectorAll('.alert.alert-dismissible').forEach(alert => {
    setTimeout(() => {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        if (bsAlert) bsAlert.close();
    }, 5000);
});

// ── Mark active sidebar links by current path ──
const currentPath = window.location.pathname;
document.querySelectorAll('.mr-nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
    }
});

// ── Utility: show a Bootstrap toast (call from other scripts) ──
window.MediRoute = window.MediRoute || {};

MediRoute.showToast = function(message, type = 'info') {
    const container = document.getElementById('toastContainer')
        || (() => {
            const c = document.createElement('div');
            c.id = 'toastContainer';
            c.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            c.style.zIndex = 9999;
            document.body.appendChild(c);
            return c;
        })();

    const colors = {
        success: '#22c55e', danger: '#ef4444',
        warning: '#f59e0b', info: '#3b82f6',
    };

    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white border-0 show';
    toast.style.backgroundColor = colors[type] || colors.info;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body fw-medium">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;

    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
};

// ── Format numbers with commas for stat display ──
document.querySelectorAll('.stat-value').forEach(el => {
    const num = parseInt(el.textContent.trim(), 10);
    if (!isNaN(num) && num >= 1000) {
        el.textContent = num.toLocaleString();
    }
});
