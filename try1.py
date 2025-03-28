import google.generativeai as genai
import streamlit as st
from pathlib import Path
import io
from docx import Document
from PIL import Image
import fitz  # PyMuPDF to convert PDFs to images
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import googleapiclient.discovery
import datetime
import os

# Google Calendar API Scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")
load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=api_key)

# Google Calendar authentication
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
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
    return service

def initialize_model():
    generation_config = {"temperature": 0.9}
    return genai.GenerativeModel("gemini-1.5-flash", generation_config=generation_config)

def generate_content(model, image_path, prompts, user_prompts):
    image_part = {"mime_type": "image/jpeg", "data": image_path.getvalue()}
    results = []
    for idx, prompt_text in enumerate(prompts):
        prompt_parts = [prompt_text, image_part]
        response = model.generate_content(prompt_parts)
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                text_part = candidate.content.parts[0]
                if text_part.text:
                    results.append(f"Prompt: {user_prompts[idx]}\nDescription:\n{text_part.text}\n")
                else:
                    results.append(f"Prompt: {user_prompts[idx]}\nDescription: No valid content generated.\n")
            else:
                results.append(f"Prompt: {user_prompts[idx]}\nDescription: No content parts found.\n")
        else:
            results.append(f"Prompt: {user_prompts[idx]}\nDescription: No candidates found.\n")
    return results

# Function to display results with prompt and description
def display_results(results):
    st.write("Medical Insights:")
    for description in results:
        # Separate the prompt and description for better readability
        if "Prompt:" in description:
            prompt_start = description.index("Prompt:")
            description_part = description[prompt_start:].replace("Prompt:", "")
            description_cleaned = description_part.split("Description:", 1)

            # Display the prompt (only the user prompt) on the next line for clarity
            st.write(f"**Prompt**: {description_cleaned[0].strip()}")
            st.write(f"**Description**: {description_cleaned[1].strip()}")
        else:
            st.write(description)

# Function to convert PDF pages to images using PyMuPDF (fitz)
def pdf_to_images(pdf_file):
    images = []
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)  # Get the page
        pix = page.get_pixmap()  # Render the page to an image (Pixmap)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # Convert to PIL Image
        
        img_io = io.BytesIO()
        img.save(img_io, format="JPEG")  # Save as JPEG to BytesIO
        img_io.seek(0)
        images.append(img_io)
    
    return images

def create_reminder_event(service, description, reminder_time):
    event = {
        'summary': 'Medical Insight Reminder',
        'description': description,
        'start': {'dateTime': reminder_time.isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (reminder_time + datetime.timedelta(minutes=15)).isoformat(), 'timeZone': 'UTC'},
    }
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event

# Streamlit app
def main():
    # Initialize session state for prompts and results
    if "prompts" not in st.session_state:
        st.session_state.prompts = ""
    if "results" not in st.session_state:
        st.session_state.results = []
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "show_calendar_inputs" not in st.session_state:
        st.session_state.show_calendar_inputs = False

    # Hidden predefined prompt for medical analysis (this will not be shown to the user)
    predefined_prompt = (
        "extract the name of the medicine given and describe the drug used for"
    )

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Choose Functionality", ["Upload Images", "Upload PDF", "History"])

    if page == "Upload Images":
        st.title("Aider Drug reminder -- upload your tablet or prescription we remind you!")

        # Upload an image file
        uploaded_file = st.file_uploader("Choose a medical scan (X-ray, CT, MRI)", type=["jpg", "jpeg", "png"])

        if uploaded_file is not None:
            st.session_state.uploaded_file = uploaded_file
            # Save the uploaded image to a BytesIO object
            img_io = io.BytesIO(uploaded_file.getvalue())
            
            # Initialize the model
            model = initialize_model()
            
            # Input for multiple prompts
            st.session_state.prompts = st.text_area(
                "Enter prompts (optional):",
                value=st.session_state.prompts
            )
            
            # Button to generate content
            if st.button("Generate Description"):
                # Split user prompts into a list (these will be displayed)
                user_prompts = [prompt.strip() for prompt in st.session_state.prompts.split('\n') if prompt.strip()]
                
                # Use both the predefined prompt and the user prompt for generation
                prompts = [predefined_prompt] + user_prompts

                st.session_state.results = generate_content(model, img_io, prompts, ["Predefined Medical Prompt"] + user_prompts)

                # Save to history
                st.session_state.history.append({
                    "image": uploaded_file,
                    "results": st.session_state.results
                })

        # Display the uploaded image and previously generated results
        if st.session_state.uploaded_file and st.session_state.results:
            st.image(st.session_state.uploaded_file, caption='Uploaded Medical Scan.', use_column_width=True)
            display_results(st.session_state.results)

            # Create a Word document from the results and provide a download link

        # Set the reminder after clicking 'Set Reminder for Generated Description'
        if st.button("Set Reminder for Generated Description"):
            st.session_state.show_calendar_inputs = True

        # Show date and time inputs after the button is clicked
        if st.session_state.show_calendar_inputs:
            reminder_time = st.time_input("Set the time for the reminder", datetime.time(9, 0))
            reminder_date = st.date_input("Set the date for the reminder", datetime.date.today())
            reminder_datetime = datetime.datetime.combine(reminder_date, reminder_time)

            if st.button("Create Calendar Event"):
                service = get_calendar_service()
                if st.session_state.results:
                    description = st.session_state.results[0]  # Take the first generated result
                    event = create_reminder_event(service, description, reminder_datetime)
                    st.success(f"Reminder set! [View Event]({event.get('htmlLink')})")

    elif page == "Upload PDF":
        st.title("Aider Drug reminder -- upload your tablet or prescription we remind you!")

        # Upload a PDF file
        uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

        if uploaded_file is not None:
            st.session_state.uploaded_file = uploaded_file
            # Convert PDF to images
            images = pdf_to_images(uploaded_file)

            # Initialize the model
            model = initialize_model()

            # Input for multiple prompts
            st.session_state.prompts = st.text_area(
                "Enter prompts (optional):",
                value=st.session_state.prompts
            )

            # Button to generate content
            if st.button("Generate Description"):
                # Split user prompts into a list (these will be displayed)
                user_prompts = [prompt.strip() for prompt in st.session_state.prompts.split('\n') if prompt.strip()]
                
                # Use both the predefined prompt and the user prompt for generation
                prompts = [predefined_prompt] + user_prompts

                all_results = []
                
                # Process all images (from the PDF)
                for img in images:
                    st.session_state.results = generate_content(model, img, prompts, ["Predefined Medical Prompt"] + user_prompts)
                    all_results.extend(st.session_state.results)

                # Save to history
                st.session_state.history.append({
                    "image": uploaded_file,
                    "results": all_results
                })

            # Display images from PDF
            captions = [f'Page {i+1}' for i in range(len(images))]
            st.image(images, caption=captions, use_column_width=True)

if __name__ == "__main__":
    main()
