import datetime


def week_bounds(day):
    """Monday and Sunday of the ISO week containing `day`."""
    start = day - datetime.timedelta(days=day.isoweekday())
    return start, start + datetime.timedelta(days=6)
