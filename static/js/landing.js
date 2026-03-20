/**
 * ScholarVault — Landing Page JavaScript
 * Hero autocomplete + Featured carousel
 */

'use strict';

// ─── Hero Search Autocomplete ────────────────────────────────────────────────
const heroInput = document.getElementById('heroSearchInput');
const heroAutocomplete = document.getElementById('heroAutocomplete');

let heroTimer;

if (heroInput && heroAutocomplete) {
  heroInput.addEventListener('input', () => {
    clearTimeout(heroTimer);
    const q = heroInput.value.trim();
    if (q.length < 2) {
      heroAutocomplete.classList.remove('visible');
      heroAutocomplete.innerHTML = '';
      return;
    }
    heroTimer = setTimeout(() => fetchHeroAutocomplete(q), 280);
  });

  heroInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const form = heroInput.closest('form');
      if (form) form.submit();
    }
    if (e.key === 'Escape') {
      heroAutocomplete.classList.remove('visible');
    }
  });

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (!heroInput.contains(e.target) && !heroAutocomplete.contains(e.target)) {
      heroAutocomplete.classList.remove('visible');
    }
  });
}

async function fetchHeroAutocomplete(query) {
  try {
    const res = await fetch(`/api/autocomplete/?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    renderHeroAutocomplete(data.results, query);
  } catch (err) {
    console.error('Autocomplete error:', err);
  }
}

function renderHeroAutocomplete(results, query) {
  if (!heroAutocomplete) return;

  if (!results || results.length === 0) {
    heroAutocomplete.classList.remove('visible');
    return;
  }

  const typeIcons = {
    journal: 'bi-journal-text',
    thesis: 'bi-file-earmark-text',
    book: 'bi-book',
    conference: 'bi-people',
  };

  heroAutocomplete.innerHTML = results.map(r => `
    <a href="/publication/${r.slug}/" class="sv-autocomplete-item">
      <i class="bi ${typeIcons[r.publication_type] || 'bi-journal'} sv-autocomplete-icon"></i>
      <div class="sv-autocomplete-text">
        <div class="sv-autocomplete-title">${highlightMatch(r.title, query)}</div>
        <div class="sv-autocomplete-author">${escapeHtml(r.author)}</div>
      </div>
      <span class="sv-autocomplete-type">${capitalise(r.publication_type)}</span>
    </a>
  `).join('') + `
    <a href="/catalogue/?q=${encodeURIComponent(query)}" class="sv-autocomplete-item" style="justify-content:center;font-weight:600;color:#1B3A6B;font-size:0.82rem;border-top:1px solid #e2e8f0;">
      <i class="bi bi-search me-2"></i>View all results for "${escapeHtml(query)}"
    </a>`;

  heroAutocomplete.classList.add('visible');
}

function highlightMatch(text, query) {
  const escaped = escapeHtml(text);
  const escapedQ = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return escaped.replace(new RegExp(`(${escapedQ})`, 'gi'), '<mark style="background:rgba(201,168,76,0.3);color:inherit;padding:0 2px;border-radius:2px;">$1</mark>');
}

function capitalise(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

// ─── Featured Carousel ───────────────────────────────────────────────────────
const track = document.getElementById('featuredTrack');
const prevBtn = document.getElementById('carouselPrev');
const nextBtn = document.getElementById('carouselNext');
const dotsContainer = document.getElementById('carouselDots');

if (track) {
  const cards = track.querySelectorAll('.sv-featured-card');
  if (cards.length === 0) {
    // Fetch featured from API if no server-rendered ones
    fetchFeaturedCarousel();
  } else {
    initCarousel(cards);
  }
}

async function fetchFeaturedCarousel() {
  if (!track) return;
  try {
    const res = await fetch('/api/publications/featured/');
    const data = await res.json();
    if (!data.length) return;

    track.innerHTML = data.map(pub => `
      <div class="sv-featured-card">
        <div class="sv-featured-card-cover">
          <img src="${pub.cover_url || '/static/img/default-cover.jpg'}" alt="${escapeHtml(pub.title)}" loading="lazy" />
          <div class="sv-featured-type-badge">${capitalise(pub.publication_type)}</div>
          ${pub.is_open_access ? '<div class="sv-oa-badge"><i class="bi bi-unlock-fill"></i></div>' : ''}
        </div>
        <div class="sv-featured-card-body">
          <div class="sv-featured-category">${escapeHtml(pub.category_name || 'General')}</div>
          <h4 class="sv-featured-title"><a href="/publication/${pub.slug}/">${escapeHtml(pub.title.slice(0,70))}</a></h4>
          <div class="sv-featured-author"><i class="bi bi-person me-1"></i>${escapeHtml(pub.author)}</div>
          <div class="sv-featured-meta">
            <span><i class="bi bi-calendar3 me-1"></i>${pub.publication_year}</span>
            <span><i class="bi bi-eye me-1"></i>${pub.view_count || 0}</span>
          </div>
        </div>
      </div>
    `).join('');

    const cards = track.querySelectorAll('.sv-featured-card');
    initCarousel(cards);
  } catch (err) {
    console.error('Carousel fetch error:', err);
  }
}

function initCarousel(cards) {
  if (!track || cards.length === 0) return;

  let currentIndex = 0;
  let autoPlayTimer;
  let isDragging = false;
  let startX = 0;
  let scrollStart = 0;

  const visibleCount = () => window.innerWidth >= 992 ? 3 : window.innerWidth >= 768 ? 2 : 1;
  const cardWidth = () => cards[0].offsetWidth + 24; // 24px gap

  // Build dots
  const totalSlides = Math.max(0, cards.length - visibleCount() + 1);
  if (dotsContainer) {
    dotsContainer.innerHTML = Array.from({ length: totalSlides }, (_, i) => `
      <div class="sv-carousel-dot ${i === 0 ? 'active' : ''}" data-index="${i}"></div>
    `).join('');

    dotsContainer.querySelectorAll('.sv-carousel-dot').forEach(dot => {
      dot.addEventListener('click', () => goTo(parseInt(dot.dataset.index)));
    });
  }

  function goTo(index) {
    currentIndex = Math.max(0, Math.min(index, cards.length - visibleCount()));
    track.style.transform = `translateX(-${currentIndex * cardWidth()}px)`;
    dotsContainer?.querySelectorAll('.sv-carousel-dot').forEach((d, i) => {
      d.classList.toggle('active', i === currentIndex);
    });
  }

  function next() { goTo((currentIndex + 1) % (cards.length - visibleCount() + 1)); }
  function prev() { goTo((currentIndex - 1 + cards.length) % (cards.length - visibleCount() + 1)); }

  prevBtn?.addEventListener('click', prev);
  nextBtn?.addEventListener('click', next);

  // Auto-play
  function startAutoPlay() {
    autoPlayTimer = setInterval(next, 4500);
  }
  function stopAutoPlay() { clearInterval(autoPlayTimer); }

  startAutoPlay();
  track.addEventListener('mouseenter', stopAutoPlay);
  track.addEventListener('mouseleave', startAutoPlay);

  // Touch/drag
  track.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX;
    scrollStart = currentIndex * cardWidth();
    stopAutoPlay();
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const delta = startX - e.clientX;
    track.style.transform = `translateX(-${scrollStart + delta}px)`;
  });

  document.addEventListener('mouseup', (e) => {
    if (!isDragging) return;
    isDragging = false;
    const delta = startX - e.clientX;
    if (Math.abs(delta) > 60) {
      delta > 0 ? next() : prev();
    } else {
      goTo(currentIndex);
    }
    startAutoPlay();
  });

  // Touch
  track.addEventListener('touchstart', (e) => {
    startX = e.touches[0].clientX;
    stopAutoPlay();
  }, { passive: true });

  track.addEventListener('touchend', (e) => {
    const delta = startX - e.changedTouches[0].clientX;
    if (Math.abs(delta) > 50) { delta > 0 ? next() : prev(); }
    startAutoPlay();
  });

  // Responsive
  window.addEventListener('resize', () => goTo(Math.min(currentIndex, cards.length - visibleCount())));
}

// ─── Animate sections on scroll ──────────────────────────────────────────────
const animateSections = document.querySelectorAll('.sv-how-step, .sv-stat-card');
if (animateSections.length && 'IntersectionObserver' in window) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }, i * 100);
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  animateSections.forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    obs.observe(el);
  });
}
