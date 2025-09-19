#!/bin/bash

# Apply a price change
# Usage: ./scripts/apply.sh <change_id> [force] [token]

set -e

CHANGE_ID="$1"
FORCE="${2:-false}"
TOKEN="${3:-$(cat token.txt 2>/dev/null || echo '')}"
API_URL="${API_URL:-http://localhost:8088}"

if [ -z "$CHANGE_ID" ]; then
    echo "Usage: $0 <change_id> [force] [token]"
    echo ""
    echo "Examples:"
    echo "  $0 550e8400-e29b-41d4-a716-446655440000"
    echo "  $0 550e8400-e29b-41d4-a716-446655440000 true"
    echo "  $0 550e8400-e29b-41d4-a716-446655440000 false \$(./scripts/dev_token.sh)"
    echo ""
    echo "Parameters:"
    echo "  change_id: UUID of the price change to apply"
    echo "  force: Skip additional guardrail checks (default: false)"
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

echo "⚡ Applying price change $CHANGE_ID..."
[ "$FORCE" = "true" ] && echo "⚠️  Force mode enabled - bypassing additional guardrails"
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
        print(f'Price change: \${data.get(\"prev_price\", 0):.2f} → \${data[\"new_price\"]:.2f}')
        if data.get('change_pct'):
            change_pct = data['change_pct'] * 100
            print(f'Change: {change_pct:+.1f}%')
        print(f'Status: {data[\"status\"]}')
        print('')
        if data['status'] != 'pending':
            print(f'⚠️  Warning: Change status is \"{data[\"status\"]}\", not \"pending\"')
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

# Confirm application (unless in automation)
if [ -t 0 ] && [ "$FORCE" != "true" ]; then
    echo -n "Apply this price change? [y/N] "
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "❌ Price change application cancelled"
        exit 0
    fi
fi

echo "🚀 Applying price change..."

RESPONSE=$(curl -s -X POST "$API_URL/changes/apply" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"change_id\": \"$CHANGE_ID\",
        \"force\": $FORCE
    }")

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
    echo "✅ Price change applied successfully!"
    echo ""
    echo "💡 View updated changes with:"
    echo "   curl -H \"Authorization: Bearer \$TOKEN\" \"$API_URL/changes/$CHANGE_ID\" | python3 -m json.tool"
else
    echo ""
    echo "❌ Failed to apply price change"
    exit 1
fi