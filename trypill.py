from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import googleapiclient.discovery
import datetime
import streamlit as st
import io
from PIL import Image
import os

# Scopes required for the Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Authenticate and get the Google Calendar service
def get_calendar_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
    return service

# Function to create a reminder event in Google Calendar
def create_reminder_event(service, pill_name, reminder_time):
    event = {
        'summary': f'Take {pill_name}',
        'description': f'Reminder to take {pill_name} as prescribed.',
        'start': {
            'dateTime': reminder_time.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': (reminder_time + datetime.timedelta(minutes=15)).isoformat(),
            'timeZone': 'UTC',
        },
    }
    
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event

# Mock function to identify medicine from image
def identify_medicine_from_image(image):
    # This is a mock function. In real implementation, you would use ML model or API.
    # For example, this can return different pill names based on color/shape/etc.
    return "Aspirin"  # Mock pill name for demonstration

# Streamlit app to upload image and set reminders
def main():
    st.title("Pill Reminder System")
    
    # Upload an image file
    uploaded_file = st.file_uploader("Upload a picture of the medicine (pill or bottle)", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        # Display the uploaded image
        img = Image.open(uploaded_file)
        st.image(img, caption='Uploaded Medicine Image', use_column_width=True)
        
        # Identify the medicine from the image (mock implementation)
        pill_name = identify_medicine_from_image(img)
        st.write(f"Identified medicine: **{pill_name}**")
        
        # User input for the reminder time
        reminder_time = st.time_input("Set the time to take the pill", datetime.time(9, 0))
        reminder_date = st.date_input("Set the date for the reminder", datetime.date.today())
        
        # Combine date and time for the reminder event
        reminder_datetime = datetime.datetime.combine(reminder_date, reminder_time)
        
        # Button to create the reminder
        if st.button("Set Pill Reminder"):
            # Get the Google Calendar service
            service = get_calendar_service()
            
            # Create the reminder event
            event = create_reminder_event(service, pill_name, reminder_datetime)
            st.success(f"Pill reminder created successfully! [View Event]({event.get('htmlLink')})")
    
if __name__ == "__main__":
    main()
