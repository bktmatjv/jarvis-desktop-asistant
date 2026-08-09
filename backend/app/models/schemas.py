"""
Pydantic schemas for the WebSocket protocol.
Defines the structure for messages sent between the Client and the Server.
"""
from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict, Any


class HandshakeRequest(BaseModel):
    type: Literal["handshake"] = "handshake"
    client_id: str
    os: str
    capabilities: List[str]

class MessageRequest(BaseModel):
    type: Literal["message"] = "message"
    content: str

class ToolResultRequest(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_call_id: str
    output: Optional[str] = None
    error: Optional[str] = None


class ToolCallResponse(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool_call_id: str
    tool: Literal["execute_bash"] = "execute_bash"
    command: str

class SpeakResponse(BaseModel):
    type: Literal["speak"] = "speak"
    message: str
