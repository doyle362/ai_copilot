#!/bin/bash

# Revert a price change
# Usage: ./scripts/revert.sh <change_id> [reason] [token]

set -e

CHANGE_ID="$1"
REASON="$2"
TOKEN="${3:-$(cat token.txt 2>/dev/null || echo '')}"
API_URL="${API_URL:-http://localhost:8088}"

if [ -z "$CHANGE_ID" ]; then
    echo "Usage: $0 <change_id> [reason] [token]"
    echo ""
    echo "Examples:"
    echo "  $0 550e8400-e29b-41d4-a716-446655440000"
    echo "  $0 550e8400-e29b-41d4-a716-446655440000 \"Customer complaints\""
    echo "  $0 550e8400-e29b-41d4-a716-446655440000 \"\" \$(./scripts/dev_token.sh)"
    echo ""
    echo "Parameters:"
    echo "  change_id: UUID of the price change to revert"
    echo "  reason: Optional reason for the reversion"
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

echo "↩️  Reverting price change $CHANGE_ID..."
[ -n "$REASON" ] && echo "Reason: $REASON"
echo ""

# First, get the change details
echo "📋 Retrieving change details..."
CHANGE_DETAILS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/changes/$CHANGE_ID")

echo "$CHANGE_DETAILS" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if 'zone_id' in data:
        print(f'Zone: {data[\"zone_id\"]}')
        print(f'Current price: \${data[\"new_price\"]:.2f}')
        if data.get('prev_price'):
            print(f'Will revert to: \${data[\"prev_price\"]:.2f}')
        print(f'Status: {data[\"status\"]}')
        print('')
        if data['status'] != 'applied':
            print(f'⚠️  Warning: Change status is \"{data[\"status\"]}\", not \"applied\"')
            if data['status'] == 'pending':
                print('💡 Hint: Cancel pending changes instead of reverting')
            print('')
    else:
        print('❌ Error: Invalid change data')
        sys.exit(1)
except:
    print('❌ Error: Failed to parse change details')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

# Confirm reversion (unless in automation)
if [ -t 0 ]; then
    echo -n "Revert this price change? [y/N] "
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "❌ Price change reversion cancelled"
        exit 0
    fi
fi

echo "🔄 Reverting price change..."

# Prepare the request payload
if [ -n "$REASON" ]; then
    PAYLOAD="{
        \"change_id\": \"$CHANGE_ID\",
        \"reason\": \"$REASON\"
    }"
else
    PAYLOAD="{
        \"change_id\": \"$CHANGE_ID\"
    }"
fi

RESPONSE=$(curl -s -X POST "$API_URL/changes/revert" \
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
    echo "✅ Price change reverted successfully!"
    echo ""
    echo "💡 View updated changes with:"
    echo "   curl -H \"Authorization: Bearer \$TOKEN\" \"$API_URL/changes/$CHANGE_ID\" | python3 -m json.tool"
else
    echo ""
    echo "❌ Failed to revert price change"
    exit 1
fi