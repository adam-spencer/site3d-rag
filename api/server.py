import os
import re
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import json
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from api import vector_store

load_dotenv()

app = FastAPI(title="Site3D RAG Demo")

# Create simple static directory for the HTML frontend
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    query: str

try:
    with open("data/pages.json", "r", encoding="utf-8") as f:
        parent_docs = json.load(f)
except Exception as e:
    print(f"Warning: Failed to load parent documents, fallback to chunks-only mode: {e}")
    parent_docs = {}

try:
    retriever = vector_store.get_retriever()
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0)
    template = """You are an expert engineering assistant for the Site3D software. Use the following context to answer the user's question clearly and accurately.

The context may contain images already formatted as valid Markdown links (e.g. `![alt_text](url)`). When you reference a UI tool, window, or concept that has an image available in the context, you MUST natively copy the exact Markdown image link into your response to show it to the user. Do not modify the URLs. 

Context:
{context}

Question: {question}

Answer:"""
    prompt = ChatPromptTemplate.from_template(template)
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
        
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
except Exception as e:
    print(f"Failed to initialize RAG chain: {e}")
    rag_chain = None

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if rag_chain is None:
        async def fallback():
            yield json.dumps({"error": "RAG Chain failed to initialize. Check GEMINI_API_KEY environment variable and vector database."}) + "\n"
        return StreamingResponse(fallback(), media_type="application/x-ndjson")

    async def generate():
        import asyncio
        try:
            # Massive buffer padding to force ASGI & Proxy servers to instantly drop the chunk to the client
            yield json.dumps({"status": "Connecting to engine..."}) + (" " * 2048) + "\n"
            await asyncio.sleep(0.05)

            yield json.dumps({"status": "Retrieving context from ChromaDB..."}) + "\n"
            await asyncio.sleep(0.05) # Force the ASGI worker to flush the stream to the socket
            
            # Explicitly thread the local ChromaDB call which completely stalls the underlying Python thread CPU
            docs = await asyncio.to_thread(retriever.invoke, request.query)
            
            yield json.dumps({"status": f"Retrieved {len(docs)} documents. Retrieving parent pages..."}) + "\n"
            await asyncio.sleep(0.05)
            
            # --- SMALL TO BIG RETRIEVAL ---
            # 1. Extract the unique source URLs from the Top-K small matching chunks
            urls = list(dict.fromkeys(doc.metadata.get("source_url") for doc in docs if doc.metadata.get("source_url")))
            
            # 2. Pull the complete overarching parent documents perfectly out of local memory dict
            full_pages = [parent_docs[url] for url in urls if url in parent_docs]
            
            # If for some reason pages were missing, natively fallback to raw snippet chunks
            if not full_pages:
                context_str = "\n\n".join(doc.page_content for doc in docs)
            else:
                context_str = "\n\n---\n\n".join(full_pages)
                
            yield json.dumps({"status": f"Expanded to {len(full_pages)} parent documents. Waiting for Gemini..."}) + "\n"
            await asyncio.sleep(0.05)
            
            # Pre-format images into absolute Markdown links so the LLM simply copies them
            def replace_img(m):
                alt = m.group(1)
                src = m.group(2)
                url = src if src.startswith("http") else f"https://www.site3d.co.uk/help/{src}"
                return f"![{alt}]({url})"
                
            context_str = re.sub(r'\[Screenshot: [^\]]+? - ([^\]]+?)\]\(([^)]+?)\)', replace_img, context_str)
            context_str = re.sub(r'\[Screenshot: ([^\]]+?)\]\(([^)]+?)\)', replace_img, context_str)
            context_str = re.sub(r'\[Icon: ([^\]]+?)\]\(([^)]+?)\)', replace_img, context_str)
            
            chain = prompt | llm | StrOutputParser()
            
            first = True
            async for chunk_text in chain.astream({"context": context_str, "question": request.query}):
                if first:
                    yield json.dumps({"status": "Generating response...", "clear": True}) + "\n"
                    first = False
                if chunk_text:
                    yield json.dumps({"chunk": chunk_text}) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
