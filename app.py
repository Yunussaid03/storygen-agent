import streamlit as st
from groq import Groq
import json
import datetime
import urllib.parse
import re

# ==========================================
# 1. TOOLS (The Agent's Actions)
# ==========================================

def save_story_to_library(title, content):
    """Saves the generated story to a local text file."""
    filename = f"{title.replace(' ', '_').lower()}.txt"
    try:
        with open(filename, "w") as file:
            file.write(f"Title: {title}\n")
            file.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            file.write("-" * 20 + "\n")
            file.write(content)
        return f"Successfully saved as {filename}"
    except Exception as e:
        return f"Error saving file: {str(e)}"

def generate_scene_image(image_prompt):
    """Generates an image URL via Pollinations.ai."""
    # Cap the prompt to 200 chars to ensure the URL doesn't break
    short_prompt = image_prompt[:200]
    encoded = urllib.parse.quote(short_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=400&nologo=true"

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
# 3. AGENT EXECUTION LOOP
# ==========================================

if prompt := st.chat_input("Write a cyberpunk story set in Sepang..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing story and visuals..."):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are a master storyteller. Always call 'generate_scene_image' to illustrate your stories. Use the JSON tool API. If you use 'save_story_to_library', provide a title and the full story content."
                        },
                        *st.session_state.messages
                    ],
                    tools=tools,
                    tool_choice="auto"
                )

                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                final_text = response_message.content or ""

                # --- PHASE 1: Handle Official Tool Calls ---
                if tool_calls:
                    for tool_call in tool_calls:
                        f_name = tool_call.function.name
                        f_args = json.loads(tool_call.function.arguments)
                        
                        if f_name == "generate_scene_image":
                            img_url = generate_scene_image(f_args['image_prompt'])
                            st.markdown(f"![Scene]({img_url})")
                            st.session_state.messages.append({"role": "assistant", "content": f"![Scene]({img_url})"})
                        
                        if f_name == "save_story_to_library":
                            result = save_story_to_library(f_args['title'], f_args['content'])
                            st.toast(result, icon="💾")

                # --- PHASE 2: Regex Backdoor for Hallucinations ---
                # This catches cases where Llama types the function call instead of using the API
                hallucinations = re.finditer(r'function=(\w+)(\{.*?\})', final_text)
                for match in hallucinations:
                    f_name, f_json = match.group(1), match.group(2)
                    try:
                        args = json.loads(f_json)
                        if f_name == "generate_scene_image":
                            url = generate_scene_image(args.get('image_prompt', ''))
                            st.markdown(f"![Scene]({url})")
                            st.session_state.messages.append({"role": "assistant", "content": f"![Scene]({url})"})
                        elif f_name == "save_story_to_library":
                            res = save_story_to_library(args.get('title', 'Story'), args.get('content', ''))
                            st.toast(res, icon="💾")
                    except:
                        continue

                # --- PHASE 3: Clean & Display Final Text ---
                # Remove raw function strings from the text display
                clean_text = re.sub(r'function=\w+\{.*?\}', '', final_text).strip()
                if clean_text and clean_text != "0":
                    st.markdown(clean_text)
                    st.session_state.messages.append({"role": "assistant", "content": clean_text})
                elif not tool_calls and not list(re.finditer(r'function=', final_text)):
                    st.write("Generated your visual story!")

            except Exception as e:
                st.error(f"Error: {str(e)}")