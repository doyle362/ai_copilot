// Simple test script to verify the general chat API flow
const API_BASE_URL = 'http://localhost:8080';
const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcHAubHZscGFya2luZy5jb20iLCJzdWIiOiJkZXYtdXNlciIsIm9yZ19pZCI6Im9yZy1kZW1vIiwicm9sZXMiOlsidmlld2VyIiwiYXBwcm92ZXIiXSwiem9uZV9pZHMiOlsiei02OTcyMiIsInotNjk3MDUiLCJ6LTY5NzEwIiwiei02OTcwMyIsInotMTEwIl0sImlhdCI6MTc1ODIyMzQ0MywiZXhwIjoxNzU4MjMwNjQzfQ.9V04vYEYNmUxN-FXXPv0Auk8xSNCjuwOzozPlcehM_E';

async function testChatFlow() {
  console.log('Testing chat flow...');

  try {
    // 1. Create general thread
    console.log('1. Creating general thread...');
    const createThreadResponse = await fetch(`${API_BASE_URL}/threads/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        thread_type: 'general'
      })
    });

    const threadData = await createThreadResponse.json();
    console.log('Thread creation response:', threadData);
    const threadId = threadData.id;

    // 2. Add user message
    console.log('2. Adding user message...');
    const userMessage = 'How many transactions do we usually get on Friday evenings?';
    const userMessageResponse = await fetch(`${API_BASE_URL}/threads/${threadId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        role: 'user',
        content: userMessage
      })
    });

    const userMessageData = await userMessageResponse.json();
    console.log('User message response:', userMessageData);

    // 3. Test analytics API
    console.log('3. Testing analytics API...');
    const analyticsResponse = await fetch(`${API_BASE_URL}/analytics/session-counts?time_filter=friday_evening`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const analyticsData = await analyticsResponse.json();
    console.log('Analytics response:', analyticsData);

    // 4. Generate AI response with real data
    console.log('4. Generating AI response...');
    if (analyticsData.success && analyticsData.data) {
      const sessions = analyticsData.data.sessions;
      const total = analyticsData.data.total_sessions;

      const zoneBreakdown = sessions.map(s => `• z-${s.zone}: ${s.session_count} sessions`).join('\n');

      const aiResponse = `Friday evenings see **${total} total sessions** across all zones:

${zoneBreakdown}

This is historical data from actual transactions. Need more detail on any specific zone or time period?`;

      console.log('Generated AI response:', aiResponse);

      // 5. Add AI message
      console.log('5. Adding AI message...');
      const aiMessageResponse = await fetch(`${API_BASE_URL}/threads/${threadId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          role: 'ai',
          content: aiResponse
        })
      });

      const aiMessageData = await aiMessageResponse.json();
      console.log('AI message response:', aiMessageData);

      console.log('✅ Test completed successfully!');
    } else {
      console.log('❌ Analytics API failed:', analyticsData);
    }

  } catch (error) {
    console.error('❌ Test failed:', error);
  }
}

testChatFlow();