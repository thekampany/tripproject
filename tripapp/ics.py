from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from icalendar import Calendar, Event

CATEGORY_ICONS = {
    "Transportation": "🚆", "Lodging": "🛏️", "Food and Drinks": "🍽️",
    "Activity": "🎟️", "Other": "📌",
}
TRANSPORT_ICONS = {
    "Airplane": "✈️", "Bus": "🚌", "Train": "🚆", "Car": "🚗",
    "Taxi": "🚕", "Walking": "🚶", "Cycling": "🚴",
}


def _tz(trip):
    try:
        return ZoneInfo(trip.timezone_name or settings.TIME_ZONE)
    except ZoneInfoNotFoundError:
        return ZoneInfo(settings.TIME_ZONE)


def _zone(name, fallback):
    try:
        return ZoneInfo(name) if name else fallback
    except ZoneInfoNotFoundError:
        return fallback


def _utc_times(item):
    trip_tz = _tz(item.dayprogram.trip)
    start_tz = _zone(item.start_timezone, trip_tz)
    end_tz = _zone(item.end_timezone, start_tz)

    day = item.dayprogram.tripdate
    start = datetime.combine(day, item.start_time, tzinfo=start_tz)
    end = datetime.combine(day, item.end_time, tzinfo=end_tz)

    start_utc = start.astimezone(dt_timezone.utc)
    end_utc = end.astimezone(dt_timezone.utc)

    # Aankomst ligt "de volgende dag" (nachtvlucht, oostwaarts vliegen, nachttrein)
    while end_utc < start_utc:
        end += timedelta(days=1)
        end_utc = end.astimezone(dt_timezone.utc)

    return start_utc, end_utc

def _summary(item):
    if item.category == "Transportation" and item.transportation_type:
        icon = TRANSPORT_ICONS.get(item.transportation_type, "🚆")
    else:
        icon = CATEGORY_ICONS.get(item.category, "📌")
    text = item.description or item.transportation_type or item.get_category_display() or "Item"
    return f"{icon} {text}"


def _description(item):
    lines = [f"Trip: {item.dayprogram.trip.name}"]
    if item.end_address:
        lines.append(f"From: {item.start_address}")
        lines.append(f"To: {item.end_address}")
    for link in item.links.all():
        if link.url:
            lines.append(f"{link.description or 'Link'}: {link.url}")
    if item.start_timezone:
        lines.append(f"Start: {item.start_time:%H:%M} ({item.start_timezone})")
    if item.end_timezone:
        lines.append(f"End: {item.end_time:%H:%M} ({item.end_timezone})")
    return "\n".join(lines)


def build_calendar(items, host, name="Trippanion"):
    cal = Calendar()
    cal.add("prodid", "-//Trippanion//Calendar feed//NL")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", name)
    cal.add("refresh-interval", timedelta(hours=1), parameters={"VALUE": "DURATION"})
    cal.add("x-published-ttl", timedelta(hours=1))

    now = datetime.now(dt_timezone.utc)
    for item in items:
        start, end = _utc_times(item)
        ev = Event()
        ev.add("uid", f"scheduleditem-{item.pk}@{host}")
        ev.add("dtstamp", now)
        ev.add("dtstart", start)
        ev.add("dtend", end)
        ev.add("summary", _summary(item))
        ev.add("description", _description(item))
        if item.start_address:
            ev.add("location", item.start_address)
        cal.add_component(ev)

    return cal.to_ical()
