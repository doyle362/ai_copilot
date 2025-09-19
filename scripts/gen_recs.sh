#!/bin/bash

# Generate recommendations for a zone
# Usage: ./scripts/gen_recs.sh <zone_id> [context] [token]

set -e

ZONE_ID="$1"
CONTEXT="$2"
TOKEN="${3:-$(cat token.txt 2>/dev/null || echo '')}"
API_URL="${API_URL:-http://localhost:8088}"

if [ -z "$ZONE_ID" ]; then
    echo "Usage: $0 <zone_id> [context] [token]"
    echo ""
    echo "Examples:"
    echo "  $0 z-110"
    echo "  $0 z-110 \"Focus on weekend revenue optimization\""
    echo "  $0 z-110 \"\" \$(./scripts/dev_token.sh)"
    echo ""
    echo "Environment variables:"
    echo "  API_URL: API base URL (default: http://localhost:8088)"
    echo "  TOKEN: JWT token (can also be read from token.txt)"
    exit 1
fi

if [ -z "$TOKEN" ]; then
    echo "❌ No token provided. Generate one with:"
    echo "   ./scripts/dev_token.sh > token.txt"
    exit 1
fi

echo "🧠 Generating AI recommendations for zone $ZONE_ID..."
[ -n "$CONTEXT" ] && echo "Context: $CONTEXT"
echo ""

# Prepare the request payload
if [ -n "$CONTEXT" ]; then
    PAYLOAD="{
        \"zone_id\": \"$ZONE_ID\",
        \"context\": \"$CONTEXT\"
    }"
else
    PAYLOAD="{
        \"zone_id\": \"$ZONE_ID\"
    }"
fi

RESPONSE=$(curl -s -X POST "$API_URL/recommendations/generate" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

echo "$RESPONSE" | python3 -m json.tool

SUCCESS=$(echo "$RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        print('true')
    else:
        print('false')
except:
    print('false')
")

if [ "$SUCCESS" = "true" ]; then
    echo ""
    echo "✅ Recommendation generation started successfully!"
    echo ""
    echo "💡 The AI is analyzing your zone data in the background."
    echo "   Check for new recommendations in 30-60 seconds with:"
    echo "   curl -H \"Authorization: Bearer \$TOKEN\" \"$API_URL/recommendations?zone_id=$ZONE_ID\" | python3 -m json.tool"
    echo ""
    echo "   Or view in the web UI at:"
    echo "   $API_URL/card?token=\$TOKEN&zone-id=$ZONE_ID"
else
    echo ""
    echo "❌ Failed to generate recommendations"
    exit 1
fi