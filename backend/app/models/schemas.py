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
    username: str = "Invitado"
    role: str = "user"
    device_name: str = "Unknown"

class ClientInfo(BaseModel):
    client_id: str
    os: str
    device_name: str
    
class UserClients(BaseModel):
    username: str
    role: str
    devices: List[ClientInfo]

class SystemStatusResponse(BaseModel):
    type: Literal["system_status"] = "system_status"
    total_clients: int
    users: List[UserClients]

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
    tool: str
    command: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    skill_name: Optional[str] = None

class SpeakResponse(BaseModel):
    type: Literal["speak"] = "speak"
    message: str

class ThinkingResponse(BaseModel):
    """Sent to the client while the reasoning model works in the background.
    The client should speak this phrase via TTS immediately."""
    type: Literal["thinking"] = "thinking"
    message: str

class TaskPlanResponse(BaseModel):
    type: Literal["task_plan"] = "task_plan"
    title: str
    steps: List[str]

class TaskUpdateResponse(BaseModel):
    type: Literal["task_update"] = "task_update"
    step_index: int
    status: Literal["in_progress", "completed", "failed"]
