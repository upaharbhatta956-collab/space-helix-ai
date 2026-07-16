import streamlit as st
from groq import Groq
import base64
import urllib.parse
import json
import re
import requests
import sqlite3
from duckduckgo_search import DDGS

# Start with sidebar COLLAPSED on the login screen
if "logged_in_user" not in st.session_state:
    st.set_page_config(page_title="Rival Chatbot", page_icon="🔐", initial_sidebar_state="collapsed")
else:
    st.set_page_config(page_title="Rival Chatbot", page_icon="💬", initial_sidebar_state="expanded")

# --- SQLITE DATABASE SETUP & HELPER FUNCTIONS ---
def get_db_connection():
    conn = sqlite3.connect("chats.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create table for users & their history if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            history TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database right away
init_db()

def db_login(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"status": "success", "history": user["history"]}
    return {"status": "fail"}

def db_signup(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Default starting history is empty json
        empty_history = json.dumps({
            "Chat 1": [{"role": "assistant", "content": "Welcome to your new account! Ready to chat."}]
        })
        cursor.execute("INSERT INTO users (username, password, history) VALUES (?, ?, ?)", (username, password, empty_history))
        conn.commit()
        status = "success"
    except sqlite3.IntegrityError:
        status = "exists"
    finally:
        conn.close()
    return {"status": status}

def save_chat_history_to_db():
    if "logged_in_user" in st.session_state and "all_chats" in st.session_state:
        conn = get_db_connection()
        cursor = conn.cursor()
        history_json = json.dumps(st.session_state.all_chats)
        cursor.execute("UPDATE users SET history = ? WHERE username = ?", (history_json, st.session_state.logged_in_user))
        conn.commit()
        conn.close()

# --- BACKGROUND IMAGE HELPER ---
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

# --- USER LOGIN/SIGNUP UI ---
if "logged_in_user" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🔐 Rival Chat Login</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>Sign in or create a local account instantly.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Login")
        login_user = st.text_input("Username", key="l_user").strip()
        login_pass = st.text_input("Password", type="password", key="l_pass").strip()
        if st.button("Sign In", use_container_width=True):
            if login_user and login_pass:
                res = db_login(login_user, login_pass)
                if res.get("status") == "success":
                    st.session_state.logged_in_user = login_user
                    st.session_state.all_chats = json.loads(res.get("history", "{}"))
                    st.session_state.active_chat = list(st.session_state.all_chats.keys())[0]
                    st.success(f"Logged in as {login_user}!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password.")
            else:
                st.warning("Please fill out both fields.")
                
    with col2:
        st.subheader("Create Account")
        reg_user = st.text_input("New Username", key="r_user").strip()
        reg_pass = st.text_input("New Password", type="password", key="r_pass").strip()
        if st.button("Sign Up", use_container_width=True):
            if reg_user and reg_pass:
                res = db_signup(reg_user, reg_pass)
                if res.get("status") == "success":
                    st.success("Account created successfully! You can now log in.")
                elif res.get("status") == "exists":
                    st.error("Username already taken.")
            else:
                st.warning("Please fill out both fields.")
                
    st.stop()  # Stop page execution until logged in

# --- MAIN CHAT APP (RUNS AFTER SUCCESSFUL LOGIN) ---
client = Groq()

if "all_chats" not in st.session_state:
    st.session_state.all_chats = {
        "Chat 1": [{"role": "assistant", "content": f"Welcome, {st.session_state.logged_in_user}! Ask me anything."}]
    }

if "active_chat" not in st.session_state:
    st.session_state.active_chat = list(st.session_state.all_chats.keys())[0]

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("💬 Chat History")
    st.write(f"👤 Logged in as: **{st.session_state.logged_in_user}**")
    
    if st.button("🚪 Log Out", use_container_width=True):
        del st.session_state.logged_in_user
        if "all_chats" in st.session_state:
            del st.session_state.all_chats
        st.rerun()
        
    st.markdown("---")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_chat_num = len(st.session_state.all_chats) + 1
        new_chat_name = f"Chat {new_chat_num}"
        st.session_state.all_chats[new_chat_name] = [{"role": "assistant", "content": "Fresh chat! Ask away."}]
        st.session_state.active_chat = new_chat_name
        save_chat_history_to_db()
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
        save_chat_history_to_db()
        st.rerun()
        
    st.markdown("---")
    st.write("### Previous Conversations:")
    
    for chat_name in list(st.session_state.all_chats.keys()):
        label = f"✨ {chat_name}" if chat_name == st.session_state.active_chat else f"📁 {chat_name}"
        if st.button(label, key=f"btn_{chat_name}", use_container_width=True):
            st.session_state.active_chat = chat_name
            st.rerun()
            
    st.markdown("---")
    # --- WIPE HISTORY (FIXED) ---
    if st.button("🧹 Wipe All History", use_container_width=True):
        st.session_state.all_chats = {"Chat 1": [{"role": "assistant", "content": "All history wiped. Fresh start!"}]}
        st.session_state.active_chat = "Chat 1"
        save_chat_history_to_db()
        st.rerun()

# --- RENDER CHAT INTERFACE ---
current_messages = st.session_state.all_chats[st.session_state.active_chat]

for msg in current_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"], caption="Generated Image ✨", use_container_width=True)
        if "video_url" in msg:
            st.video(msg["video_url"])

# Capture user prompt
if prompt := st.chat_input("Talk, draw, or play a video..."):
    prompt = prompt.strip()
    if prompt:
        current_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Get response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            # Keywords checks
            image_keywords = ["generate image", "draw", "generate an image", "create an image of", "paint", "make a picture of"]
            is_image_request = any(keyword in prompt.lower() for keyword in image_keywords)
            
            video_keywords = ["play", "watch", "youtube", "listen to", "search youtube for"]
            is_video_request = any(keyword in prompt.lower() for keyword in video_keywords)
            
            if is_image_request:
                response_placeholder.info("Generating your masterpiece... 🎨")
                image_prompt = prompt
                for kw in image_keywords:
                    image_prompt = image_prompt.replace(kw, "")
                image_prompt = image_prompt.strip() or "a majestic futuristic neon city"
                
                encoded_prompt = urllib.parse.quote(image_prompt)
                image_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&nologo=true"
                
                response_placeholder.empty()
                st.image(image_url, caption=f'"{image_prompt}"', use_container_width=True)
                
                current_messages.append({
                    "role": "assistant", 
                    "content": f"Here is the image I generated for: '{image_prompt}'",
                    "image_url": image_url
                })
                save_chat_history_to_db()
                st.rerun()
                
            elif is_video_request:
                response_placeholder.info("Searching YouTube directly... 🔍")
                search_query = prompt
                for kw in video_keywords:
                    search_query = search_query.replace(kw, "")
                search_query = search_query.strip() or "never gonna give you up"
                
                try:
                    encoded_search = urllib.parse.quote(search_query)
                    url = f"https://www.youtube.com/results?search_query={encoded_search}"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    html = response.text
                    video_ids = re.findall(r'"videoId":"([^"]{11})"', html) or re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                    
                    if video_ids:
                        video_url = f"https://www.youtube.com/watch?v={list(dict.fromkeys(video_ids))[0]}"
                        response_placeholder.empty()
                        st.video(video_url)
                        
                        current_messages.append({
                            "role": "assistant",
                            "content": f"Found a video for: **{search_query}** 🎥",
                            "video_url": video_url
                        })
                        save_chat_history_to_db()
                        st.rerun()
                    else:
                        response_placeholder.error("Couldn't find any videos for that search.")
                except Exception as e:
                    response_placeholder.error(f"Failed to find video: {e}")
                
            else:
                # Text Chat
                try:
                    response_placeholder.info("Searching the live web for facts... 🌐")
                    web_context = ""
                    try:
                        with DDGS() as ddgs:
                            search_results = ddgs.text(prompt, max_results=3)
                            if search_results:
                                for r in search_results:
                                    web_context += f"Source URL: {r.get('href')}\nTitle: {r.get('title')}\nSnippet: {r.get('body')}\n\n"
                    except Exception:
                        web_context = ""
                    
                    system_prompt = "You are a helpful assistant with access to web results.\n"
                    if web_context:
                        system_prompt += f"\nWeb Context:\n{web_context}"
                    
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
                    save_chat_history_to_db()
                    st.rerun()
                    
                except Exception as e:
                    response_placeholder.error(f"Oops! Something went wrong: {e}")
