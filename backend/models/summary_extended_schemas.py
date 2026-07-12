"""Extended schemas for mind map and AI Q&A (additive module)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MindMapNode(BaseModel):
    label: str
    children: list["MindMapNode"] = Field(default_factory=list)


class MindMapRequest(BaseModel):
    task_id: str


class MindMapResponse(BaseModel):
    root: MindMapNode


class ChatMessage(BaseModel):
    role: str
    content: str


class SummaryChatRequest(BaseModel):
    task_id: str
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class SummaryChatResponse(BaseModel):
    reply: str
