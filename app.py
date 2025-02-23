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

# Define chat chain for both report and policy interaction
chat_chain = ChatPromptTemplate.from_messages([
    ("system", "You are an expert assistant specialized in helping users understand company policies and compliance reports. The company policy content is: {company_policy}. If a report exists, its content is: {report_content}. Provide concise and accurate answers, referencing specific sections of the policy or report when relevant. If no report exists, assist based on the policy alone."),
    ("human", "{user_question}")
]) | llm | StrOutputParser()

# Streamlit App Configuration
st.set_page_config(page_title="Policy Analyzer", layout="wide")
st.markdown("""
    <style>
    .main {background-color: #1a1a1a;}
    .stButton>button {background-color: #4CAF50; color: white; border-radius: 5px; padding: 10px 20px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);}
    .stTextInput>div>div>input {border-radius: 5px; background-color: #2d2d2d; color: white; border: 1px solid #4CAF50; padding: 10px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);}
    .chat-container {
        background-color: #2d2d2d;
        border: 2px solid #4CAF50;
        border-radius: 10px;
        padding: 20px;
        height: 600px;  /* Increased height for more chat space */
        overflow-y: auto;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;  /* Added spacing below chat */
    }
    .chat-message {
        padding: 15px 20px;  /* Increased padding for readability */
        border-radius: 15px;
        margin: 15px 0;  /* More vertical spacing between messages */
        max-width: 85%;  /* Slightly wider messages */
        font-size: 16px;
        line-height: 1.6;  /* Improved readability */
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
    .footer {font-size: 12px; color: #888888; text-align: center; padding: 5px 0;}  /* Smaller footer */
    </style>
""", unsafe_allow_html=True)

# Industry Dropdown (Coming Soon)
st.selectbox(
    "Select Industry (Coming Soon)",
    ["General", "Healthcare", "Finance", "Technology"],
    disabled=True,
    help="Industry-specific policy analysis coming soon!"
)

# Title and description
st.title("📑 Company Policy Analyzer")
st.markdown("Upload a PDF document to analyze it against company policies or chat directly with the policy document.")

# Layout with columns (adjusted proportions for more chat space)
col1, col2 = st.columns([1.5, 2.5])  # Reduced col1, increased col2 for chat

# Path to master data
MASTER_DATA_PATH = "./cleaned_document.docx"

if not os.path.exists(MASTER_DATA_PATH):
    st.error(f"Master data file not found at: {MASTER_DATA_PATH}")
else:
    # Load company policy
    company_policy = load_master_data(MASTER_DATA_PATH)
    
    # Initialize chat history if not present
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = [{"role": "assistant", "content": "Hello! You can ask me anything about the company policy, or upload a document to analyze it against the policy."}]
    
    with col1:
        # File uploader
        uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"], help="Supported format: PDF")
        
        if uploaded_file is not None:
            # Save uploaded file temporarily
            with open("temp.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Load and parse PDF
            loader = PyPDFLoader("temp.pdf")
            pages = loader.load_and_split()
            document_content = "\n".join(page.page_content for page in pages)
            
            # Analysis Section
            if st.button("Analyze Document", key="analyze"):
                with st.spinner("Analyzing document..."):
                    try:
                        report = analysis_chain.invoke({
                            "company_policy": company_policy,
                            "document_content": document_content
                        })
                        st.session_state['report'] = report
                        st.session_state['chat_history'] = [{"role": "assistant", "content": "Hello! I've generated the compliance report. Feel free to ask me any questions about it or the company policy."}]
                        st.success("Analysis complete!")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                os.remove("temp.pdf")
        
        # Display report if it exists
        if 'report' in st.session_state:
            st.subheader("Analysis Report")
            with st.expander("View Full Report", expanded=False):  # Collapsed by default to save space
                st.markdown(st.session_state['report'])
            st.download_button(
                label="Download Report",
                data=st.session_state['report'],
                file_name="compliance_report.md",
                mime="text/markdown"
            )
    
    with col2:
        st.subheader("Chat with Policy & Report")
        # Build chat history HTML
        chat_html = ""
        for message in st.session_state['chat_history']:
            if message['role'] == 'user':
                chat_html += f'<div style="display: flex; justify-content: flex-end;"><div class="chat-message user-message">👤 {message["content"]}</div></div>'
            else:
                chat_html += f'<div style="display: flex; justify-content: flex-start;"><div class="chat-message assistant-message">🤖 {message["content"]}</div></div>'
        st.markdown(f'<div class="chat-container">{chat_html}</div>', unsafe_allow_html=True)
        
        # Chat input and buttons with more spacing
        user_input = st.text_input("Ask a question about the policy or report:", placeholder="e.g., 'What does the policy say about data security?'", key="chat_input")
        col_send, col_clear = st.columns([1, 1])
        with col_send:
            if st.button("Send", key="send_chat"):
                if user_input:
                    st.session_state['chat_history'].append({"role": "user", "content": user_input})
                    with st.spinner("Thinking..."):
                        report_content = st.session_state.get('report', "No report generated yet.")
                        response = chat_chain.invoke({
                            "company_policy": company_policy,
                            "report_content": report_content,
                            "user_question": user_input
                        })
                        st.session_state['chat_history'].append({"role": "assistant", "content": response})
                    st.rerun()
        with col_clear:
            if st.button("Clear Chat", key="clear_chat"):
                st.session_state['chat_history'] = [{"role": "assistant", "content": "Hello! You can ask me anything about the company policy, or upload a document to analyze it against the policy."}]
                st.rerun()

# Reduced Footer
st.markdown('<div class="footer">Powered by xAI | © 2025</div>', unsafe_allow_html=True)