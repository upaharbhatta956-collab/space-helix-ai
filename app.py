import streamlit as st
from groq import Groq
import base64
import urllib.parse
import urllib.request
import re

# Start with the sidebar EXPANDED by default!
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
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {
        "Chat 1": [{"role": "assistant", "content": "Ready to go. Ask me to generate an image, play a YouTube video, or just chat!"}]
    }

if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Chat 1"

# --- COLLAPSIBLE SIDEBAR ---
with st.sidebar:
    st.title("💬 Chat History")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_chat_num = len(st.session_state.all_chats) + 1
        new_chat_name = f"Chat {new_chat_num}"
        st.session_state.all_chats[new_chat_name] = [{"role": "assistant", "content": "Started a fresh chat! Ready to go."}]
        st.session_state.active_chat = new_chat_name
        st.rerun()
    
    st.markdown("---")
    
    st.write("### ✏️ Rename Active Chat")
    new_title = st.text_input(
        "Type a new name and hit Enter:", 
        value=st.session_state.active_chat,
        key="rename_input"
    ).strip()
    
    if new_title and new_title != st.session_state.active_chat:
        st.session_state.all_chats[new_title] = st.session_state.all_chats.pop(st.session_state.active_chat)
        st.session_state.active_chat = new_title
        st.rerun()
        
    st.markdown("---")
    st.write("### Previous Conversations:")
    
    for chat_name in list(st.session_state.all_chats.keys()):
        label = f"✨ {chat_name}" if chat_name == st.session_state.active_chat else f"📁 {chat_name}"
        if st.button(label, key=f"btn_{chat_name}", use_container_width=True):
            st.session_state.active_chat = chat_name
            st.rerun()
            
    st.markdown("---")
    st.write("### 💾 Export Chat")
    
    chat_export_text = ""
    for msg in st.session_state.all_chats[st.session_state.active_chat]:
        role_label = "Bot" if msg["role"] == "assistant" else "You"
        chat_export_text += f"[{role_label}]: {msg['content']}\n"
        if "image_url" in msg:
            chat_export_text += f"[Generated Image]: {msg['image_url']}\n"
        if "video_url" in msg:
            chat_export_text += f"[YouTube Video Embedded]: {msg['video_url']}\n"
        chat_export_text += "-"*40 + "\n"
        
    st.download_button(
        label="📥 Download This Chat (.txt)",
        data=chat_export_text,
        file_name=f"{st.session_state.active_chat.lower().replace(' ', '_')}_history.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    st.markdown("---")
    if st.button("🧹 Wipe All History", use_container_width=True):
        st.session_state.all_chats = {"Chat 1": [{"role": "assistant", "content": "All history wiped. Fresh start!"}]}
        st.session_state.active_chat = "Chat 1"
        st.rerun()

# --- LOAD CURRENT ACTIVE CHAT MESSAGES ---
current_messages = st.session_state.all_chats[st.session_state.active_chat]

# Render messages
for msg in current_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"], caption="Generated Image ✨", use_container_width=True)
        if "video_url" in msg:
            st.video(msg["video_url"])

# Watch for user input
if prompt := st.chat_input("Talk, draw, or play a video..."):
    prompt = prompt.strip()
    if prompt:
        current_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Get response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            # 1. CHECK FOR IMAGE REQUESTS
            image_keywords = ["generate image", "draw", "generate an image", "create an image of", "paint", "make a picture of"]
            is_image_request = any(keyword in prompt.lower() for keyword in image_keywords)
            
            # 2. CHECK FOR YOUTUBE REQUESTS
            video_keywords = ["play", "watch", "youtube", "listen to", "search youtube for"]
            is_video_request = any(keyword in prompt.lower() for keyword in video_keywords)
            
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
                
                current_messages.append({
                    "role": "assistant", 
                    "content": f"Here is the image I generated for: '{image_prompt}'",
                    "image_url": image_url
                })
                st.rerun()
                
            elif is_video_request:
                response_placeholder.info("Searching YouTube directly... 🔍")
                
                search_query = prompt
                for kw in video_keywords:
                    search_query = search_query.replace(kw, "")
                search_query = search_query.strip()
                
                if not search_query:
                    search_query = "never gonna give you up"
                
                try:
                    # Query YouTube directly
                    encoded_search = urllib.parse.quote(search_query)
                    url = f"https://www.youtube.com/results?search_query={encoded_search}"
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept-Language': 'en-US,en;q=0.9'
                    }
                    req = urllib.request.Request(url, headers=headers)
                    
                    with urllib.request.urlopen(req) as response:
                        html = response.read().decode('utf-8', errors='ignore')
                        
                    # Extract video IDs
                    video_ids = re.findall(r'"videoId":"([^"]{11})"', html)
                    
                    if not video_ids:
                        video_ids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                    
                    if video_ids:
                        unique_ids = list(dict.fromkeys(video_ids))
                        video_id = unique_ids[0]
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        response_placeholder.empty()
                        st.video(video_url)
                        
                        current_messages.append({
                            "role": "assistant",
                            "content": f"Found a video for: **{search_query}** 🎥",
                            "video_url": video_url
                        })
                        st.rerun()
                    else:
                        response_placeholder.error("Couldn't find any videos for that search. Try phrasing it differently!")
                except Exception as e:
                    response_placeholder.error(f"Failed to find video. Error: {e}")
                
            else:
                # Standard Text Chat Logic with Groq
                try:
                    # CRITICAL FIX: Clean the messages so Groq doesn't see 'video_url' or 'image_url' keys!
                    clean_messages = []
                    for msg in current_messages:
                        clean_messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })

                    messages_with_system = [
                        {"role": "system", "content": "You are a helpful assistant. If the user wants to play a video or watch something, tell them you can search YouTube and play it for them!"}
                    ] + clean_messages
                    
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
                    
                    current_messages.append({"role": "assistant", "content": full_response})
                    st.rerun()
                    
                except Exception as e:
                    response_placeholder.error(f"Oops! Something went wrong: {e}")
