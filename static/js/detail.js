/**
 * ScholarVault — Publication Detail Page JS
 */
'use strict';

// Tabs, bookmark toggle, citation copy handled by main.js
// This file adds detail-specific extras.

// Password toggle on auth pages
function togglePwd(id, btn) {
  const input = document.getElementById(id);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    btn.innerHTML = '<i class="bi bi-eye-slash-fill"></i>';
  } else {
    input.type = 'password';
    btn.innerHTML = '<i class="bi bi-eye-fill"></i>';
  }
}

// Share publication
const shareBtn = document.getElementById('shareBtn');
if (shareBtn) {
  shareBtn.addEventListener('click', async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: document.title, url: window.location.href });
      } catch (_) {}
    } else {
      await navigator.clipboard.writeText(window.location.href);
      shareBtn.innerHTML = '<i class="bi bi-check2 me-1"></i>Link Copied!';
      setTimeout(() => { shareBtn.innerHTML = '<i class="bi bi-share me-1"></i>Share'; }, 2500);
    }
  });
}

// Track view (fire and forget)
(function trackView() {
  const slug = window.DETAIL_CONFIG?.slug;
  if (!slug) return;
  fetch(`/api/publications/${slug}/`, { method: 'GET' }).catch(() => {});
})();

// ── PDF.js Inline Viewer ────────────────────────────────────────────────────

(function initPdfViewer() {
  const cfg = window.DETAIL_CONFIG;
  if (!cfg || !cfg.hasPdf || !cfg.pdfUrl) return;

  // Lazy-init: only start when the user clicks the Preview tab
  const previewTab = document.querySelector('[data-tab="preview"]');
  if (!previewTab) return;

  let pdfDoc = null;
  let currentPage = 1;
  let scale = 1.2;
  let renderTask = null;
  let initialised = false;

  const canvas       = document.getElementById('pdfCanvas');
  const ctx          = canvas ? canvas.getContext('2d') : null;
  const loadingEl    = document.getElementById('pdfLoading');
  const prevBtn      = document.getElementById('pdfPrevPage');
  const nextBtn      = document.getElementById('pdfNextPage');
  const zoomInBtn    = document.getElementById('pdfZoomIn');
  const zoomOutBtn   = document.getElementById('pdfZoomOut');
  const fullscreenBtn= document.getElementById('pdfFullscreen');
  const currentPageEl= document.getElementById('pdfCurrentPage');
  const totalPagesEl = document.getElementById('pdfTotalPages');
  const zoomLabelEl  = document.getElementById('pdfZoomLabel');
  const canvasWrap   = document.getElementById('pdfCanvasWrap');

  function showLoading(on) {
    if (loadingEl) loadingEl.style.display = on ? 'flex' : 'none';
    if (canvas) canvas.style.opacity = on ? '0' : '1';
  }

  async function renderPage(num) {
    if (!pdfDoc || !canvas || !ctx) return;
    if (renderTask) { renderTask.cancel(); }

    showLoading(true);
    try {
      const page = await pdfDoc.getPage(num);
      const viewport = page.getViewport({ scale });
      canvas.width  = viewport.width;
      canvas.height = viewport.height;

      renderTask = page.render({ canvasContext: ctx, viewport });
      await renderTask.promise;
      renderTask = null;

      currentPage = num;
      if (currentPageEl) currentPageEl.textContent = num;
      if (prevBtn) prevBtn.disabled = (num <= 1);
      if (nextBtn) nextBtn.disabled = (num >= pdfDoc.numPages);
    } catch (e) {
      if (e.name !== 'RenderingCancelledException') {
        console.error('PDF render error:', e);
      }
    } finally {
      showLoading(false);
    }
  }

  async function loadPdf() {
    if (initialised) return;
    initialised = true;
    showLoading(true);

    // Dynamically load PDF.js from CDN
    const PDFJS_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs';
    const WORKER_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs';

    try {
      const pdfjsLib = await import(PDFJS_CDN);
      pdfjsLib.GlobalWorkerOptions.workerSrc = WORKER_CDN;

      pdfDoc = await pdfjsLib.getDocument(cfg.pdfUrl).promise;
      if (totalPagesEl) totalPagesEl.textContent = pdfDoc.numPages;
      await renderPage(1);
    } catch (e) {
      console.error('PDF load error:', e);
      if (loadingEl) {
        loadingEl.innerHTML = '<p class="text-danger">Could not load PDF preview. Please download instead.</p>';
        loadingEl.style.display = 'flex';
      }
    }
  }

  // Init when Preview tab is clicked
  previewTab.addEventListener('click', () => {
    setTimeout(loadPdf, 100); // slight delay for panel transition
  });

  // If preview tab is already active on page load, init immediately
  if (previewTab.classList.contains('active')) {
    loadPdf();
  }

  // Navigation
  if (prevBtn) prevBtn.addEventListener('click', () => {
    if (pdfDoc && currentPage > 1) renderPage(currentPage - 1);
  });
  if (nextBtn) nextBtn.addEventListener('click', () => {
    if (pdfDoc && currentPage < pdfDoc.numPages) renderPage(currentPage + 1);
  });

  // Zoom
  function setScale(newScale) {
    scale = Math.min(3.0, Math.max(0.5, newScale));
    if (zoomLabelEl) zoomLabelEl.textContent = Math.round(scale * 100) + '%';
    if (pdfDoc) renderPage(currentPage);
  }
  if (zoomInBtn)  zoomInBtn.addEventListener('click',  () => setScale(scale + 0.2));
  if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => setScale(scale - 0.2));

  // Fullscreen
  if (fullscreenBtn && canvasWrap) {
    fullscreenBtn.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        canvasWrap.requestFullscreen().catch(() => {});
        fullscreenBtn.querySelector('i').className = 'bi bi-fullscreen-exit';
      } else {
        document.exitFullscreen();
        fullscreenBtn.querySelector('i').className = 'bi bi-fullscreen';
      }
    });
  }

  // Keyboard navigation when viewer is active
  document.addEventListener('keydown', (e) => {
    const panel = document.querySelector('[data-panel="preview"]');
    if (!panel || !panel.classList.contains('active')) return;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      if (pdfDoc && currentPage < pdfDoc.numPages) renderPage(currentPage + 1);
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      if (pdfDoc && currentPage > 1) renderPage(currentPage - 1);
    }
  });
})();
