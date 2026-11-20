"""The library's room list. Trusted data owned by the application, not the model."""

ROOMS = {
    "B12": {"id": "B12", "name": "Room B12 · Quiet floor", "where": "King Library, 2nd floor",
            "details": "Seats 4 · whiteboard · large display", "seats": 4},
    "C3": {"id": "C3", "name": "Room C3 · Group pod", "where": "King Library, 3rd floor",
           "details": "Seats 6 · whiteboard", "seats": 6},
    "A7": {"id": "A7", "name": "Room A7 · Focus booth", "where": "King Library, 1st floor",
           "details": "Seats 2 · power outlets", "seats": 2},
}
BOOKED = {("C3", "Tomorrow 14:00-16:00")}  # already taken slots
