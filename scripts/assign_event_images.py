# scripts/assign_event_images.py
"""
Assigns high-resolution, thematic, category-appropriate banner image URLs
to all 66 events in MongoDB Atlas.
"""

import os
import sys
from bson import ObjectId

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from app.services.db import get_db

# Specific image mapping by event ID or keyword
IMAGE_MAPPINGS = {
    # 1. Quantum Computing
    "quantum": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=800&q=80",
    # 2. Biotech
    "biotech": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=800&q=80",
    # 3. Sustainable Architecture
    "architecture": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80",
    # 4. Kubernetes Hackathon
    "kubernetes hands-on hackathon": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=800&q=80",
    # 5. DevOps & CI/CD Pipeline
    "ci/cd pipeline": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=800&q=80",
    # 6. Generative AI
    "generative ai": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=80",
    # 7. Folk Dance
    "folk dance": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=800&q=80",
    # 8. Sitar & Tabla
    "sitar": "https://images.unsplash.com/photo-1511192336575-5a79af67a629?auto=format&fit=crop&w=800&q=80",
    # 9. Food Carnival
    "carnival": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=800&q=80",
    # 10. Indie Rock Jam
    "indie rock jam": "https://images.unsplash.com/photo-1465847899084-d164df4dedc6?auto=format&fit=crop&w=800&q=80",
    # 11. Electronic Beats DJ
    "electronic beats": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=800&q=80",
    # 12. Stand-Up Comedy Evening
    "stand-up comedy evening": "https://images.unsplash.com/photo-1585699324551-f6c309eedeca?auto=format&fit=crop&w=800&q=80",
    # 13. Sunrise Marathon
    "sunrise marathon": "https://images.unsplash.com/photo-1452626038306-9aae5e071dd3?auto=format&fit=crop&w=800&q=80",
    # 14. Basketball
    "basketball": "https://images.unsplash.com/photo-1546519638-68e109498ffc?auto=format&fit=crop&w=800&q=80",
    # 15. Badminton Open
    "badminton smash open": "https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?auto=format&fit=crop&w=800&q=80",
    # 16. Canvas Painting & Pottery
    "pottery studio": "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=800&q=80",
    # 17. Street Photography Workshop
    "darkroom workshop": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=800&q=80",
    # 18. Creative Writing Slam
    "poetry slam": "https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=800&q=80",
    # 19. Esports Valorant
    "esports tournament": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=80",
    # 20. Retro Arcade
    "retro arcade": "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=800&q=80",
    # 21. Indie Game Dev
    "indie game dev": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=800&q=80",
    # 22. Shark Tank Startup Pitch
    "shark tank": "https://images.unsplash.com/photo-1475721027785-f74eccf877e2?auto=format&fit=crop&w=800&q=80",
    # 23. Seed Funding Masterclass
    "seed funding": "https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=800&q=80",
    # 24. Personal Finance & Stock Trading
    "stock trading": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=800&q=80",
    # 25. Morning Yoga
    "morning yoga": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=800&q=80",
    # 26. Stress Management
    "stress management": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=800&q=80",
    # 27. Plant-Based Culinary Masterclass
    "plant-based culinary": "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80",
    # 28. Lake Restoration
    "lake restoration": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=800&q=80",
    # 29. Blood Donation Camp
    "blood donation": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=800&q=80",
    # 30. Coding Mentorship
    "coding mentorship": "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=800&q=80",
    # 31. Global Tech Summit
    "global tech summit": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?auto=format&fit=crop&w=800&q=80",
    # 32. DevOps World
    "devops world": "https://images.unsplash.com/photo-1591115765373-5207764f72e7?auto=format&fit=crop&w=800&q=80",
    # 33. Autonomous Systems & Quantum
    "autonomous systems": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=800&q=80",
    # 34. Lifelong Learning Symposium
    "lifelong learning": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=800&q=80",
    # 35. Applied Machine Learning
    "machine learning masterclass": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80",
    # 36. Green Infrastructure Summit
    "green infrastructure": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80",
    # 37. Starlight Music Festival
    "starlight music festival": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?auto=format&fit=crop&w=800&q=80",
    # 38. Symphonic Jazz & Blues
    "symphonic jazz": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80",
    # 39. Prime Time Stand-Up
    "prime time stand-up": "https://images.unsplash.com/photo-1514306191717-452ec28c7814?auto=format&fit=crop&w=800&q=80",
    # 40. Visual Arts & Sculpture
    "visual arts & sculpture": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=800&q=80",
    # 41. Urban Street Photography Walk
    "photography & visual storytelling": "https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?auto=format&fit=crop&w=800&q=80",
    # 42. Ceramic & Clay Craft
    "ceramic & clay": "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=800&q=80",
    # 43. City Marathon
    "city marathon": "https://images.unsplash.com/photo-1530549387789-4c1017266635?auto=format&fit=crop&w=800&q=80",
    # 44. Metropolitan Badminton
    "metropolitan open badminton": "https://images.unsplash.com/photo-1521537634581-0dced2fee2ef?auto=format&fit=crop&w=800&q=80",
    # 45. Futsal Champions Cup
    "futsal": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=800&q=80",
    # 46. Venture Capital Summit
    "venture capital summit": "https://images.unsplash.com/photo-1515187029135-18ee286d815b?auto=format&fit=crop&w=800&q=80",
    # 47. Angel Investors Roundtable
    "angel investors": "https://images.unsplash.com/photo-1528605248644-14dd04022da1?auto=format&fit=crop&w=800&q=80",
    # 48. Product Leadership Agile
    "product leadership": "https://images.unsplash.com/photo-1531403009284-440f080d1e12?auto=format&fit=crop&w=800&q=80",
    # 49. Mindful Living Retreat
    "mindful living": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=800&q=80",
    # 50. Stress Resilience Seminar
    "stress resilience": "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80",
    # 51. Functional Movement
    "functional movement": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=800&q=80",
    # 52. Gourmet Culinary Masterclass
    "gourmet culinary": "https://images.unsplash.com/photo-1556910103-1c02745aae4d?auto=format&fit=crop&w=800&q=80",
    # 53. Specialty Coffee Roasting
    "coffee roasting": "https://images.unsplash.com/photo-1447933601403-0c6688de566e?auto=format&fit=crop&w=800&q=80",
    # 54. Street Food & Wine Pairing
    "wine pairing": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?auto=format&fit=crop&w=800&q=80",
    # 55. Wilderness Trek
    "wilderness trek": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80",
    # 56. Coastal Kayaking
    "coastal kayaking": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=800&q=80",
    # 57. Heritage Trail
    "heritage trail": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=800&q=80",
    # 58. Tree Plantation
    "tree plantation": "https://images.unsplash.com/photo-1576085898323-218337e3e43c?auto=format&fit=crop&w=800&q=80",
    # 59. Animal Adoption Fair
    "pet adoption": "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=800&q=80",
    # 60. Youth Mentorship
    "youth mentorship": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=800&q=80"
}

