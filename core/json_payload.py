import json


def parse_json_object(request):
    """Return the request body as a dict, or None when it is not a JSON object."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def parse_id(value):
    """Return a positive integer id, or None for missing or non-numeric values."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        return int(value) or None
    return None
