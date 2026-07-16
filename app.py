import streamlit as st
from groq import Groq
import base64

# Simple browser tab title
st.set_page_config(page_title="Chatbot", page_icon="💬")

# --- BACKGROUND IMAGE HELPER FUNCTION ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    # This reads your uploaded 'background.png' and converts it for CSS
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
    /* Make the chat messages easy to read over the background */
    .stChatMessage {{
        background-color: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(10px);
        border-radius: 10px;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)
except FileNotFoundError:
    # If the image isn't uploaded yet, it will just use a nice dark gradient instead!
    page_bg_gradient = '''
    <style>
    .stApp {
        background: linear-gradient(135deg, #1e1e2f, #111119);
    }
    </style>
    '''
    st.markdown(page_bg_gradient, unsafe_allow_html=True)
# ----------------------------------------

# Initialize the Groq client
client = Groq()

# Your custom greeting
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ready to go"}]

# Render current chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Watch for user input
if prompt := st.chat_input("Talk away..."):
    prompt = prompt.strip()
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Fetch response from Groq
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=st.session_state.messages,
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
