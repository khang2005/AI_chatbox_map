"""Polyline encoding/decoding utilities."""
from typing import List, Tuple


def encode_polyline(coords: List) -> str:
    """Encode a list of [lng, lat] coordinates to a polyline string."""
    result = []
    for coord in coords:
        lng, lat = coord[0], coord[1]
        lat = int(round(lat * 1e5))
        lng = int(round(lng * 1e5))
        
        dlat = lat - (result[-1] if result else 0)
        dlng = lng - (result[-2] if len(result) > 1 else 0)
        
        for val in (dlat, dlng):
            val = (val << 1) ^ (val >> 31) if val < 0 else val
            while val >= 0x20:
                result.append(((0x20 | (val & 0x1f)) + 63))
                val >>= 5
            result.append(val + 63)
    
    return ''.join(chr(c) for c in result)


def decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    """Decode a polyline string to a list of coordinates."""
    coords = []
    index = 0
    lat = 0
    lng = 0
    
    while index < len(encoded):
        # Decode latitude
        b = ord(encoded[index]) - 63
        index += 1
        dlat = (b & 0x1f) << 5
        if b >= 0x20:
            b = ord(encoded[index]) - 63
            index += 1
            dlat |= b & 0x1f
            while b >= 0x20:
                b = ord(encoded[index]) - 63
                index += 1
                dlat = (dlat << 5) | (b & 0x1f)
        dlat = (dlat >> 1) ^ -(dlat & 1)
        lat += dlat
        
        # Decode longitude
        b = ord(encoded[index]) - 63
        index += 1
        dlng = (b & 0x1f) << 5
        if b >= 0x20:
            b = ord(encoded[index]) - 63
            index += 1
            dlng |= b & 0x1f
            while b >= 0x20:
                b = ord(encoded[index]) - 63
                index += 1
                dlng = (dlng << 5) | (b & 0x1f)
        dlng = (dlng >> 1) ^ -(dlng & 1)
        lng += dlng
        
        coords.append((lat / 1e5, lng / 1e5))
    
    return coords