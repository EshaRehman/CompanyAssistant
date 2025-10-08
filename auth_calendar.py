from src.utils.calendar_creator import GoogleCalendarMeetingCreator
from datetime import datetime, timedelta

print('🔐 Authenticating with Google Calendar...')
print('This will open a browser window - please login and approve.')

try:
    # This will trigger OAuth flow and save token.json
    calendar = GoogleCalendarMeetingCreator()
    
    # Test by creating a quick event
    test_time = datetime.now() + timedelta(days=1)
    test_end = test_time + timedelta(minutes=30)
    
    print('\n Authentication successful!')
    print(f' Token saved to: token.json')
    print('\n Calendar integration ready for LangGraph Studio!')
    
except Exception as e:
    print(f' Error: {e}')
