from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter 
from langchain_core.pydantic_v1 import BaseModel
from pydantic import BaseModel

DATA_PATH = 'data/'
DB_FAISS_PATH = 'vectorstore/db_faiss'

# Create vector database
def create_vector_db():
    loader = DirectoryLoader(DATA_PATH, glob='*.pdf', loader_cls=PyPDFLoader)

    try:
        documents = loader.load()
    except Exception as e:
        print(f"Error loading documents: {e}")
        return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    try:
        texts = text_splitter.split_documents(documents)
    except Exception as e:
        print(f"Error splitting documents: {e}")
        return

    try:
        embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2',
                                           model_kwargs={'device': 'cpu'})
        db = FAISS.from_documents(texts, embeddings)
        db.save_local(DB_FAISS_PATH)
    except Exception as e:
        print(f"Error creating or saving vector database: {e}")

if __name__ == "__main__":
    create_vector_db()