import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
import os

# Load environment variables
load_dotenv()
api_key = st.secrets["GOOGLE_API_KEY"]
# Initialize the LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=api_key
)

# Import your existing prompts (assuming they exist in prompt.py)
from prompt import prompt, cp

# Load master data (company policy)
def load_master_data(docx_path):
    loader = Docx2txtLoader(docx_path)
    data = loader.load()
    return "\n".join([doc.page_content for doc in data])

# Define analysis chain
analysis_chain = ChatPromptTemplate.from_messages([
    ("system", prompt),
    ("human", "Company Policy: {company_policy}"),
    ("human", "Document Content: {document_content}"),
    ("human", "Provide a Professional Detailed Report.")
]) | llm | StrOutputParser()

# Define chat chain with improved prompt
chat_chain = ChatPromptTemplate.from_messages([
    ("system", "You are an expert assistant specialized in helping users understand the compliance report generated from their uploaded document and the company policies. The report content is as follows: {report_content}. Please provide concise and accurate answers, referencing specific sections of the report when relevant."),
    ("human", "{user_question}")
]) | llm | StrOutputParser()

# Streamlit App Configuration
st.set_page_config(page_title="Policy Analyzer", layout="wide")
st.markdown("""
    <style>
    .main {background-color: #1a1a1a;}
    .stButton>button {background-color: #4CAF50; color: white; border-radius: 5px; padding: 8px 16px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);}
    .stTextInput>div>div>input {border-radius: 5px; background-color: #2d2d2d; color: white; border: 1px solid #4CAF50; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);}
    .chat-container {
        background-color: #2d2d2d;
        border: 2px solid #4CAF50;
        border-radius: 10px;
        padding: 15px;
        height: 400px;
        overflow-y: auto;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    }
    .chat-message {
        padding: 12px 15px;
        border-radius: 15px;
        margin: 10px 0;
        max-width: 80%;
        font-size: 16px;
        line-height: 1.5;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .user-message {
        background-color: #4CAF50;
        color: white;
        align-self: flex-end;
    }
    .assistant-message {
        background-color: #3a3a3a;
        color: #ffffff;
        align-self: flex-start;
    }
    .stMarkdown h2 {color: #4CAF50;}
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title("📑 Company Policy Analyzer")
st.markdown("Upload a PDF document to analyze it against company policies and ask follow-up questions.")

# Layout with columns
col1, col2 = st.columns([2, 1])

with col1:
    # File uploader
    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"], help="Supported format: PDF")

# Path to master data
MASTER_DATA_PATH = "./cleaned_document.docx"

if not os.path.exists(MASTER_DATA_PATH):
    st.error(f"Master data file not found at: {MASTER_DATA_PATH}")
else:
    # Load company policy
    company_policy = load_master_data(MASTER_DATA_PATH)
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Load and parse PDF
        loader = PyPDFLoader("temp.pdf")
        pages = loader.load_and_split()
        document_content = "\n".join(page.page_content for page in pages)
        
        # Analysis Section
        with col1:
            if st.button("Analyze Document", key="analyze"):
                with st.spinner("Analyzing document..."):
                    try:
                        report = analysis_chain.invoke({
                            "company_policy": company_policy,
                            "document_content": document_content
                        })
                        st.session_state['report'] = report
                        st.session_state['chat_history'] = [{"role": "assistant", "content": "Hello! I've generated the compliance report. Feel free to ask me any questions about it, e.g., 'What are the main gaps identified?'"}]
                        st.success("Analysis complete!")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                os.remove("temp.pdf")
        
        # Display report and chat interface
        if 'report' in st.session_state:
            with col1:
                st.subheader("Analysis Report")
                with st.expander("View Full Report", expanded=True):
                    st.markdown(st.session_state['report'])
                st.download_button(
                    label="Download Report",
                    data=st.session_state['report'],
                    file_name="compliance_report.md",
                    mime="text/markdown"
                )
            
            with col2:
                st.subheader("Chat with Report")
                # Build chat history HTML
                chat_html = ""
                for message in st.session_state['chat_history']:
                    if message['role'] == 'user':
                        chat_html += f'<div style="display: flex; justify-content: flex-end;"><div class="chat-message user-message">👤 {message["content"]}</div></div>'
                    else:
                        chat_html += f'<div style="display: flex; justify-content: flex-start;"><div class="chat-message assistant-message">🤖 {message["content"]}</div></div>'
                st.markdown(f'<div class="chat-container">{chat_html}</div>', unsafe_allow_html=True)
                
                # Chat input and buttons
                user_input = st.text_input("Ask a question about the report:", placeholder="e.g., 'What are the main gaps identified?'", key="chat_input")
                col_send, col_clear = st.columns([1, 1])
                with col_send:
                    if st.button("Send", key="send_chat"):
                        if user_input:
                            st.session_state['chat_history'].append({"role": "user", "content": user_input})
                            with st.spinner("Thinking..."):
                                response = chat_chain.invoke({
                                    "report_content": st.session_state['report'],
                                    "user_question": user_input
                                })
                                st.session_state['chat_history'].append({"role": "assistant", "content": response})
                            # Clear the input by letting st.rerun reset it naturally
                            st.rerun()
                with col_clear:
                    if st.button("Clear Chat", key="clear_chat"):
                        st.session_state['chat_history'] = [{"role": "assistant", "content": "Hello! I've generated the compliance report. Feel free to ask me any questions about it, e.g., 'What are the main gaps identified?'"}]
                        st.rerun()

# Footer
st.markdown("---")
st.markdown("Powered byI | © 2025")