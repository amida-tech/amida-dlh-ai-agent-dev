import os
from typing import Optional
import logging
import aiofiles

logger = logging.getLogger(__name__)


class FileProcessor:
    """
    Service for processing uploaded files and extracting text content
    """
    
    def __init__(self):
        self.supported_extensions = {
            '.txt': self._read_text_file,
            '.md': self._read_text_file,
            '.py': self._read_text_file,
            '.js': self._read_text_file,
            '.ts': self._read_text_file,
            '.json': self._read_text_file,
            '.csv': self._read_text_file,
            '.xml': self._read_text_file,
            '.html': self._read_text_file,
            '.pdf': self._read_pdf_file,
            '.docx': self._read_docx_file,
        }
    
    async def extract_text(self, file_path: str) -> str:
        """
        Extract text content from a file based on its extension
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        try:
            processor_func = self.supported_extensions[file_extension]
            content = await processor_func(file_path)
            return content
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise
    
    async def _read_text_file(self, file_path: str) -> str:
        """
        Read plain text files
        """
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
                return content
        except UnicodeDecodeError:
            # Try with different encoding
            async with aiofiles.open(file_path, 'r', encoding='latin-1') as file:
                content = await file.read()
                return content
    
    async def _read_pdf_file(self, file_path: str) -> str:
        """
        Extract text from PDF files using PyPDF
        """
        try:
            import pypdf
            
            text_content = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content.append(page.extract_text())
            
            return '\n'.join(text_content)
            
        except ImportError:
            raise ValueError("PyPDF library not installed. Cannot process PDF files.")
        except Exception as e:
            logger.error(f"Error reading PDF file: {str(e)}")
            raise ValueError(f"Could not read PDF file: {str(e)}")
    
    async def _read_docx_file(self, file_path: str) -> str:
        """
        Extract text from DOCX files using python-docx
        """
        try:
            from docx import Document
            
            doc = Document(file_path)
            text_content = []
            
            for paragraph in doc.paragraphs:
                text_content.append(paragraph.text)
            
            return '\n'.join(text_content)
            
        except ImportError:
            raise ValueError("python-docx library not installed. Cannot process DOCX files.")
        except Exception as e:
            logger.error(f"Error reading DOCX file: {str(e)}")
            raise ValueError(f"Could not read DOCX file: {str(e)}")
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get information about a file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat_info = os.stat(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        return {
            "filename": os.path.basename(file_path),
            "extension": file_extension,
            "size_bytes": stat_info.st_size,
            "size_mb": round(stat_info.st_size / (1024 * 1024), 2),
            "is_supported": file_extension in self.supported_extensions,
            "modified_time": stat_info.st_mtime
        }
    
    def is_supported_file(self, filename: str) -> bool:
        """
        Check if a file type is supported for processing
        """
        file_extension = os.path.splitext(filename)[1].lower()
        return file_extension in self.supported_extensions
    
    def get_supported_extensions(self) -> list:
        """
        Get list of supported file extensions
        """
        return list(self.supported_extensions.keys())