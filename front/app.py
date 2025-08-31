import streamlit as st
import requests
import re

API_URL = "http://localhost:8000/api/workflow/run_workflow"
SMS_API_URL = "http://localhost:8000/api/notify/send-sms"
WHATSAPP_API_URL = "http://localhost:8000/api/notify/send-whatsapp"
EMAIL_API_URL = "http://localhost:8000/api/notify/send-email"

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def is_valid_phone(phone):
    # Basic E.164 format validation (e.g., +1234567890)
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, phone))

def fetch_data(page=1, page_size=5):
    try:
        response = requests.get(API_URL, params={"page": page, "page_size": page_size})
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch data: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

def send_sms(phone_number, message):
    if not is_valid_phone(phone_number):
        st.error("Invalid phone number format. Use E.164 format (e.g., +1234567890).")
        return
    if not message:
        st.error("Message cannot be empty.")
        return
    try:
        payload = {"to": phone_number, "body": message}
        response = requests.post(SMS_API_URL, json=payload)
        if response.status_code == 200:
            st.success(f"Pitch sent to {phone_number} via SMS!")
        else:
            st.error(f"Failed to send SMS: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Error sending SMS: {str(e)}")

def send_whatsapp(phone_number, message):
    
    if not message:
        st.error("Message cannot be empty.")
        return
    try:
        payload = {"to": phone_number, "body": message}
        response = requests.post(WHATSAPP_API_URL, json=payload)
        if response.status_code == 200:
            st.success(f"Pitch sent to {phone_number} via WhatsApp!")
        else:
            st.error(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Error sending WhatsApp message: {str(e)}")

def send_email(email, subject, message):
    if not is_valid_email(email):
        st.error("Invalid email format.")
        return
    if not subject or not message:
        st.error("Subject and message cannot be empty.")
        return
    try:
        payload = {"to": email, "subject": subject, "body": message}
        response = requests.post(EMAIL_API_URL, json=payload)
        if response.status_code == 200:
            st.success(f"Pitch sent to {email} via email!")
        else:
            st.error(f"Failed to send email: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")

st.title("Client Recommendations UI")

# Sidebar
st.sidebar.title("Settings")
page_size_options = [5, 10, 20]
page_size = st.sidebar.selectbox("Page Size", page_size_options, index=0)

# Session state for current page
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Fetch data
data = fetch_data(st.session_state.current_page, page_size)

if data:
    total_pages = data.get('total_pages', 1)
    st.write(f"Page {data['page']} of {total_pages} | Total Clients: {data['total_clients']}")

    # Pagination buttons
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("Previous") and st.session_state.current_page > 1:
            st.session_state.current_page -= 1
            st.rerun()
    with col3:
        if st.button("Next") and st.session_state.current_page < total_pages:
            st.session_state.current_page += 1
            st.rerun()

    # Display cards
    for item in data['pitchs']:
        client = item['pitch']['client']
        product = item['pitch']['product']
        with st.expander(f"Client: {client} - Product: {product} (Ref: {item['client_ref']})"):
            st.write("**Recommendations:**", item['recommendations'])
            st.write("**Pitch:**", item['pitch']['pitch'])

            # Refine pitch section (simple chat-like interface)
            st.subheader("Discuss and Refine Pitch with LLM")
            chat_key = f"chat_history_{item['client_ref']}"
            if chat_key not in st.session_state:
                st.session_state[chat_key] = []

            # Display chat history
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state[chat_key]:
                    if msg.startswith("User:"):
                        st.chat_message("user").write(msg)
                    else:
                        st.chat_message("assistant").write(msg)

            # Input for refinement
            user_input = st.chat_input("Type your message to refine the pitch...", key=f"chat_input_{item['client_ref']}")
            if user_input:
                # Append user message
                st.session_state[chat_key].append(f"User: {user_input}")
                
                # Simulate LLM response (replace with actual LLM API call if available)
                refined_response = f"LLM: Here's a refined pitch based on your input '{user_input}': [Refined version of the pitch]."
                st.session_state[chat_key].append(refined_response)
                
                st.rerun()

            # Send options
            st.subheader("Send Pitch")
            st.write("Enter contact details to send:")
            
            email = st.text_input("Recipient Email:", key=f"email_{item['client_ref']}")
            if st.button("Send via Email", key=f"email_btn_{item['client_ref']}") and email:
                subject = f"Insurance Pitch for {client} - {product}"
                send_email(email, subject, item['pitch']['pitch'])
            
            whatsapp_num = st.text_input("Recipient WhatsApp Number (e.g., +1234567890):", key=f"whatsapp_{item['client_ref']}")
            if st.button("Send via WhatsApp", key=f"whatsapp_btn_{item['client_ref']}") and whatsapp_num:
                send_whatsapp(whatsapp_num, item['pitch']['pitch'])
            
            sms_num = st.text_input("Recipient SMS Number (e.g., +1234567890):", key=f"sms_{item['client_ref']}")
            if st.button("Send via SMS", key=f"sms_btn_{item['client_ref']}") and sms_num:
                send_sms(sms_num, item['pitch']['pitch'])
else:
    st.warning("No data available or failed to load.")