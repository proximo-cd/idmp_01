import streamlit as st
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import fitz  # PyMuPDF
import asyncio
import tempfile  # Import the tempfile module
from azure.core.exceptions import HttpResponseError
from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# Function to extract text from a PDF file using PyMuPDF
def extract_text_from_pdf(pdf_file):
    text = ""
    # Reopen the temporary file for reading
    with open(pdf_file.name, "rb") as temp_file:
        pdf_document = fitz.open(stream=temp_file.read(), filetype="pdf")
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text += page.get_text()
    return text

# Function to analyze the layout of a document
async def analyze_layout_async(file_path, endpoint, key):
    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )
    async with document_analysis_client:
        with open(file_path, "rb") as f:
            poller = await document_analysis_client.begin_analyze_document(
                "prebuilt-layout", document=f
            )
        result = await poller.result()
    return result

# Function to generate a word cloud from text
def generate_wordcloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)
    return wordcloud

# Streamlit web app
st.title("IDMP Text Extraction Prototype")

# Azure Form Recognizer endpoint and key
endpoint = "https://cog-pcm-pdf-sbx-eu-1.cognitiveservices.azure.com/"
key = "e03cac118c80488ab9f8a0453d4d2ed8"

# File upload widget to allow users to upload PDFs
uploaded_files = st.file_uploader("Upload PDF Documents", type=["pdf"], accept_multiple_files=True)

# Check if the required environment variables are set
if not endpoint or not key:
    st.error("Azure Form Recognizer configuration is missing. Set FORM_RECOGNIZER_ENDPOINT and FORM_RECOGNIZER_KEY environment variables.")
else:
    extracted_text_data = {}  # Dictionary to store extracted text and results

    # Perform analysis when files are uploaded
    for uploaded_file in uploaded_files:
        st.write(f"Analyzing document...")

        # Use the document name as the unique identifier
        unique_id = uploaded_file.name

        # Create a temporary file with the document name to store the uploaded PDF content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix=unique_id) as temp_file:
            temp_file.write(uploaded_file.read())

        # Extract text from the temporary PDF file using PyMuPDF
        extracted_text = extract_text_from_pdf(temp_file)

        # Analyze the uploaded PDF using the Azure Form Recognizer layout analysis
        try:
            # Call the analysis function here and pass the file path
            result = asyncio.run(analyze_layout_async(temp_file.name, endpoint, key))

            # Store the extracted text and result in the dictionary using the document name as the key
            extracted_text_data[unique_id] = {
                "Text": extracted_text,
                "AnalysisResult": result,
                "FileName": uploaded_file.name  # Store the filename
            }

        except HttpResponseError as error:
            st.error(f"Error analyzing document: {error}")

    # Create tabs for each document
    selected_unique_id = st.sidebar.radio("Select a Document", list(extracted_text_data.keys()))
    
    if selected_unique_id is not None:
        selected_document = extracted_text_data[selected_unique_id]

        st.subheader(f"Word Cloud for Selected Document (Name: {selected_unique_id})")
        wordcloud = generate_wordcloud(selected_document["Text"])
        
        # Display the word cloud as an image without use_container_width
        st.image(wordcloud.to_array(), caption=f"Word Cloud for {selected_unique_id}", use_column_width=True)

        st.subheader(f"Extracted Text for Selected Document (Name: {selected_unique_id})")
        st.write(selected_document["Text"])
