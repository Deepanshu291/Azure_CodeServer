from pydantic import BaseModel
from fastapi.requests import Request
from typing import Optional

class Iuser(BaseModel):
    username: str
    password: str
    github_url: Optional[str] = "https://github.com/microsoft/vscode-remote-try-python"
    vscode_url: Optional[str] = None 
