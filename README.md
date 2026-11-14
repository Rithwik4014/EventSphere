# EventSphere – Universal Event Management & Discovery Platform

EventSphere is a full-stack, responsive event discovery, booking, and administrative management web platform. Powered by Python Flask, Bootstrap 5, vanilla JavaScript, and MongoDB Atlas via the native PyMongo driver, EventSphere features multi-document ACID transactions, full-text search, live analytics dashboards, digital tickets with QR verification, and a secure authentication workflow.

---

## Key Features

- **Universal Event Discovery:** Explore events across 10 diverse categories (Technology & Innovation, Education & Learning, Music & Entertainment, Arts & Creativity, Sports & Fitness, Business & Entrepreneurship, Health & Wellness, Food & Lifestyle, Travel & Adventure, Social & Community).
- **Transactional Seat Reservations:** Multi-document ACID transactions via PyMongo client sessions guarantee zero overselling and immediate seat restock upon reservation cancellation.
- **Real-Time Seat Availability:** Dynamic seat capacity meters and status badges.
- **Digital Tickets & Verification:** Unique alphanumeric booking codes (`EVT-2026-XXXX`) with printable passes and scannable QR verification.
- **Admin Management & Analytics:** Event lifecycle controls (create, edit, reschedule, cancel), attendee rosters, and interactive Chart.js analytics.
- **Security & RBAC:** Salted password hashing (Werkzeug PBKDF2/scrypt), strict role separation (`admin` vs. `user`), time-limited and single-use password reset tokens (SHA-256 hashed).

---

## Tech Stack

- **Backend:** Python 3.10+, Flask 3.0+
- **Database:** MongoDB Atlas via PyMongo (Native driver with `$jsonSchema` validation)
- **Frontend:** HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, Chart.js
- **Environment Management:** python-dotenv

---

## Getting Started

### 1. Clone the Repository & Configure Environment

```bash
git clone <repository-url>
cd EventSphere
```

Copy the example configuration file:
```bash
cp .env.example .env
```
Update `.env` with your MongoDB Atlas connection string (`MONGO_URI`) and Gmail SMTP credentials if email recovery is enabled.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Database & Seed Demo Accounts

```bash
python scripts/init_db.py
python scripts/seed_demo_accounts.py
```

### 4. Run the Application

```bash
python run.py
```
Open your browser and navigate to `http://127.0.0.1:5050`.

---

## Testing

Run the automated test suites:
```bash
python tests/test_frontend.py
python tests/test_security_rbac.py
python tests/test_auth_and_password_reset.py
python tests/test_event_reschedule.py
python tests/test_email_and_categories.py
```

---

## License

This project is licensed under the MIT License.
