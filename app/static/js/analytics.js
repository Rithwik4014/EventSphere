// app/static/js/analytics.js
// Handles Chart.js rendering for the EventSphere Admin Dashboard

let eventChart = null;
let categoryChart = null;
let trendChart = null;

async function loadAdminAnalytics() {
    try {
        // 1. Fetch Platform KPIs
        const kpiRes = await fetch('/api/admin/analytics/summary');
        const kpiData = await kpiRes.json();
        if (kpiData.success && kpiData.kpis) {
            document.getElementById('kpi-bookings').innerText = kpiData.kpis.total_confirmed_bookings || 0;
            document.getElementById('kpi-tickets').innerText = kpiData.kpis.total_tickets_sold || 0;
            document.getElementById('kpi-revenue').innerText = `₹${(kpiData.kpis.cumulative_revenue || 0).toLocaleString('en-IN')}`;
            document.getElementById('kpi-avg-order').innerText = `₹${(kpiData.kpis.avg_booking_value || 0).toLocaleString('en-IN')}`;
        }

        // 2. Fetch Event Performance (Top 5)
        const evRes = await fetch('/api/admin/analytics/events');
        const evData = await evRes.json();
        if (evData.success && evData.events) {
            renderEventPerformanceChart(evData.events.slice(0, 5));
        }

        // 3. Fetch Category Breakdown
        const catRes = await fetch('/api/admin/analytics/categories');
        const catData = await catRes.json();
        if (catData.success && catData.categories) {
            renderCategoryChart(catData.categories);
        }

        // 4. Fetch Monthly Trends
        const monthRes = await fetch('/api/admin/analytics/monthly');
        const monthData = await monthRes.json();
        if (monthData.success && monthData.monthly_trends) {
            renderMonthlyTrendChart(monthData.monthly_trends);
        }

    } catch (err) {
        console.error('Failed to load admin analytics:', err);
        showAlert('Could not load analytics data.', 'danger');
    }
}

function renderEventPerformanceChart(events) {
    const ctx = document.getElementById('chart-events');
    if (!ctx) return;

    const labels = events.map(e => e.title.length > 20 ? e.title.substring(0, 18) + '...' : e.title);
    const tickets = events.map(e => e.total_tickets_sold);
    const revenues = events.map(e => e.total_revenue);

    if (eventChart) eventChart.destroy();

    eventChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Tickets Sold',
                    data: tickets,
                    backgroundColor: '#2563eb',
                    borderRadius: 6
                },
                {
                    label: 'Revenue (₹)',
                    data: revenues,
                    backgroundColor: '#10b981',
                    borderRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: { mode: 'index', intersect: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function renderCategoryChart(categories) {
    const ctx = document.getElementById('chart-categories');
    if (!ctx) return;

    const labels = categories.map(c => c.category);
    const counts = categories.map(c => c.total_events);
    const colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#64748b'];

    if (categoryChart) categoryChart.destroy();

    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: colors.slice(0, labels.length),
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function renderMonthlyTrendChart(trends) {
    const ctx = document.getElementById('chart-trends');
    if (!ctx) return;

    const labels = trends.map(t => t.month);
    const revenue = trends.map(t => t.total_revenue);
    const tickets = trends.map(t => t.total_tickets_sold);

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Monthly Revenue (₹)',
                    data: revenue,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Tickets Sold',
                    data: tickets,
                    borderColor: '#2563eb',
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                x: { grid: { display: false } }
            }
        }
    });
}