# Category fallbacks for any unmapped or test events
CATEGORY_FALLBACKS = {
    "Technology & Innovation": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80",
    "Education & Learning": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=800&q=80",
    "Music & Entertainment": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=800&q=80",
    "Arts & Creativity": "https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?auto=format&fit=crop&w=800&q=80",
    "Sports & Fitness": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?auto=format&fit=crop&w=800&q=80",
    "Business & Entrepreneurship": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=800&q=80",
    "Health & Wellness": "https://images.unsplash.com/photo-1545205597-3d9d02c29597?auto=format&fit=crop&w=800&q=80",
    "Food & Lifestyle": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80",
    "Travel & Adventure": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
    "Social & Community": "https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&w=800&q=80",
    "Cultural": "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&w=800&q=80",
    "Gaming": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=800&q=80",
    "Workshop": "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=800&q=80"
}

def pick_image_for_event(title, category):
    title_lower = title.lower()
    for key, url in IMAGE_MAPPINGS.items():
        if key in title_lower:
            return url
    return CATEGORY_FALLBACKS.get(category, "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=800&q=80")

def update_events():
    app = create_app()
    with app.app_context():
        db = get_db()
        events = list(db.events.find({}))
        print(f"Total events found in DB: {len(events)}")
        
        updated_count = 0
        for ev in events:
            ev_id = ev["_id"]
            title = ev.get("title", "")
            category = ev.get("category", "Technology & Innovation")
            
            chosen_url = pick_image_for_event(title, category)
            db.events.update_one({"_id": ev_id}, {"$set": {"image_url": chosen_url}})
            updated_count += 1
            print(f"Updated: [{category}] {title[:40]} -> {chosen_url[:50]}...")
            
        print(f"\nSuccessfully updated image_url for {updated_count} events.")

if __name__ == "__main__":
    update_events()
