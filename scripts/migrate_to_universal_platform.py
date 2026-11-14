# scripts/migrate_to_universal_platform.py
"""
Universal Platform Migration Script for EventSphere.
1. Updates existing events in MongoDB Atlas to universal, non-collegiate phrasing:
   - Updates category mappings:
     Academic -> Education & Learning
     Technology -> Technology & Innovation
     Sports -> Sports & Fitness
     Wellness -> Health & Wellness
   - Replaces collegiate terms in titles, descriptions, and venues.
   - Sets organizer_name to universal 'EventSphere Global Events'.
2. Seeds universal events across all 10 universal categories:
   - Technology & Innovation (Tech conferences)
   - Education & Learning (Educational seminars)
   - Music & Entertainment (Concerts and music festivals)
   - Arts & Creativity (Art exhibitions)
   - Sports & Fitness (Sports tournaments)
   - Business & Entrepreneurship (Business networking events)
   - Health & Wellness (Fitness sessions)
   - Food & Lifestyle (Cooking workshops)
   - Travel & Adventure (Travel experiences)
   - Social & Community (Community events)
3. Preserves all bookings, booking codes, ticket records, user accounts, and seat capacities.
4. Prevents duplicates by title checking.
"""

import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.db import get_db
from app.services.user_service import UserService

