
from datetime import date

HEADERS = ("Date", "Client", "Category", "Description", "Hours", "Rate")


def validate_input_rows(rows):
    problems = []
    if not rows:
        return ["at least one row is required."]

    for row_number, row in enumerate(rows, start=1):
        if len(row) != len(HEADERS):
            problems.append(f"Row {row_number}: expected {len(HEADERS)} values.")
            continue

        work_date, client, category, description, hours, rate = row
        prefix = f"Row {row_number}: "
        try:
            date.fromisoformat(str(work_date).strip())
        except (TypeError, ValueError):
            problems.append(prefix + "enter a valid date as YYYY-MM-DD.")

        for label, value in (("client", client), ("category", category), ("description", description)):
            if not str(value).strip():
                problems.append(prefix + f"{label} cannot be blank.")
        try:
            if float(hours) <= 0:
                problems.append(prefix + "hours cannot be negative")
        except (TypeError, ValueError):
            problems.append(prefix + "hours must be a number.")
        try:
            if float(rate) < 0:
                problems.append(prefix + "rate cannot be negative.")
        except (TypeError, ValueError):
            problems.append(prefix + "rate must be a number.")
    return problems


def calculate_totals(rows):
   
    total_hours = 0.0
    amount_by_client = {}
    for row in rows:
        client = str(row[1]).strip()
        amount = float(row[4]) * float(row[5])
        total_hours += float(row[4])
        amount_by_client[client] = amount_by_client.get(client, 0.0) + amount
    return total_hours, sum(amount_by_client.values()), amount_by_client
