import requests
import streamlit as st
from datetime import datetime, timedelta
import base64
import time
BACKEND_URL = "https://scheduly-api-backend.onrender.com"


# ---- Page Configuration ----
st.set_page_config(layout="wide", page_title="Scheduly - Booking Assistant", page_icon="🗓️")

# ---- Utility: Convert image to base64 ----
def get_base64_image(image_path): 
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        # Return a placeholder if image not found
        return ""

# ---- Load Avatars ----
user_avatar_b64 = get_base64_image("icons8-user-80.png")
scheduly_avatar_b64 = get_base64_image("schedule.png")

# ---- Session State ----
if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_input" not in st.session_state:
    st.session_state.user_input = ""


# ---- Email Prompt ----

def handle_email_submit():
    email = st.session_state.email_input.strip()
    if email:
        st.session_state.user_email = email

# Show email input only if not already set
if "user_email" not in st.session_state or not st.session_state.user_email:
    st.markdown("""
        <div style='text-align: center; margin-top: 100px;'>
            <h3>Please enter your email to continue</h3>
        </div>
    """, unsafe_allow_html=True)

    st.text_input(
        "Email Address",
        key="email_input",
        on_change=handle_email_submit,
        label_visibility="collapsed"
    )

    st.stop()

# ---- Input Handler ----
def handle_input():
    
    user_input = st.session_state.user_input.strip()
    if user_input:
        st.session_state.messages.append(("You", user_input))
        
        with st.spinner("Processing your request..."):
            try:
                response = requests.post(
                f"{BACKEND_URL}/setresponse",
                json={
                    "message": user_input,
                    "email": st.session_state.user_email
                },
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )

                response.raise_for_status()
                json_response = response.json()
                
                formatted_response = ""
                if isinstance(json_response, dict):
                    for key, value in json_response.items():
                        if key == "status":
                            continue
                        if key == "link":
                            formatted_response += f"{key.upper()} : <a href='{value}'>Click Here To View</a><br>"
                            continue
                        formatted_response += f"{key.upper()} : {value}<br>"
                else:
                    formatted_response = str(json_response)

            except requests.exceptions.Timeout:
                formatted_response = "⚠ Request timed out. Please try again."
            except requests.exceptions.ConnectionError:
                formatted_response = "⚠ Cannot connect to backend server. Please ensure the backend is running."
            except requests.exceptions.HTTPError as e:
                formatted_response = f"⚠ Server error: {e}"
            except requests.exceptions.RequestException as e:
                formatted_response = f"⚠ Request failed: {str(e)}"
            except Exception as e:
                formatted_response = f"⚠ Unexpected error: {str(e)}"

        st.session_state.messages.append(("Assistant", formatted_response))
        st.session_state.user_input = ""

# ---- Custom CSS ----
st.markdown("""<style> ... (your entire CSS block unchanged) ... </style>""", unsafe_allow_html=True)

# ---- Backend Status Check ----
def check_backend_status():
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def format_response(json_response):
    """Format the JSON response into a readable message"""
    try:
        # Check if it's a booking confirmation
        if json_response.get("status") == "confirmed":
            formatted_response = (
                f"✅ **Booking Confirmed!**\n\n"
                f"**Title**: {json_response.get('title', 'Meeting')}\n\n"
                f"**Summary**: {json_response.get('summary', 'No summary provided')}\n\n"
                f"**Start**: {json_response.get('start', 'N/A')}\n\n"
                f"**End**: {json_response.get('end', 'N/A')}"
            )
            if "link" in json_response:
                formatted_response += f"\n\n[View Calendar Event]({json_response['link']})"
                
        elif json_response.get("status") == "conflict":
            formatted_response = (
                f"❌ **Cannot Book: Time Conflict**\n\n"
                f"**Conflicting Event**: {json_response.get('title', 'Unknown')}\n\n"
                f"**Start**: {json_response.get('start', 'N/A')}\n\n"
                f"**End**: {json_response.get('end', 'N/A')}\n\n"
                f"Please choose a different time slot."
            )
            
        elif json_response.get("status") == "error":
            formatted_response = f"⚠️ **Error**: {json_response.get('error', 'Unknown error occurred')}"
            
        else:
            # Generic response formatting
            formatted_response = ""
            if "title" in json_response:
                formatted_response += f"**Title**: {json_response['title']}\n\n"
            if "summary" in json_response:
                formatted_response += f"**Summary**: {json_response['summary']}\n\n"
            if "start" in json_response:
                formatted_response += f"**Start**: {json_response['start']}\n\n"
            if "end" in json_response:
                formatted_response += f"**End**: {json_response['end']}\n\n"
            if "message" in json_response:
                formatted_response += f"**Response**: {json_response['message']}\n\n"
                
            if not formatted_response:
                formatted_response = "Response received but no details available."
                
    except Exception as e:
        formatted_response = f"Error formatting response: {str(e)}"
        
    return formatted_response

