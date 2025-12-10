from groq import Groq              # Importing the Groq library to use its API.
from json import load, dump        # Importing functions to read and write JSON files.
import datetime                    # Importing the datetime module for real-time date and time information.
from dotenv import load_dotenv     # ✅ CHANGED: Import load_dotenv instead of dotenv_values
from pathlib import Path           # Added for robust file path handling
import os                          # ✅ ADDED: Import os for environment variable access
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

# Retrieve specific environment variables for username, assistant name, and API key.
Username = os.getenv("Username")            # ✅ CHANGED: Use os.getenv instead of env_vars.get
Assistantname = os.getenv("Assistantname") # ✅ CHANGED: Use os.getenv instead of env_vars.get
GroqAPIKey = os.getenv("GroqAPIKey")        # ✅ CHANGED: Use os.getenv instead of env_vars.get

# Initialize the Groq client using the provided API key.
client = Groq(api_key=GroqAPIKey)

# --- RL knob (safe default matching current behavior) ---
TEMPERATURE = 0.7
def set_temperature(t: float):
    global TEMPERATURE
    try:
        TEMPERATURE = float(t)
    except Exception:
        TEMPERATURE = 0.7
# --- END RL knob ---

# Initialize an empty list to store chat messages.
messages = []

# Define a system message that provides context to the AI chatbot about its role and behavior.
System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""

# A list of system instructions for the chatbot.
SystemChatBot = [
    {"role": "system", "content": System}
]

# Attempt to load the chat log from a JSON file.
try:
    with open(CHAT_LOG_FILE, "r") as f:  # ✅ FIXED PATH
        messages = load(f)         # Load existing messages from the chat log.
except FileNotFoundError:
    # If the file doesn't exist, create an empty JSON file to store chat logs.
    with open(CHAT_LOG_FILE, "w") as f:  # ✅ FIXED PATH
        dump([], f)

# Function to get real-time date and time information.
def RealtimeInformation():
    current_date_time = datetime.datetime.now()    # Get the current date and time.
    day = current_date_time.strftime("%A")               # Day of the week.
    date = current_date_time.strftime("%d")              # Day of the month.
    month = current_date_time.strftime("%B")             # Full month name.
    year = current_date_time.strftime("%Y")             # Year.
    hour = current_date_time.strftime("%H")             # Hour in 24-hour format
    minute = current_date_time.strftime("%M")            # Minute.
    second = current_date_time.strftime("%S")            # Second.

    # Format the information into a string.
    data = f"Please use this real-time information if needed, \n"
    data += f"Day: {day}\nDate: {date}\nMonth: {month}\nYear: {year}\n" 
    data += f"Time: {hour} hours : {minute} minutes : {second} seconds. \n" 
    return data

# Function to modify the chatbot's response for better formatting.
def AnswerModifier(Answer):
    lines = Answer.split('\n')                              # Split the response into lines.
    non_empty_lines = [line for line in lines if line.strip()]  # Remove empty lines.
    modified_answer = '\n'.join(non_empty_lines)              # Join the cleaned lines back together.
    return modified_answer

# Main chatbot function to handle user queries.
def ChatBot(Query):
    """ This function sends the user's query to the chatbot and returns the AI's response. """

    try:
        # Load the existing chat log from the JSON file.  
        with open(CHAT_LOG_FILE, "r") as f:  # ✅ FIXED PATH
            messages = load(f)

        # Append the user's query to the messages list.
        messages.append({"role": "user", "content": f"{Query}"})

        # Make a request to the Groq API for a response.
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",        # Specify the AI model to use.
            messages=SystemChatBot + [{"role": "system", "content": RealtimeInformation()}] + messages, # Include system instructions, real-time info, and chat history.
            max_tokens=1024,                # Limit the maximum tokens in the response.
            temperature=TEMPERATURE,        # ← RL-controlled, default unchanged
            top_p=1,                        # Use nucleus sampling to control diversity.
            stream=True,                    # Enable streaming response.
            stop=None                       # Allow the model to determine when to stop.
        )

        Answer = ""                         # Initialize an empty string to store the AI's response.

        # Process the streamed response chunks.
        for chunk in completion:
            if chunk.choices[0].delta.content:               # Check if there's content in the current chunk.
                Answer += chunk.choices[0].delta.content      # Append the content to the answer.

        Answer = Answer.replace("</s>", "")                  # Clean up any unwanted tokens from the response.

        # Append the chatbot's response to the messages list.
        messages.append({"role": "assistant", "content": Answer})

        # Save the updated chat log to the JSON file.
        with open(CHAT_LOG_FILE, "w") as f:  # ✅ FIXED PATH
            dump(messages, f, indent=4)

        # Return the formatted response.
        return AnswerModifier(Answer=Answer)
    
    except Exception as e:
        # Handle errors by printing the exception and resetting the chat log.
        print(f"Error: {e}")
        with open(CHAT_LOG_FILE, "w") as f:  # ✅ FIXED PATH
            dump([], f, indent=4)
        return ChatBot(Query)                      # Retry the query
    
# Main program entry point.
if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ")     # Prompt the user for a question.
        print(ChatBot(user_input))                     # Call the chatbot function and print its response.
