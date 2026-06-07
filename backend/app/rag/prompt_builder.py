"""Prompt builder for RAG pipeline."""

from dataclasses import dataclass
from typing import Any


@dataclass
class PromptTemplate:
    """Represents a prompt template."""
    
    system: str
    user: str
    
    def format_system(self, **kwargs) -> str:
        """Format the system prompt."""
        return self.system.format(**kwargs)
    
    def format_user(self, **kwargs) -> str:
        """Format the user prompt."""
        return self.user.format(**kwargs)


class PromptBuilder:
    """Builds prompts for RAG queries."""
    
    SYSTEM_PROMPT = """You are KnowledgePilot AI, an intelligent technical knowledge assistant.

Your role is to answer questions using ONLY the information provided in the retrieved documents below.

## Critical Rules:
1. ONLY use information from the provided context documents
2. NEVER make up or hallucinate information
3. If the context doesn't contain enough information to answer, say: "I could not find this information in the knowledge base."
4. Always cite your sources using [Source: document_name, Page: X] format
5. Be precise, technical, and helpful
6. If multiple documents provide relevant information, synthesize them coherently
7. Maintain a professional, knowledgeable tone

## Response Format:
- Start with a direct answer to the question
- Provide supporting details from the documents
- Include citations for each piece of information
- End with a confidence indicator if relevant

## Retrieved Context:
{context}
"""

    USER_PROMPT = """Question: {question}

Please provide a comprehensive answer based solely on the retrieved documents above."""

    CONVERSATION_SYSTEM_PROMPT = """You are KnowledgePilot AI, an intelligent technical knowledge assistant.

Your role is to answer questions using ONLY the information provided in the retrieved documents below.

## Critical Rules:
1. ONLY use information from the provided context documents
2. NEVER make up or hallucinate information
3. If the context doesn't contain enough information to answer, say: "I could not find this information in the knowledge base."
4. Always cite your sources using [Source: document_name, Page: X] format
5. Be precise, technical, and helpful
6. Consider the conversation history for context
7. Maintain a professional, knowledgeable tone

## Retrieved Context:
{context}

## Conversation History:
{history}
"""

    NO_CONTEXT_RESPONSE = """I could not find relevant information in the knowledge base to answer your question.

Please try:
- Rephrasing your question
- Asking about a different topic covered in your uploaded documents
- Uploading additional documents that might contain the information you need"""

    def __init__(self):
        self.templates = {
            "default": PromptTemplate(
                system=self.SYSTEM_PROMPT,
                user=self.USER_PROMPT,
            ),
            "conversation": PromptTemplate(
                system=self.CONVERSATION_SYSTEM_PROMPT,
                user=self.USER_PROMPT,
            ),
        }
    
    def build_context(
        self,
        retrieved_chunks: list[dict[str, Any]],
        max_tokens: int = 4000,
    ) -> str:
        """Build context string from retrieved chunks.
        
        Args:
            retrieved_chunks: List of chunk dictionaries with content and metadata.
            max_tokens: Approximate maximum tokens for context.
            
        Returns:
            Formatted context string.
        """
        if not retrieved_chunks:
            return ""
        
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Approximate chars per token
        
        for i, chunk in enumerate(retrieved_chunks, start=1):
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            score = chunk.get("score", 0.0)
            
            # Build source reference
            doc_name = metadata.get("document_name", metadata.get("file_name", "Unknown"))
            page_num = metadata.get("page_number", "N/A")
            
            # Format chunk
            chunk_text = f"""
---
[Document {i}]
Source: {doc_name}
Page: {page_num}
Relevance: {score:.2%}

{content}
---
"""
            
            # Check length
            if total_chars + len(chunk_text) > max_chars:
                break
            
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)
        
        return "\n".join(context_parts)
    
    def build_history(
        self,
        messages: list[dict[str, str]],
        max_messages: int = 10,
    ) -> str:
        """Build conversation history string.
        
        Args:
            messages: List of message dictionaries with role and content.
            max_messages: Maximum number of messages to include.
            
        Returns:
            Formatted history string.
        """
        if not messages:
            return "No previous conversation."
        
        # Take last N messages
        recent_messages = messages[-max_messages:]
        
        history_parts = []
        for msg in recent_messages:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            history_parts.append(f"{role}: {content}")
        
        return "\n".join(history_parts)
    
    def build_messages(
        self,
        question: str,
        retrieved_chunks: list[dict[str, Any]],
        conversation_history: list[dict[str, str]] | None = None,
        max_context_tokens: int = 4000,
    ) -> list[dict[str, str]]:
        """Build complete message list for LLM.
        
        Args:
            question: The user's question.
            retrieved_chunks: Retrieved context chunks.
            conversation_history: Optional conversation history.
            max_context_tokens: Maximum tokens for context.
            
        Returns:
            List of message dictionaries for LLM.
        """
        # Build context
        context = self.build_context(retrieved_chunks, max_context_tokens)
        
        if not context:
            return []
        
        # Choose template based on conversation history
        if conversation_history:
            template = self.templates["conversation"]
            history = self.build_history(conversation_history)
            system_content = template.format_system(context=context, history=history)
        else:
            template = self.templates["default"]
            system_content = template.format_system(context=context)
        
        user_content = template.format_user(question=question)
        
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Args:
            text: The text to estimate.
            
        Returns:
            Estimated token count.
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4
