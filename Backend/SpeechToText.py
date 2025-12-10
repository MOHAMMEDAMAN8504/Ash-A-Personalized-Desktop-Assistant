import os
from pathlib import Path


# SUPPRESS WARNINGS - Add these environment variables at the very start
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.chrome.options import Options 
from webdriver_manager.chrome import ChromeDriverManager 
from dotenv import load_dotenv                   # ✅ CHANGED: Import load_dotenv instead of dotenv_values
import mtranslate as mt


# ✅ FIX FILE PATHS - ONLY ADDITION TO YOUR CODE
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "Data"
DATA_DIR.mkdir(exist_ok=True)


def get_data_file(filename):
    return DATA_DIR / filename


VOICE_HTML_FILE = get_data_file("Voice.html")


# ✅ FIXED: Load environment variables from absolute path
load_dotenv(BASE_DIR / ".env")
# Get the input language setting from the environment variables.
InputLanguage = os.getenv("InputLanguage")      # ✅ CHANGED: Use os.getenv instead of env_vars.get


# Define the HTML code for the speech recognition interface.
HtmlCode = '''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Speech Recognition</title>
</head>
<body>
    <button id="start" onclick="startRecognition()">Start Recognition</button>
    <button id="end" onclick="stopRecognition()">Stop Recognition</button>
    <p id="output"></p>
    <script>
        const output = document.getElementById('output');
        let recognition;


        function startRecognition() {
            recognition = new webkitSpeechRecognition() || new SpeechRecognition();
            recognition.lang = '';
            recognition.continuous = true;


            recognition.onresult = function(event) {
                const transcript = event.results[event.results.length - 1][0].transcript;
                output.textContent += transcript;
            };


            recognition.onend = function() {
                recognition.start();
            };
            recognition.start();
        }


        function stopRecognition() {
            recognition.stop();
            output.innerHTML = "";
        }
    </script>
</body>
</html>'''


# Replace the language setting in the HTML code with the input language from the environment variables.
HtmlCode = str(HtmlCode).replace("recognition.lang = '';", f"recognition.lang = '{InputLanguage}';")


# Write the modified HTML code to a file.
with open(VOICE_HTML_FILE, "w") as f:  # ✅ FIXED PATH
    f.write(HtmlCode)


# Get the current working directory.
current_dir = os.getcwd()
# Generate the file path for the HTML file.
Link = f"file:///{str(VOICE_HTML_FILE).replace(chr(92), '/')}"  # ✅ FIXED PATH


# Set Chrome options for the WebDriver.
chrome_options = Options()
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Like Gecko) Chrome/89.0.142.86 Safari/537.36"
chrome_options.add_argument(f'user-agent={user_agent}')
chrome_options.add_argument("--use-fake-ui-for-media-stream")
chrome_options.add_argument("--use-fake-device-for-media-stream")
chrome_options.add_argument("--headless=new")


# ✅ ENHANCED: ADD THESE LINES TO SUPPRESS CHROME WARNINGS/ERRORS
chrome_options.add_argument("--log-level=3")
chrome_options.add_argument("--silent")
chrome_options.add_argument("--disable-logging")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-features=VoiceInteractionHotword,VoiceInteraction")
chrome_options.add_argument("--disable-component-update")
chrome_options.add_argument("--disable-background-networking")
chrome_options.add_argument("--disable-sync")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
chrome_options.add_experimental_option('useAutomationExtension', False)


# Initialize the Chrome WebDriver using the ChromeDriverManager.
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)


# ✅ FIXED: Define the path for temporary files with absolute path
TempDirPath = str(BASE_DIR / "Frontend" / "Files")


# Function to set the assistant's status by writing it to a file.
def SetAssistantStatus(Status):
    with open(rf'{TempDirPath}/Status.data', "w", encoding='utf-8') as file:
        file.write(Status)


# Function to modify a query to ensure proper punctuation and formatting.
def QueryModifier(Query):
    new_query = Query.lower().strip()
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's", "can you"]


    # Check if the query is a question and add a question mark if necessary.
    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        # Add a period if the query is not a question.
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."


    return new_query.capitalize()


# Function to translate text into English using the mtranslate library.
def UniversalTranslator(Text):
    english_translation = mt.translate(Text, "en", "auto")
    return english_translation.capitalize()


# Function to perform speech recognition using the WebDriver.
def SpeechRecognition():
    # Open the HTML file in the browser.
    driver.get(Link)  # ✅ USES FIXED PATH
    # Start speech recognition by clicking the start button.
    driver.find_element(by=By.ID, value="start").click()


    while True:
        try:
            # Get the recognized text from the HTML output element.
            Text = driver.find_element(by=By.ID, value="output").text


            if Text:
                # Stop recognition by clicking the stop button.
                driver.find_element(by=By.ID, value="end").click()


                # If the input language is English, return the modified query.
                if InputLanguage.lower() == "en" or "en" in InputLanguage.lower():
                    return QueryModifier(Text)
                else:
                    # If the input language is not English, translate the text and return it.
                    SetAssistantStatus("Translating ... ")
                    return QueryModifier(UniversalTranslator(Text))
                
        except Exception as e:
            pass


# Main execution block.
if __name__ == "__main__":
    while True:
        # Continuously perform speech recognition and print the recognized text.
        Text = SpeechRecognition()
        print(Text)
