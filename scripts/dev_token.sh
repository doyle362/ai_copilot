#!/bin/bash

# Generate a development JWT token for Level Analyst
# Usage: ./scripts/dev_token.sh [zone_ids] [expiry_minutes]

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
ZONE_IDS="${1:-${DEV_ZONE_IDS:-z-110,z-221}}"
EXPIRY_MINUTES="${2:-30}"
SECRET="${DEV_JWT_HS256_SECRET:-dev-local-please-rotate-9b1b7df7b6f54c8bbf7a9c}"
ISSUER="${JWT_ISSUER:-app.lvlparking.com}"
ORG="${ORG_ID:-org-demo}"

# Calculate expiry timestamp
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    EXP=$(date -v +${EXPIRY_MINUTES}M +%s)
    IAT=$(date +%s)
else
    # Linux
    EXP=$(date -d "+${EXPIRY_MINUTES} minutes" +%s)
    IAT=$(date +%s)
fi

# Convert zone IDs to JSON array
ZONE_JSON="[\"$(echo "$ZONE_IDS" | sed 's/,/","/g')\"]"

# Create JWT payload
PAYLOAD=$(cat <<EOF | tr -d '\n' | tr -d ' '
{
  "iss": "$ISSUER",
  "sub": "dev-user",
  "org_id": "$ORG",
  "roles": ["viewer", "approver"],
  "zone_ids": $ZONE_JSON,
  "iat": $IAT,
  "exp": $EXP
}
EOF
)

# Generate JWT using Python (most systems have Python)
python3 << EOF
import json
import hmac
import hashlib
import base64
import sys

def base64url_encode(data):
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')

def base64url_decode(data):
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data.encode('ascii'))

# JWT Header
header = {"alg": "HS256", "typ": "JWT"}
header_encoded = base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))

# JWT Payload
payload = '''$PAYLOAD'''
payload_encoded = base64url_encode(payload.encode('utf-8'))

# Create signature
message = f"{header_encoded}.{payload_encoded}"
secret = "$SECRET".encode('utf-8')
signature = hmac.new(secret, message.encode('utf-8'), hashlib.sha256).digest()
signature_encoded = base64url_encode(signature)

# Generate final JWT
jwt_token = f"{header_encoded}.{payload_encoded}.{signature_encoded}"

print(jwt_token)
EOF