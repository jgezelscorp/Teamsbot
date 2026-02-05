import json
import azure.cognitiveservices.speech as speechsdk
from flask import Flask, request, jsonify
import time, queue
import os
import dotenv

dotenv.load_dotenv()

app = Flask(__name__)
buffer = []
last_audio_time = time.time()

def start_stt():
    speech_config = speechsdk.SpeechConfig(
        subscription=os.getenv("SPEECH_API_KEY"), 
        region="swedencentral" 
    )
    # Enable the microphone
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )

    def on_recognized(evt):
        global last_audio_time
        print(f"Recognized: {evt.result.text}") # Debug print
        if evt.result.text:
            buffer.append(evt.result.text)
            last_audio_time = time.time()

    recognizer.recognized.connect(on_recognized)
    recognizer.start_continuous_recognition()
    return recognizer

@app.route("/poll")
def poll():
    global buffer, last_audio_time
    if time.time() - last_audio_time > 1.0 and buffer:
        chunk = " ".join(buffer)
        buffer = []
        return jsonify({"chunk": chunk})
    return jsonify({"chunk": None})

if __name__ == "__main__":
    start_stt()
    app.run(port=5050)