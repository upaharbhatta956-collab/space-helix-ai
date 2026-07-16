import streamlit as st
from groq import Groq

# Simple browser tab title
st.set_page_config(page_title="Chatbot", page_icon="💬")

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
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Fetch response from Groq
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-specdec",
            messages=st.session_state.messages,
            stream=True,
        )
        
        full_response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                response_placeholder.write(full_response)
        
    st.session_state.messages.append({"role": "assistant", "content": full_response})
