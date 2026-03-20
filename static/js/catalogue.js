/**
 * ScholarVault — Catalogue Page JavaScript
 * Full AJAX search + multi-filter system with debounce
 */

'use strict';

// ─── State ───────────────────────────────────────────────────────────────────
const state = {
  q: '',
  category: '',
  type: '',
  year_from: '',
  year_to: '',
  author: '',
  open_access: '',
  sort: '-created_at',
  page: 1,
};

// Merge URL params into state on load
if (window.CATALOGUE_CONFIG?.currentFilters) {
  Object.assign(state, window.CATALOGUE_CONFIG.currentFilters);
}

let searchDebounce;
let currentRequest = null;

// ─── DOM refs ────────────────────────────────────────────────────────────────
const grid = document.getElementById('publicationsGrid');
const resultCount = document.getElementById('resultCount');
const loadingIndicator = document.getElementById('loadingIndicator');
const activeFiltersEl = document.getElementById('activeFilters');
const paginationContainer = document.getElementById('paginationContainer');
const searchInput = document.getElementById('searchInput');
const yearFrom = document.getElementById('yearFrom');
const yearTo = document.getElementById('yearTo');
const authorFilter = document.getElementById('authorFilter');
const openAccessFilter = document.getElementById('openAccessFilter');
const sortFilter = document.getElementById('sortFilter');
const clearFiltersBtn = document.getElementById('clearFiltersBtn');
const gridViewBtn = document.getElementById('gridViewBtn');
const listViewBtn = document.getElementById('listViewBtn');

// ─── Bind Events ─────────────────────────────────────────────────────────────
searchInput?.addEventListener('input', () => {
  clearTimeout(searchDebounce);
  state.q = searchInput.value;
  state.page = 1;
  searchDebounce = setTimeout(doSearch, 350);
});

yearFrom?.addEventListener('change', () => { state.year_from = yearFrom.value; state.page = 1; doSearch(); });
yearTo?.addEventListener('change', () => { state.year_to = yearTo.value; state.page = 1; doSearch(); });
authorFilter?.addEventListener('input', () => {
  clearTimeout(searchDebounce);
  state.author = authorFilter.value;
  state.page = 1;
  searchDebounce = setTimeout(doSearch, 400);
});
openAccessFilter?.addEventListener('change', () => {
  state.open_access = openAccessFilter.checked ? '1' : '';
  state.page = 1;
  doSearch();
});
sortFilter?.addEventListener('change', () => { state.sort = sortFilter.value; state.page = 1; doSearch(); });
clearFiltersBtn?.addEventListener('click', clearAllFilters);
document.getElementById('resetSearchBtn')?.addEventListener('click', clearAllFilters);

// Category filter clicks
document.querySelectorAll('[data-filter="category"]').forEach(el => {
  el.addEventListener('click', () => {
    document.querySelectorAll('[data-filter="category"]').forEach(e => e.classList.remove('active'));
    el.classList.add('active');
    state.category = el.dataset.value;
    state.page = 1;
    doSearch();
  });
});

// Type filter clicks
document.querySelectorAll('[data-filter="type"]').forEach(el => {
  el.addEventListener('click', () => {
    document.querySelectorAll('[data-filter="type"]').forEach(e => e.classList.remove('active'));
    el.classList.add('active');
    state.type = el.dataset.value;
    state.page = 1;
    doSearch();
  });
});

// View toggle
gridViewBtn?.addEventListener('click', () => {
  grid?.classList.remove('list-view');
  gridViewBtn.classList.add('active');
  listViewBtn?.classList.remove('active');
  localStorage.setItem('sv-view', 'grid');
});
listViewBtn?.addEventListener('click', () => {
  grid?.classList.add('list-view');
  listViewBtn.classList.add('active');
  gridViewBtn?.classList.remove('active');
  localStorage.setItem('sv-view', 'list');
});

// Restore view preference
if (localStorage.getItem('sv-view') === 'list') {
  grid?.classList.add('list-view');
  listViewBtn?.classList.add('active');
  gridViewBtn?.classList.remove('active');
}

// ─── AJAX Search ─────────────────────────────────────────────────────────────
async function doSearch() {
  if (!grid) return;

  // Cancel in-flight request
  if (currentRequest) {
    currentRequest.abort?.();
  }

  showLoading(true);
  updateActiveFilters();
  updateURL();

  const params = buildParams();
  const url = `/api/publications/search/?${params}`;

  try {
    const controller = new AbortController();
    currentRequest = controller;

    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    renderResults(data);
    renderPagination(data);

    if (resultCount) {
      resultCount.textContent = (data.count || data.total_count || 0).toLocaleString();
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error('Search failed:', err);
      showError();
    }
  } finally {
    showLoading(false);
    currentRequest = null;
  }
}

