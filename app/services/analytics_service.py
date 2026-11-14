# app/services/analytics_service.py
"""
Analytics Service for EventSphere.
Implements MongoDB aggregation pipelines using native PyMongo for platform metrics,
event performance, category trends, user booking histories, and monthly statistics.
"""

from bson import ObjectId
from .db import get_db, to_object_id

class AnalyticsService:
    @staticmethod
    def get_db():
        return get_db()

    @classmethod
    def get_event_booking_summary(cls, event_id=None, limit=50):
        """
        Pipeline 1 & 2: Total bookings, total tickets sold, and actual revenue generated
        by each event using confirmed bookings.
        Uses $match, $lookup, $project, and $sort.
        """
        match_stage = {"status": {"$in": ["published", "completed"]}}
        if event_id:
            match_stage["_id"] = to_object_id(event_id)

        pipeline = [
            {"$match": match_stage},
            {
                "$lookup": {
                    "from": "bookings",
                    "localField": "_id",
                    "foreignField": "event_id",
                    "as": "event_bookings"
                }
            },
            {
                "$project": {
                    "title": 1,
                    "category": 1,
                    "total_capacity": 1,
                    "remaining_capacity": 1,
                    "price": 1,
                    "event_date": 1,
                    "confirmed_bookings": {
                        "$filter": {
                            "input": "$event_bookings",
                            "as": "b",
                            "cond": {"$eq": ["$$b.status", "confirmed"]}
                        }
                    }
                }
            },
            {
                "$project": {
                    "title": 1,
                    "category": 1,
                    "total_capacity": 1,
                    "remaining_capacity": 1,
                    "price": 1,
                    "event_date": 1,
                    "total_bookings_count": {"$size": "$confirmed_bookings"},
                    "total_tickets_sold": {"$sum": "$confirmed_bookings.tickets_count"},
                    # Accurately sum actual total_amount paid from confirmed bookings:
                    "total_revenue": {"$sum": "$confirmed_bookings.total_amount"},
                    "occupancy_rate": {
                        "$cond": [
                            {"$gt": ["$total_capacity", 0]},
                            {
                                "$round": [
                                    {
                                        "$multiply": [
                                            {
                                                "$divide": [
                                                    {"$sum": "$confirmed_bookings.tickets_count"},
                                                    "$total_capacity"
                                                ]
                                            },
                                            100
                                        ]
                                    },
                                    2
                                ]
                            },
                            0
                        ]
                    }
                }
            },
            {"$sort": {"total_tickets_sold": -1, "total_revenue": -1}},
            {"$limit": limit}
        ]

        return list(cls.get_db().events.aggregate(pipeline))

    @classmethod
    def get_most_popular_categories(cls):
        """
        Pipeline 3: Most popular event categories by event volume, tickets sold,
        and confirmed booking revenue.
        Uses $lookup, $project, $filter, $group, and $sort.
        """
        pipeline = [
            {
                "$lookup": {
                    "from": "bookings",
                    "localField": "_id",
                    "foreignField": "event_id",
                    "as": "event_bookings"
                }
            },
            {
                "$project": {
                    "category": 1,
                    "price": 1,
                    "total_capacity": 1,
                    "confirmed_bookings": {
                        "$filter": {
                            "input": "$event_bookings",
                            "as": "b",
                            "cond": {"$eq": ["$$b.status", "confirmed"]}
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": "$category",
                    "total_events": {"$sum": 1},
                    "total_tickets_sold": {"$sum": {"$sum": "$confirmed_bookings.tickets_count"}},
                    "total_revenue": {"$sum": {"$sum": "$confirmed_bookings.total_amount"}},
                    "total_seats_offered": {"$sum": "$total_capacity"}
                }
            },
            {"$sort": {"total_tickets_sold": -1, "total_events": -1}},
            {
                "$project": {
                    "category": "$_id",
                    "_id": 0,
                    "total_events": 1,
                    "total_tickets_sold": 1,
                    "total_revenue": {"$round": ["$total_revenue", 2]},
                    "total_seats_offered": 1
                }
            }
        ]

        return list(cls.get_db().events.aggregate(pipeline))

    @classmethod
    def get_user_booking_history(cls, user_id=None, limit=50):
        """
        Pipeline 4: User booking history enriched with full event and user details
        using $lookup and $unwind.
        Uses $match, $lookup, $unwind, $project, and $sort.
        """
        match_stage = {}
        if user_id:
            match_stage["user_id"] = to_object_id(user_id)

        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})

        pipeline.extend([
            {
                "$lookup": {
                    "from": "events",
                    "localField": "event_id",
                    "foreignField": "_id",
                    "as": "event"
                }
            },
            {
                "$unwind": {
                    "path": "$event",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {
                "$unwind": {
                    "path": "$user",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$project": {
                    "booking_code": 1,
                    "booking_date": 1,
                    "tickets_count": 1,
                    "total_amount": 1,
                    "status": 1,
                    "ticket_details": 1,
                    "cancelled_at": 1,
                    "event_id": 1,
                    "event_title": "$event.title",
                    "event_category": "$event.category",
                    "event_date": "$event.event_date",
                    "event_venue": "$event.venue",
                    "event_price": "$event.price",
                    "user_id": 1,
                    "user_name": "$user.name",
                    "user_email": "$user.email"
                }
            },
            {"$sort": {"booking_date": -1}},
            {"$limit": limit}
        ])

        return list(cls.get_db().bookings.aggregate(pipeline))

    @classmethod
    def get_monthly_booking_statistics(cls):
        """
        Pipeline 5: Monthly booking statistics (revenue, ticket volume, transaction count,
        and average booking value).
        Uses $match, $group, $sort, and $project.
        """
        pipeline = [
            {"$match": {"status": "confirmed"}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m", "date": "$booking_date"}},
                    "total_bookings": {"$sum": 1},
                    "total_tickets_sold": {"$sum": "$tickets_count"},
                    "total_revenue": {"$sum": "$total_amount"},
                    "avg_booking_amount": {"$avg": "$total_amount"}
                }
            },
            {"$sort": {"_id": 1}},
            {
                "$project": {
                    "month": "$_id",
                    "_id": 0,
                    "total_bookings": 1,
                    "total_tickets_sold": 1,
                    "total_revenue": {"$round": ["$total_revenue", 2]},
                    "avg_booking_amount": {"$round": ["$avg_booking_amount", 2]}
                }
            }
        ]

        return list(cls.get_db().bookings.aggregate(pipeline))

    @classmethod
    def get_platform_kpis(cls):
        """
        Platform Overview KPIs: Computes total bookings, total tickets sold,
        cumulative revenue, and average booking value from confirmed bookings.
        """
        pipeline = [
            {"$match": {"status": "confirmed"}},
            {
                "$group": {
                    "_id": None,
                    "total_confirmed_bookings": {"$sum": 1},
                    "total_tickets_sold": {"$sum": "$tickets_count"},
                    "cumulative_revenue": {"$sum": "$total_amount"},
                    "avg_booking_value": {"$avg": "$total_amount"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "total_confirmed_bookings": 1,
                    "total_tickets_sold": 1,
                    "cumulative_revenue": {"$round": ["$cumulative_revenue", 2]},
                    "avg_booking_value": {"$round": ["$avg_booking_value", 2]}
                }
            }
        ]

        result = list(cls.get_db().bookings.aggregate(pipeline))
        if result:
            return result[0]
        return {
            "total_confirmed_bookings": 0,
            "total_tickets_sold": 0,
            "cumulative_revenue": 0.0,
            "avg_booking_value": 0.0
        }
