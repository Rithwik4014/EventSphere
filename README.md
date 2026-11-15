# EventSphere

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20%7C%20PyMongo-47A248?style=flat&logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6%2B-F7DF1E?style=flat&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384?style=flat&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)

EventSphere is a full-stack, universal event discovery, booking, and administrative management platform. Designed to support diverse audiences, EventSphere enables attendees to discover and reserve passes for conferences, concerts, workshops, sports tournaments, and community gatherings, while providing organizers and administrators with tools to manage event lifecycles, seat capacities, bookings, and live analytics.

The application is built on **Python Flask** and connected directly to **MongoDB Atlas** using the official **PyMongo** driver without intermediate ORM layers, utilizing native BSON handling, `$jsonSchema` collection validators, and multi-document ACID transactions.

---

## Implemented Features

### Universal Event Discovery & Catalog
- **Diverse Event Categories:** Supports 10 distinct categories:
  - *Technology & Innovation*
  - *Education & Learning*
  - *Music & Entertainment*
  - *Arts & Creativity*
  - *Sports & Fitness*
  - *Business & Entrepreneurship*
  - *Health & Wellness*
  - *Food & Lifestyle*
  - *Travel & Adventure*
  - *Social & Community*
- **Full-Text Search:** Query events across title, description, and tags via MongoDB text indexes.
- **Dynamic Category Filtering:** Filter events by category with URL query parameters and responsive filter buttons.
- **Thematic Visuals:** Thematic banner imagery matching event categories with automatic fallback handling.

### Seat Reservation & Capacity Management
- **Transactional Bookings:** Bookings are processed inside a PyMongo Client Session (`client.start_session()` / `session.start_transaction()`).
- **Atomic Capacity Decrements:** Seat availability is validated and decremented atomically (`$inc: { remaining_capacity: -count }`), preventing over-allocation.
- **Atomic Cancellation Restock:** Attendees can cancel reservations, which atomically marks the booking as cancelled and returns reserved seats back to the event's available capacity.
- **Reservation Limits:** Allows booking between 1 and 5 tickets per transaction with attendee contact details.

### Digital Ticket Passes & Dynamic QR Verification
- **Unique Booking Codes:** Every confirmed reservation generates an alphanumeric code (`EVT-2026-XXXXXX`).
- **Dynamic QR Code Generation:** Generated dynamically using the Python `qrcode` library with Pillow (`box_size=8`, `border=2`), producing a crisp, camera-scannable PNG image.
- **Embedded Verification Payload:** Encodes `booking_code|user_id|event_id` into the QR code image, associating the booking, attendee, and event.
- **Gate Verification & Check-in API:** Dedicated endpoints (`POST /api/bookings/verify` and `POST /api/bookings/check-in`) validate the decoded payload directly against MongoDB Atlas, confirming existence, code match, user/event match, and confirmed status while rejecting cancelled or tampered tickets and preventing duplicate check-in admissions.
- **Admin Gate Verification Interface:** Dedicated admin verification portal (`/admin/verify`) and digital ticket gate controls allowing administrators to inspect passes, execute check-in, and display instant green confirmation receipts.
- **Printable Ticket Pass:** A dedicated ticket view (`/ticket/<booking_id>`) displaying the genuine scannable QR code alongside attendee details, status badge, and print-ready stylesheet.

### Admin Management & Operations
- **Role-Based Access Control (RBAC):** Strict separation between regular users and authenticated administrators.
- **Event Lifecycle Controls:** Admins can publish new events, update details (title, description, price, venue), cancel events, and reschedule timings.
- **Reschedule with Audit Tracking:** Changing event dates validates that the new time is in the future, updates the document in-place, and preserves original date records for audit purposes.
- **Attendee Roster:** Admins can inspect booking history and confirmed attendees per event.

### Interactive Analytics Dashboard
- **Aggregation Pipelines:** Five multi-stage MongoDB aggregation pipelines calculate platform metrics in real time:
  - Overall platform KPIs (total events, published events, total bookings, confirmed seats, revenue, registered users)
  - Turnout and capacity utilization rates
  - Category popularity and booking share
  - Monthly reservation and revenue trends
  - Top performing events
- **Visual Charts:** Interactive charts rendered with Chart.js (donut, bar, line charts).

### Authentication & Access Control
- **Password Security:** Salted password hashing with Werkzeug (`scrypt`/PBKDF2). Passwords are never stored in plaintext.
- **Public Registration Isolation:** Public sign-up strictly assigns the `user` role regardless of incoming payload data.
- **Session Authentication:** Standard HTTP session authentication with secure cookies and role-based access control (RBAC).
- **Simplified UI Workflow:** Forgot Password functionality is not exposed in the current application UI, and Gmail SMTP configuration is not required for platform evaluation or operation.

