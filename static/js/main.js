/**
 * ScholarVault — Main JavaScript
 * Handles: Navbar, Search Overlay, Toast Messages, Bookmarks, Tabs
 */

'use strict';

// ─── Navbar scroll effect ────────────────────────────────────────────────────
const navbar = document.getElementById('mainNav');
if (navbar) {
  const handleScroll = () => {
    navbar.classList.toggle('scrolled', window.scrollY > 60);
  };
  window.addEventListener('scroll', handleScroll, { passive: true });
}

// ─── Search Overlay ──────────────────────────────────────────────────────────
const searchOverlay = document.getElementById('searchOverlay');
const navSearchBtn = document.getElementById('navSearchBtn');
const searchOverlayClose = document.getElementById('searchOverlayClose');
const overlaySearchInput = document.getElementById('overlaySearchInput');
const overlaySearchResults = document.getElementById('overlaySearchResults');

let overlaySearchTimer;

function openSearchOverlay() {
  searchOverlay?.classList.add('active');
  document.body.style.overflow = 'hidden';
  setTimeout(() => overlaySearchInput?.focus(), 100);
}

function closeSearchOverlay() {
  searchOverlay?.classList.remove('active');
  document.body.style.overflow = '';
  if (overlaySearchInput) overlaySearchInput.value = '';
  if (overlaySearchResults) overlaySearchResults.innerHTML = '';
}

navSearchBtn?.addEventListener('click', openSearchOverlay);
searchOverlayClose?.addEventListener('click', closeSearchOverlay);
searchOverlay?.addEventListener('click', (e) => {
  if (e.target === searchOverlay) closeSearchOverlay();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeSearchOverlay();
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    openSearchOverlay();
  }
});

overlaySearchInput?.addEventListener('input', () => {
  clearTimeout(overlaySearchTimer);
  const q = overlaySearchInput.value.trim();
  if (q.length < 2) { overlaySearchResults.innerHTML = ''; return; }
  overlaySearchTimer = setTimeout(() => overlaySearch(q), 280);
});

async function overlaySearch(query) {
  try {
    const res = await fetch(`/api/autocomplete/?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    renderOverlayResults(data.results, query);
  } catch (err) {
    console.error('Search error:', err);
  }
}

function renderOverlayResults(results, query) {
  if (!overlaySearchResults) return;
  if (!results.length) {
    overlaySearchResults.innerHTML = `
      <div style="padding: 1.5rem; text-align:center; color: #64748b; font-size:0.875rem;">
        No results for "<strong>${escapeHtml(query)}</strong>". 
        <a href="/catalogue/?q=${encodeURIComponent(query)}" style="color:#1B3A6B;font-weight:600;">Search full library →</a>
      </div>`;
    return;
  }
  overlaySearchResults.innerHTML = results.map(r => `
    <a href="/publication/${r.slug}/" class="sv-overlay-result-item">
      <i class="bi bi-journal-text" style="color:#64748b;flex-shrink:0;"></i>
      <div style="flex:1;min-width:0;">
        <div style="font-weight:600;font-size:0.875rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(r.title)}</div>
        <div style="font-size:0.75rem;color:#94a3b8;">${escapeHtml(r.author)}</div>
      </div>
      <span class="sv-overlay-result-type">${escapeHtml(r.publication_type)}</span>
    </a>
  `).join('') + `
    <a href="/catalogue/?q=${encodeURIComponent(query)}" class="sv-overlay-result-item" style="justify-content:center;font-weight:600;color:#1B3A6B;font-size:0.875rem;">
      <i class="bi bi-search me-2"></i>Search all results for "${escapeHtml(query)}"
    </a>`;
}

// ─── Toast Messages ──────────────────────────────────────────────────────────
document.querySelectorAll('.sv-toast').forEach(toast => {
  const closeBtn = toast.querySelector('.sv-toast-close');
  closeBtn?.addEventListener('click', () => dismissToast(toast));
  setTimeout(() => dismissToast(toast), 5000);
});

function dismissToast(toast) {
  toast.style.animation = 'slideInToast 0.3s ease reverse forwards';
  setTimeout(() => toast.remove(), 300);
}

// ─── Tab System (Publication Detail) ─────────────────────────────────────────
const tabs = document.querySelectorAll('.sv-tab');
const panels = document.querySelectorAll('.sv-tab-panel');

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const targetPanel = tab.dataset.tab;
    tabs.forEach(t => t.classList.remove('active'));
    panels.forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.querySelector(`[data-panel="${targetPanel}"]`)?.classList.add('active');
  });
});

// ─── Citation Copy Buttons ───────────────────────────────────────────────────
document.querySelectorAll('.sv-copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetId = btn.dataset.target;
    const text = document.getElementById(targetId)?.textContent || '';
    navigator.clipboard.writeText(text).then(() => {
      const original = btn.innerHTML;
      btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Copied!';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.innerHTML = original;
        btn.classList.remove('copied');
      }, 2500);
    });
  });
});

// ─── Bookmark Toggle (Detail Page) ───────────────────────────────────────────
const bookmarkBtn = document.getElementById('bookmarkBtn');
if (bookmarkBtn && window.DETAIL_CONFIG) {
  bookmarkBtn.addEventListener('click', async () => {
    if (!DETAIL_CONFIG.isAuthenticated) {
      window.location.href = `/auth/login/?next=/publication/${DETAIL_CONFIG.slug}/`;
      return;
    }
    try {
      const res = await fetch(`/api/bookmarks/toggle/${DETAIL_CONFIG.slug}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': DETAIL_CONFIG.csrfToken, 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      const icon = document.getElementById('bookmarkIcon');
      const text = document.getElementById('bookmarkText');
      if (data.bookmarked) {
        icon.className = 'bi bi-bookmark-fill me-2';
        text.textContent = 'Saved';
        bookmarkBtn.classList.add('sv-bookmarked');
        showInlineMessage('Saved to your library!', 'success');
      } else {
        icon.className = 'bi bi-bookmark me-2';
        text.textContent = 'Save to Library';
        bookmarkBtn.classList.remove('sv-bookmarked');
        showInlineMessage('Removed from library.', 'info');
      }
    } catch (err) {
      console.error('Bookmark error:', err);
    }
  });
}