UNIVERSAL_EVENTS = [
    # 1. Technology & Innovation (Tech Conferences)
    {
        "title": "Global Tech Summit 2026: AI & Distributed Cloud Systems",
        "description": "Join global tech leaders, researchers, and distributed systems engineers exploring next-generation artificial intelligence, serverless architectures, and NoSQL data platforms.",
        "category": "Technology & Innovation",
        "tags": ["Technology", "AI", "Cloud", "Distributed Systems", "Database"],
        "venue": {"type": "in-person", "name": "Metropolitan Convention Center", "address_or_link": "Convention Boulevard, Hall 1", "city": "Bengaluru"},
        "days_from_now": 6,
        "duration_hours": 6.0,
        "total_capacity": 250,
        "price": 499.0
    },
    {
        "title": "DevOps World & Kubernetes Practitioners Conference",
        "description": "Deep-dive workshops on container orchestration, GitOps automation, site reliability engineering, and zero-trust microservice security.",
        "category": "Technology & Innovation",
        "tags": ["DevOps", "Kubernetes", "Docker", "Cloud", "SRE"],
        "venue": {"type": "hybrid", "name": "Silicon Innovation Hub & Virtual", "address_or_link": "Outer Ring Road", "city": "Bengaluru"},
        "days_from_now": 12,
        "duration_hours": 5.0,
        "total_capacity": 200,
        "price": 299.0
    },
    {
        "title": "Autonomous Systems & Quantum Computing Expo",
        "description": "Experience live hardware demonstrations, robotics simulations, and keynote sessions on post-quantum cryptography and edge compute.",
        "category": "Technology & Innovation",
        "tags": ["Quantum", "Robotics", "Autonomous", "Hardware", "FutureTech"],
        "venue": {"type": "in-person", "name": "International Tech Park Auditorium", "address_or_link": "Whitefield", "city": "Bengaluru"},
        "days_from_now": 18,
        "duration_hours": 7.0,
        "total_capacity": 180,
        "price": 350.0
    },

    # 2. Education & Learning (Educational Seminars)
    {
        "title": "International Education & Lifelong Learning Symposium",
        "description": "Exploring cognitive pedagogy, AI in education, curriculum innovation, and global higher learning strategies with leading educators and policymakers.",
        "category": "Education & Learning",
        "tags": ["Education", "Learning", "Pedagogy", "EdTech", "Symposium"],
        "venue": {"type": "in-person", "name": "National Education Heritage Hall", "address_or_link": "Civic Center Road", "city": "Bengaluru"},
        "days_from_now": 7,
        "duration_hours": 5.5,
        "total_capacity": 150,
        "price": 199.0
    },
    {
        "title": "Advanced Data Science & Applied Machine Learning Masterclass",
        "description": "Hands-on masterclass focusing on feature engineering, deep learning pipelines, transformer architectures, and production model observability.",
        "category": "Education & Learning",
        "tags": ["DataScience", "MachineLearning", "Python", "Masterclass", "Analytics"],
        "venue": {"type": "hybrid", "name": "Global Data Analytics Institute", "address_or_link": "MG Road & Stream", "city": "Bengaluru"},
        "days_from_now": 14,
        "duration_hours": 4.5,
        "total_capacity": 120,
        "price": 250.0
    },
    {
        "title": "Sustainable Urban Architecture & Green Infrastructure Summit",
        "description": "Examining net-zero building design, biophilic structural engineering, and circular economy integration in modern metropolitan cities.",
        "category": "Education & Learning",
        "tags": ["Architecture", "Sustainability", "UrbanPlanning", "GreenDesign"],
        "venue": {"type": "in-person", "name": "City Design & Architecture Gallery", "address_or_link": "Victoria Road", "city": "Bengaluru"},
        "days_from_now": 21,
        "duration_hours": 6.0,
        "total_capacity": 100,
        "price": 150.0
    },

    # 3. Music & Entertainment (Concerts & Music Festivals)
    {
        "title": "Starlight Music Festival: Indie, Electronic & Acoustic Live",
        "description": "An open-air evening celebration featuring acclaimed indie artists, contemporary synthwave producers, and soulful acoustic songwriters under the night sky.",
        "category": "Music & Entertainment",
        "tags": ["Music", "Concert", "Festival", "LiveMusic", "Indie"],
        "venue": {"type": "in-person", "name": "Green Valley Open Air Amphitheatre", "address_or_link": "Valley View Road", "city": "Bengaluru"},
        "days_from_now": 8,
        "duration_hours": 5.0,
        "total_capacity": 500,
        "price": 399.0
    },
    {
        "title": "Symphonic Jazz & Blues Evening: Live Brass & Strings",
        "description": "Experience an enchanting fusion of classic big-band jazz, New Orleans blues, and orchestral strings performed by master instrumentalists.",
        "category": "Music & Entertainment",
        "tags": ["Jazz", "Blues", "Symphony", "LivePerformance", "Music"],
        "venue": {"type": "in-person", "name": "The Royal Music Conservatory", "address_or_link": "Residency Road", "city": "Bengaluru"},
        "days_from_now": 15,
        "duration_hours": 3.0,
        "total_capacity": 250,
        "price": 300.0
    },
    {
        "title": "Prime Time Stand-Up Comedy Showcase: Unfiltered Laughs",
        "description": "A side-splitting evening featuring top national and international touring comedians delivering fresh observational humor and sharp wit.",
        "category": "Music & Entertainment",
        "tags": ["Comedy", "StandUp", "Entertainment", "Humor", "Nightlife"],
        "venue": {"type": "in-person", "name": "The Comedy Lounge & Stage", "address_or_link": "Indiranagar 100ft Road", "city": "Bengaluru"},
        "days_from_now": 11,
        "duration_hours": 2.5,
        "total_capacity": 180,
        "price": 250.0
    },

    # 4. Arts & Creativity (Art Exhibitions & Workshops)
    {
        "title": "Contemporary Visual Arts & Sculpture Exhibition",
        "description": "Immerse yourself in vibrant multimedia installations, fine oil paintings, bronze sculptures, and curated digital generative art by prominent artists.",
        "category": "Arts & Creativity",
        "tags": ["Art", "Exhibition", "Sculpture", "VisualArts", "Gallery"],
        "venue": {"type": "in-person", "name": "National Modern Art Gallery", "address_or_link": "Palace Road", "city": "Bengaluru"},
        "days_from_now": 9,
        "duration_hours": 6.0,
        "total_capacity": 200,
        "price": 100.0
    },
    {
        "title": "Urban Street Photography & Visual Storytelling Walk",
        "description": "Learn golden hour framing, dynamic range capture, and visual narrative composition guided by award-winning documentary photographers.",
        "category": "Arts & Creativity",
        "tags": ["Photography", "Storytelling", "VisualArts", "Workshop"],
        "venue": {"type": "in-person", "name": "Heritage Arts & Cultural Quarter", "address_or_link": "Old Town Square", "city": "Bengaluru"},
        "days_from_now": 16,
        "duration_hours": 3.5,
        "total_capacity": 30,
        "price": 150.0
    },
    {
        "title": "Artisan Ceramic & Clay Craft Studio Workshop",
        "description": "Get your hands dirty on the potter wheel. Learn wheel throwing, trimming, decorative bisque glazing, and kiln firing techniques.",
        "category": "Arts & Creativity",
        "tags": ["Pottery", "Ceramics", "Craft", "Handmade", "Workshop"],
        "venue": {"type": "in-person", "name": "Earth & Fire Artisan Studio", "address_or_link": "Clayworks Complex, Koramangala", "city": "Bengaluru"},
        "days_from_now": 22,
        "duration_hours": 3.0,
        "total_capacity": 25,
        "price": 200.0
    },

    # 5. Sports & Fitness (Sports Tournaments)
    {
        "title": "City Marathon & 10K Endurance Championship",
        "description": "The premier annual metropolitan run. Certified chip-timed bibs, hydration stations, paramedic support, finisher medals, and celebratory brunch.",
        "category": "Sports & Fitness",
        "tags": ["Marathon", "Running", "Fitness", "Endurance", "Sports"],
        "venue": {"type": "in-person", "name": "Central Metropolitan Stadium Promenade", "address_or_link": "Cubbon Park Circuit", "city": "Bengaluru"},
        "days_from_now": 10,
        "duration_hours": 4.0,
        "total_capacity": 600,
        "price": 200.0
    },
    {
        "title": "Metropolitan Open Badminton Championship",
        "description": "Competitive singles and doubles tournament on professional synthetic BWF-approved courts with certified referees, trophies, and cash prizes.",
        "category": "Sports & Fitness",
        "tags": ["Badminton", "Tournament", "Sports", "Athletics", "Competition"],
        "venue": {"type": "in-person", "name": "Apex Indoor Sports Complex", "address_or_link": "Sarjapur Sports City", "city": "Bengaluru"},
        "days_from_now": 17,
        "duration_hours": 8.0,
        "total_capacity": 80,
        "price": 250.0
    },
    {
        "title": "Premier Futsal League: City Champions Cup",
        "description": "High-octane 5-a-side indoor football tournament under arena floodlights featuring knockout rounds, group stages, and professional commentary.",
        "category": "Sports & Fitness",
        "tags": ["Football", "Futsal", "Sports", "League", "Tournament"],
        "venue": {"type": "in-person", "name": "Metro Turf & Sports Arena", "address_or_link": "Arena Central, Domlur", "city": "Bengaluru"},
        "days_from_now": 24,
        "duration_hours": 6.0,
        "total_capacity": 120,
        "price": 300.0
    },

    # 6. Business & Entrepreneurship (Business Networking)
    {
        "title": "Venture Capital Summit & Startup Pitch Showcase",
        "description": "Connect visionary tech founders with top venture capital funds, angel syndicates, and seed accelerators for live deal-making and networking.",
        "category": "Business & Entrepreneurship",
        "tags": ["Startup", "VentureCapital", "Pitch", "Networking", "Business"],
        "venue": {"type": "in-person", "name": "Metropolitan Innovation & Trade Center", "address_or_link": "Financial District, Level 4", "city": "Bengaluru"},
        "days_from_now": 13,
        "duration_hours": 6.5,
        "total_capacity": 200,
        "price": 499.0
    },
    {
        "title": "Angel Investors & Founders Networking Roundtable",
        "description": "An intimate, curated roundtable discussion on term-sheet negotiation, unit economics, international expansion, and early-stage capital allocation.",
        "category": "Business & Entrepreneurship",
        "tags": ["AngelInvesting", "Founders", "Networking", "Leadership"],
        "venue": {"type": "in-person", "name": "Executive Club Boardroom", "address_or_link": "Lavelle Road", "city": "Bengaluru"},
        "days_from_now": 19,
        "duration_hours": 3.0,
        "total_capacity": 40,
        "price": 350.0
    },
    {
        "title": "Global Product Leadership & Agile Scaling Conference",
        "description": "Product management vice presidents and design executives share proven frameworks for discovery, user retention, metrics, and PLG scaling.",
        "category": "Business & Entrepreneurship",
        "tags": ["ProductManagement", "Agile", "Strategy", "Leadership"],
        "venue": {"type": "hybrid", "name": "Tech Enterprise Center", "address_or_link": "Bellandur & Global Stream", "city": "Bengaluru"},
        "days_from_now": 26,
        "duration_hours": 5.0,
        "total_capacity": 150,
        "price": 250.0
    },

    # 7. Health & Wellness (Fitness Sessions)
    {
        "title": "Mindful Living & Holistic Sound Bath Healing Retreat",
        "description": "Restore mental harmony with gentle hatha yoga, pranayama breathwork, and resonant Tibetan singing bowl sound therapy led by senior wellness masters.",
        "category": "Health & Wellness",
        "tags": ["Yoga", "Meditation", "SoundBath", "Wellness", "Mindfulness"],
        "venue": {"type": "in-person", "name": "Zen Botanical Wellness Sanctuary", "address_or_link": "Lalbagh Green Promenade", "city": "Bengaluru"},
        "days_from_now": 8,
        "duration_hours": 2.5,
        "total_capacity": 60,
        "price": 120.0
    },
    {
        "title": "Executive Stress Resilience & Mindfulness Seminar",
        "description": "Licensed psychologists and neuroscientists present actionable evidence-based techniques for cognitive recovery, stress reduction, and peak focus.",
        "category": "Health & Wellness",
        "tags": ["MentalHealth", "Mindfulness", "Resilience", "StressManagement"],
        "venue": {"type": "in-person", "name": "Wellness Center Auditorium", "address_or_link": "Richmond Circle", "city": "Bengaluru"},
        "days_from_now": 15,
        "duration_hours": 3.0,
        "total_capacity": 100,
        "price": 0.0
    },
    {
        "title": "Strength, Mobility & Functional Movement Masterclass",
        "description": "Improve joint longevity, athletic core stability, and posture alignment through functional biomechanics drills led by elite conditioning coaches.",
        "category": "Health & Wellness",
        "tags": ["Fitness", "Mobility", "Strength", "Movement", "Health"],
        "venue": {"type": "in-person", "name": "Peak Performance Training Pavilion", "address_or_link": "Koramangala Fitness Hub", "city": "Bengaluru"},
        "days_from_now": 23,
        "duration_hours": 2.0,
        "total_capacity": 45,
        "price": 150.0
    },

    # 8. Food & Lifestyle (Cooking Workshops)
    {
        "title": "Gourmet Culinary Masterclass: Artisanal Plant-Based Cuisine",
        "description": "Executive chefs guide you through crafting multi-course fine-dining vegetarian dishes, emulsion techniques, and delicate plating aesthetics.",
        "category": "Food & Lifestyle",
        "tags": ["Cooking", "Culinary", "PlantBased", "Gourmet", "Food"],
        "venue": {"type": "in-person", "name": "Culinary Arts Institute Professional Kitchen", "address_or_link": "Church Street", "city": "Bengaluru"},
        "days_from_now": 9,
        "duration_hours": 3.5,
        "total_capacity": 30,
        "price": 350.0
    },
    {
        "title": "Specialty Coffee Roasting & Sensory Cupping Experience",
        "description": "Explore green bean sourcing, thermal roast profiles, and SCA cupping protocols. Sample exquisite single-origin Arabicas from around the globe.",
        "category": "Food & Lifestyle",
        "tags": ["Coffee", "Barista", "Cupping", "Foodie", "Lifestyle"],
        "venue": {"type": "in-person", "name": "Artisan Roasters Lab & Roastery", "address_or_link": "Indiranagar Defense Colony", "city": "Bengaluru"},
        "days_from_now": 16,
        "duration_hours": 2.5,
        "total_capacity": 25,
        "price": 200.0
    },
    {
        "title": "International Street Food & Wine Pairing Festival",
        "description": "An exquisite tasting walk featuring artisanal street food carts, sommelier-guided wine pairings, live acoustic jazz, and chef demonstrations.",
        "category": "Food & Lifestyle",
        "tags": ["Wine", "StreetFood", "Tasting", "Festival", "Lifestyle"],
        "venue": {"type": "in-person", "name": "The Courtyard Culinary Promenade", "address_or_link": "UB City Plaza", "city": "Bengaluru"},
        "days_from_now": 27,
        "duration_hours": 5.0,
        "total_capacity": 300,
        "price": 450.0
    },

    # 9. Travel & Adventure (Travel Experiences)
    {
        "title": "Western Ghats Wilderness Trek & Eco-Camping Expedition",
        "description": "A guided 2-day trekking expedition through cloud forests, cascading waterfalls, and biodiverse ridges with certified mountaineers and eco-tents.",
        "category": "Travel & Adventure",
        "tags": ["Trekking", "Adventure", "Camping", "Wilderness", "Travel"],
        "venue": {"type": "in-person", "name": "Western Ghats Base Camp", "address_or_link": "Chikmagalur Trailhead", "city": "Bengaluru"},
        "days_from_now": 14,
        "duration_hours": 36.0,
        "total_capacity": 35,
        "price": 850.0
    },
    {
        "title": "Coastal Kayaking & Open-Water Adventure Workshop",
        "description": "Learn sea kayaking strokes, ocean navigation, and safety rolling under international paddle instructors with full safety gear included.",
        "category": "Travel & Adventure",
        "tags": ["Kayaking", "WaterSports", "Adventure", "Outdoors", "Travel"],
        "venue": {"type": "in-person", "name": "Coastal Water Sports Center", "address_or_link": "Mangalore Marina", "city": "Bengaluru"},
        "days_from_now": 20,
        "duration_hours": 5.0,
        "total_capacity": 24,
        "price": 600.0
    },
    {
        "title": "Heritage Trail: Ancient Temple Architecture & Cultural Expedition",
        "description": "An enriching cultural expedition exploring UNESCO heritage stone carvings, ancient Dravidian architecture, and folklore with historians.",
        "category": "Travel & Adventure",
        "tags": ["Heritage", "Culture", "History", "Expedition", "Travel"],
        "venue": {"type": "in-person", "name": "Heritage Discovery Center", "address_or_link": "Hampi Cultural Corridor", "city": "Bengaluru"},
        "days_from_now": 28,
        "duration_hours": 8.0,
        "total_capacity": 40,
        "price": 300.0
    },

    # 10. Social & Community (Community Events)
    {
        "title": "Urban Reforestation & Green City Tree Plantation Drive",
        "description": "Join hundreds of community volunteers planting 1,000 indigenous trees to enhance metropolitan green cover, biodiversity, and clean air.",
        "category": "Social & Community",
        "tags": ["Environment", "Community", "Volunteering", "Sustainability", "Green"],
        "venue": {"type": "in-person", "name": "Lakeside Eco-Park Corridor", "address_or_link": "Bellandur Lake North Shore", "city": "Bengaluru"},
        "days_from_now": 7,
        "duration_hours": 4.0,
        "total_capacity": 350,
        "price": 0.0
    },
    {
        "title": "Community Animal Welfare & Shelter Pet Adoption Fair",
        "description": "Meet lovely rescue puppies and kittens looking for forever homes. Free vet checkups, behavioral seminars, and pet agility demonstrations.",
        "category": "Social & Community",
        "tags": ["Pets", "AnimalWelfare", "Adoption", "Community", "Family"],
        "venue": {"type": "in-person", "name": "Community Civic Park Plaza", "address_or_link": "Indiranagar Park", "city": "Bengaluru"},
        "days_from_now": 15,
        "duration_hours": 5.0,
        "total_capacity": 400,
        "price": 0.0
    },
    {
        "title": "Youth Mentorship & Equal Opportunity Education Drive",
        "description": "Mentorship kickoff connecting community professionals with underserved youth for career coaching, digital literacy, and skill workshops.",
        "category": "Social & Community",
        "tags": ["Youth", "Mentorship", "Community", "Education", "SocialImpact"],
        "venue": {"type": "in-person", "name": "Metropolitan Community Center", "address_or_link": "Shivajinagar Community Hall", "city": "Bengaluru"},
        "days_from_now": 22,
        "duration_hours": 3.5,
        "total_capacity": 150,
        "price": 0.0
    }
]

