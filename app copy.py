import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
import os

# Load environment variables
load_dotenv()

# Initialize the LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=os.getenv("GOOGLE_API_KEY")  # Ensure you have GOOGLE_API_KEY in .env
)

# Import your existing prompts
from prompt import prompt, cp  # Assuming these are defined in a file named `prompt.py`

# Load the master data (e.g., company policy) from a .docx file
def load_master_data(docx_path):
    loader = Docx2txtLoader(docx_path)
    data = loader.load()
    return "\n".join([doc.page_content for doc in data])

# Define the chain using your imported prompt
chain = ChatPromptTemplate.from_messages(
    [
        ("system", prompt),  # Use the imported system prompt
        ("human", "Here is the {company_policy}"),
        ("human", "Here is the document content: {document_content}"),
         ("human", "Provide a Proffesional Detailed Report.")
    ]
) | llm | StrOutputParser()

# Streamlit App
st.title("Company Policy  Analyzer ")

# File uploader for PDF
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

# Path to the master data (company policy or other reference)
MASTER_DATA_PATH = "./cleaned_document.docx"

if not os.path.exists(MASTER_DATA_PATH):
    st.error(f"Master data file not found at: {MASTER_DATA_PATH}")
else:
    # Load the master data
    company_policy = load_master_data(MASTER_DATA_PATH)

    if uploaded_file is not None:
        # Save the uploaded file temporarily
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Load and parse the PDF
        loader = PyPDFLoader("temp.pdf")
        pages = loader.load_and_split()
        
        # Combine all pages into a single string
        document_content = "\n".join(page.page_content for page in pages)
        
        # Button to trigger analysis
        if st.button("Analyze Document"):
            with st.spinner("Analyzing the document..."):
                try:
                    # Invoke the chain with both company policy and document content
                    response = chain.invoke({
                        "company_policy": company_policy,
                        "document_content": document_content
                    })
                    
                    # Display the response
                    st.subheader("Analysis Result:")
                    st.write(response)
                except Exception as e:
                    st.error(f"An error occurred: {e}")
            
            # Clean up the temporary file
            os.remove("temp.pdf")