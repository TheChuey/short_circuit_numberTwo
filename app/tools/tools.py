# The model backend functions live in build/class_definition.py.
# ask_llm is re-exported here so the public name
# `from app.tools.tools import ask_llm` keeps working.
from build.class_definition import ask_llm
from datetime import datetime
import os
import subprocess

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# ==========================================
# WORKSPACE TOOLS
# ==========================================

def create_folder(folder_path: str) -> str:
    """Creates a directory at the specified path."""
    os.makedirs(folder_path, exist_ok=True)
    return f"Folder successfully created at: {folder_path}"

def create_file(file_path: str, content: str = "") -> str:
    """Creates a new file with optional initial content."""
    print("create a file -------------------------")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"File successfully created at: {file_path}"

def setup_venv(env_dir: str = ".venv") -> str:
    """Creates a Python virtual environment (.venv)."""
    subprocess.run(["python", "-m", "venv", env_dir], check=True)
    return f"Virtual environment created at: {env_dir}"

def read_file(file_path: str) -> str:
    """Reads and returns the contents of a text file."""
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(file_path: str, content: str) -> str:
    """Writes or overwrites text content to a file."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Content successfully written to: {file_path}"

def read_pdf(pdf_path: str) -> str:
    """Extracts text contents from a PDF file."""
    if not PdfReader:
        return "Error: pypdf is not installed. Install via `pip install pypdf`."
    if not os.path.exists(pdf_path):
        return f"Error: PDF '{pdf_path}' does not exist."
    
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

# ==========================================
# TEST TOOL
# ==========================================
def tell_me_the_date_and_time() -> str:
    """Returns the current date and time."""
    now = datetime.now()
    return f"The current date and time is {now.strftime('%Y-%m-%d %H:%M:%S')}"

def get_current_date() -> str:
    """Returns the real current date as a formatted string."""
    return datetime.now().strftime("%A, %B %d, %Y")


# SKILL_REGISTRY exposes our available tools to the agents.
# To add a tool, define the function above and add it here.
SKILL_REGISTRY = {
    "create_folder": create_folder,
    "create_file": create_file,
    "setup_venv": setup_venv,
    "read_file": read_file,
    "write_file": write_file,
    "read_pdf": read_pdf,
    "get_current_date": get_current_date,
    "tell_me_the_date_and_time": tell_me_the_date_and_time
}
