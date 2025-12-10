from groq import Groq                                # Importing the Groq library to use its API.
import os                                            # Added missing import
from json import load, dump                          # Importing functions to read and write JSON files.
import datetime                                      # Importing the datetime module for real-time date and time information.
from dotenv import load_dotenv                       # ✅ CHANGED: Import load_dotenv instead of dotenv_values
import time                                          # Added for search delays
import requests
from pathlib import Path                              # Added for robust file path handling
from .Config import Username, Assistantname

# ✅ FIX FILE PATHS - ONLY ADDITION TO YOUR CODE
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "Data"
DATA_DIR.mkdir(exist_ok=True)

def get_data_file(filename):
    return DATA_DIR / filename

CHAT_LOG_FILE = get_data_file("ChatLog.json")

# ✅ FIXED: Load environment variables from absolute path
load_dotenv(BASE_DIR / ".env")

# Retrieve environment variables for the chatbot configuration.
Username = os.getenv("Username")                    # ✅ CHANGED: Use os.getenv instead of env_vars.get
Assistantname = os.getenv("Assistantname")         # ✅ CHANGED: Use os.getenv instead of env_vars.get
GroqAPIKey = os.getenv("GroqAPIKey")                # ✅ CHANGED: Use os.getenv instead of env_vars.get
BraveAPIKey = os.getenv("BraveAPIKey")              # ✅ CHANGED: Use os.getenv instead of env_vars.get

# Initialize the Groq client with the provided API key.
client = Groq(api_key=GroqAPIKey)

# --- RL knob (safe default matching current behavior) ---
TOP_K = 5
def set_top_k(k: int):
    global TOP_K
    try:
        TOP_K = int(k)
    except Exception:
        TOP_K = 5
# --- END RL knob ---

# Define the system instructions for the chatbot.
System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which has real-time up-to-date information from the internet.

IMPORTANT INSTRUCTIONS:
- When you receive search results between [start] and [end] tags, use that information as your PRIMARY source for answers.
- If search results are limited or unclear, you can supplement with your knowledge but clearly indicate when information might not be current.
- For recent events, movie releases, or current information, prioritize search results over training data.
- If you don't have specific current information, say "Based on available information" and provide what you can find.
- Be helpful while being honest about information limitations.

