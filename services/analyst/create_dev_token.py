#!/usr/bin/env python3
"""Create a development JWT token for testing"""

import jwt
import time
from datetime import datetime, timedelta

# JWT Settings from config
jwt_secret = "dev-local-please-rotate-9b1b7df7b6f54c8bbf7a9c"
jwt_issuer = "app.lvlparking.com"

# All zones with transaction data (22 zones total)
active_zones = [
    "69722", "69710", "69703", "69715", "69705", "69718", "69714", "69717",
    "69712", "69719", "69711", "69716", "69708", "69724", "69709", "69721",
    "69713", "69701", "69723", "12345", "69720", "69702"
]

# Create JWT payload
payload = {
    "sub": "dev-user-001",
    "org_id": "org-demo",
    "roles": ["admin", "analyst"],
    "zone_ids": active_zones,
    "iss": jwt_issuer,
    "iat": int(time.time()),
    "exp": int(time.time()) + (24 * 60 * 60)  # 24 hours
}

# Create JWT token
token = jwt.encode(payload, jwt_secret, algorithm="HS256")

print("🔑 DEVELOPMENT JWT TOKEN:")
print(token)
print()
print("📊 Token includes access to zones:")
for zone in active_zones:
    print(f"  - {zone}")
print()
print("🧪 Test with curl:")
print(f'curl -H "Authorization: Bearer {token}" "http://localhost:8080/recommendations/"')
print()
print("⏰ Token expires:", datetime.fromtimestamp(payload["exp"]).isoformat())