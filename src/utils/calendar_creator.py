"""
Google Calendar Meeting Creator for LangGraph Studio
"""
import os
from datetime import datetime, timedelta, UTC
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleCalendarMeetingCreator:
    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        """
        Initialize the Google Calendar Meeting Creator.

        Args:
            credentials_file (str): Path to the OAuth2 credentials JSON file
            token_file (str): Path to store the access token
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Handle OAuth2 authentication and build the Calendar service."""
        creds = None

        # Load existing token if available
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)

        # If there are no valid credentials available, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Credentials file '{self.credentials_file}' not found!")

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        # Build the Calendar service
        self.service = build('calendar', 'v3', credentials=creds)
        print("Successfully authenticated with Google Calendar API!")

    def create_meeting(self, title, description="", start_time=None, end_time=None,
                       attendees=None, location="", timezone='UTC'):
        """Create a new calendar meeting/event."""
        try:
            # Set default times if not provided (1 hour from now)
            if start_time is None:
                start_time = datetime.now(UTC) + timedelta(hours=1)
            if end_time is None:
                end_time = start_time + timedelta(hours=1)

            # Ensure datetime objects are timezone-aware
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=UTC)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=UTC)

            # Format attendees
            attendee_list = []
            if attendees:
                attendee_list = [{'email': email} for email in attendees]

            # Create the event body
            event = {
                'summary': title,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                },
                'attendees': attendee_list,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 10},  # 10 minutes before
                    ],
                },
            }

            # Create the event
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendNotifications=True  # Send email invitations
            ).execute()

            print(f"Meeting created successfully!")
            print(f"Event ID: {created_event['id']}")
            print(f"Meeting Link: {created_event.get('htmlLink')}")

            return created_event

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def create_meeting_with_google_meet(self, title, description="", start_time=None,
                                        end_time=None, attendees=None, timezone='UTC'):
        """Create a meeting with Google Meet video conferencing."""
        try:
            # Set default times if not provided
            if start_time is None:
                start_time = datetime.now(UTC) + timedelta(hours=1)
            if end_time is None:
                end_time = start_time + timedelta(hours=1)

            # Ensure datetime objects are timezone-aware
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=UTC)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=UTC)

            # Format attendees
            attendee_list = []
            if attendees:
                attendee_list = [{'email': email} for email in attendees]

            # Create the event body with Google Meet
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                },
                'attendees': attendee_list,
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meet-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }

            # Create the event with conferenceDataVersion=1 to enable Google Meet
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendNotifications=True
            ).execute()

            print(f"Meeting with Google Meet created successfully!")
            print(f"Event ID: {created_event['id']}")
            print(f"Meeting Link: {created_event.get('htmlLink')}")

            # Extract Google Meet link if available
            if 'conferenceData' in created_event:
                meet_link = created_event['conferenceData'].get('entryPoints', [{}])[0].get('uri')
                if meet_link:
                    print(f"Google Meet Link: {meet_link}")

            return created_event

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def list_upcoming_events(self, max_results=10):
        """List upcoming events from the calendar."""
        try:
            now = datetime.now(UTC).isoformat()
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            if not events:
                print('No upcoming events found.')
                return []

            print(f'Upcoming {len(events)} events:')
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(f"- {event['summary']} ({start})")

            return events

        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def delete_event(self, event_id):
        """Delete a calendar event."""
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            print(f"Event {event_id} deleted successfully!")
            return True
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False

    def update_event(self, event_id, title=None, description=None, start_time=None,
                     end_time=None, attendees=None, location=None, timezone='UTC'):
        """Update an existing calendar event."""
        try:
            # Get the existing event
            existing_event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()

            # Update only the provided fields
            if title is not None:
                existing_event['summary'] = title
            if description is not None:
                existing_event['description'] = description
            if location is not None:
                existing_event['location'] = location

            if start_time is not None:
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=UTC)
                existing_event['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                }

            if end_time is not None:
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=UTC)
                existing_event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                }

            if attendees is not None:
                existing_event['attendees'] = [{'email': email} for email in attendees]

            # Update the event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=existing_event,
                sendNotifications=True
            ).execute()

            print(f"Event updated successfully!")
            print(f"Event ID: {updated_event['id']}")
            print(f"Meeting Link: {updated_event.get('htmlLink')}")

            return updated_event

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def create_recurring_meeting(self, title, description="", start_time=None, end_time=None,
                                 attendees=None, location="", timezone='UTC', recurrence_rule="WEEKLY"):
        """Create a recurring calendar meeting/event."""
        try:
            # Set default times if not provided (1 hour from now)
            if start_time is None:
                start_time = datetime.now(UTC) + timedelta(hours=1)
            if end_time is None:
                end_time = start_time + timedelta(hours=1)

            # Ensure datetime objects are timezone-aware
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=UTC)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=UTC)

            # Format attendees
            attendee_list = []
            if attendees:
                attendee_list = [{'email': email} for email in attendees]

            # Create recurrence rules
            recurrence_rules = [f"RRULE:FREQ={recurrence_rule.upper()}"]

            # Create the event body
            event = {
                'summary': title,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                },
                'attendees': attendee_list,
                'recurrence': recurrence_rules,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 10},  # 10 minutes before
                    ],
                },
            }

            # Create the event
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendNotifications=True  # Send email invitations
            ).execute()

            print(f"Recurring meeting created successfully!")
            print(f"Event ID: {created_event['id']}")
            print(f"Meeting Link: {created_event.get('htmlLink')}")
            print(f"Recurrence: {recurrence_rule}")

            return created_event

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None