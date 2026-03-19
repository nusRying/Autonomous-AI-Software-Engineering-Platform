"""
LLM Adapters: wraps call_llm() for use in LlamaIndex and CrewAI.
"""
from typing import Any, Optional, Sequence
from llama_index.core.llms import (
    CustomLLM,
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata,
)
from app.api_manager.rotator import call_llm
from sqlalchemy.ext.asyncio import AsyncSession

class LlamaIndexRotatorLLM(CustomLLM):
    """
    A custom LlamaIndex LLM that uses our centralized call_llm() logic.
    """
    db: AsyncSession
    provider: str
    model_name: str

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            model_name=self.model_name,
            is_chat_model=True,
        )

    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        messages = [{"role": "user", "content": prompt}]
        response_text = await call_llm(
            db=self.db,
            messages=messages,
            provider=self.provider,
            model=self.model_name
        )
        return CompletionResponse(text=response_text)

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        # LlamaIndex sometimes calls synchronous complete().
        # We wrap the async call since call_llm depends on AsyncSession.
        import asyncio
        return asyncio.run(self.acomplete(prompt, **kwargs))

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

class CrewAIRotatorLLM(BaseChatModel):
    """
    A LangChain-compatible ChatModel that uses our centralized call_llm() logic.
    Works perfectly with CrewAI Agents.
    """
    db: AsyncSession
    provider: str
    model_name: str

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # CrewAI calls this synchronously.
        import asyncio
        import nest_asyncio
        nest_asyncio.apply() # CrewAI might be running in a thread with its own loop

        # Convert LangChain messages to LiteLLM format
        formatted_messages = []
        for m in messages:
            role = "user"
            if m.type == "ai": role = "assistant"
            elif m.type == "system": role = "system"
            formatted_messages.append({"role": role, "content": m.content})

        # Run async call_llm synchronously
        response_text = asyncio.run(call_llm(
            db=self.db,
            messages=formatted_messages,
            provider=self.provider,
            model=self.model_name
        ))

        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "rotator-llm"
