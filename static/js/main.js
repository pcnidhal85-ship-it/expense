/* ============================================================
   CashTrack — main.js
   Handles: dark/light mode, sidebar, Chart.js charts,
            auto-dismiss alerts, delete confirmation guard
   ============================================================ */

'use strict';

/* ── Theme ── */
const THEME_KEY = 'cashtrack-theme';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || 'dark';
  applyTheme(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
}

/* ── Sidebar ── */
function initSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('overlay');
  const hamburger = document.getElementById('hamburgerBtn');

  if (!sidebar) return;

  function openSidebar() {
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  if (hamburger) hamburger.addEventListener('click', openSidebar);
  if (overlay)   overlay.addEventListener('click', closeSidebar);
}

/* ── Auto-dismiss alerts ── */
function initAlerts() {
  document.querySelectorAll('.alert').forEach(function(el) {
    const closeBtn = el.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function() { el.remove(); });
    }
    setTimeout(function() {
      el.style.transition = 'opacity .4s ease';
      el.style.opacity = '0';
      setTimeout(function() { el.remove(); }, 420);
    }, 4000);
  });
}

/* ── Charts ── */
function initCharts() {
  const chartSection = document.getElementById('chartsSection');
  if (!chartSection) return;

  // Check if Chart.js is loaded
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js not loaded');
    return;
  }

  const isDark = document.documentElement.getAttribute('data-theme') !== 'light';

  Chart.defaults.color = isDark ? '#8b949e' : '#57606a';
  Chart.defaults.borderColor = isDark ? '#30363d' : '#d0d7de';
  Chart.defaults.font.family = "'Inter', sans-serif";

  fetch('/api/charts/')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      // 1. Category doughnut
      const catCtx = document.getElementById('catChart');
      if (catCtx && data.category && data.category.labels.length > 0) {
        new Chart(catCtx, {
          type: 'doughnut',
          data: {
            labels: data.category.labels,
            datasets: [{
              data: data.category.data,
              backgroundColor: data.category.colors,
              borderWidth: 2,
              borderColor: isDark ? '#1c2333' : '#ffffff',
              hoverOffset: 8,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
              legend: { position: 'right', labels: { padding: 16, font: { size: 12 } } },
              tooltip: {
                callbacks: {
                  label: function(ctx) {
                    return ' ₹' + parseFloat(ctx.raw).toLocaleString('en-IN', { minimumFractionDigits: 2 });
                  }
                }
              }
            }
          }
        });
      } else if (catCtx) {
        catCtx.parentElement.innerHTML = '<p class="text-muted text-center" style="padding:40px">No expenses this month</p>';
      }

      // 2. Monthly bar chart
      const monthCtx = document.getElementById('monthChart');
      if (monthCtx) {
        new Chart(monthCtx, {
          type: 'bar',
          data: {
            labels: data.monthly.labels,
            datasets: [{
              label: 'Monthly Spending',
              data: data.monthly.data,
              backgroundColor: 'rgba(88,166,255,.25)',
              borderColor: '#58a6ff',
              borderWidth: 2,
              borderRadius: 6,
              borderSkipped: false,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  callback: function(v) { return '₹' + v.toLocaleString('en-IN'); }
                }
              }
            }
          }
        });
      }

      // 3. Daily line chart
      const dailyCtx = document.getElementById('dailyChart');
      if (dailyCtx) {
        new Chart(dailyCtx, {
          type: 'line',
          data: {
            labels: data.daily.labels,
            datasets: [{
              label: 'Daily Spending',
              data: data.daily.data,
              borderColor: '#3fb950',
              backgroundColor: 'rgba(63,185,80,.1)',
              borderWidth: 2.5,
              tension: 0.4,
              fill: true,
              pointBackgroundColor: '#3fb950',
              pointRadius: 4,
              pointHoverRadius: 6,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  callback: function(v) { return '₹' + v.toLocaleString('en-IN'); }
                }
              }
            }
          }
        });
      }
    })
    .catch(function(err) { console.error('Charts error:', err); });
}

/* ── Budget ring ── */
function initBudgetRing() {
  const ring = document.getElementById('budgetRing');
  if (!ring) return;
  const pct = parseFloat(ring.dataset.pct) || 0;
  const r = 70;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (Math.min(pct, 100) / 100) * circumference;
  const circle = document.getElementById('budgetRingCircle');
  if (circle) {
    circle.style.strokeDasharray = circumference;
    circle.style.strokeDashoffset = circumference; // start at 0
    setTimeout(function() {
      circle.style.transition = 'stroke-dashoffset 1s cubic-bezier(.34,1.56,.64,1)';
      circle.style.strokeDashoffset = offset;
    }, 200);
    // color
    const color = pct >= 100 ? '#f85149' : pct >= 80 ? '#f0a500' : '#58a6ff';
    circle.style.stroke = color;
    const ringPct = document.getElementById('budgetRingPct');
    if (ringPct) ringPct.style.color = color;
  }
}

/* ── Animated counter ── */
function animateCounters() {
  document.querySelectorAll('[data-counter]').forEach(function(el) {
    const target = parseFloat(el.dataset.counter) || 0;
    const duration = 900;
    const start = performance.now();
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';

    function step(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const value = target * ease;
      el.textContent = prefix + value.toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
}

/* ── Confirm delete ── (handled by the server-side confirmation page) */

/* ── Date shortcuts ── */
function initDateShortcuts() {
  document.querySelectorAll('[data-date-preset]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      const preset = btn.dataset.datePreset;
      const target = document.getElementById(btn.dataset.target);
      if (!target) return;
      const today = new Date();
      if (preset === 'today') {
        target.value = today.toISOString().split('T')[0];
      } else if (preset === 'yesterday') {
        today.setDate(today.getDate() - 1);
        target.value = today.toISOString().split('T')[0];
      }
    });
  });
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', function() {
  initTheme();
  initSidebar();
  initAlerts();
  initBudgetRing();
  animateCounters();
  initDateShortcuts();
  initCharts();

  // Expose toggle globally
  const themeBtn = document.getElementById('themeToggle');
  if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
});
