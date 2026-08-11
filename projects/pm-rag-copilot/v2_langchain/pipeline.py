"""
Version 2: LangChain RAG Pipeline
Rebuilds the manual RAG pipeline using LangChain's standard loaders, splitters, Chroma, and LCEL chain.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


class LangChainRAGPipeline:
    """RAG pipeline implemented using LangChain components."""

    def __init__(
        self,
        data_dir: str,
        persist_dir: str,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.1"
    ):
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.embedding_model_name = embedding_model_name
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model

        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        self.vector_store = None
        self.retriever = None
        self.chain = None

    def ingest_documents(self):
        """Loads, splits, embeds, and indexes documents into Chroma in a few lines of code."""
        # 1. Load files from directory
        loader = DirectoryLoader(
            self.data_dir,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        docs = loader.load()

        # 2. Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=450, chunk_overlap=60)
        chunks = text_splitter.split_documents(docs)

        # 3 & 4. Embed chunks and save to ChromaDB
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.persist_dir,
            collection_name="jira_docs_langchain"
        )

    def load_existing_vector_store(self):
        """Loads existing Chroma vector store from disk."""
        self.vector_store = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings,
            collection_name="jira_docs_langchain"
        )

    def build_chain(self):
        """Builds LCEL chain: Retriever -> PromptTemplate -> OllamaLLM -> OutputParser."""
        if self.vector_store is None:
            self.load_existing_vector_store()

        self.retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 3, "score_threshold": 0.3}
        )

        template = (
            "You are a helpful PM Copilot assisting product managers with Jira documentation.\n"
            "Answer the user's question using ONLY the provided Jira documentation context below.\n"
            "If the context does not contain enough information to answer the question accurately, "
            "state: 'I couldn't find enough information in the available Jira documentation to answer this.'\n"
            "Do NOT make up information or rely on external knowledge not present in the context.\n\n"
            "=== RETRIEVED JIRA DOCUMENTATION CONTEXT ===\n"
            "{context}\n"
            "===========================================\n\n"
            "User Question: {question}\n\n"
            "Answer:"
        )

        prompt = PromptTemplate(template=template, input_variables=["context", "question"])
        llm = OllamaLLM(base_url=self.ollama_base_url, model=self.ollama_model, temperature=0.1)

        def format_docs(docs):
            if not docs:
                return "[No relevant documentation found.]"
            return "\n\n".join(
                f"--- Context Chunk (Source: {os.path.basename(doc.metadata.get('source', 'Unknown'))}) ---\n{doc.page_content}"
                for doc in docs
            )

        # Connect components using LangChain Expression Language (LCEL) pipe syntax
        self.chain = (
            {"context": self.retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

    def answer_question(self, question: str) -> Dict[str, Any]:
        """Runs the question through the chain and returns answer and sources."""
        if self.chain is None:
            self.build_chain()

        retrieved_docs = self.retriever.invoke(question)

        if not retrieved_docs:
            return {
                "answer": "I couldn't find enough information in the available Jira documentation to answer this.",
                "sources": "None"
            }

        answer = self.chain.invoke(question)
        sources = list(set([os.path.basename(doc.metadata.get("source", "Unknown")) for doc in retrieved_docs]))
        formatted_sources = "\n".join(f"- {s}" for s in sources)

        return {
            "answer": answer,
            "sources": formatted_sources,
            "retrieved_docs": retrieved_docs
        }
