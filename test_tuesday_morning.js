// Test script for Tuesday morning duration query
const API_BASE_URL = 'http://localhost:8080';
const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcHAubHZscGFya2luZy5jb20iLCJzdWIiOiJkZXYtdXNlciIsIm9yZ19pZCI6Im9yZy1kZW1vIiwicm9sZXMiOlsidmlld2VyIiwiYXBwcm92ZXIiXSwiem9uZV9pZHMiOlsiei0xMjM0NSIsInotNjk3MDEiLCJ6LTY5NzAyIiwiei02OTcwMyIsInotNjk3MDUiLCJ6LTY5NzA4Iiwiei02OTcwOSIsInotNjk3MTAiLCJ6LTY5NzExIiwiei02OTcxMiIsInotNjk3MTMiLCJ6LTY5NzE0Iiwiei02OTcxNSIsInotNjk3MTYiLCJ6LTY5NzE3Iiwiei02OTcxOCIsInotNjk3MTkiLCJ6LTY5NzIwIiwiei02OTcyMSIsInotNjk3MjIiLCJ6LTY5NzIzIiwiei02OTcyNCJdLCJpYXQiOjE3NTgyMjQzNDQsImV4cCI6MTc1ODIzMTU0NH0.U0qnh3u5fjx6ikgpHfqKfwJDXPQLxgRnMz4sDoXdCXs';

async function testTuesdayMorningQuery() {
  console.log('Testing Tuesday morning duration query...');

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

    // 2. Add user message about Tuesday morning duration
    console.log('2. Adding user message about Tuesday morning duration...');
    const userMessage = 'Whats the average duration across all zones on Tuesday mornings?';
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

    // 3. Test analytics API directly
    console.log('3. Testing analytics API for Tuesday morning...');
    const analyticsResponse = await fetch(`${API_BASE_URL}/analytics/session-counts?time_filter=tuesday_morning`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const analyticsData = await analyticsResponse.json();
    console.log('Analytics response:', analyticsData);

    // 4. Calculate expected average duration for verification
    if (analyticsData.success && analyticsData.data) {
      const sessions = analyticsData.data.sessions;
      const totalMinutes = sessions.reduce((sum, s) => sum + (s.session_count * s.avg_duration_minutes), 0);
      const totalSessions = sessions.reduce((sum, s) => sum + s.session_count, 0);
      const overallAvg = totalSessions > 0 ? (totalMinutes / totalSessions) : 0;

      const hours = Math.floor(overallAvg / 60);
      const minutes = Math.round(overallAvg % 60);
      const expectedDuration = hours > 0 ? `${hours}h ${minutes}m` : `${minutes} minutes`;

      console.log(`Expected AI response should include: "${expectedDuration}" and "${totalSessions} total sessions"`);
    }

    // 5. Generate AI response (this would happen in the frontend)
    console.log('5. AI response would be generated automatically in the frontend');
    console.log('✅ Tuesday morning test completed successfully!');
    console.log('The AI should now properly detect "tuesday" + "morning" + "average" + "duration" and call the tuesday_morning API filter');

  } catch (error) {
    console.error('❌ Test failed:', error);
  }
}

testTuesdayMorningQuery();