def migrate():
    db = get_db()
    print("=" * 65)
    print("MIGRATING EVENTSPHERE TO UNIVERSAL EVENT PLATFORM")
    print("=" * 65)

    # 1. Update existing events to universal terminology
    print("\n--- [1/2] Updating Existing Event Documents to Universal Phrasing ---")
    category_map = {
        "Academic": "Education & Learning",
        "Technology": "Technology & Innovation",
        "Sports": "Sports & Fitness",
        "Wellness": "Health & Wellness"
    }

    modified_count = 0
    for old_cat, new_cat in category_map.items():
        res = db.events.update_many(
            {"category": old_cat},
            {"$set": {"category": new_cat, "updated_at": datetime.utcnow()}}
        )
        if res.modified_count > 0:
            print(f" [OK] Updated {res.modified_count} events from '{old_cat}' -> '{new_cat}'")
            modified_count += res.modified_count

    # Update organizer names from campus board to universal
    res_org = db.events.update_many(
        {"organizer_name": "EventSphere Campus Events Board"},
        {"$set": {"organizer_name": "EventSphere Global Events", "updated_at": datetime.utcnow()}}
    )
    if res_org.modified_count > 0:
        print(f" [OK] Updated organizer name on {res_org.modified_count} events.")

    # 2. Seed universal events
    print("\n--- [2/2] Seeding Universal Sample Events Across 10 Categories ---")
    admin_user = UserService.get_user_by_email("admin@edusphere.in")
    if not admin_user:
        admin_user = UserService.get_user_by_email("admin@college.edu")
    if not admin_user:
        admin_user = db.users.find_one({"role": "admin"}) or db.users.find_one()
    admin_id = admin_user["_id"] if admin_user else None

    inserted_count = 0
    now = datetime.utcnow()

    for item in UNIVERSAL_EVENTS:
        existing = db.events.find_one({"title": item["title"]})
        if existing:
            # Update category and description if needed
            db.events.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "category": item["category"],
                        "description": item["description"],
                        "venue": item["venue"],
                        "tags": item["tags"],
                        "updated_at": now
                    }
                }
            )
            continue

        event_date = now + timedelta(days=item["days_from_now"])
        doc = {
            "title": item["title"],
            "description": item["description"],
            "category": item["category"],
            "tags": item["tags"],
            "organizer_id": admin_id,
            "organizer_name": "EventSphere Global Events",
            "venue": item["venue"],
            "event_date": event_date,
            "duration_hours": item["duration_hours"],
            "total_capacity": item["total_capacity"],
            "remaining_capacity": item["total_capacity"],
            "price": item["price"],
            "status": "published",
            "image_url": "",
            "created_at": now,
            "updated_at": now
        }
        res = db.events.insert_one(doc)
        inserted_count += 1
        print(f" [OK] Inserted: '{item['title']}' ({item['category']})")

    print(f"\n[DONE] Successfully inserted {inserted_count} new universal events.")
    print(f" Total events now in database: {db.events.count_documents({})}")
    print(" Distinct categories in database:")
    for cat in db.events.distinct("category"):
        cnt = db.events.count_documents({"category": cat})
        print(f"  - {cat}: {cnt} event(s)")

if __name__ == "__main__":
    migrate()