# ---- Custom CSS ----
st.markdown("""
<style>
    .block-container {
        padding-top: 3rem;
        padding-left: 2rem;
        padding-right: 2rem;
        min-height: 100vh;
        display: flex;
        flex-direction: column;
    }
    .main-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .conversation-section {
        width: 100%;
        max-width: 600px;
        max-height: 200px;
        overflow-y: auto;
        background: #ebf5fc;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 16px;
        position: relative;
        margin-bottom: 1rem;
    }
    .conversation-section::-webkit-scrollbar {
        width: 6px;
    }
    .conversation-section::-webkit-scrollbar-thumb {
        background-color: #bbb;
        border-radius: 10px;
    }
    .msg-row {
        display: flex;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    .msg-row.you {
        flex-direction: row-reverse;
    }
    .msg-row .avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        margin: 0 0.5rem;
        border: 2px solid #007bff;
        box-shadow: 0 0 4px rgba(0, 123, 255, 0.4);
        background: #f0f0f0;
    }
    .bubble {
        background: white;
        padding: 0.5rem 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.1);
        max-width: 75%;
        word-wrap: break-word;
        color: #2c3e50;
        line-height: 1.4;
        white-space: pre-wrap;
    }
    .bubble.user {
        background: #007bff;
        color: white;
    }
    .bubble.assistant {
        background: #f8f9fa;
        color: #495057;
        border: 1px solid #e9ecef;
    }
    .bubble a {
        color: #007bff;
        text-decoration: none;
        font-weight: 500;
    }
    .bubble.user a {
        color: #b3d9ff;
    }
    .bubble a:hover {
        text-decoration: underline;
    }
    .input-section {
        width: 100%;
        max-width: 600px;
    }
    .input-section input {
        padding-left: 12px !important;
    }
    .status-indicator {
        position: fixed;
        top: 10px;
        right: 10px;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        z-index: 1000;
    }
    .status-online {
        background: #28a745;
        color: white;
    }
    .status-offline {
        background: #dc3545;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ---- Backend Status Check ----
def check_backend_status():
    try:
        response = requests.get(f"{BACKEND_URL}/health/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# ---- Header ----
with st.container():
    col1, col2, col3 = st.columns([0.2, 5, 1])
    with col1:
        if scheduly_avatar_b64:
            st.markdown(f'<img src="data:image/png;base64,{scheduly_avatar_b64}" width="50">', unsafe_allow_html=True)
        else:
            st.markdown("🗓️", unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div style='font-size: 30px; font-family: Times;'>
                <b>Scheduly</b>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        # Backend status indicator
        if check_backend_status():
            st.markdown('<div class="status-indicator status-online">Backend Online</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-indicator status-offline">Backend Offline</div>', unsafe_allow_html=True)

st.markdown('<div style="height: 90px;"></div>', unsafe_allow_html=True)

# ---- Title ----
st.markdown('<div class="main-content">', unsafe_allow_html=True)
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 2rem;'>
                <h2 style='font-size: 2.5rem; font-family: Times; font-weight: 300; color: white;'>
                    Book Your Timeslots Now 
                </h2>
                <p style='font-size: 1.2rem; color: white;'>
                    Simply tell me when you'd like to schedule your meeting
                </p>
            </div>
        """, unsafe_allow_html=True)

# ---- Chat Display ----
if st.session_state.messages:
    conversation_html = ""
    for sender, msg in st.session_state.messages:
        avatar = user_avatar_b64 if sender == "You" else scheduly_avatar_b64
        sender_class = "you" if sender == "You" else "assistant"
        bubble_class = "user" if sender == "You" else "assistant"
        
        # Handle missing avatars
        if not avatar:
            avatar_html = f'<div class="avatar" style="display: flex; align-items: center; justify-content: center; background: #007bff; color: white; font-weight: bold;">{"U" if sender == "You" else "S"}</div>'
        else:
            avatar_html = f'<img src="data:image/png;base64,{avatar}" class="avatar"/>'
            
        conversation_html += f"""
            <div class='msg-row {sender_class}'>
                {avatar_html}
                <div class='bubble {bubble_class}'>{msg}</div>
            </div>
        """
    print("conversation_html = ", conversation_html)

    c1, c2, c3 = st.columns([1.2, 2, 1])
    with c2:
        st.markdown(f"""
            <div class="conversation-section" id="chat-box">
                {conversation_html}
            </div>
        """, unsafe_allow_html=True)
    print("conversation_html = ", conversation_html)

# ---- Input Box ----
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="input-section">', unsafe_allow_html=True)
        st.text_input(
            "",
            placeholder="Type your request (e.g., 'Book a meeting at 4 PM'):",
            key="user_input",
            on_change=handle_input
        ) 
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close main-content
