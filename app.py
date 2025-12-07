import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Mood Companion", page_icon="🤖")
st.title("🤖 Your AI Companion")

# 1. Setup Database Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Setup AI (Gemini)
# We retrieve the API key from Streamlit secrets (configured in Step 4)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
else:
    st.error("API Key missing. Please set it in Streamlit Secrets.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- HELPER FUNCTIONS ---
def analyze_sentiment(text):
    """Asks the AI to classify the user's text"""
    try:
        prompt = f"Analyze the sentiment of this text: '{text}'. Return only one word: 'Happy', 'Sad', 'Angry', or 'Neutral'."
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Neutral"

def save_mood(mood, note=""):
    """Saves mood data to Google Sheets"""
    try:
        # Fetch existing data (cache_ttl=0 ensures we see updates instantly)
        existing_data = conn.read(worksheet="Sheet1", usecols=[0, 1, 2], ttl=0)
        
        # Create new entry
        new_entry = pd.DataFrame([{
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Mood": mood,
            "Note": note
        }])
        
        # Append and update
        updated_data = pd.concat([existing_data, new_entry], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_data)
        st.success(f"Logged feeling: {mood}")
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- APP INTERFACE ---

# 1. Daily Mood Tracker (Sidebar)
with st.sidebar:
    st.header("📝 Daily Check-in")
    st.write("How was your day overall?")
    
    col1, col2, col3 = st.columns(3)
    if col1.button("😊"):
        save_mood("Happy", "User rated day as Happy")
    if col2.button("😐"):
        save_mood("Neutral", "User rated day as Neutral")
    if col3.button("😢"):
        save_mood("Sad", "User rated day as Sad")
        
    st.divider()
    st.write("📊 *Data is stored securely in your Google Sheet.*")

# 2. Chat Interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Tell me what's on your mind..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Analyze Sentiment
    sentiment = analyze_sentiment(prompt)
    
    # Adjust AI Persona based on sentiment
    system_instruction = ""
    if "Sad" in sentiment or "Angry" in sentiment:
        system_instruction = "The user is feeling down. Be empathetic, warm, and supportive. Keep responses short and comforting."
    elif "Happy" in sentiment:
        system_instruction = "The user is happy! Be energetic, celebrate with them, and use emojis."
    else:
        system_instruction = "Be a helpful, friendly, and calm AI companion."

    # Generate Response
    full_prompt = f"System Instruction: {system_instruction}\n\nUser Message: {prompt}"
    try:
        response = model.generate_content(full_prompt)
        bot_reply = response.text
    except Exception as e:
        bot_reply = "I'm having trouble connecting to my brain right now. Try again?"

    # Display Response
    with st.chat_message("assistant"):
        st.markdown(bot_reply)
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})