function buildParams() {
  const p = new URLSearchParams();
  if (state.q) p.set('q', state.q);
  if (state.category) p.set('category', state.category);
  if (state.type) p.set('type', state.type);
  if (state.year_from) p.set('year_from', state.year_from);
  if (state.year_to) p.set('year_to', state.year_to);
  if (state.author) p.set('author', state.author);
  if (state.open_access) p.set('open_access', state.open_access);
  if (state.sort) p.set('sort', state.sort);
  if (state.page > 1) p.set('page', state.page);
  return p.toString();
}

function updateURL() {
  const params = buildParams();
  const newUrl = `${window.location.pathname}${params ? '?' + params : ''}`;
  history.replaceState(null, '', newUrl);
}

// ─── Render Functions ─────────────────────────────────────────────────────────
function renderResults(data) {
  if (!grid) return;
  const results = data.results || [];

  if (results.length === 0) {
    grid.innerHTML = `
      <div class="sv-empty-state" style="grid-column:1/-1;">
        <i class="bi bi-search"></i>
        <h4>No publications found</h4>
        <p>Try adjusting your search terms or removing some filters.</p>
        <button class="sv-btn-primary" onclick="clearAllFilters()">Clear All Filters</button>
      </div>`;
    return;
  }

  grid.innerHTML = results.map(pub => renderCard(pub)).join('');

  // Rebind bookmark buttons in new results
  grid.querySelectorAll('.sv-bookmark-btn').forEach(btn => {
    btn.addEventListener('click', handleBookmark);
  });

  // Animate in
  grid.querySelectorAll('.sv-pub-card').forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(12px)';
    setTimeout(() => {
      card.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, i * 40);
  });
}

function renderCard(pub) {
  const isOA = pub.is_open_access;
  const coverUrl = pub.cover_url || '/static/img/default-cover.jpg';
  return `
    <div class="sv-pub-card" data-slug="${escapeHtml(pub.slug)}">
      <div class="sv-pub-card-cover">
        <a href="/publication/${escapeHtml(pub.slug)}/">
          <img src="${escapeHtml(coverUrl)}" alt="${escapeHtml(pub.title)}" loading="lazy" />
        </a>
        <div class="sv-pub-type">${escapeHtml(pub.publication_type_display || pub.publication_type)}</div>
        ${isOA ? '<div class="sv-oa-badge" title="Open Access"><i class="bi bi-unlock-fill"></i></div>' : ''}
        <div class="sv-pub-hover-actions">
          <a href="/publication/${escapeHtml(pub.slug)}/" class="sv-pub-action-btn" title="View Details">
            <i class="bi bi-eye-fill"></i>
          </a>
          <button class="sv-pub-action-btn sv-bookmark-btn ${pub.is_bookmarked ? 'active' : ''}"
                  data-slug="${escapeHtml(pub.slug)}" title="Bookmark">
            <i class="bi bi-bookmark${pub.is_bookmarked ? '-fill' : ''}"></i>
          </button>
          ${isOA ? `<a href="/publication/${escapeHtml(pub.slug)}/download/" class="sv-pub-action-btn" title="Download"><i class="bi bi-download"></i></a>` : ''}
        </div>
      </div>
      <div class="sv-pub-card-body">
        ${pub.category_name ? `<a href="/catalogue/?category=${encodeURIComponent(pub.category_slug || '')}" class="sv-pub-category">${escapeHtml(pub.category_name)}</a>` : ''}
        <h5 class="sv-pub-title">
          <a href="/publication/${escapeHtml(pub.slug)}/">${escapeHtml(pub.title.slice(0, 65))}</a>
        </h5>
        <div class="sv-pub-author"><i class="bi bi-person me-1"></i>${escapeHtml(pub.author)}</div>
        <div class="sv-pub-footer">
          <span class="sv-pub-year"><i class="bi bi-calendar3 me-1"></i>${pub.publication_year || '—'}</span>
          <span class="sv-pub-views"><i class="bi bi-eye me-1"></i>${(pub.view_count || 0).toLocaleString()}</span>
        </div>
      </div>
    </div>`;
}

