# scripts/seed_30_events.py
"""
Seeds 30 realistic, diverse campus events across all 10 expanded categories.
Prevents duplicate event insertion by checking existing titles.
"""

import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.db import get_db
from app.services.user_service import UserService

SAMPLE_EVENTS = [
    # --- 1. ACADEMIC ---
    {
        "title": "National Symposium on Quantum Computing & Cryptography",
        "description": "Explore theoretical foundations and real-world post-quantum cryptography algorithms with leading researchers from national science labs.",
        "category": "Academic",
        "tags": ["Quantum", "Physics", "Cryptography", "Research", "Computing"],
        "venue": {"type": "in-person", "name": "Sir C.V. Raman Physics Auditorium", "address_or_link": "Science Block, Floor 2", "city": "Bengaluru"},
        "days_from_now": 5,
        "duration_hours": 6.0,
        "total_capacity": 150,
        "price": 200.0
    },
    {
        "title": "Undergraduate Research Colloquium: Frontiers in Biotech",
        "description": "Poster sessions, oral presentations, and keynote addresses showcasing novel undergraduate gene therapy and biofuel breakthroughs.",
        "category": "Academic",
        "tags": ["Biotechnology", "Genetics", "Research", "Colloquium"],
        "venue": {"type": "hybrid", "name": "Bio-Sciences Seminar Hall & Zoom", "address_or_link": "Life Sciences Wing B", "city": "Bengaluru"},
        "days_from_now": 9,
        "duration_hours": 5.0,
        "total_capacity": 120,
        "price": 0.0
    },
    {
        "title": "International Conference on Sustainable Urban Architecture",
        "description": "Examining net-zero campus design, biophilic structural engineering, and renewable energy integration in smart university cities.",
        "category": "Academic",
        "tags": ["Architecture", "Sustainability", "Urban Planning", "Green Energy"],
        "venue": {"type": "in-person", "name": "Design & Architecture Gallery", "address_or_link": "Block 7, Innovation Campus", "city": "Bengaluru"},
        "days_from_now": 14,
        "duration_hours": 7.0,
        "total_capacity": 100,
        "price": 250.0
    },

    # --- 2. TECHNOLOGY ---
    {
        "title": "Cloud Native & Kubernetes Hands-On Hackathon",
        "description": "Deploy, scale, and optimize microservices architectures on live cloud infrastructure with cluster observability and service meshes.",
        "category": "Technology",
        "tags": ["Kubernetes", "DevOps", "Cloud", "Hackathon", "Docker"],
        "venue": {"type": "in-person", "name": "Advanced Computing Laboratory 4", "address_or_link": "Tech Park Floor 3", "city": "Bengaluru"},
        "days_from_now": 6,
        "duration_hours": 12.0,
        "total_capacity": 80,
        "price": 150.0
    },
    {
        "title": "Open Source DevOps & CI/CD Pipeline Intensive",
        "description": "Build automated GitHub Actions workflows, containerized security scanning, and infrastructure-as-code deployments using Terraform.",
        "category": "Technology",
        "tags": ["DevOps", "GitHub", "Terraform", "Automation", "CI/CD"],
        "venue": {"type": "online", "name": "Google Meet Virtual Lab", "address_or_link": "https://meet.google.com/evt-devops", "city": "Bengaluru"},
        "days_from_now": 11,
        "duration_hours": 3.5,
        "total_capacity": 200,
        "price": 0.0
    },
    {
        "title": "Generative AI & LLM Autonomous Agent Bootcamp",
        "description": "Learn LangChain, Retrieval-Augmented Generation (RAG) with vector databases, and multi-agent coordination frameworks from scratch.",
        "category": "Technology",
        "tags": ["AI", "GenAI", "LLM", "Python", "Machine Learning"],
        "venue": {"type": "in-person", "name": "APJ Abdul Kalam Auditorium", "address_or_link": "Main Administrative Block", "city": "Bengaluru"},
        "days_from_now": 16,
        "duration_hours": 8.0,
        "total_capacity": 250,
        "price": 300.0
    },

    # --- 3. CULTURAL ---
    {
        "title": "Heritage Folk Dance & Fusion Music Extravaganza",
        "description": "An electrifying celebration of diverse regional folk traditions, classical Indian ensembles, and contemporary fusion choreographies.",
        "category": "Cultural",
        "tags": ["Dance", "Culture", "Folk", "Tradition", "Heritage"],
        "venue": {"type": "in-person", "name": "Open Air Amphitheatre", "address_or_link": "Central Campus Lawn", "city": "Bengaluru"},
        "days_from_now": 7,
        "duration_hours": 4.0,
        "total_capacity": 400,
        "price": 50.0
    },
    {
        "title": "Sanskritik Sandhya: Classical Sitar & Tabla Jugalbandi",
        "description": "An evening of mesmerizing North and South Indian classical ragas performed by celebrated maestro faculty and visiting virtuosos.",
        "category": "Cultural",
        "tags": ["Classical", "Music", "Sitar", "Tabla", "Raga"],
        "venue": {"type": "in-person", "name": "Vivekananda Cultural Hall", "address_or_link": "Arts Complex, Wing A", "city": "Bengaluru"},
        "days_from_now": 13,
        "duration_hours": 3.0,
        "total_capacity": 180,
        "price": 100.0
    },
    {
        "title": "International Food & Cultural Diversity Carnival",
        "description": "Taste authentic delicacies from over fifteen global cuisines, enjoy traditional attire parades, and experience world folk arts.",
        "category": "Cultural",
        "tags": ["Food", "International", "Carnival", "Festival"],
        "venue": {"type": "in-person", "name": "University Quadrangle Courtyard", "address_or_link": "Campus Pavilion", "city": "Bengaluru"},
        "days_from_now": 20,
        "duration_hours": 6.0,
        "total_capacity": 500,
        "price": 0.0
    },

    # --- 4. MUSIC & ENTERTAINMENT ---
    {
        "title": "Starlight Acoustic & Indie Rock Jam Session",
        "description": "Under-the-stars live performance featuring student indie bands, acoustic songwriters, and beatboxing battles with bonfire vibes.",
        "category": "Music & Entertainment",
        "tags": ["Live Music", "Indie Rock", "Acoustic", "Bands", "Concert"],
        "venue": {"type": "in-person", "name": "Pine Grove Amphitheatre", "address_or_link": "West Campus Green", "city": "Bengaluru"},
        "days_from_now": 4,
        "duration_hours": 4.5,
        "total_capacity": 300,
        "price": 100.0
    },
    {
        "title": "Electronic Beats & DJ Showcase Night",
        "description": "High-energy EDM, synth-wave, and house music sets produced by student electronic producers featuring laser lighting setups.",
        "category": "Music & Entertainment",
        "tags": ["EDM", "DJ", "Electronic", "Party", "Nightlife"],
        "venue": {"type": "in-person", "name": "Student Activities Multi-Purpose Hall", "address_or_link": "Student Center Level 1", "city": "Bengaluru"},
        "days_from_now": 12,
        "duration_hours": 5.0,
        "total_capacity": 350,
        "price": 150.0
    },
    {
        "title": "Campus Stand-Up Comedy Evening: Unfiltered Laughs",
        "description": "An unfiltered evening of observational comedy, crowd-work roasts, and relatable college humor featuring top collegiate comedians.",
        "category": "Music & Entertainment",
        "tags": ["Comedy", "StandUp", "Humor", "Entertainment"],
        "venue": {"type": "in-person", "name": "Black Box Theater", "address_or_link": "Performing Arts Block", "city": "Bengaluru"},
        "days_from_now": 18,
        "duration_hours": 2.5,
        "total_capacity": 150,
        "price": 120.0
    },

    # --- 5. SPORTS ---
    {
        "title": "Annual Inter-University 5K Sunrise Marathon",
        "description": "Lace up your running shoes for the annual campus 5K run. Timed chip bibs, hydration stations, finisher medals, and breakfast provided.",
        "category": "Sports",
        "tags": ["Marathon", "Running", "Fitness", "5K", "Athletics"],
        "venue": {"type": "in-person", "name": "Olympic Athletic Stadium Track", "address_or_link": "Sports Village Gate 4", "city": "Bengaluru"},
        "days_from_now": 8,
        "duration_hours": 3.0,
        "total_capacity": 500,
        "price": 100.0
    },
    {
        "title": "3-on-3 Street Basketball Slam Tournament",
        "description": "Fast-paced half-court basketball tournament following FIBA 3x3 rules. Trophies, cash prize pool, and 3-point contest included.",
        "category": "Sports",
        "tags": ["Basketball", "Tournament", "Hoops", "Sports"],
        "venue": {"type": "in-person", "name": "Floodlit Outdoor Basketball Courts", "address_or_link": "Sports Complex Court 2", "city": "Bengaluru"},
        "days_from_now": 15,
        "duration_hours": 6.0,
        "total_capacity": 120,
        "price": 150.0
    },
    {
        "title": "Badminton Smash Open Championship 2026",
        "description": "Singles and doubles knockout tournament on BWF standard synthetic courts with certified umpires and live scoreboards.",
        "category": "Sports",
        "tags": ["Badminton", "Smash", "Racket", "Tournament"],
        "venue": {"type": "in-person", "name": "Indoor Badminton Arena", "address_or_link": "Gymkhana Hall 1", "city": "Bengaluru"},
        "days_from_now": 22,
        "duration_hours": 8.0,
        "total_capacity": 64,
        "price": 80.0
    },

    # --- 6. ARTS & CREATIVITY ---
    {
        "title": "Contemporary Canvas Painting & Live Pottery Studio",
        "description": "Hands-on creative sanctuary with canvas acrylic painting, potter's wheel throwing, clay glazing, and student art exhibition.",
        "category": "Arts & Creativity",
        "tags": ["Painting", "Pottery", "Art", "Canvas", "Creativity"],
        "venue": {"type": "in-person", "name": "Fine Arts Atelier Studio", "address_or_link": "Visual Arts Annex", "city": "Bengaluru"},
        "days_from_now": 6,
        "duration_hours": 4.0,
        "total_capacity": 40,
        "price": 200.0
    },
    {
        "title": "Urban Street Photography & Darkroom Workshop",
        "description": "Master aperture, shutter dynamics, framing golden-hour portraits, and analog 35mm film development in a working darkroom.",
        "category": "Arts & Creativity",
        "tags": ["Photography", "Camera", "Darkroom", "Art", "Visual"],
        "venue": {"type": "in-person", "name": "Media Center Darkroom & Studio", "address_or_link": "Journalism Building", "city": "Bengaluru"},
        "days_from_now": 14,
        "duration_hours": 5.0,
        "total_capacity": 35,
        "price": 180.0
    },
    {
        "title": "Creative Writing & Spoken Word Poetry Slam",
        "description": "An intimate stage for poets, storytellers, and novelists to share raw prose, rhythm verse, and receive mentorship from published authors.",
        "category": "Arts & Creativity",
        "tags": ["Poetry", "Writing", "Literature", "Spoken Word"],
        "venue": {"type": "in-person", "name": "Old Library Reading Room", "address_or_link": "Central Library Floor 1", "city": "Bengaluru"},
        "days_from_now": 19,
        "duration_hours": 3.0,
        "total_capacity": 75,
        "price": 0.0
    },

    # --- 7. GAMING ---
    {
        "title": "Valorant & CS:GO Campus Esports Tournament",
        "description": "5v5 tactical shooter showdown on 240Hz tournament rigs with live shoutcasting, Twitch stream broadcast, and custom trophies.",
        "category": "Gaming",
        "tags": ["Esports", "Valorant", "CSGO", "PC Gaming", "Tournament"],
        "venue": {"type": "in-person", "name": "Alienware Gaming & Esports Arena", "address_or_link": "Tech Block Ground Floor", "city": "Bengaluru"},
        "days_from_now": 7,
        "duration_hours": 8.0,
        "total_capacity": 80,
        "price": 100.0
    },
    {
        "title": "Retro Arcade & Super Smash Bros Brawl Night",
        "description": "CRT televisions, GameCubes, arcade cabinets, and double-elimination Smash Ultimate bracket with pizza and refreshments.",
        "category": "Gaming",
        "tags": ["SmashBros", "Nintendo", "Retro", "Arcade", "Gaming"],
        "venue": {"type": "in-person", "name": "Student Lounge Recreation Center", "address_or_link": "Student Union Hall", "city": "Bengaluru"},
        "days_from_now": 10,
        "duration_hours": 4.0,
        "total_capacity": 90,
        "price": 50.0
    },
    {
        "title": "Indie Game Dev Showcase & Playtesting Arena",
        "description": "Play unreleased student-built games developed in Unity, Unreal Engine 5, and Godot. Vote for audience choice awards.",
        "category": "Gaming",
        "tags": ["GameDev", "Unity", "UnrealEngine", "IndieGames"],
        "venue": {"type": "hybrid", "name": "Interactive Media Hall & Discord", "address_or_link": "Animation Wing Room 3", "city": "Bengaluru"},
        "days_from_now": 25,
        "duration_hours": 4.0,
        "total_capacity": 150,
        "price": 0.0
    },

    # --- 8. BUSINESS & ENTREPRENEURSHIP ---
    {
        "title": "Campus Shark Tank: Student Startup Pitch Fest",
        "description": "Watch ten vetted student founder teams pitch innovative software and hardware ventures to angel investors and industry VCs.",
        "category": "Business & Entrepreneurship",
        "tags": ["Startup", "Pitch", "VentureCapital", "Entrepreneurship"],
        "venue": {"type": "in-person", "name": "Executive MBA Boardroom", "address_or_link": "School of Management Floor 4", "city": "Bengaluru"},
        "days_from_now": 10,
        "duration_hours": 5.0,
        "total_capacity": 120,
        "price": 100.0
    },
    {
        "title": "Venture Capital & Seed Funding Masterclass",
        "description": "Demystifying term sheets, founder equity vesting, convertible SAFE notes, and scaling to product-market fit.",
        "category": "Business & Entrepreneurship",
        "tags": ["VentureCapital", "Finance", "SeedFunding", "Startups"],
        "venue": {"type": "online", "name": "Virtual Webinar Room 1", "address_or_link": "https://meet.google.com/evt-vc-masterclass", "city": "Bengaluru"},
        "days_from_now": 17,
        "duration_hours": 2.5,
        "total_capacity": 300,
        "price": 0.0
    },
    {
        "title": "Personal Finance & Algorithmic Stock Trading Seminar",
        "description": "Learn disciplined investing fundamentals, index funds, mutual fund portfolio construction, and automated Python trading bots.",
        "category": "Business & Entrepreneurship",
        "tags": ["Investing", "StockMarket", "Finance", "Python", "Trading"],
        "venue": {"type": "in-person", "name": "Finance Lab & Bloomberg Terminal Room", "address_or_link": "Commerce Block Room 12", "city": "Bengaluru"},
        "days_from_now": 21,
        "duration_hours": 3.0,
        "total_capacity": 60,
        "price": 75.0
    },

    # --- 9. WELLNESS ---
    {
        "title": "Mindful Morning Yoga & Sound Bath Healing",
        "description": "Gentle hatha yoga flow, pranayama breathwork, and Tibetan singing bowl sound meditation on the scenic sunrise lawn.",
        "category": "Wellness",
        "tags": ["Yoga", "Meditation", "Mindfulness", "Wellness", "Health"],
        "venue": {"type": "in-person", "name": "Sunrise Botanical Garden Lawn", "address_or_link": "Eco Garden Section 3", "city": "Bengaluru"},
        "days_from_now": 3,
        "duration_hours": 2.0,
        "total_capacity": 50,
        "price": 0.0
    },
    {
        "title": "Mental Resilience & Stress Management Workshop",
        "description": "Clinical psychologists share evidence-based cognitive strategies for managing exam anxiety, perfectionism, and student burnout.",
        "category": "Wellness",
        "tags": ["MentalHealth", "Resilience", "StressRelief", "Psychology"],
        "venue": {"type": "in-person", "name": "Counseling & Wellness Sanctuary", "address_or_link": "Health Center Floor 2", "city": "Bengaluru"},
        "days_from_now": 11,
        "duration_hours": 2.5,
        "total_capacity": 60,
        "price": 0.0
    },
    {
        "title": "Holistic Nutrition & Plant-Based Culinary Masterclass",
        "description": "Interactive cooking workshop demonstrating wholesome, budget-friendly high-protein student meal preps with nutritionist insights.",
        "category": "Wellness",
        "tags": ["Nutrition", "Cooking", "HealthyEating", "PlantBased"],
        "venue": {"type": "in-person", "name": "Hospitality & Culinary Demonstration Kitchen", "address_or_link": "Culinary Arts Block", "city": "Bengaluru"},
        "days_from_now": 23,
        "duration_hours": 3.0,
        "total_capacity": 30,
        "price": 120.0
    },

    # --- 10. SOCIAL & COMMUNITY ---
    {
        "title": "Clean Campus Green Earth: Lake Restoration Drive",
        "description": "Community volunteer initiative to clean nearby water bodies, plant native saplings, and install solar-powered trash bins.",
        "category": "Social & Community",
        "tags": ["Environment", "Volunteering", "Eco", "Community", "Service"],
        "venue": {"type": "in-person", "name": "Campus Eco-Lake North Shore", "address_or_link": "Eco-Park Entrance", "city": "Bengaluru"},
        "days_from_now": 5,
        "duration_hours": 4.0,
        "total_capacity": 150,
        "price": 0.0
    },
    {
        "title": "Red Cross Blood Donation & Health Checkup Community Camp",
        "description": "Partnering with the Red Cross to host our semi-annual blood donation drive with complimentary vitals and hemoglobin testing.",
        "category": "Social & Community",
        "tags": ["BloodDonation", "Health", "RedCross", "Charity", "Community"],
        "venue": {"type": "in-person", "name": "University Main Gymnasium", "address_or_link": "Central Campus Gym", "city": "Bengaluru"},
        "days_from_now": 12,
        "duration_hours": 6.0,
        "total_capacity": 250,
        "price": 0.0
    },
    {
        "title": "Tech for Good: Coding Mentorship for Local Schools",
        "description": "Volunteer as a coding mentor to teach foundational Scratch, robotics, and basic Python to visiting middle school students.",
        "category": "Social & Community",
        "tags": ["Mentorship", "Education", "Coding", "SocialImpact", "Volunteering"],
        "venue": {"type": "in-person", "name": "Community Outreach Center", "address_or_link": "Block 1 Room 104", "city": "Bengaluru"},
        "days_from_now": 18,
        "duration_hours": 4.0,
        "total_capacity": 45,
        "price": 0.0
    }
]

