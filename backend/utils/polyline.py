"""Polyline encoding/decoding utilities."""
from typing import List, Tuple


def _encode_value(result: list, val: int) -> None:
    """Encode a single integer value into polyline format."""
    val = val << 1
    if val < 0:
        val = ~val
    while val >= 0x20:
        result.append((val & 0x1F) | 0x20)
        val >>= 5
    result.append(val)


def encode_polyline(coords: List) -> str:
    """Encode a list of [lng, lat] coordinates to a polyline string."""
    result = []
    prev_lat = 0
    prev_lng = 0
    for coord in coords:
        lng, lat = coord[0], coord[1]
        lat_i = int(round(lat * 1e5))
        lng_i = int(round(lng * 1e5))
        _encode_value(result, lat_i - prev_lat)
        _encode_value(result, lng_i - prev_lng)
        prev_lat = lat_i
        prev_lng = lng_i
    return ''.join(chr(c) for c in result)


def _decode_value(encoded: str, index: int) -> Tuple[int, int]:
    """Decode a single polyline value starting at index. Returns (value, new_index)."""
    shift = 0
    result = 0
    while True:
        b = ord(encoded[index]) - 63
        index += 1
        result |= (b & 0x1F) << shift
        shift += 5
        if b < 0x20:
            break
    dval = (result >> 1) ^ -(result & 1)
    return dval, index


def decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    """Decode a polyline string to a list of (lat, lng) tuples."""
    coords = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        dlat, index = _decode_value(encoded, index)
        lat += dlat
        dlng, index = _decode_value(encoded, index)
        lng += dlng
        coords.append((lat / 1e5, lng / 1e5))

    return coords
