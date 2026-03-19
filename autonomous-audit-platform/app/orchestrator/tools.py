from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os

class FileWriterInput(BaseModel):
    """Input for FileWriterTool."""
    file_path: str = Field(..., description="The full path where the file should be saved.")
    content: str = Field(..., description="The content to write to the file.")

class FileWriterTool(BaseTool):
    name: str = "file_writer_tool"
    description: str = "Writes content to a file at a specific path. Creates directories if they don't exist."
    args_schema: Type[BaseModel] = FileWriterInput

    def _run(self, file_path: str, content: str) -> str:
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