*** Provide Answers In a Professional Way, make sure to add full stops, commas, question marks, and use proper grammar.***
*** Answer questions helpfully using both search results and your knowledge when appropriate. ***"""

# Try to load the chat log from a JSON file, or create an empty one if it doesn't exist.
try:
    with open(CHAT_LOG_FILE, "r") as f:  # ✅ FIXED PATH
        messages = load(f)
except:
    with open(CHAT_LOG_FILE, "w") as f:  # ✅ FIXED PATH
        dump([], f)
        messages = []                     # Fixed initialization

# Function to perform a Brave Search and format the results.
def BraveSearch(query):
    time.sleep(2)
    try:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BraveAPIKey
        }
        params = {
            "q": query,
            "count": TOP_K,  # ← RL-controlled web results count (default 5)
            "search_lang": "en",
            "country": "IN",
            "safesearch": "moderate",
            "freshness": "pd"  # Past day for current events
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        search_results = response.json()
        
        results = []
        
        # Extract web results (slice by TOP_K to mirror count)
        if 'web' in search_results and 'results' in search_results['web']:
            for result in search_results['web']['results'][:TOP_K]:
                title = result.get('title', 'No Title')
                description = result.get('description', 'No description')
                url = result.get('url', '')
                
                # Clean up description
                description = description.replace('\n', ' ').strip()
                results.append(f"• {title}: {description}")
        
        # Add news results if available (keep original 2 to preserve behavior)
        if 'news' in search_results and 'results' in search_results['news']:
            for result in search_results['news']['results'][:2]:
                title = result.get('title', 'No Title')
                description = result.get('description', 'No description')
                results.append(f"• [NEWS] {title}: {description}")
        
        if results:
            Answer = f"BRAVE SEARCH RESULTS for '{query}' (Current as of August 31, 2025):\n[start]\n"
            Answer += "\n".join(results)
            Answer += "\n[end]"
            return Answer
        else:
            return f"[start]\nNo current results found for '{query}'. Please try a different search term.\n[end]"
            
    except requests.exceptions.RequestException as e:
        return f"[start]\nSearch request failed: {str(e)}\n[end]"
    except Exception as e:
        return f"[start]\nBrave search error: {str(e)}\n[end]"

# Function to clean up the answer by removing empty lines.
def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

# Predefined chatbot conversation system message and an initial user message.
SystemChatBot = [
    {"role": "system", "content": System},
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello, how can I help you?"}
]

# Function to get real-time information like the current date and time.
def Information():
    data = ""
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")
    data += f"Use This Real-time Information if needed: \n"
    data += f"Day: {day}\n"
    data += f"Date: {date}\n"
    data += f"Month: {month}\n"
    data += f"Year: {year}\n"
    data += f"Time: {hour} hours, {minute} minutes, {second} seconds.\n"
    return data

# Function to handle real-time search and response generation.
def RealtimeSearchEngine(prompt):
    global SystemChatBot, messages
    
    # Load the chat log from the JSON file.
    try:
        with open(CHAT_LOG_FILE, "r") as f:  # ✅ FIXED PATH
            messages = load(f)
    except:
        messages = []
    
    # Keep only last 5 messages to prevent token limit
    if len(messages) > 10:
        messages = messages[-10:]
    
    messages.append({"role": "user", "content": f"{prompt}"})
    
    # Pattern-based detection without hardcoded lists
    def is_casual_conversation(text):
        text_lower = text.strip().lower()
        words = text_lower.split()
        
        # Very short single-word responses that are likely greetings
        if len(words) == 1 and len(text_lower) <= 5:
            return True
        
        # Common greeting patterns
        if text_lower.startswith(('hi', 'hey', 'hello')):
            return True
        if 'how are' in text_lower or "what's up" in text_lower or 'whats up' in text_lower:
            return True
        if text_lower.endswith(('morning', 'evening', 'night')):
            return True
        if text_lower in ['thanks', 'thank you', 'bye', 'goodbye', 'ok', 'okay', 'yes', 'no']:
            return True
        
        return False
    
    # Check if it's casual conversation
    if is_casual_conversation(prompt):
        # Skip search and provide simple greeting response
        greeting_responses = {
            'hello': "Hello! How can I assist you today?",
            'hi': "Hi there! What can I help you with?",
            'hey': "Hey! How can I help you?",
            'thanks': "You're welcome!",
            'thank you': "You're welcome!",
            'bye': "Goodbye! Have a great day!",
            'goodbye': "Goodbye! Take care!",
            'ok': "Understood. Is there anything else I can help with?",
            'okay': "Got it! Anything else you need?",
            'yes': "Great! How can I assist you further?",
            'no': "Alright! Let me know if you need anything else."
        }
        
        # Get appropriate response or default
        response_key = prompt.strip().lower()
        if response_key in greeting_responses:
            Answer = greeting_responses[response_key]
        else:
            Answer = "Hello! How can I assist you today?"
        
        messages.append({"role": "assistant", "content": Answer})
        
        # Save the updated chat log back to the JSON file.
        with open(CHAT_LOG_FILE, "w") as f:  # ✅ FIXED PATH
            dump(messages, f, indent=4)
        
        return Answer
    else:
        # Perform search for informational queries
        search_results = BraveSearch(prompt)
        search_instruction = f"""
TASK: Provide a concise and informative answer to the user's question using the search results in 2-3 clear sentences.

SEARCH RESULTS:
{search_results}

USER QUESTION: {prompt}

INSTRUCTIONS:
1. Give a clear and informative answer in exactly 2-3 sentences.
2. Include important facts, numbers, or dates if relevant.
3. Avoid unnecessary details or long explanations.
4. If no relevant answer exists, say: "I couldn't find the information."

ANSWER FORMAT: Well-structured, concise answer only.
"""
    
        # Create conversation with explicit search context
        conversation = [
            {"role": "system", "content": System},
            {"role": "user", "content": search_instruction}
        ]
    
        # Generate a response using the Groq client.
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=conversation,
                temperature=0.3,  # Balanced temperature for accuracy and clarity
                max_tokens=150,   # Perfect for 2-3 sentences
                top_p=1,
                stream=True,
                stop=None
            )
        
            Answer = ""
        
            # Concatenate response chunks from the streaming output.
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    Answer += chunk.choices[0].delta.content
        
            # Clean up the response.
            Answer = Answer.strip().replace("</S>", "").replace("<|eot_id|>", "")
            messages.append({"role": "assistant", "content": Answer})
        
            # Save the updated chat log back to the JSON file.
            with open(CHAT_LOG_FILE, "w") as f:  # ✅ FIXED PATH
                dump(messages, f, indent=4)
        
            return AnswerModifier(Answer=Answer)
        
        except Exception as e:
            return f"Error generating response: {str(e)}"

# Main entry point of the program for interactive querying.
if __name__ == "__main__":
    print(f"Hello {Username}! {Assistantname} is ready with real-time search capabilities.")
    while True:
        try:
            prompt = input("\nEnter your query: ")
            if prompt.lower() in ['exit', 'quit', 'bye']:
                print("Goodbye!")
                break
            print(f"\n{Assistantname}: {RealtimeSearchEngine(prompt)}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
