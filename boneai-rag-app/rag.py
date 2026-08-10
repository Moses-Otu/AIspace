import os
import tempfile
from io import BytesIO
from typing import List
from PIL import Image
from dotenv import load_dotenv

from azure.storage.blob import BlobServiceClient
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain.schema import Document
from langchain_pinecone import Pinecone as LangchainPinecone

from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai

# Load environment variables
load_dotenv()
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Constants
DOC_EXTENSIONS = [".pdf", ".docx", ".txt"]
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
PROCESSED_LOG = "processed_files.txt"

# Gemini setup
genai.configure(api_key=GOOGLE_API_KEY)
vision_model = genai.GenerativeModel("gemini-1.5-flash")


class AzureDataIngestor:
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        self.container_client = self.blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

    def list_files(self) -> List[str]:
        return [
            blob.name for blob in self.container_client.list_blobs()
            if any(blob.name.lower().endswith(ext) for ext in DOC_EXTENSIONS + IMAGE_EXTENSIONS)
        ]

    def download_file(self, blob_name: str):
        blob_client = self.container_client.get_blob_client(blob_name)
        stream = blob_client.download_blob()
        return stream.readall(), blob_name


class SimpleRAG:
    def __init__(self):
        self.data_ingestor = AzureDataIngestor()
        self.embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            openai_api_version="2023-05-15"
        )
        self.index_name = "developer-quickstart-py"
        self.vectorstore = self._init_pinecone_vectorstore()
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.processed_files = self._load_processed_files()

    def _init_pinecone_vectorstore(self):
        pc = Pinecone(api_key=PINECONE_API_KEY)
        if not pc.has_index(self.index_name):
            print("🔧 Creating Pinecone index...")
            pc.create_index(
                name=self.index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        return LangchainPinecone.from_existing_index(index_name=self.index_name, embedding=self.embeddings)

    def _load_processed_files(self) -> set:
        if os.path.exists(PROCESSED_LOG):
            with open(PROCESSED_LOG, "r") as f:
                return set(line.strip() for line in f.readlines())
        return set()

    def _save_processed_file(self, filename: str):
        with open(PROCESSED_LOG, "a") as f:
            f.write(filename + "\n")

    def embed_documents(self):
        all_files = self.data_ingestor.list_files()
        new_files = [f for f in all_files if f not in self.processed_files]

        if not new_files:
            print("✅ No new files to process.")
            return

        print(f"🔍 Found {len(new_files)} new files to process")
        documents = []

        for file_path in new_files:
            try:
                content, name = self.data_ingestor.download_file(file_path)
                print(f"📄 Processing: {name}")
                suffix = os.path.splitext(name)[1].lower()

                if suffix in DOC_EXTENSIONS:
                    documents.extend(self._process_text_file(content, name, suffix))
                elif suffix in IMAGE_EXTENSIONS:
                    documents.append(self._process_image_file(content, name))

                self._save_processed_file(file_path)

            except Exception as e:
                print(f"❌ Failed to process {file_path}: {str(e)}")

        if documents:
            print(f"🧩 Adding {len(documents)} chunks to Pinecone...")
            self.vectorstore.add_documents(documents)
            print("✅ Embedding completed successfully!")
            self._log_sample_documents(documents)
        else:
            print("⚠️ No documents were processed.")

    def _process_text_file(self, content: bytes, name: str, suffix: str) -> List[Document]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            if suffix == ".pdf":
                loader = PyPDFLoader(tmp_path)
            elif suffix == ".docx":
                loader = Docx2txtLoader(tmp_path)
            else:
                return [Document(page_content=content.decode("utf-8"), metadata={"source": name})]

            docs = loader.load()
            split_docs = []
            for doc in docs:
                doc.metadata.update({"source": name, "file_type": suffix[1:].upper()})
                split_docs.extend(self.text_splitter.split_documents([doc]))
            return split_docs
        except Exception as e:
            print(f"❌ Failed to load {name}: {str(e)}")
            return []
        finally:
            os.unlink(tmp_path)

    def _process_image_file(self, content: bytes, name: str) -> Document:
        try:
            image = Image.open(BytesIO(content)).convert("RGB")
            caption = self._generate_image_caption(image)
            return Document(
                page_content=f"IMAGE CAPTION: {caption}",
                metadata={"source": name, "file_type": "IMAGE", "caption": caption}
            )
        except Exception as e:
            print(f"❌ Failed to process image {name}: {str(e)}")
            return Document(
                page_content="IMAGE CAPTION: [Unable to process image]",
                metadata={"source": name, "file_type": "IMAGE"}
            )

    def _generate_image_caption(self, image: Image.Image) -> str:
        try:
            response = vision_model.generate_content([
                "Describe this image in detail, including text, objects, colors, and context. Be concise:",
                image
            ])
            return response.text.strip()
        except Exception as e:
            print(f"⚠️ Image captioning failed: {str(e)}")
            return "Image caption unavailable"

    def _log_sample_documents(self, docs: List[Document]):
        print("\n📝 Sample Documents:")
        for i, doc in enumerate(docs[:3]):
            print(f"\nDocument {i + 1}:")
            print(f"Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"Type: {doc.metadata.get('file_type', 'Unknown')}")
            print(f"Content: {doc.page_content[:200]}...")


if __name__ == "__main__":
    print("🚀 Starting RAG processing pipeline...")
    rag = SimpleRAG()
    rag.embed_documents()
