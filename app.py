import streamlit as st
from groq import Groq
import json
import datetime
import urllib.parse
import re
import requests
from supabase import create_client, Client

# ==========================================
# SUPABASE CLOUD CONNECTION
# ==========================================
SUPABASE_URL = "https://nizpcbcwytiwdaxrftjo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5penBjYmN3eXRpd2RheHJmdGpvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkwMTc5NjUsImV4cCI6MjA5NDU5Mzk2NX0.VB9dNMaHmI7mf2zQd4cqOdFZ6Tgb6IawPOULv2hJM7Q"

# Initialize the cloud client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 1. TOOLS (The Agent's Actions)
# ==========================================

def save_story_to_library(title, content):
    """Saves the generated story to the Cloud (Supabase) and locally."""
    try:
        # 1. Push to Cloud Database
        supabase.table("stories").insert({
            "title": title, 
            "content": content
        }).execute()
        
        # 2. Save local backup
        filename = f"{title.replace(' ', '_').lower()}.txt"
        with open(filename, "w") as file:
            file.write(f"Title: {title}\nDate: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content}")
            
        return f"Successfully saved '{title}' to the Cloud! ☁️"
    except Exception as e:
        return f"Database Error: {str(e)}"
    
def generate_scene_image(image_prompt):
    """Generates and downloads an image via Pollinations.ai."""
    short_prompt = image_prompt[:200]
    encoded = urllib.parse.quote(short_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=400&nologo=true"
    
    # Create a unique filename based on the current time
    filename = f"scene_{int(datetime.datetime.now().timestamp())}.jpg"
    
    try:
        # The agent physically downloads the image to your VM
        response = requests.get(url, timeout=15)
        with open(filename, "wb") as file:
            file.write(response.content)
        return filename # Return the local file path instead of the URL
    except Exception as e:
        return url # Fallback to the URL if the download fails

# Define the tool schema for Groq
tools = [
    {
        "type": "function",
        "function": {
            "name": "save_story_to_library",
            "description": "Saves a story to a local text file",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_scene_image",
            "description": "Generates a scene image URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_prompt": {"type": "string"}
                },
                "required": ["image_prompt"]
            }
        }
    }
]

# ==========================================
# 2. UI SETUP & INITIALIZATION
# ==========================================

st.set_page_config(page_title="Storygen Agent", page_icon="⚡")
st.title("⚡ Groq Multimodal Story Agent")
st.write("Secure, Regex-Powered AI Agent Prototype")

with st.sidebar:
    api_key = st.text_input("Enter Groq API Key", type="password")
    st.info("Get a key at [console.groq.com](https://console.groq.com/keys)")

if not api_key:
    st.warning("Please enter your Groq API Key to start.")
    st.stop()

client = Groq(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 3. AGENT EXECUTION LOOP (Zero-Crash Manual Parsing)
# ==========================================

if prompt := st.chat_input("Write a cyberpunk story set in Sepang..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing story and visuals..."):
            try:
                # We do NOT pass the tools=tools array here anymore. 
                # This stops Groq from throwing 400 errors when Llama slips up.
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system", 
                            "content": (
                                "You are a master storyteller. You must provide a story and trigger actions.\n"
                                "To generate an image, you MUST include this exact string in your response:\n"
                                "TRIGGER_IMAGE: [Your visual prompt here]\n\n"
                                "To save the story, you MUST include this exact string at the end:\n"
                                "TRIGGER_SAVE: [Story Title] | [Full Story Content]\n\n"
                                "Keep the story text concise (2-3 sentences)."
                            )
                        },
                        *st.session_state.messages
                    ]
                )

                final_text = response.choices[0].message.content or ""

                # --- 1. Intercept Image Trigger ---
                image_match = re.search(r'TRIGGER_IMAGE:\s*(.*)', final_text)
                if image_match:
                    # Extract the prompt up to the next newline or end of string
                    img_prompt = image_match.group(1).split('\n')[0].strip()
                    img_url = generate_scene_image(img_prompt)
                    st.image(img_url, caption="Generated Scene")
                    st.session_state.messages.append({"role": "assistant", "content": f"📁 Local Image Saved: {img_url}"})

                # --- 2. Intercept Save Trigger ---
                save_match = re.search(r'TRIGGER_SAVE:\s*(.*?)\s*\|\s*(.*)', final_text, re.DOTALL)
                if save_match:
                    title = save_match.group(1).strip()
                    content = save_match.group(2).strip()
                    result = save_story_to_library(title, content)
                    st.toast(result, icon="💾")

                # --- 3. Clean up UI Display Text ---
                # Remove the ugly trigger codes so the user only sees a clean story
                clean_text = re.sub(r'TRIGGER_IMAGE:.*', '', final_text)
                clean_text = re.sub(r'TRIGGER_SAVE:.*', '', clean_text, flags=re.DOTALL).strip()
                
                if clean_text:
                    st.markdown(clean_text)
                    st.session_state.messages.append({"role": "assistant", "content": clean_text})

            except Exception as e:
                st.error(f"Execution Error: {str(e)}")