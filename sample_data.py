
from datetime import date


def get_sample_rows():
    return [
        [date(2026, 10, 3).isoformat(), "Max Studio", "Design", "Landing page ", 8, 75.00],
        [date(2026, 10, 7).isoformat(), "Max Studio", "Development", "Checkout page", 12, 95.00],
        [date(2026, 10, 12).isoformat(), "blueBerry", "Consulting", "Project planning", 5, 110.00],
        [date(2026, 10, 18).isoformat(), "blueBerry", "Development", " UI/UX ", 10, 95.00],
    ]
