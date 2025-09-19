#!/bin/bash

# Start a discussion thread for an insight
# Usage: ./scripts/thread_start.sh <insight_id> <zone_id> [token]

set -e

INSIGHT_ID="$1"
ZONE_ID="$2"
TOKEN="${3:-$(cat token.txt 2>/dev/null || echo '')}"
API_URL="${API_URL:-http://localhost:8088}"

if [ -z "$INSIGHT_ID" ] || [ -z "$ZONE_ID" ]; then
    echo "Usage: $0 <insight_id> <zone_id> [token]"
    echo ""
    echo "Examples:"
    echo "  $0 550e8400-e29b-41d4-a716-446655440000 z-110"
    echo "  $0 550e8400-e29b-41d4-a716-446655440000 z-110 \$(./scripts/dev_token.sh)"
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

echo "🧵 Starting discussion thread for insight $INSIGHT_ID in zone $ZONE_ID..."

RESPONSE=$(curl -s -X POST "$API_URL/threads/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"insight_id\": \"$INSIGHT_ID\",
        \"zone_id\": \"$ZONE_ID\"
    }")

echo "$RESPONSE" | python3 -m json.tool

THREAD_ID=$(echo "$RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if 'id' in data:
        print(data['id'])
    else:
        print('Error: No thread ID in response', file=sys.stderr)
        sys.exit(1)
except:
    print('Error: Invalid JSON response', file=sys.stderr)
    sys.exit(1)
")

if [ $? -eq 0 ]; then
    echo "✅ Thread created successfully with ID: $THREAD_ID"
    echo "$THREAD_ID" > thread_id.txt
    echo "💡 Reply to this thread with:"
    echo "   ./scripts/thread_reply.sh $THREAD_ID \"Your message here\""
else
    echo "❌ Failed to create thread"
    exit 1
fi