# tripapp/schemas.py

ITINERARY_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day_sequence": {"type": "integer"},
                    "day_description": {"type": "string"},
                    "day_possible_date": {"type": "string", "format": "date"},
                    "day_locations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sequence": {"type": "integer"},
                                "lat": {"type": "number"},
                                "long": {"type": "number"},
                                "radius": {"type": "number"},
                                "description": {"type": "string"},
                            },
                            "required": ["sequence", "lat", "long"]
                        }
                    },
                    "overnightlocation": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number"},
                            "long": {"type": "number"},
                            "radius": {"type": "number"},
                            "description": {"type": "string"},
                        },
                        "required": ["lat", "long"]
                    },
                },
                "required": ["day_sequence"]
            }
        },
    },
    "required": ["name", "days"]
}
