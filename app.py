import streamlit as st
from groq import Groq
import base64
import urllib.parse
import re
import requests
from duckduckgo_search import DDGS

# Fast, clean, full-screen chat layout
st.set_page_config(page_title="SparkHelix AI", page_icon="💬", layout="centered")

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

# Title
st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>💬 Rival Chat</h1>", unsafe_allow_html=True)

# --- IN-MEMORY CHAT HISTORY (Clears on refresh) ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hey! Ask me to write, draw an image, or play a video. (Note: History will clear if you refresh!)"}]

# Render current session messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"], use_container_width=True)
        if "video_url" in msg:
            st.video(msg["video_url"])

# Main chatbot input
if prompt := st.chat_input("Talk, draw, or play a video..."):
    prompt = prompt.strip()
    if prompt:
        # Show user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Generate Assistant response
        with st.chat_message("assistant"):
            placeholder = st.empty()
            
            # Keywords checks
            image_keywords = ["generate image", "draw", "paint", "create an image of", "make a picture of"]
            is_image = any(kw in prompt.lower() for kw in image_keywords)
            
            video_keywords = ["play", "watch", "youtube", "search youtube for"]
            is_video = any(kw in prompt.lower() for kw in video_keywords)
            
            # 1. Image Generation
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
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Here is your image of: '{clean_prompt}'",
                    "image_url": image_url
                })
                st.rerun()
                
            # 2. Video Search
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
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Found video for: **{clean_search}**",
                            "video_url": video_url
                        })
                        st.rerun()
                    else:
                        placeholder.error("No videos found.")
                except Exception as e:
                    placeholder.error(f"Error fetching video: {e}")
            
            # 3. Standard Text / Search response
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
                        
                    # Build history payload
                    clean_hist = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    full_messages = [{"role": "system", "content": system}] + clean_hist
                    
                    placeholder.empty()
                    client = Groq()
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
                            
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
                except Exception as e:
                    placeholder.error(f"Error generating answer: {e}")
