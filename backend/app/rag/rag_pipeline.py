"""RAG Pipeline for KnowledgePilot AI."""

import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

import structlog
from google import genai
from google.genai import types
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from app.config import settings
from app.rag.prompt_builder import PromptBuilder
from app.rag.retriever import Retriever
from app.schemas.chat import SourceCitation

logger = structlog.get_logger()


@dataclass
class RAGResponse:
    """Response from RAG pipeline."""
    
    content: str
    sources: list[SourceCitation] = field(default_factory=list)
    confidence_score: float = 0.0
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    response_time_ms: int = 0
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)


class RAGPipeline:
    """Orchestrates the RAG process."""
    
    def __init__(
        self,
        retriever: Retriever | None = None,
        prompt_builder: PromptBuilder | None = None,
        model: str | None = None,
        provider: str | None = None,
    ):
        self.retriever = retriever or Retriever()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.provider = provider or settings.llm_provider
        self.model = model or settings.model_for_provider(self.provider)

        # Initialize LLM clients
        self._openai_client: AsyncOpenAI | None = None
        self._anthropic_client: AsyncAnthropic | None = None
        self._google_client: genai.Client | None = None

    def _has_llm_configured(self) -> bool:
        """Check if the active provider has a valid API key."""
        if self.provider == "google":
            return settings.has_valid_google_key
        if self.provider == "anthropic":
            key = settings.anthropic_api_key
            return bool(key and key.strip())
        return settings.has_valid_openai_key

    def _ensure_llm_configured(self) -> None:
        """Log a warning if no LLM API key is configured."""
        if not self._has_llm_configured():
            logger.warning(
                "No LLM API key configured for provider '%s'. Falling back to local mock responses.",
                self.provider,
            )
    
    async def _generate_mock(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> str:
        """Generate a simulated response using retrieved context for demo purposes."""
        if not retrieved_chunks:
            return self.prompt_builder.NO_CONTEXT_RESPONSE
            
        best_chunks = retrieved_chunks[:3]
        response_parts = [
            f"### 📝 AI Answer (Local Demo Mode — No API Key Configured)\n\n"
            f"Based on your query *\"{question}\"*, here is the relevant information extracted from your knowledge base:\n"
        ]
        
        for i, chunk in enumerate(best_chunks, start=1):
            meta = chunk.get("metadata", {})
            doc_name = meta.get("document_name", meta.get("file_name", "Document"))
            page_num = meta.get("page_number", "N/A")
            score = chunk.get("score", 0.0)
            content = chunk.get("content", "").strip()
            
            # Simple chunk presentation
            response_parts.append(
                f"#### [{i}] {doc_name} (Page {page_num}) — *Similarity: {score:.1%}*\n"
                f"> {content[:400]}...\n"
            )
            
        response_parts.append(
            "\n*Note: Configure `GOOGLE_API_KEY` (free at https://aistudio.google.com/apikey) "
            "or `OPENAI_API_KEY` in `backend/.env` for real AI answers.*"
        )
        return "\n".join(response_parts)
    
    def _no_context_response(self, start_time: float) -> RAGResponse:
        """Return a response when no relevant documents are found."""
        return RAGResponse(
            content=self.prompt_builder.NO_CONTEXT_RESPONSE,
            sources=[],
            confidence_score=0.0,
            model_used="none",
            response_time_ms=int((time.time() - start_time) * 1000),
        )
    
    def _get_google_client(self) -> genai.Client:
        """Get or create Google Gemini client."""
        if self._google_client is None:
            self._google_client = genai.Client(api_key=settings.google_api_key)
        return self._google_client

    def _split_messages_for_gemini(
        self,
        messages: list[dict[str, str]],
    ) -> tuple[str, str]:
        """Extract system instruction and user content from OpenAI-style messages."""
        system_content = ""
        user_content = ""

        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user":
                user_content = msg["content"]
            elif msg["role"] == "assistant":
                user_content = f"{user_content}\n\nAssistant: {msg['content']}".strip()

        return system_content, user_content

    def _gemini_generate_config(
        self,
        system_content: str,
        temperature: float,
    ) -> types.GenerateContentConfig:
        """Build Gemini generation config."""
        return types.GenerateContentConfig(
            system_instruction=system_content or None,
            temperature=temperature,
            max_output_tokens=2000,
        )

    def _usage_from_gemini(self, response) -> dict[str, int]:
        """Extract token usage from a Gemini response."""
        usage_meta = getattr(response, "usage_metadata", None)
        if not usage_meta:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage_meta, "total_token_count", 0) or (
            prompt_tokens + completion_tokens
        )
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    def _get_openai_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client."""
        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai_client
    
    def _get_anthropic_client(self) -> AsyncAnthropic:
        """Get or create Anthropic client."""
        if self._anthropic_client is None:
            self._anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._anthropic_client
    
    async def query(
        self,
        question: str,
        user_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        document_ids: list[str] | None = None,
        top_k: int | None = None,
        temperature: float = 0.7,
    ) -> RAGResponse:
        """Execute RAG query.
        
        Args:
            question: The user's question.
            user_id: The user's ID for filtering.
            conversation_history: Optional conversation history.
            document_ids: Optional specific document IDs to search.
            top_k: Number of chunks to retrieve.
            temperature: LLM temperature.
            
        Returns:
            RAGResponse with answer and metadata.
        """
        start_time = time.time()
        
        logger.info("Starting RAG query", question=question[:100], user_id=user_id)
        
        self._ensure_llm_configured()
        
        # Step 1: Retrieve relevant chunks
        retrieved_chunks = await self.retriever.retrieve(
            query=question,
            top_k=top_k,
            filter_user_id=user_id,
            filter_document_ids=document_ids,
        )
        
        # Step 2: Rerank if enabled
        if settings.rag_rerank_enabled and retrieved_chunks:
            retrieved_chunks = await self.retriever.rerank(
                query=question,
                results=retrieved_chunks,
                top_k=top_k,
            )
        
        # Step 3: Calculate confidence
        confidence_score = self.retriever.calculate_confidence(retrieved_chunks)
        
        # Step 4: Build prompt / Fallback to Mock
        if not self._has_llm_configured():
            response_content = await self._generate_mock(question, retrieved_chunks)
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        else:
            messages = self.prompt_builder.build_messages(
                question=question,
                retrieved_chunks=retrieved_chunks,
                conversation_history=conversation_history,
            )
            
            if not messages:
                return self._no_context_response(start_time)
            
            # Step 5: Generate response
            if self.provider == "google":
                response_content, usage = await self._generate_google(
                    messages=messages,
                    temperature=temperature,
                )
            elif self.provider == "anthropic":
                response_content, usage = await self._generate_anthropic(
                    messages=messages,
                    temperature=temperature,
                )
            else:
                response_content, usage = await self._generate_openai(
                    messages=messages,
                    temperature=temperature,
                )
        
        # Step 6: Build source citations
        sources = self._build_citations(retrieved_chunks)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "RAG query completed",
            response_time_ms=response_time_ms,
            sources_count=len(sources),
            confidence=confidence_score,
        )
        
        return RAGResponse(
            content=response_content,
            sources=sources,
            confidence_score=confidence_score,
            model_used=self.model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            response_time_ms=response_time_ms,
            retrieved_chunks=retrieved_chunks,
        )
    
    async def query_stream(
        self,
        question: str,
        user_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        document_ids: list[str] | None = None,
        top_k: int | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute RAG query with streaming response.
        
        Yields:
            Dictionaries with type and content/source/metadata.
        """
        start_time = time.time()
        
        self._ensure_llm_configured()
        
        # Step 1: Retrieve
        retrieved_chunks = await self.retriever.retrieve(
            query=question,
            top_k=top_k,
            filter_user_id=user_id,
            filter_document_ids=document_ids,
        )
        
        # Step 2: Rerank
        if settings.rag_rerank_enabled and retrieved_chunks:
            retrieved_chunks = await self.retriever.rerank(
                query=question,
                results=retrieved_chunks,
                top_k=top_k,
            )
        
        # Step 3: Calculate confidence
        confidence_score = self.retriever.calculate_confidence(retrieved_chunks)
        
        # Step 4: Build prompt / Fallback to Mock
        if not self._has_llm_configured():
            # Step 5: Stream mock response
            import asyncio
            mock_content = await self._generate_mock(question, retrieved_chunks)
            words = mock_content.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3]) + " "
                await asyncio.sleep(0.04)
                yield {"type": "content", "content": chunk}
        else:
            messages = self.prompt_builder.build_messages(
                question=question,
                retrieved_chunks=retrieved_chunks,
                conversation_history=conversation_history,
            )
            
            if not messages:
                yield {"type": "content", "content": self.prompt_builder.NO_CONTEXT_RESPONSE}
                yield {"type": "done", "confidence_score": 0.0, "response_time_ms": int((time.time() - start_time) * 1000), "model_used": "none"}
                return
            
            # Step 5: Stream response
            if self.provider == "google":
                async for chunk in self._stream_google(messages, temperature):
                    yield {"type": "content", "content": chunk}
            elif self.provider == "anthropic":
                async for chunk in self._stream_anthropic(messages, temperature):
                    yield {"type": "content", "content": chunk}
            else:
                async for chunk in self._stream_openai(messages, temperature):
                    yield {"type": "content", "content": chunk}
        
        # Step 6: Yield sources
        sources = self._build_citations(retrieved_chunks)
        for source in sources:
            yield {"type": "source", "source": source.model_dump()}
        
        # Step 7: Yield completion
        response_time_ms = int((time.time() - start_time) * 1000)
        
        yield {
            "type": "done",
            "confidence_score": confidence_score,
            "response_time_ms": response_time_ms,
            "model_used": self.model,
        }
    
    async def _generate_google(
        self,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> tuple[str, dict[str, int]]:
        """Generate response using Google Gemini."""
        client = self._get_google_client()
        system_content, user_content = self._split_messages_for_gemini(messages)

        response = await client.aio.models.generate_content(
            model=self.model,
            contents=user_content,
            config=self._gemini_generate_config(system_content, temperature),
        )

        content = response.text or ""
        return content, self._usage_from_gemini(response)

    async def _generate_openai(
        self,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> tuple[str, dict[str, int]]:
        """Generate response using OpenAI."""
        client = self._get_openai_client()
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
        
        return content, usage
    
    async def _generate_anthropic(
        self,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> tuple[str, dict[str, int]]:
        """Generate response using Anthropic."""
        client = self._get_anthropic_client()
        
        # Extract system message
        system_content = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                user_messages.append(msg)
        
        response = await client.messages.create(
            model=self.model,
            system=system_content,
            messages=user_messages,
            temperature=temperature,
            max_tokens=2000,
        )
        
        content = response.content[0].text if response.content else ""
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }
        
        return content, usage
    
    async def _stream_openai(
        self,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI."""
        client = self._get_openai_client()
        
        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=2000,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _stream_google(
        self,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream response from Google Gemini."""
        client = self._get_google_client()
        system_content, user_content = self._split_messages_for_gemini(messages)

        stream = await client.aio.models.generate_content_stream(
            model=self.model,
            contents=user_content,
            config=self._gemini_generate_config(system_content, temperature),
        )

        async for chunk in stream:
            if chunk.text:
                yield chunk.text

    async def _stream_anthropic(
        self,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream response from Anthropic."""
        client = self._get_anthropic_client()
        
        # Extract system message
        system_content = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                user_messages.append(msg)
        
        async with client.messages.stream(
            model=self.model,
            system=system_content,
            messages=user_messages,
            temperature=temperature,
            max_tokens=2000,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    def _build_citations(
        self,
        retrieved_chunks: list[dict[str, Any]],
    ) -> list[SourceCitation]:
        """Build source citations from retrieved chunks."""
        citations = []
        
        for chunk in retrieved_chunks:
            metadata = chunk.get("metadata", {})
            
            citation = SourceCitation(
                document_id=metadata.get("document_id", ""),
                document_name=metadata.get("document_name", metadata.get("file_name", "Unknown")),
                chunk_id=chunk.get("id", ""),
                content=chunk.get("content", "")[:500],  # Truncate for display
                page_number=metadata.get("page_number"),
                relevance_score=chunk.get("score", 0.0),
            )
            citations.append(citation)
        
        return citations
