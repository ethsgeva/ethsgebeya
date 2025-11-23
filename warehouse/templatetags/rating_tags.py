from django import template

register = template.Library()

@register.simple_tag
def rating_breakdown(avg):
    """
    Given a numeric average (can be None), return a dict with counts for full, half, and empty stars out of 5.
    Rounds to nearest half for display.
    """
    try:
        if avg is None:
            return {"full": 0, "half": 0, "empty": 5}
        val = float(avg)
    except Exception:
        return {"full": 0, "half": 0, "empty": 5}

    # Round to nearest 0.5
    rounded = round(val * 2) / 2.0
    full = int(rounded // 1)
    half = 1 if (rounded - full) >= 0.5 else 0
    empty = max(0, 5 - full - half)
    return {"full": full, "half": half, "empty": empty}


@register.filter
def fmt_avg(avg):
    """Format average to 1 decimal or return '-' if None."""
    try:
        return f"{float(avg):.1f}"
    except Exception:
        return "-"


@register.filter
def times(n):
    """Return range(n) to allow `{% for _ in n|times %}` in templates."""
    try:
        n = int(n)
        if n < 0:
            n = 0
    except Exception:
        n = 0
    return range(n)
