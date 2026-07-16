import streamlit as st
from groq import Groq
import base64
import urllib.parse
import json
import re
import requests
from duckduckgo_search import DDGS
from streamlit_local_storage import LocalStorage

# Initialize local storage helper
local_storage = LocalStorage()

# UI Config
if "logged_in_user" not in st.session_state:
    st.set_page_config(page_title="Rival Chatbot", page_icon="🔐", initial_sidebar_state="collapsed")
else:
    st.set_page_config(page_title="Rival Chatbot", page_icon="💬", initial_sidebar_state="expanded")

# --- AUTO-LOAD CHATS FROM BROWSER STORAGE ---
# Attempt to load previously saved chats from the browser cache
if "all_chats" not in st.session_state:
    saved_chats = local_storage.getItem("rival_chat_history")
    if saved_chats:
        try:
            st.session_state.all_chats = json.loads(saved_chats)
        except Exception:
            st.session_state.all_chats = None
    
    # Fallback if no saved chats exist yet
    if not st.session_state.get("all_chats"):
        st.session_state.all_chats = {
            "Chat 1": [{"role": "assistant", "content": "Welcome back! This chat is saved directly to your browser."}]
        }

if "active_chat" not in st.session_state:
    st.session_state.active_chat = list(st.session_state.all_chats.keys())[0]

# --- SAVE CHATS HELPER ---
def save_chats_to_browser():
    if "all_chats" in st.session_state:
        chats_json = json.dumps(st.session_state.all_chats)
        local_storage.setItem("rival_chat_history", chats_json)

# --- BACKGROUND STYLE ---
try:
    with open('background.png', 'rb') as f:
        bin_str = base64.b64encode(f.read()).decode()
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
        background-color: rgba(15, 15, 25, 0.85) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        color: #f0f0f5 !important;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)
except FileNotFoundError:
    page_bg_gradient = f'''
    <style>
    .stApp {{
        background: linear-gradient(135deg, #1e1e2f, #111119);
    }}
    .stChatMessage {{
        background-color: rgba(25, 25, 35, 0.85) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        color: #f0f0f5 !important;
    }}
    </style>
    '''
    st.markdown(page_bg_gradient, unsafe_allow_html=True)

# --- CHAT INTERFACE ---
client = Groq()

# --- SIDEBAR CONTROL panel ---
with st.sidebar:
    st.title("💬 Chat History")
    st.write("💾 *Saves automatically to your device*")
    
    st.markdown("---")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_chat_num = len(st.session_state.all_chats) + 1
        new_chat_name = f"Chat {new_chat_num}"
        st.session_state.all_chats[new_chat_name] = [{"role": "assistant", "content": "Fresh chat! Ask away."}]
        st.session_state.active_chat = new_chat_name
        save_chats_to_browser()
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
        save_chats_to_browser()
        st.rerun()
        
    st.markdown("---")
    st.write("### Previous Conversations:")
    
    for chat_name in list(st.session_state.all_chats.keys()):
        label = f"✨ {chat_name}" if chat_name == st.session_state.active_chat else f"📁 {chat_name}"
        if st.button(label, key=f"btn_{chat_name}", use_container_width=True):
            st.session_state.active_chat = chat_name
            st.rerun()
            
    st.markdown("---")
    if st.button("🧹 Wipe All History", use_container_width=True):
        st.session_state.all_chats = {"Chat 1": [{"role": "assistant", "content": "All history wiped. Fresh start!"}]}
        st.session_state.active_chat = "Chat 1"
        save_chats_to_browser()
        st.rerun()

# --- MAIN CHAT LAYOUT ---
current_messages = st.session_state.all_chats[st.session_state.active_chat]

# Render active conversation
for msg in current_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"], caption="Generated Image ✨", use_container_width=True)
        if "video_url" in msg:
            st.video(msg["video_url"])

# Capture User Message
if prompt := st.chat_input("Talk, draw, or play a video..."):
    prompt = prompt.strip()
    if prompt:
        current_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Generate Bot Response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            image_keywords = ["generate image", "draw", "generate an image", "create an image of", "paint", "make a picture of"]
            is_image_request = any(keyword in prompt.lower() for keyword in image_keywords)
            
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
                save_chats_to_browser()
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
                    encoded_search = urllib.parse.quote(search_query)
                    url = f"https://www.youtube.com/results?search_query={encoded_search}"
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept-Language': 'en-US,en;q=0.9'
                    }
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    html = response.text
                        
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
                        save_chats_to_browser()
                        st.rerun()
                    else:
                        response_placeholder.error("Couldn't find any videos for that search. Try phrasing it differently!")
                except Exception as e:
                    response_placeholder.error(f"Failed to find video. Error: {e}")
                
            else:
                # Text Response & Web Search
                try:
                    response_placeholder.info("Searching the live web for facts... 🌐")
                    
                    web_context = ""
                    try:
                        with DDGS() as ddgs:
                            search_results = ddgs.text(prompt, max_results=3)
                            if search_results:
                                {
                                    "user": prompt,
                                    "results": [r.get('body') for r in search_results]
                                }
                                for r in search_results:
                                    web_context += f"Source URL: {r.get('href')}\nTitle: {r.get('title')}\nSnippet: {r.get('body')}\n\n"
                    except Exception:
                        web_context = ""
                    
                    system_prompt = (
                        "You are a helpful, extremely fast, and highly accurate assistant. "
                        "You have access to live web results to answer the user's prompt. "
                    )
                    if web_context:
                        system_prompt += f"\nHere is the live web search context related to the user's question:\n\n{web_context}"
                    else:
                        system_prompt += "\nNo live web search results were found."

                    clean_messages = [{"role": msg["role"], "content": msg["content"]} for msg in current_messages]
                    messages_with_system = [{"role": "system", "content": system_prompt}] + clean_messages
                    
                    response_placeholder.empty()
                    
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
                    save_chats_to_browser()
                    st.rerun()
                    
                except Exception as e:
                    response_placeholder.error(f"Oops! Something went wrong: {e}")
