import azure.cognitiveservices.speech as speechsdk
import sounddevice as sd
from flask import Flask, jsonify
from openai import OpenAI
import time
import threading
import os
import dotenv

dotenv.load_dotenv()

app = Flask(__name__)

SPEECH_API_KEY = os.getenv("SPEECH_API_KEY")
REGION = "swedencentral"
transcript_log = []

# Config
REFINER_TIMEOUT = 5  # seconds of silence to trigger refinement
transcript_buffer = []            # collects recent mic transcripts until timeout
buffer_lock = threading.Lock()    # protects access to transcript_buffer
_last_timer = None                # holds the active threading.Timer
refined_queue = []                # stores refined prompts/results for polling

# Foundry / Azure OpenAI settings
FOUNDRY_ENDPOINT = os.getenv('FOUNDRY_ENDPOINT')
FOUNDRY_DEPLOYMENT = os.getenv('FOUNDRY_DEPLOYMENT')
FOUNDRY_API_KEY = os.getenv('FOUNDRY_API_KEY')

def refine_transcript(raw_transcript: str) -> str:
    if not (FOUNDRY_ENDPOINT and FOUNDRY_DEPLOYMENT and FOUNDRY_API_KEY):
        print("Refiner not configured.")
        return "Configuration Error"

    try:
        # Initialize the client specifically for Azure AI Foundry
        client = OpenAI(
            base_url=f"{FOUNDRY_ENDPOINT}openai/deployments/{FOUNDRY_DEPLOYMENT}", 
            api_key=FOUNDRY_API_KEY,
            default_query={"api-version": "2024-05-01-preview"} 
        )

        completion = client.chat.completions.create(
            model=FOUNDRY_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a Transcript Refiner. Your goal is to convert a messy meeting transcript into a single, precise search query. If there is no clear technical question, return 'NO_QUERY'."},
                {"role": "user", "content": raw_transcript}
            ],
            temperature=0.1,
        )

        # Correct way to access content in the new OpenAI v1.x library
        msg = completion.choices[0].message.content
        print(f"Refiner result: {msg}")
        return msg
    except Exception as e:
        err = f"Refiner error: {e}"
        print(err)
        return err


def _process_transcript_timeout():
    """Timer callback: called when silence exceeds REFINER_TIMEOUT. Grabs buffer, clears it, and runs refiner in background."""
    global _last_timer
    with buffer_lock:
        if not transcript_buffer:
            _last_timer = None
            return
        raw = " ".join(transcript_buffer).strip()
        transcript_buffer.clear()
        _last_timer = None

    if not raw:
        return

    print(f"Silence detected — refining transcript: {raw}")

    def worker(text):
        refined = refine_transcript(text)
        # Store refined prompt for polling (main can call Copilot Studio agent with it)
        with buffer_lock:
            refined_queue.append({"time": time.time(), "refined": refined})

    threading.Thread(target=worker, args=(raw,), daemon=True).start()

# System listener removed for demo (mic-only)

def start_mic_listener():
    # This stays on default mic (Auto)
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_API_KEY, region=REGION)
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    def on_mic_recognized(evt):
        global _last_timer
        if evt.result.text:
            text = evt.result.text.strip()
            if not text:
                return
            print(text)
            transcript_log.append({"time": time.time(), "text": text})
            # add to buffer and reset the idle timer
            with buffer_lock:
                transcript_buffer.append(text)
                # cancel previous timer if running
                if _last_timer is not None:
                    try:
                        _last_timer.cancel()
                    except Exception:
                        pass
                _last_timer = threading.Timer(REFINER_TIMEOUT, _process_transcript_timeout)
                _last_timer.daemon = True
                _last_timer.start()

    recognizer.recognized.connect(on_mic_recognized)
    recognizer.start_continuous_recognition()
    return recognizer



@app.route("/poll")
def poll():
    global transcript_log
    if transcript_log:
        transcript_log.sort(key=lambda x: x['time'])
        chunk = "\n".join([x['text'] for x in transcript_log])
        transcript_log = []
        return jsonify({"chunk": chunk})
    return jsonify({"chunk": None})

@app.route('/refined')
def get_refined():
    """Return the next refined prompt/result, if any. Consumer (main/frontend) can poll this endpoint and then send the refined prompt to Copilot Studio agent."""
    with buffer_lock:
        if not refined_queue:
            return jsonify({"refined": None})
        refined_queue.sort(key=lambda x: x['time'])
        item = refined_queue.pop(0)
        return jsonify({"refined": item['refined']})

if __name__ == "__main__":
    print("Starting Listener...")
    mic_rec = start_mic_listener()
    app.run(port=5050)