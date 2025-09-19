#!/bin/bash

# Reply to a discussion thread
# Usage: ./scripts/thread_reply.sh <thread_id> <message> [token]

set -e

THREAD_ID="$1"
MESSAGE="$2"
TOKEN="${3:-$(cat token.txt 2>/dev/null || echo '')}"
API_URL="${API_URL:-http://localhost:8088}"

if [ -z "$THREAD_ID" ] || [ -z "$MESSAGE" ]; then
    echo "Usage: $0 <thread_id> <message> [token]"
    echo ""
    echo "Examples:"
    echo "  $0 123 \"Can you explain why this happened?\""
    echo "  $0 123 \"Generate a recommendation for this\" \$(./scripts/dev_token.sh)"
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

echo "💬 Sending message to thread $THREAD_ID..."
echo "Message: $MESSAGE"
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/threads/$THREAD_ID/messages" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"role\": \"user\",
        \"content\": \"$MESSAGE\"
    }")

echo "$RESPONSE" | python3 -m json.tool

MESSAGE_ID=$(echo "$RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if 'id' in data:
        print(data['id'])
        print('✅ Message sent successfully', file=sys.stderr)
    else:
        print('❌ Error: No message ID in response', file=sys.stderr)
        sys.exit(1)
except:
    print('❌ Error: Invalid JSON response', file=sys.stderr)
    sys.exit(1)
")

if [ $? -eq 0 ]; then
    echo ""
    echo "💡 View the full thread with:"
    echo "   curl -H \"Authorization: Bearer \$TOKEN\" \"$API_URL/threads/$THREAD_ID\" | python3 -m json.tool"
fi