def seed_sample_events():
    db = get_db()
    print("Checking sample events seeding in MongoDB Atlas...")

    admin_user = UserService.get_user_by_email("admin@edusphere.in") or UserService.get_user_by_email("admin@college.edu")
    if not admin_user:
        admin_user = db.users.find_one({"role": "admin"})

    if not admin_user:
        print("[ERROR] No admin user found in database. Please seed demo accounts first.")
        return

    admin_id = admin_user["_id"]
    now = datetime.utcnow()

    inserted_count = 0
    existing_count = 0

    for item in SAMPLE_EVENTS:
        existing = db.events.find_one({"title": item["title"]})
        if existing:
            existing_count += 1
            continue

        event_date = now + timedelta(days=item["days_from_now"])
        # Format time nicely: 10:00 AM
        event_date = event_date.replace(hour=10, minute=0, second=0, microsecond=0)

        event_doc = {
            "title": item["title"],
            "description": item["description"],
            "category": item["category"],
            "tags": item["tags"],
            "organizer_id": admin_id,
            "organizer_name": "EventSphere Campus Events Board",
            "venue": item["venue"],
            "event_date": event_date,
            "duration_hours": float(item["duration_hours"]),
            "total_capacity": int(item["total_capacity"]),
            "remaining_capacity": int(item["total_capacity"]),
            "price": float(item["price"]),
            "status": "published",
            "image_url": "",
            "created_at": now,
            "updated_at": now
        }

        db.events.insert_one(event_doc)
        inserted_count += 1

    print(f"\n[DONE] Seeding complete:")
    print(f"       New events inserted: {inserted_count}")
    print(f"       Existing events kept: {existing_count}")
    print(f"       Total events in DB: {db.events.count_documents({})}")

if __name__ == "__main__":
    seed_sample_events()
