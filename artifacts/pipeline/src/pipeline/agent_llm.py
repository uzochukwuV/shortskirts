"""
Agent LLM client using TokenRouter.

TokenRouter provides unified access to multiple LLM providers.
This module provides async chat functionality for the agent orchestrator.
"""

from __future__ import annotations

import os
import json
from typing import Any, Optional
from dataclasses import dataclass, field

import httpx


TOKENROUTER_API_URL = os.getenv("TOKENROUTER_API_URL", "https://api.tokenrouter.com/v1")
TOKENROUTER_MODEL = os.getenv("TOKENROUTER_MODEL", "moonshotai/kimi-k3-free")
TOKENROUTER_API_KEY = os.getenv("TOKENROUTER_API_KEY", "")


@dataclass
class ChatMessage:
    """A chat message."""
    role: str
    content: str
    name: Optional[str] = None


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    name: str
    arguments: dict[str, Any]
    id: str = ""


@dataclass
class ChatResponse:
    """Response from chat completion."""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"


class AgentLLMError(Exception):
    """Error from agent LLM operations."""
    pass


class TokenRouterClient:
    """
    Async client for TokenRouter API.
    
    TokenRouter provides unified access to multiple LLM providers
    with a single API key.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or TOKENROUTER_API_KEY
        self.base_url = base_url or TOKENROUTER_API_URL
        self.model = model or TOKENROUTER_MODEL
        
        if not self.api_key:
            raise AgentLLMError("TOKENROUTER_API_KEY is required")
    
    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def chat(
        self,
        messages: list[ChatMessage | dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
    ) -> ChatResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of chat messages (can be ChatMessage objects or dicts)
            model: Override default model
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            tools: Optional list of tool definitions for function calling
            tool_choice: "auto", "none", or "required"
        
        Returns:
            ChatResponse with content and optional tool calls
        """
        # Convert messages to dict format
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
                if msg.name:
                    formatted_messages[-1]["name"] = msg.name
            else:
                formatted_messages.append(msg)
        
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                raise AgentLLMError(f"HTTP error {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                raise AgentLLMError(f"Request error: {e}")
        
        # Parse response
        choices = data.get("choices", [])
        if not choices:
            return ChatResponse(content="", tool_calls=[], finish_reason="empty")
        
        choice = choices[0]
        message = choice.get("message", {})
        
        # Get content - handle cases where it's null
        content = message.get("content") or ""
        finish_reason = choice.get("finish_reason", "stop")
        
        # Skip reasoning content if content is empty
        if not content and message.get("reasoning_content"):
            content = message.get("reasoning_content", "")
        
        # Parse tool calls if present
        tool_calls = []
        raw_tool_calls = message.get("tool_calls", [])
        for tc in raw_tool_calls:
            func = tc.get("function", {})
            arguments_str = func.get("arguments", "{}")
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append(ToolCall(
                name=func.get("name", ""),
                arguments=arguments,
                id=tc.get("id", ""),
            ))
        
        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )
    
    async def chat_simple(
        self,
        messages: list[ChatMessage | dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Simple chat that returns just the content string.
        """
        response = await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content


# Global client instance (lazy initialization)
_agent_llm: Optional[TokenRouterClient] = None


def get_agent_llm() -> TokenRouterClient:
    """Get or create the global TokenRouter client."""
    global _agent_llm
    if _agent_llm is None:
        _agent_llm = TokenRouterClient()
    return _agent_llm


async def agent_chat(
    messages: list[ChatMessage | dict],
    **kwargs,
) -> ChatResponse:
    """
    Convenience function for agent chat using the global client.
    """
    client = get_agent_llm()
    return await client.chat(messages, **kwargs)


async def agent_chat_simple(
    messages: list[ChatMessage | dict],
    **kwargs,
) -> str:
    """
    Convenience function for simple agent chat.
    """
    response = await agent_chat(messages, **kwargs)
    return response.content
