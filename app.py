import streamlit as st
from groq import Groq
import base64
import urllib.parse

# Simple browser tab title
st.set_page_config(page_title="Rival Chatbot", page_icon="💬")

# --- BACKGROUND IMAGE HELPER ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    bin_str = get_base64_of_bin_file('background.png')
    page_bg_img = f'''
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    .stChatMessage {{
        background-color: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(10px);
        border-radius: 10px;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)
except FileNotFoundError:
    page_bg_gradient = '''
    <style>
    .stApp {
        background: linear-gradient(135deg, #1e1e2f, #111119);
    }
    </style>
    '''
    st.markdown(page_bg_gradient, unsafe_allow_html=True)

# Initialize the Groq client
client = Groq()

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ready to go. Ask me to generate an image or just chat!"}]

# Render current chat history (including text and any generated images)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"], caption="Generated Image ✨", use_container_width=True)

# Watch for user input
if prompt := st.chat_input("Talk or ask for an image..."):
    prompt = prompt.strip()
    if prompt:
        # Display and record user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Get response from Assistant
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            # Check if user is asking for an image
            image_keywords = ["generate image", "draw", "generate an image", "create an image of", "paint", "make a picture of"]
            is_image_request = any(keyword in prompt.lower() for keyword in image_keywords)
            
            if is_image_request:
                # 1. Let the user know we're rendering it
                response_placeholder.info("Generating your masterpiece... 🎨")
                
                # Clean up prompt to extract just the image description
                image_prompt = prompt
                for kw in image_keywords:
                    image_prompt = image_prompt.replace(kw, "")
                image_prompt = image_prompt.strip()
                
                # Fallback if the user just typed "draw" without details
                if not image_prompt:
                    image_prompt = "a majestic futuristic neon city"
                
                # 2. Generate the safe URL-encoded image using the high-quality Flux engine
                encoded_prompt = urllib.parse.quote(image_prompt)
                image_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&nologo=true"
                
                # 3. Clean up the placeholder and render the image!
                response_placeholder.empty()
                st.image(image_url, caption=f'"{image_prompt}"', use_container_width=True)
                
                # 4. Save both the bot message and the image to chat history
                text_response = f"Here is the image I generated for: '{image_prompt}'"
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": text_response,
                    "image_url": image_url
                })
                
            else:
                # Standard Text Chat Logic with Groq
                try:
                    # Let Groq know about our image ability in a system prompt!
                    messages_with_system = [
                        {"role": "system", "content": "You are a helpful assistant. If the user wants an image, they can use words like 'draw' or 'generate image' to trigger your image generation tool."}
                    ] + st.session_state.messages
                    
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages_with_system,
                        stream=True,
                    )
                    
                    full_response = ""
                    for chunk in completion:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            response_placeholder.write(full_response)
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                except Exception as e:
                    response_placeholder.error(f"Oops! Something went wrong: {e}")
