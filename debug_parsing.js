// Debug the parsing for "Whats the average duration across all zones on wednesday mornings?"

const message = "Whats the average duration across all zones on wednesday mornings?".toLowerCase();

console.log('Message:', message);

// Check data detection
const dataKeywords = ['how many', 'average', 'duration', 'sessions', 'transactions', 'revenue', 'occupancy', 'total', 'stats', 'metrics'];
const requiresData = dataKeywords.some(keyword => message.includes(keyword));

console.log('Data keywords found:', dataKeywords.filter(keyword => message.includes(keyword)));
console.log('Requires data:', requiresData);

// Check data type
let dataType = 'general';
if (message.includes('duration') || message.includes('time')) dataType = 'duration';
else if (message.includes('revenue') || message.includes('money') || message.includes('price')) dataType = 'revenue';
else if (message.includes('occupancy') || message.includes('utilization')) dataType = 'occupancy';
else if (message.includes('sessions') || message.includes('transactions') || message.includes('how many')) dataType = 'sessions';

console.log('Data type:', dataType);

// Check analysis type
let analysisType = 'total';
if (message.includes('average') || message.includes('avg')) analysisType = 'average';
else if (message.includes('breakdown') || message.includes('by zone') || message.includes('each zone')) analysisType = 'breakdown';
else if (message.includes('how many') || message.includes('total')) analysisType = 'total';
else if (message.includes('compare') || message.includes('vs')) analysisType = 'comparison';

console.log('Analysis type:', analysisType);

// Parse time
function parseTimeFromMessage(message) {
  const lowerMessage = message.toLowerCase();

  // Parse day of week
  let dayOfWeek;
  let timeDescription = 'all time periods';

  const dayNames = {
    'sunday': '0', 'monday': '1', 'tuesday': '2', 'wednesday': '3',
    'thursday': '4', 'friday': '5', 'saturday': '6'
  };

  // Find specific day
  for (const [day, num] of Object.entries(dayNames)) {
    if (lowerMessage.includes(day)) {
      dayOfWeek = num;
      timeDescription = day;
      break;
    }
  }

  // Parse time of day
  let hourStart;
  let hourEnd;

  if (lowerMessage.includes('morning')) {
    hourStart = 6;
    hourEnd = 11;
    timeDescription += dayOfWeek ? ' mornings' : 'mornings';
  } else if (lowerMessage.includes('afternoon')) {
    hourStart = 12;
    hourEnd = 17;
    timeDescription += dayOfWeek ? ' afternoons' : 'afternoons';
  } else if (lowerMessage.includes('evening') || lowerMessage.includes('night')) {
    hourStart = 17;
    hourEnd = 21;
    timeDescription += dayOfWeek ? ' evenings' : 'evenings';
  }

  return { dayOfWeek, hourStart, hourEnd, timeDescription };
}

const timeInfo = parseTimeFromMessage(message);
console.log('Time info:', timeInfo);

console.log('\nExpected behavior:');
console.log('- Should detect as data request: YES');
console.log('- Should use duration dataType: YES');
console.log('- Should use average analysisType: YES');
console.log('- Should parse Wednesday morning time: YES');
console.log('- Should call API with day_of_week=3&hour_start=6&hour_end=11');