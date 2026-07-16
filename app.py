import streamlit as st
from groq import Groq
import base64
import urllib.parse
import json
import re
import requests
from duckduckgo_search import DDGS
from streamlit_cookies_controller import CookieController

# Initialize the cookie manager
controller = CookieController()

# Set up page configurations
if "logged_in" not in st.session_state:
    st.set_page_config(page_title="Rival Chatbot", page_icon="🔐", initial_sidebar_state="collapsed")
else:
    st.set_page_config(page_title="Rival Chatbot", page_icon="💬", initial_sidebar_state="expanded")

# --- COOKIE-BASED DATABASE SYSTEM ---
def load_all_userData():
    """Load all users and passwords from cookies"""
    data = controller.get("rival_users_db")
    if data:
        try:
            return json.loads(data)
        except Exception:
            return {}
    return {}

def save_all_userData(data):
    """Save all users database to cookies"""
    controller.set("rival_users_db", json.dumps(data))

# --- APP BACKGROUNDS ---
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

# --- LOGIN SCREEN ---
if "logged_in" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🔐 Rival Chat Login</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>Saves securely to this browser session.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    users_db = load_all_userData()
    
    with col1:
        st.subheader("Login")
        login_user = st.text_input("Username", key="l_user").strip()
        login_pass = st.text_input("Password", type="password", key="l_pass").strip()
        if st.button("Sign In", use_container_width=True):
            if login_user in users_db and users_db[login_user]["password"] == login_pass:
                st.session_state.logged_in = True
                st.session_state.username = login_user
                st.session_state.all_chats = users_db[login_user]["history"]
                st.session_state.active_chat = list(st.session_state.all_chats.keys())[0]
                st.success("Welcome back!")
                st.rerun()
            else:
                st.error("Invalid Username or Password.")
                
    with col2:
        st.subheader("Create Account")
        reg_user = st.text_input("New Username", key="r_user").strip()
        reg_pass = st.text_input("New Password", type="password", key="r_pass").strip()
        if st.button("Sign Up", use_container_width=True):
            if reg_user and reg_pass:
                if reg_user in users_db:
                    st.error("Username already taken.")
                else:
                    users_db[reg_user] = {
                        "password": reg_pass,
                        "history": {
                            "Chat 1": [{"role": "assistant", "content": "Account created! Ask me anything."}]
                        }
                    }
                    save_all_userData(users_db)
                    st.success("Account created successfully! You can now log in.")
            else:
                st.warning("Please fill out both fields.")
    st.stop()

# --- MAIN APP ROUTINE ---
client = Groq()

# Save utility
def force_sync_db():
    users_db = load_all_userData()
    if st.session_state.username in users_db:
        users_db[st.session_state.username]["history"] = st.session_state.all_chats
        save_all_userData(users_db)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.title("💬 Chat History")
    st.write(f"👤 User: **{st.session_state.username}**")
    
    if st.button("🚪 Log Out", use_container_width=True):
        del st.session_state.logged_in
        del st.session_state.username
        del st.session_state.all_chats
        st.rerun()
        
    st.markdown("---")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_chat_name = f"Chat {len(st.session_state.all_chats) + 1}"
        st.session_state.all_chats[new_chat_name] = [{"role": "assistant", "content": "Fresh chat! Ask away."}]
        st.session_state.active_chat = new_chat_name
        force_sync_db()
        st.rerun()
        
    st.markdown("---")
    
    st.write("### ✏️ Rename Active Chat")
    new_title = st.text_input("Type new name & hit Enter:", value=st.session_state.active_chat, key="rename_chat").strip()
    if new_title and new_title != st.session_state.active_chat:
        st.session_state.all_chats[new_title] = st.session_state.all_chats.pop(st.session_state.active_chat)
        st.session_state.active_chat = new_title
        force_sync_db()
        st.rerun()
        
    st.markdown("---")
    st.write("### Previous Conversations:")
    for chat_name in list(st.session_state.all_chats.keys()):
        label = f"✨ {chat_name}" if chat_name == st.session_state.active_chat else f"📁 {chat_name}"
        if st.button(label, key=f"sel_{chat_name}", use_container_width=True):
            st.session_state.active_chat = chat_name
            st.rerun()
            
    st.markdown("---")
    # CLEAN WIPE BUTTON
    if st.button("🧹 Wipe All History", use_container_width=True):
        st.session_state.all_chats = {
            "Chat 1": [{"role": "assistant", "content": "All history cleanly wiped! Fresh start."}]
        }
        st.session_state.active_chat = "Chat 1"
        force_sync_db()
        st.rerun()