---

## Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+, Flask 3.0+ | Application factory, modular Blueprints, session authentication |
| **Database** | MongoDB Atlas, PyMongo 4.6+ | Native driver, multi-document transactions, `$jsonSchema` validators |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+) | Vanilla client scripts, fetch API, responsive glassmorphism UI |
| **UI Framework** | Bootstrap 5.3, Bootstrap Icons | Responsive grid, modal dialogs, utility components |
| **Data Visualization** | Chart.js 4.4 | Admin analytics charts and KPI visualizers |
| **Configuration** | python-dotenv | Environment variable management via `.env` |

---

## Project Structure

```text
EventSphere/
├── app/
│   ├── __init__.py                # Flask application factory & JSON providers
│   ├── config.py                  # Environment configurations (Dev, Test, Prod)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # MongoDB $jsonSchema validators for collections
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── admin_routes.py        # Admin management & aggregation analytics API
│   │   ├── auth_helpers.py        # RBAC decorators & password hashing
│   │   ├── auth_routes.py         # Login, register, profile, and password reset API
│   │   ├── booking_routes.py      # Booking creation & cancellation endpoints
│   │   ├── event_routes.py        # Event CRUD, text search & category filter API
│   │   └── web_routes.py          # HTML page view routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analytics_service.py   # Aggregation pipelines for live dashboards
│   │   ├── booking_service.py     # Transactional reservations & ticket generation
│   │   ├── db.py                  # PyMongo client singleton & connection utilities
│   │   ├── event_service.py       # Event CRUD, capacity checks & rescheduling
│   │   └── user_service.py        # User CRUD & secure reset token management
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css          # Custom styling, hero mosaic, and ticket styles
│   │   └── js/
│   │       ├── analytics.js       # Chart.js dashboard integration
│   │       ├── main.js            # Shared UI toasts, auth helpers & image fallbacks
│   │       └── search.js          # Catalog search and filter event handlers
│   └── templates/
│       ├── base.html              # Base HTML layout with responsive navbar & footer
│       ├── admin/
│       │   ├── dashboard.html     # Analytics and visual KPI charts
│       │   ├── event_manage.html  # Admin event management, edit & reschedule
│       │   └── verify_ticket.html # Admin ticket verification & gate check-in
│       ├── auth/
│       │   ├── forgot_password.html # Password recovery request page
│       │   ├── login.html         # User sign-in page with quick-fill
│       │   ├── profile.html       # Account profile view
│       │   ├── register.html      # User registration form
│       │   └── reset_password.html  # Secure password reset form
│       ├── bookings/
│       │   ├── my_bookings.html   # Attendee reservation history & ticket links
│       │   └── ticket.html        # Digital ticket pass with verification payload
│       └── events/
│           ├── detail.html        # Event details, seat availability & booking modal
│           ├── form.html          # New event creation form
│           ├── index.html         # Homepage hero, category pills & featured events
│           └── list.html          # Searchable event catalog explorer
├── scripts/
│   ├── assign_event_images.py     # Assigns thematic image URLs to catalog events
│   ├── init_db.py                 # Initializes collections, schemas & indexes
│   ├── migrate_to_universal_platform.py # Universal platform migration script
│   ├── seed_30_events.py          # Seeds sample events across 10 categories
│   ├── seed_demo_accounts.py      # Seeds default admin and student demo accounts
│   └── update_events_schema.py    # Schema update utilities
├── tests/
│   ├── test_aggregations.py       # Tests for analytics aggregation pipelines
│   ├── test_api.py                # REST API endpoint integration tests
│   ├── test_auth_and_password_reset.py # Authentication & reset token verification
│   ├── test_crud.py               # Database CRUD unit tests
│   ├── test_email_and_categories.py # Category filtering & registration tests
│   ├── test_event_reschedule.py   # Admin reschedule, audit & RBAC tests
│   ├── test_frontend.py           # HTML template & static asset route tests
│   ├── test_security_rbac.py      # Privilege escalation prevention tests
│   ├── test_production_credential_safeguards.py # Production credential safeguards
│   └── test_ticket_qr_and_verification.py # Genuine QR code & gate check-in tests
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules for secrets, caches & logs
├── PROJECT_ARCHITECTURE.md        # Technical architecture specification
├── README.md                      # Project documentation
├── requirements.txt               # Python package dependencies
├── run.py                         # Application entry point
└── test_connection.py             # MongoDB connection verification utility
```

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Git
- Access to a MongoDB Atlas cluster (or local MongoDB 6.0+)

