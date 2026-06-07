import asyncio
from app.rag.rag_pipeline import RAGPipeline

async def main():
    print("Initializing RAG Pipeline...")
    pipeline = RAGPipeline()
    
    question = "What are the financial highlights from the Q1 FY27 Press Release?"
    user_id = "991bd867-a5dc-4010-ab28-fab2b902eb41"
    
    print(f"\nQuerying: '{question}' for user '{user_id}'...")
    response = await pipeline.query(question, user_id)
    
    print("\n--- RESPONSE ---")
    print(response.content)
    print("\n--- SOURCES ---")
    for src in response.sources:
        print(f"- {src.document_name} (Page {src.page_number}) [Relevance: {src.relevance_score:.1%}]")
        
    print(f"\nConfidence Score: {response.confidence_score:.2%}")
    print(f"Response Time: {response.response_time_ms}ms")

if __name__ == "__main__":
    asyncio.run(main())