# --- RENDER MESSAGES ---
current_messages = st.session_state.all_chats[st.session_state.active_chat]

for msg in current_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"], use_container_width=True)
        if "video_url" in msg:
            st.video(msg["video_url"])

# --- HANDLE INCOMING USER MESSAGE ---
if prompt := st.chat_input("Talk, draw, or search..."):
    prompt = prompt.strip()
    if prompt:
        current_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        with st.chat_message("assistant"):
            placeholder = st.empty()
            
            image_keywords = ["generate image", "draw", "paint", "create an image of", "make a picture of"]
            is_image = any(kw in prompt.lower() for kw in image_keywords)
            
            video_keywords = ["play", "watch", "youtube", "search youtube for"]
            is_video = any(kw in prompt.lower() for kw in video_keywords)
            
            if is_image:
                placeholder.info("Drawing... 🎨")
                clean_prompt = prompt
                for kw in image_keywords:
                    clean_prompt = clean_prompt.replace(kw, "")
                clean_prompt = clean_prompt.strip() or "neon futuristic skyline"
                
                url_prompt = urllib.parse.quote(clean_prompt)
                image_url = f"https://image.pollinations.ai/p/{url_prompt}?width=1024&height=1024&nologo=true"
                
                placeholder.empty()
                st.image(image_url, caption=f'"{clean_prompt}"', use_container_width=True)
                current_messages.append({
                    "role": "assistant",
                    "content": f"Here is your image of: '{clean_prompt}'",
                    "image_url": image_url
                })
                force_sync_db()
                st.rerun()
                
            elif is_video:
                placeholder.info("Searching YouTube... 🔍")
                clean_search = prompt
                for kw in video_keywords:
                    clean_search = clean_search.replace(kw, "")
                clean_search = clean_search.strip() or "never gonna give you up"
                
                try:
                    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean_search)}"
                    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                    video_ids = re.findall(r'"videoId":"([^"]{11})"', res.text)
                    if video_ids:
                        video_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                        placeholder.empty()
                        st.video(video_url)
                        current_messages.append({
                            "role": "assistant",
                            "content": f"Found video for: **{clean_search}**",
                            "video_url": video_url
                        })
                        force_sync_db()
                        st.rerun()
                    else:
                        placeholder.error("No videos found.")
                except Exception as e:
                    placeholder.error(f"Error fetching video: {e}")
                    
            else:
                try:
                    placeholder.info("Searching the web... 🌐")
                    context = ""
                    try:
                        with DDGS() as ddgs:
                            results = ddgs.text(prompt, max_results=3)
                            for r in results:
                                context += f"Source: {r.get('href')}\nSnippet: {r.get('body')}\n\n"
                    except Exception:
                        pass
                    
                    system = "You are a helpful assistant."
                    if context:
                        system += f"\n\nHere is search engine context:\n{context}"
                        
                    clean_hist = [{"role": m["role"], "content": m["content"]} for m in current_messages]
                    full_messages = [{"role": "system", "content": system}] + clean_hist
                    
                    placeholder.empty()
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=full_messages,
                        stream=True
                    )
                    
                    response = ""
                    for chunk in completion:
                        if chunk.choices[0].delta.content:
                            response += chunk.choices[0].delta.content
                            placeholder.write(response)
                            
                    current_messages.append({"role": "assistant", "content": response})
                    force_sync_db()
                    st.rerun()
                except Exception as e:
                    placeholder.error(f"Error generating answer: {e}")