// ─── Catalogue Bookmark Buttons ───────────────────────────────────────────────
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.sv-bookmark-btn');
  if (!btn) return;
  e.preventDefault();
  const slug = btn.dataset.slug;
  if (!slug) return;
  const csrfEl = document.querySelector('[name=csrfmiddlewaretoken]');
  const csrf = csrfEl?.value || getCookie('csrftoken');
  try {
    const res = await fetch(`/api/bookmarks/toggle/${slug}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf, 'Content-Type': 'application/json' },
    });
    const data = await res.json();
    const icon = btn.querySelector('i');
    if (data.bookmarked) {
      btn.classList.add('active');
      if (icon) icon.className = 'bi bi-bookmark-fill';
    } else {
      btn.classList.remove('active');
      if (icon) icon.className = 'bi bi-bookmark';
    }
  } catch (err) { console.error(err); }
});

// ─── Mobile Filter Panel ─────────────────────────────────────────────────────
const filterPanel = document.getElementById('filterPanel');
const mobileFilterBtn = document.getElementById('mobileFilterBtn');
let filterOverlay;

mobileFilterBtn?.addEventListener('click', () => {
  filterPanel?.classList.toggle('open');
  if (!filterOverlay) {
    filterOverlay = document.createElement('div');
    filterOverlay.className = 'sv-filter-overlay';
    filterOverlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:998;';
    document.body.appendChild(filterOverlay);
    filterOverlay.addEventListener('click', () => {
      filterPanel?.classList.remove('open');
      filterOverlay.remove();
      filterOverlay = null;
    });
  } else {
    filterOverlay.remove();
    filterOverlay = null;
  }
});

// ─── Intersection Observer for fade-in animations ────────────────────────────
const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -40px 0px' };
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      entry.target.style.animationDelay = `${i * 0.05}s`;
      entry.target.classList.add('sv-animate-in');
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

document.querySelectorAll('.sv-category-card, .sv-pub-card, .sv-how-step, .sv-stat-card').forEach(el => {
  el.style.opacity = '0';
  observer.observe(el);
});

// ─── Utilities ───────────────────────────────────────────────────────────────
function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function getCookie(name) {
  const cookie = document.cookie.split(';').find(c => c.trim().startsWith(name + '='));
  return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
}

function showInlineMessage(message, type = 'success') {
  const container = document.querySelector('.sv-messages-container') || (() => {
    const el = document.createElement('div');
    el.className = 'sv-messages-container';
    document.body.appendChild(el);
    return el;
  })();
  const icons = { success: 'check-circle-fill', info: 'info-circle-fill', error: 'exclamation-circle-fill' };
  const toast = document.createElement('div');
  toast.className = `sv-toast sv-toast--${type}`;
  toast.innerHTML = `<i class="bi bi-${icons[type] || icons.info} me-2"></i>${escapeHtml(message)}<button class="sv-toast-close">&times;</button>`;
  container.appendChild(toast);
  toast.querySelector('.sv-toast-close').addEventListener('click', () => dismissToast(toast));
  setTimeout(() => dismissToast(toast), 4000);
}
