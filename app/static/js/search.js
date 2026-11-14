// app/static/js/search.js
// Handles catalog searching, category filtering, and dynamic rendering

let currentCategory = '';
let currentSearchTerm = '';
let searchDebounceTimeout = null;

async function loadEvents(category = '', search = '', sortBy = 'event_date') {
    const grid = document.getElementById('events-grid');
    const loadingSpinner = document.getElementById('loading-spinner');
    const noEventsMsg = document.getElementById('no-events-msg');

    if (loadingSpinner) loadingSpinner.style.display = 'block';
    if (noEventsMsg) noEventsMsg.style.display = 'none';
    if (grid) grid.innerHTML = '';

    try {
        let url = '';
        if (search) {
            url = `/api/events/search?q=${encodeURIComponent(search)}${category ? `&category=${encodeURIComponent(category)}` : ''}`;
        } else {
            url = `/api/events?sort_by=${sortBy}${category ? `&category=${encodeURIComponent(category)}` : ''}`;
        }

        const res = await fetch(url);
        const data = await res.json();

        if (loadingSpinner) loadingSpinner.style.display = 'none';

        if (!data.success || !data.events || data.events.length === 0) {
            if (noEventsMsg) noEventsMsg.style.display = 'block';
            return;
        }

        renderEventCards(data.events);
    } catch (err) {
        if (loadingSpinner) loadingSpinner.style.display = 'none';
        console.error('Failed to load events:', err);
        showAlert('Could not load events from server.', 'danger');
    }
}

function renderEventCards(events) {
    const grid = document.getElementById('events-grid');
    if (!grid) return;

    grid.innerHTML = events.map(event => {
        const remaining = event.remaining_capacity;
        const total = event.total_capacity;
        const isSoldOut = remaining <= 0;
        const priceDisplay = event.price === 0 ? 'FREE' : `₹${event.price}`;
        const imgUrl = event.image_url || getCategoryFallbackImage(event.category);

        return `
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="event-card">
                    <div class="event-card-img-wrapper">
                        <img src="${imgUrl}" class="event-card-img" alt="${escapeHtml(event.title)}" loading="lazy" onerror="handleImageError(this, '${escapeHtml(event.category)}')">
                        <div class="event-card-overlay"></div>
                        <span class="event-badge">${escapeHtml(event.category)}</span>
                        <span class="event-price-tag">${priceDisplay}</span>
                    </div>
                    <div class="p-4 d-flex flex-column flex-grow-1">
                        <div class="text-muted small mb-2">
                            <i class="bi bi-calendar3 me-1"></i>${formatDate(event.event_date)}
                        </div>
                        <h5 class="fw-bold text-dark mb-2">${escapeHtml(event.title)}</h5>
                        <p class="text-muted small flex-grow-1">${escapeHtml(event.description.substring(0, 110))}...</p>
                        
                        <div class="d-flex align-items-center text-muted small mb-3">
                            <i class="bi bi-geo-alt me-1 text-danger"></i>
                            <span>${escapeHtml(event.venue?.name || 'Main Hall')}, ${escapeHtml(event.venue?.city || 'Bengaluru')}</span>
                        </div>

                        <div class="mb-3">
                            <div class="d-flex justify-content-between small text-muted mb-1">
                                <span>Seats Available</span>
                                <span class="fw-bold ${remaining < 5 ? 'text-danger' : 'text-success'}">${remaining} / ${total}</span>
                            </div>
                            <div class="progress" style="height: 6px;">
                                <div class="progress-bar ${remaining < 5 ? 'bg-danger' : 'bg-primary'}" role="progressbar" 
                                     style="width: ${((total - remaining) / total) * 100}%"></div>
                            </div>
                        </div>

                        <a href="/events/${event._id}" class="btn ${isSoldOut ? 'btn-secondary disabled' : 'btn-primary'} w-100 rounded-pill">
                            ${isSoldOut ? 'Sold Out' : 'View Details & Book'}
                        </a>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function onSearchInput(val) {
    clearTimeout(searchDebounceTimeout);
    searchDebounceTimeout = setTimeout(() => {
        currentSearchTerm = val.trim();
        loadEvents(currentCategory, currentSearchTerm);
    }, 350);
}

function onCategorySelect(category) {
    currentCategory = category;
    document.querySelectorAll('.category-pill').forEach(btn => {
        if (btn.dataset.category === category) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    loadEvents(currentCategory, currentSearchTerm);
}
