import streamlit as st
from groq import Groq
import base64
import urllib.parse

# 1. Start with the sidebar EXPANDED by default!
st.set_page_config(
    page_title="Rival Chatbot", 
    page_icon="💬", 
    initial_sidebar_state="expanded"
)

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

# --- CHAT HISTORY STORAGE ---
# 'all_chats' stores previous sessions: { "Chat Name": [messages] }
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {
        "Chat 1": [{"role": "assistant", "content": "Ready to go. Ask me to generate an image or just chat!"}]
    }

# 'active_chat' tracks which chat name we are currently looking at
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Chat 1"

# --- COLLAPSIBLE SIDEBAR ---
with st.sidebar:
    st.title("💬 Chat History")
    
    # Button to start a brand-new chat session
    if st.button("➕ New Chat", use_container_width=True):
        new_chat_num = len(st.session_state.all_chats) + 1
        new_chat_name = f"Chat {new_chat_num}"
        st.session_state.all_chats[new_chat_name] = [{"role": "assistant", "content": "Started a fresh chat! Ready to go."}]
        st.session_state.active_chat = new_chat_name
        st.rerun()
    
    st.markdown("---")
    st.write("### Previous Conversations:")
    
    # List all saved chats as clickable buttons
    for chat_name in list(st.session_state.all_chats.keys()):
        # Highlight the current chat using a visual emoji
        label = f"✨ {chat_name}" if chat_name == st.session_state.active_chat else f"📁 {chat_name}"
        
        if st.button(label, key=f"btn_{chat_name}", use_container_width=True):
            st.session_state.active_chat = chat_name
            st.rerun()
            
    st.markdown("---")
    
    # Danger zone button to wipe everything
    if st.button("🧹 Wipe All History", use_container_width=True):
        st.session_state.all_chats = {"Chat 1": [{"role": "assistant", "content": "All history wiped. Fresh start!"}]}
        st.session_state.active_chat = "Chat 1"
        st.rerun()

# --- LOAD CURRENT ACTIVE CHAT MESSAGES ---
current_messages = st.session_state.all_chats[st.session_state.active_chat]

# Render messages from the active session
for msg in current_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"], caption="Generated Image ✨", use_container_width=True)

# Watch for user input
if prompt := st.chat_input("Talk or ask for an image..."):
    prompt = prompt.strip()
    if prompt:
        # Save user message to active history
        current_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Get response from Assistant
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            image_keywords = ["generate image", "draw", "generate an image", "create an image of", "paint", "make a picture of"]
            is_image_request = any(keyword in prompt.lower() for keyword in image_keywords)
            
            if is_image_request:
                response_placeholder.info("Generating your masterpiece... 🎨")
                
                image_prompt = prompt
                for kw in image_keywords:
                    image_prompt = image_prompt.replace(kw, "")
                image_prompt = image_prompt.strip()
                
                if not image_prompt:
                    image_prompt = "a majestic futuristic neon city"
                
                encoded_prompt = urllib.parse.quote(image_prompt)
                image_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&nologo=true"
                
                response_placeholder.empty()
                st.image(image_url, caption=f'"{image_prompt}"', use_container_width=True)
                
                text_response = f"Here is the image I generated for: '{image_prompt}'"
                current_messages.append({
                    "role": "assistant", 
                    "content": text_response,
                    "image_url": image_url
                })
                st.rerun()
                
            else:
                try:
                    messages_with_system = [
                        {"role": "system", "content": "You are a helpful assistant. If the user wants an image, they can use words like 'draw' or 'generate image' to trigger your image generation tool."}
                    ] + current_messages
                    
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-specdec",
                        messages=messages_with_system,
                        stream=True,
                    )
                    
                    full_response = ""
                    for chunk in completion:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            response_placeholder.write(full_response)
                    
                    current_messages.append({"role": "assistant", "content": full_response})
                    st.rerun()
                    
                except Exception as e:
                    response_placeholder.error(f"Oops! Something went wrong: {e}")
