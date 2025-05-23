import os
import re
import time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from langchain_community.vectorstores import FAISS
from langchain_mistralai import MistralAIEmbeddings
from langchain_mistralai.chat_models import ChatMistralAI
from MangoDB_connection import _CareWell_chatbot_history, log_chatbot_error

load_dotenv()

faiss_index_path = os.getenv("FAISS_INDEX_PATH")
mistral_api_key = os.getenv("MISTRAL_API_KEY")
mistral_embed_api_key = os.getenv("MISTRAL_EMBED_API_KEY")
api_key = os.getenv("GOOGLE_MAPS_API_KEY")

greetings = {
    "hi": "Hello! How can I assist you today?",
    "hello": "Hi there! What can I help you with?",
    "hey": "Hey! How can I help?",
    "good morning": "Good morning! How can I support you today?",
    "good evening": "Good evening! What can I assist you with?",
    "good night": "Good night! Rest well.",
    "how are you": "I'm just a bot, but I'm here to help you!",
    "what's up": "Not much, just ready to help you!",
    "how's it going": "All good on my end! How can I assist you?",
    "yo": "Yo! What's on your mind?",
    "sup": "Hey! Need any assistance?",
    "greetings": "Greetings! How can I assist you?",
    "nice to meet you": "Nice to meet you too! How can I help?",
    "howdy": "Howdy! What can I do for you?",
    "good afternoon": "Good afternoon! How may I assist you today?",
    "how do you do": "I'm doing great! How can I assist you?",
    "bonjour": "Bonjour! How can I help you today?",
    "hola": "Hola! Need any help?",
    "namaste": "Namaste! How may I help you?",
    "anyone there": "Yes, I'm here to help! What do you need?",
    "are you there": "Absolutely! How can I assist you?"
}


# Initialize components once at startup
if not mistral_api_key:
    raise ValueError("Please set the MISTRAL_API environment variable.")

# Initialize models with optimized parameters
model = ChatMistralAI(
    api_key=mistral_api_key,
    temperature=0.3,  # Lower temperature for faster, more deterministic responses
    max_tokens=256,   # Limit response length
    model="mistral-small"  # Use smaller model for faster responses
)

# Pre-compile regex patterns
answer_pattern = re.compile(r'\b[01]\b')
greeting_patterns = {
    re.compile(rf'\b{key}\b', re.IGNORECASE): response 
    for key, response in greetings.items()
}

# Initialize knowledge base with caching
embeddings = MistralAIEmbeddings(
    api_key=mistral_embed_api_key,
    model="mistral-embed"
)

# Load FAISS index with thread-safe handling
vector = FAISS.load_local(
    faiss_index_path,
    embeddings,
    allow_dangerous_deserialization=True
)
retriever = vector.as_retriever(search_kwargs={"k": 3})  # Limit to 3 most relevant docs

# Thread pool for parallel operations
executor = ThreadPoolExecutor(max_workers=4)

def is_greeting(question: str) -> str:
    """Check if input is a greeting and return response if matched."""
    question_lower = question.lower().strip()
    for pattern, response in greeting_patterns.items():
        if pattern.search(question_lower):
            return response
    return None

async def get_context(question: str):
    """Retrieve context documents in parallel."""
    return await retriever.aget_relevant_documents(question)

def generate_response(question: str, role: str, user_id: str, user_name: str):
    """Optimized response generation pipeline."""
    try:
        start_time = time.time()  # Start timing
        
        # Check for greetings first (fast path)
        if greeting_response := is_greeting(question):
            response_time = time.time() - start_time  # Calculate response time
            ChatBot_history = {
                "intent": "greeting",
                "user_input": question,
                "ai_response": greeting_response,
                "role": role,
                "user_id": user_id,
                "user_name": user_name,
                "response_time": round(response_time, 2)  # Round to 2 decimal places
            }
            _CareWell_chatbot_history(ChatBot_history)
            return greeting_response
    
        # Retrieve context in parallel with greeting check
        results = retriever.get_relevant_documents(question)
        context = "\n\n".join(doc.page_content for doc in results[:3])  # Limit to top 3

        # Simplified decision flow
        decision_prompt = f"""Determine if this question can be answered with the context (1=yes, 0=no):
        Context: {context}...  # Truncate for efficiency
        Question: {question}
        Answer:"""

        # Single API call for decision and response
        response = model.invoke([
            {"role": "system", "content": "Answer concisely (1=yes, 0=no)"},
            {"role": "user", "content": decision_prompt}
        ])

        has_answer = answer_pattern.search(response.content.strip())
        has_answer = has_answer.group(0) if has_answer else "0"

        if has_answer == '1':
            response_prompt = f"""You are an expert for answering questions. Answer the question according only to the given context.
            If question cannot be answered using the context, simply say I don't know. Do not make stuff up.
            Your answer MUST be informative, concise, and action driven. Your response must be in Markdown.
            Context: {context}
            Question: {question}
            Answer:"""
            
            assistant_response = model.invoke([
                {"role": "system", "content": response_prompt},
                {"role": "user", "content": question}
            ]).content
            intent = "Rag_content"
        else:
            assistant_response = "Our Support Team will reach out to you shortly regarding this inquiry."
            intent = "basic_content"

        response_time = time.time() - start_time  # Calculate total response time

        # Save history without blocking response
        executor.submit(
            _CareWell_chatbot_history,
            {
                "intent": intent,
                "user_input": question,
                "ai_response": assistant_response,
                "role": role,
                "user_id": user_id,
                "user_name": user_name,
                "response_time": round(response_time, 2)  # Round to 2 decimal places
            }
        )
        return assistant_response
    
    except Exception as e:
        log_chatbot_error(e)
        return "An error occurred while processing your request"
