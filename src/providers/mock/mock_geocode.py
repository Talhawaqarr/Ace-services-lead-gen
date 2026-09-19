from typing import Dict, Any


class MockGeocodingProvider:
    def geocode(self, address: str) -> Dict[str, Any]:
        # Deterministic placeholder: returns null coords for empty address
        if not address:
            return {"latitude": None, "longitude": None, "confidence": 0}
        # Simple hash-based pseudo-coordinates for deterministic variety
        h = sum(ord(c) for c in address) % 90
        return {"latitude": 30.0 + h * 0.1, "longitude": -90.0 - h * 0.1, "confidence": 0.6}
