"""
STEP 1: Document Loader
Reads raw markdown (.md) files from disk and loads them into memory with source metadata.
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class Document:
    """Stores the text content and metadata (filename, title) of a loaded document."""
    page_content: str
    metadata: Dict[str, Any]


class DocumentLoader:
    """Loads all markdown files from the raw data directory."""

    def __init__(self, raw_data_dir: str):
        self.raw_data_dir = raw_data_dir

    def load_documents(self) -> List[Document]:
        """Scans the directory for .md files and returns a list of Document objects."""
        documents: List[Document] = []
        if not os.path.exists(self.raw_data_dir):
            raise FileNotFoundError(f"Raw data directory not found: {self.raw_data_dir}")

        for root, _, files in os.walk(self.raw_data_dir):
            for file_name in sorted(files):
                if file_name.endswith(".md"):
                    file_path = os.path.join(root, file_name)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Extract title from the first header line if available
                    lines = content.strip().splitlines()
                    title = lines[0].lstrip("#").strip() if lines and lines[0].startswith("#") else file_name

                    metadata = {
                        "source": file_name,
                        "title": title,
                        "file_path": file_path
                    }
                    documents.append(Document(page_content=content, metadata=metadata))

        return documents
