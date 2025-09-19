#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8080}"
echo "=== Level Analyst Quick Demo ==="
echo "API URL: $API_URL"

# Step 1: Seed demo data
echo "🌱 Step 1: Seeding demo data..."
if ! bash scripts/seed_demo.sh; then
    echo "❌ ERROR: Demo data seeding failed"
    exit 1
fi
echo "✅ Demo data seeded successfully"

# Step 2: Generate dev token if possible
echo "🔑 Step 2: Setting up authentication..."
if [[ -x "scripts/dev_token.sh" ]]; then
    echo "   Generating dev token..."
    TOKEN=$(bash scripts/dev_token.sh 2>/dev/null | grep -o 'eyJ[A-Za-z0-9._-]*' | head -1 || echo "")
    if [[ -n "$TOKEN" ]]; then
        echo "✓ Dev token generated"
    else
        echo "⚠️  Dev token generation failed, using default"
        TOKEN="dev-token"
    fi
else
    echo "⚠️  scripts/dev_token.sh not found, using default token"
    echo "   Create scripts/dev_token.sh to generate proper JWT tokens"
    TOKEN="dev-token"
fi

# Step 3: Generate recommendations
echo "🤖 Step 3: Generating AI recommendations..."

# Try using gen_recs.sh if it exists
if [[ -x "scripts/gen_recs.sh" ]]; then
    echo "   Using scripts/gen_recs.sh..."
    if bash scripts/gen_recs.sh z-110 2>/dev/null; then
        echo "✓ Recommendations generated via gen_recs.sh"
    else
        echo "⚠️  gen_recs.sh failed, trying direct API call..."
    fi
else
    echo "   Making direct API calls..."
fi

# Direct API calls for both zones
for ZONE in "z-110" "z-221"; do
    echo "   Generating recommendations for zone: $ZONE"

    RESPONSE=$(curl -s -X POST "$API_URL/recommendations/generate" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"zone_id\": \"$ZONE\", \"context\": \"Demo: optimize pricing based on recent transaction patterns\"}" \
        2>/dev/null || echo "{\"error\": \"API call failed\"}")

    if echo "$RESPONSE" | grep -q '"success".*true'; then
        # Extract key info from successful response
        REC_ID=$(echo "$RESPONSE" | grep -o '"id":[^,]*' | head -1 | cut -d: -f2 | tr -d ' "')
        CONFIDENCE=$(echo "$RESPONSE" | grep -o '"confidence":[^,}]*' | head -1 | cut -d: -f2 | tr -d ' ')
        echo "     ✓ Generated recommendation $REC_ID (confidence: $CONFIDENCE) for $ZONE"
    else
        echo "     ⚠️  Failed to generate recommendation for $ZONE"
        echo "        Response: $(echo "$RESPONSE" | head -c 100)..."
    fi
done

# Step 4: Show recommendations summary
echo "📊 Step 4: Recommendations summary..."
RECS_RESPONSE=$(curl -s "$API_URL/recommendations/" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "{}")

if echo "$RECS_RESPONSE" | grep -q '"success".*true'; then
    echo "$RECS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    recs = data.get('data', [])
    print(f'   Total recommendations: {len(recs)}')
    for rec in recs[-3:]:  # Show last 3
        zone = rec.get('zone_id', 'unknown')
        confidence = rec.get('confidence', 0)
        rec_type = rec.get('type', 'unknown')
        print(f'   • {zone}: {rec_type} (confidence: {confidence:.2f})')
except:
    print('   Could not parse recommendations response')
" 2>/dev/null || echo "   Could not parse recommendations"
else
    echo "   ⚠️  Could not fetch recommendations summary"
fi

# Step 5: Database diagnostics
echo "🔍 Step 5: Database connectivity check..."
DIAG_RESPONSE=$(curl -s "$API_URL/diag/db" 2>/dev/null || echo "{}")
if command -v jq >/dev/null 2>&1; then
    echo "$DIAG_RESPONSE" | jq -r '
        "   DB Connection: " + (if .psycopg_connect.ok then "✓ OK" else "❌ Failed" end) +
        " (" + (.psycopg_connect.roundtrip_ms // 0 | tostring) + "ms)" +
        if .hints and (.hints | length > 0) then "\n   Hints: " + (.hints | join(", ")) else "" end
    ' 2>/dev/null || echo "$DIAG_RESPONSE"
else
    echo "$DIAG_RESPONSE"
fi

# Step 6: Next steps
echo ""
echo "🎉 Quick demo completed!"
echo ""
echo "Next steps:"
echo "  📖 API Documentation: $API_URL/docs"
echo "  🎨 Web Card Interface: $API_URL/card/"
echo "  🔧 Health Check: $API_URL/health/"
echo "  📊 Diagnostics: $API_URL/diag/db"
echo ""
echo "Explore the API:"
echo "  • GET  $API_URL/insights/ - View insights"
echo "  • GET  $API_URL/recommendations/ - View recommendations"
echo "  • POST $API_URL/threads/ - Start discussion threads"
echo "  • POST $API_URL/memories/upsert - Save feedback as memories"
echo ""
echo "🔑 Using token: ${TOKEN:0:20}..."
echo ""
echo "Happy analyzing! 🚀"

exit 0