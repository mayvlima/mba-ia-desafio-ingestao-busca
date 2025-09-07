
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_postgres import PGVector

def validate_env():
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")):
        raise RuntimeError("At least one of GOOGLE_API_KEY or OPENAI_API_KEY must be set")
    for k in ("DATABASE_URL", "PG_VECTOR_COLLECTION_NAME"):
        if not os.getenv(k):
            raise RuntimeError(f"Environment variable {k} is not set")
    if not os.getenv("PDF_PATH"):
        raise RuntimeError("Environment variable PDF_PATH is not set")

def get_embedding_model():
    if os.getenv("GOOGLE_API_KEY"):
        return GoogleGenerativeAIEmbeddings(model=os.getenv("GOOGLE_EMBEDDING_MODEL"))
    return OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDING_MODEL"))

def ingest_pdf():
    load_dotenv()
    validate_env()
    pdf_path = os.getenv("PDF_PATH")
    docs = PyPDFLoader(str(pdf_path)).load()
    if not docs:
        print("No documents found in the PDF.")
        return
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        add_start_index=False
    )
    splits = splitter.split_documents(docs)
    if not splits:
        print("No document splits created.")
        return
    enriched = [
        Document(
            page_content=d.page_content,
            metadata={k: v for k, v in d.metadata.items() if v not in ("", None)}
        )
        for d in splits
    ]
    ids = [f"doc-{i}" for i in range(len(enriched))]
    embedding_model = get_embedding_model()
    store = PGVector(
        embeddings=embedding_model,
        collection_name=os.getenv("PG_VECTOR_COLLECTION_NAME"),
        connection=os.getenv("DATABASE_URL"),
        use_jsonb=True,
    )
    store.add_documents(documents=enriched, ids=ids)
    print(f"{len(enriched)} documents ingested successfully.")

if __name__ == "__main__":
    ingest_pdf()