function renderPagination(data) {
  if (!paginationContainer) return;
  const count = data.count || 0;
  const pageSize = 20;
  const totalPages = Math.ceil(count / pageSize);

  if (totalPages <= 1) { paginationContainer.innerHTML = ''; return; }

  const pages = [];
  const current = state.page;

  pages.push(`<li>${current > 1 ? `<a class="sv-page-btn sv-page-nav" href="#" data-page="${current - 1}"><i class="bi bi-chevron-left"></i></a>` : '<span class="sv-page-btn sv-page-nav" style="opacity:0.3"><i class="bi bi-chevron-left"></i></span>'}</li>`);

  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= current - 2 && i <= current + 2)) {
      pages.push(`<li><a class="sv-page-btn ${i === current ? 'active' : ''}" href="#" data-page="${i}">${i}</a></li>`);
    } else if (i === current - 3 || i === current + 3) {
      pages.push('<li><span class="sv-page-btn" style="border:none;cursor:default;">…</span></li>');
    }
  }

  pages.push(`<li>${current < totalPages ? `<a class="sv-page-btn sv-page-nav" href="#" data-page="${current + 1}"><i class="bi bi-chevron-right"></i></a>` : '<span class="sv-page-btn sv-page-nav" style="opacity:0.3"><i class="bi bi-chevron-right"></i></span>'}</li>`);

  paginationContainer.innerHTML = `<nav><ul class="sv-page-list">${pages.join('')}</ul></nav>`;

  paginationContainer.querySelectorAll('[data-page]').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      state.page = parseInt(link.dataset.page);
      doSearch();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
}

// ─── Active Filter Pills ──────────────────────────────────────────────────────
const filterLabels = {
  q: 'Search',
  category: 'Category',
  type: 'Type',
  year_from: 'From Year',
  year_to: 'To Year',
  author: 'Author',
  open_access: 'Open Access',
};

function updateActiveFilters() {
  if (!activeFiltersEl) return;
  const pills = [];
  Object.entries(state).forEach(([key, val]) => {
    if (!val || key === 'sort' || key === 'page') return;
    pills.push(`
      <div class="sv-filter-pill">
        <span>${filterLabels[key] || key}: <strong>${key === 'open_access' ? 'Yes' : val}</strong></span>
        <button onclick="clearFilter('${key}')" title="Remove filter"><i class="bi bi-x"></i></button>
      </div>`);
  });
  activeFiltersEl.innerHTML = pills.join('');
}

window.clearFilter = function(key) {
  state[key] = '';
  state.page = 1;

  // Reset UI controls
  if (key === 'q' && searchInput) searchInput.value = '';
  if (key === 'year_from' && yearFrom) yearFrom.value = '';
  if (key === 'year_to' && yearTo) yearTo.value = '';
  if (key === 'author' && authorFilter) authorFilter.value = '';
  if (key === 'open_access' && openAccessFilter) openAccessFilter.checked = false;
  if (key === 'category') {
    document.querySelectorAll('[data-filter="category"]').forEach(el => el.classList.remove('active'));
    document.querySelector('[data-filter="category"][data-value=""]')?.classList.add('active');
  }
  if (key === 'type') {
    document.querySelectorAll('[data-filter="type"]').forEach(el => el.classList.remove('active'));
    document.querySelector('[data-filter="type"][data-value=""]')?.classList.add('active');
  }
  doSearch();
};

function clearAllFilters() {
  state.q = '';
  state.category = '';
  state.type = '';
  state.year_from = '';
  state.year_to = '';
  state.author = '';
  state.open_access = '';
  state.page = 1;

  if (searchInput) searchInput.value = '';
  if (yearFrom) yearFrom.value = '';
  if (yearTo) yearTo.value = '';
  if (authorFilter) authorFilter.value = '';
  if (openAccessFilter) openAccessFilter.checked = false;

  document.querySelectorAll('[data-filter]').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('[data-filter][data-value=""]').forEach(el => el.classList.add('active'));

  doSearch();
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────
function showLoading(show) {
  if (loadingIndicator) loadingIndicator.style.display = show ? 'flex' : 'none';
  if (grid) grid.style.opacity = show ? '0.4' : '1';
}

function showError() {
  if (!grid) return;
  grid.innerHTML = `
    <div class="sv-empty-state" style="grid-column:1/-1;">
      <i class="bi bi-exclamation-triangle" style="color:#EF4444;"></i>
      <h4>Something went wrong</h4>
      <p>Could not load results. Please try again.</p>
      <button class="sv-btn-primary" onclick="doSearch()">Retry</button>
    </div>`;
}

async function handleBookmark(e) {
  e.preventDefault();
  e.stopPropagation();
  const btn = e.currentTarget;
  const slug = btn.dataset.slug;
  const csrf = getCookie('csrftoken');
  try {
    const res = await fetch(`/api/bookmarks/toggle/${slug}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf },
    });
    if (res.status === 403) { window.location.href = '/auth/login/'; return; }
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
}

function getCookie(name) {
  const cookie = document.cookie.split(';').find(c => c.trim().startsWith(name + '='));
  return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

// ─── Init: run search if URL has params ──────────────────────────────────────
(function init() {
  const hasFilters = Object.values(state).some(v => v && v !== '-created_at' && v !== 1);
  if (hasFilters) {
    doSearch();
  }
})();