### 1. Clone the Repository
```bash
git clone https://github.com/Rithwik4014/EventSphere.git
cd EventSphere
```

### 2. Configure Environment Variables
Copy the template configuration file to `.env`:
```bash
cp .env.example .env
```

Open `.env` and supply your MongoDB Atlas connection details:
```ini
# Flask Configuration
FLASK_ENV=development
PORT=5050
SECRET_KEY=your-custom-secret-key-here
BASE_URL=http://127.0.0.1:5050

# MongoDB Atlas Connection
MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/eventsphere_db?retryWrites=true&w=majority
DB_NAME=eventsphere_db
```

> [!IMPORTANT]
> The `.env` file contains sensitive credentials and is strictly excluded from version control via `.gitignore`. Never commit `.env` to a repository.

### 3. Create a Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 4. Initialize Database & Seed Accounts
Run the initialization scripts to apply schema validators, create indexes, and set up demo accounts:
```bash
# Initialize collections, $jsonSchema validators, and indexes
python scripts/init_db.py

# Seed demo accounts (admin and attendee)
python scripts/seed_demo_accounts.py

# Seed sample events across the 10 universal categories
python scripts/migrate_to_universal_platform.py
```

### 5. Start the Application
```bash
python run.py
```

The application will start locally:
- **Local URL:** `http://127.0.0.1:5050` (or `http://localhost:5050`)
- **Sign In:** `http://127.0.0.1:5050/login`
- **Catalog:** `http://127.0.0.1:5050/events`

---

## Local Evaluation & Sample User

To test the application with preconfigured roles without manually creating accounts:

1. **Seed Evaluation Accounts:**
   Run the seeding script to create or update local test accounts in MongoDB Atlas with salted password hashes:
   ```bash
   python scripts/seed_demo_accounts.py
   ```
2. **Sample User Credentials:**
   The seed script configures a standard attendee account for local evaluation:
   - **Role:** Attendee / User
   - **Email:** `user@edusphere.in`
   - **Password:** `user123`
3. **Login Page Quick Fill:**
   On the login page (`/login`), click the **Sample User** button in the Quick Fill section to automatically populate the evaluation credentials (`user@edusphere.in` / `user123`).
4. **New User Registration:**
   Alternatively, register a new attendee account at `/register`. All public sign-ups are assigned the `user` role by default.
5. **Administrator Access:**
   To access the administrative dashboard and event management controls, sign in with an account having the `admin` role (configured via `scripts/seed_demo_accounts.py` or by updating the user role in MongoDB Atlas). Administrator credentials are reserved for authorized operators and are not exposed in public interfaces.

---

## Running Automated Tests

EventSphere includes test suites covering frontend routes, CRUD operations, transactions, security, and analytics.

Run any test suite directly:

```bash
# Verify all HTML routes, templates, and static assets render with HTTP 200
python tests/test_frontend.py

# Verify RBAC, privilege escalation prevention, and role isolation
python tests/test_security_rbac.py

# Verify production credential safeguards and password preservation
python tests/test_production_credential_safeguards.py

# Verify login, quick-fill, rate limiting, and password reset token workflows
python tests/test_auth_and_password_reset.py

# Verify admin reschedule, audit history, and capacity preservation
python tests/test_event_reschedule.py

# Verify 10-category filtering, event publishing, and email providers
python tests/test_email_and_categories.py

# Verify genuine QR code generation, Pillow rendering, and gate verification
python tests/test_ticket_qr_and_verification.py

# Verify PyMongo multi-document ACID transactions and CRUD operations
python tests/test_crud.py

# Verify multi-stage aggregation pipelines and analytics metrics
python tests/test_aggregations.py

# Verify REST API endpoints and response payloads
python tests/test_api.py
```

---

## Screenshots

*(Screenshots can be added here)*

| View | Preview |
| :--- | :--- |
| **Homepage & Hero Section** | *`[Screenshot: Homepage with search, 10 categories, and event mosaic]`* |
| **Events Catalog Explorer** | *`[Screenshot: Catalog with text search and category filter pills]`* |
| **Event Details & Booking** | *`[Screenshot: Event detail banner, seat capacity meter, and booking modal]`* |
| **Digital Ticket Pass** | *`[Screenshot: Confirmed digital ticket pass with verification payload and print option]`* |
| **Admin Management** | *`[Screenshot: Admin event management table with Edit, Reschedule, and Cancel]`* |
| **Analytics Dashboard** | *`[Screenshot: Chart.js visualization of category share and revenue trends]`* |
