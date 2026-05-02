import streamlit as st
import google.generativeai as genai
import datetime
import urllib.parse

# ==========================================
# 1. DEFINE YOUR TOOLS (The Agent's Actions)
# ==========================================
def save_story_to_library(title: str, content: str) -> str:
    """Saves the generated story to a local text file."""
    filename = f"{title.replace(' ', '_').lower()}.txt"
    with open(filename, "w") as file:
        file.write(f"Title: {title}\n")
        file.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        file.write(content)
        
    st.toast(f"💾 Agent Action: Saved '{title}'!")
    return f"Successfully saved the story as {filename}."

def generate_scene_image(image_prompt: str) -> str:
    """
    Generates an image based on a prompt and returns the image URL.
    The agent should call this to get an image for the story.
    """
    st.toast("🎨 Agent Action: Generating image...")
    encoded_prompt = urllib.parse.quote(image_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=400&nologo=true"
    
    return image_url

# ==========================================
# 2. UI & INITIALIZATION
# ==========================================
st.set_page_config(page_title="Storygen Agent", page_icon="✍️")
st.title("✍️ Multimodal Storygen Agent")
st.write("An end-to-end storyteller that writes, illustrates, and saves its work.")

with st.sidebar:
    api_key = st.text_input("Enter Google AI Studio API Key", type="password")
    st.markdown("[Get your free key here](https://aistudio.google.com/app/apikey)")

if not api_key:
    st.info("Please enter your API Key in the sidebar to start.")
    st.stop()

genai.configure(api_key=api_key)

system_prompt = """
You are a master storyteller and illustrator. 
1. When asked to write a story, you should also generate ONE highly descriptive image prompt based on the scene.
2. Use the 'generate_scene_image' tool with that prompt.
3. The tool will return a URL. You MUST display the image in your final response using Markdown formatting: ![Scene](URL)
4. If the user asks you to save the story, use the 'save_story_to_library' tool.
"""

if "chat_session" not in st.session_state:
    model = genai.GenerativeModel(
        model_name='models/gemini-3.1-flash-image-preview',
        system_instruction=system_prompt,
        tools=[save_story_to_library, generate_scene_image] 
    )
    st.session_state.chat_session = model.start_chat(enable_automatic_function_calling=True)

# ==========================================
# 3. THE CHAT INTERFACE
# ==========================================
for message in st.session_state.chat_session.history:
    for part in message.parts:
        if part.text:
            role = "assistant" if message.role == "model" else "user"
            with st.chat_message(role):
                st.markdown(part.text)

if prompt := st.chat_input("Ask me to write a story..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Drafting, illustrating, and orchestrating..."):
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)