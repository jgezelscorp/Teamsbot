# Real‑Time Pause‑Triggered STT → Refinement → Copilot Studio Agent (MVP)

## **Overview**

This MVP demonstrates a **local real‑time speech pipeline** that:

1.  Captures system audio
2.  Streams it to **Azure Speech real‑time STT** (low‑latency endpoint)    [\[Agent J | SharePoint\]](https://microsoft.sharepoint.com/teams/MCAPSAcademy/SitePages/Agent_J.aspx?web=1)
3.  Detects pauses (≥ \~1 second)
4.  Sends the spoken chunk for **refinement** using an Azure model
5.  Sends the refined text as a **prompt** to a **Copilot Studio agent**, which supports API calls    [\[Copilot Studio Day | PowerPoint\]](https://microsoft.sharepoint.com/teams/MMSAlcoholTracker/_layouts/15/Doc.aspx?sourcedoc=%7B2849548A-BB8C-47FF-AD77-338C2D8B82D2%7D\&file=Copilot%20Studio%20Day.pptx\&action=edit\&mobileredirect=true\&DefaultItemOpen=1)
6.  Displays agent responses in a simple local UI

No Teams bot is required — this is **client‑side audio capture only**.

This architecture is intentionally minimal for demo purposes.

***

## **1. High‑Level Architecture**

    ┌──────────────────────────┐
    │ System Audio (Teams/etc.) │
    └─────────────┬────────────┘
                  ↓
    ┌──────────────────────────┐
    │ Local Audio Capture        │
    │ (loopback device)          │
    └─────────────┬────────────┘
                  ↓ PCM stream
    ┌──────────────────────────┐
    │ Python Host               │
    │ - Azure Speech STT        │
    │ - Pause detection          │
    │ - Chunk buffering          │
    └─────────────┬────────────┘
                  ↓ text chunk
    ┌──────────────────────────┐
    │ Refinement Model          │
    │ (Azure OpenAI / Foundry)  │
    └─────────────┬────────────┘
                  ↓ refined prompt
    ┌──────────────────────────┐
    │ Copilot Studio Agent      │
    │ (via HTTP POST)           │
    └─────────────┬────────────┘
                  ↓ agent output
    ┌──────────────────────────┐
    │ Local Frontend (JS)       │
    │ Displays agent responses  │
    └──────────────────────────┘

### Why this works

*   Speech Service supports **real‑time streaming STT with minimal latency**, suitable for live audio.    [\[Agent J | SharePoint\]](https://microsoft.sharepoint.com/teams/MCAPSAcademy/SitePages/Agent_J.aspx?web=1)
*   The Speech SDK supports real‑time speech scenarios from local applications.    [\[Architectu...tion modes | Word\]](https://microsoft.sharepoint.com/teams/SkypeCallingApps/_layouts/15/Doc.aspx?sourcedoc=%7B0CB6D7E8-245B-4BB1-BFC3-44592BD0E70C%7D\&file=Architecture%20proposals%20for%20transcription%20modes.docx\&action=default\&mobileredirect=true)
*   Copilot Studio supports **API calls to external services**, letting your local host feed it prompts.    [\[Copilot Studio Day | PowerPoint\]](https://microsoft.sharepoint.com/teams/MMSAlcoholTracker/_layouts/15/Doc.aspx?sourcedoc=%7B2849548A-BB8C-47FF-AD77-338C2D8B82D2%7D\&file=Copilot%20Studio%20Day.pptx\&action=edit\&mobileredirect=true\&DefaultItemOpen=1)

***

## **2. Components Required**

### **Azure resources**

*   **Azure Speech Service**\
    (for real‑time STT)    [\[Architectu...tion modes | Word\]](https://microsoft.sharepoint.com/teams/SkypeCallingApps/_layouts/15/Doc.aspx?sourcedoc=%7B0CB6D7E8-245B-4BB1-BFC3-44592BD0E70C%7D\&file=Architecture%20proposals%20for%20transcription%20modes.docx\&action=default\&mobileredirect=true)

*   **Azure OpenAI / Azure AI Foundry model**\
    (optional refinement step)

### **Local components**

*   Python 3.x
*   `azure-cognitiveservices-speech` SDK
*   Flask/FastAPI backend
*   Vanilla JS static webpage
*   Loopback audio driver (VB‑Cable, BlackHole, etc.)

***

## **3. Core Pipeline Logic**

### **Step 1 — Live STT via Azure Speech**

The Python host uses Speech SDK:

*   Real‑time streaming endpoint
*   Minimal latency STT    [\[Agent J | SharePoint\]](https://microsoft.sharepoint.com/teams/MCAPSAcademy/SitePages/Agent_J.aspx?web=1)
*   Emits partial & final results    [\[Architectu...tion modes | Word\]](https://microsoft.sharepoint.com/teams/SkypeCallingApps/_layouts/15/Doc.aspx?sourcedoc=%7B0CB6D7E8-245B-4BB1-BFC3-44592BD0E70C%7D\&file=Architecture%20proposals%20for%20transcription%20modes.docx\&action=default\&mobileredirect=true)

### **Step 2 — Pause Detection**

Inside the Python host:

*   Track timestamp of last non‑silent audio
*   If silence ≥ 1 second → close current “utterance chunk”
*   Send chunk into refinement pipeline

### **Step 3 — Refinement (LLM Cleanup)**

Send chunk to an Azure LLM for:

*   punctuation
*   removing filler words
*   correcting partial phrases
*   semantic tightening

(This uses the agent’s “clean input before reasoning” behaviour.)

### **Step 4 — Copilot Studio Agent Call**

Call the agent via REST:

    POST http://<your-copilotstudio-endpoint>/invoke
    {
       "input": "<refined text>"
    }

Copilot Studio supports HTTP calls to external services.    [\[Copilot Studio Day | PowerPoint\]](https://microsoft.sharepoint.com/teams/MMSAlcoholTracker/_layouts/15/Doc.aspx?sourcedoc=%7B2849548A-BB8C-47FF-AD77-338C2D8B82D2%7D\&file=Copilot%20Studio%20Day.pptx\&action=edit\&mobileredirect=true\&DefaultItemOpen=1)

### **Step 5 — Display Response**

Local frontend connects to the Python host using SSE/WebSockets.

***

## **4. Minimal Python Host (Example)**

```python
import azure.cognitiveservices.speech as speechsdk
from flask import Flask, request, jsonify
import time, queue

app = Flask(__name__)
buffer = []
last_audio_time = time.time()

def start_stt():
    speech_config = speechsdk.SpeechConfig(
        subscription="YOUR_KEY",
        region="YOUR_REGION"
    )
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=False)
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    def on_recognized(evt):
        global last_audio_time
        if evt.result.text:
            buffer.append(evt.result.text)
            last_audio_time = time.time()

    recognizer.recognized.connect(on_recognized)
    recognizer.start_continuous_recognition()

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
```

This uses the real‑time STT SDK referenced in your speech deck.    [\[Architectu...tion modes | Word\]](https://microsoft.sharepoint.com/teams/SkypeCallingApps/_layouts/15/Doc.aspx?sourcedoc=%7B0CB6D7E8-245B-4BB1-BFC3-44592BD0E70C%7D\&file=Architecture%20proposals%20for%20transcription%20modes.docx\&action=default\&mobileredirect=true)

***

## **5. Minimal Frontend (Vanilla JS)**



***

## **6. Copilot Studio Integration**

Your Copilot Studio agent must include:

*   **One custom action** calling your Python host (via HTTP)
*   **One topic** triggered by incoming prompts
*   **Agent output** returned to your frontend

According to the Copilot Studio capability slides:

> “Copilot Studio supports any API / HTTP calls to Azure services.”    [\[Copilot Studio Day | PowerPoint\]](https://microsoft.sharepoint.com/teams/MMSAlcoholTracker/_layouts/15/Doc.aspx?sourcedoc=%7B2849548A-BB8C-47FF-AD77-338C2D8B82D2%7D\&file=Copilot%20Studio%20Day.pptx\&action=edit\&mobileredirect=true\&DefaultItemOpen=1)

Thus your local host appears simply as an external API to the agent.

***

## **7. MVP Limitations**

*   Mixed system audio, no diarisation
*   Single‑user session
*   Basic pause detection
*   No advanced alignment or buffering

However, this is **ideal and simple** for a demo.

***

## **8. Optional Enhancements**

Not needed for demo, but possible using Azure capabilities:

*   Custom speech model training (Speech Studio)    [\[Architectu...tion modes | Word\]](https://microsoft.sharepoint.com/teams/SkypeCallingApps/_layouts/15/Doc.aspx?sourcedoc=%7B0CB6D7E8-245B-4BB1-BFC3-44592BD0E70C%7D\&file=Architecture%20proposals%20for%20transcription%20modes.docx\&action=default\&mobileredirect=true)
*   Text analytics for sentiment, key phrases\
    (part of real‑time call intelligence pipeline)    [\[Architectu...tion modes | Word\]](https://microsoft.sharepoint.com/teams/SkypeCallingApps/_layouts/15/Doc.aspx?sourcedoc=%7B0CB6D7E8-245B-4BB1-BFC3-44592BD0E70C%7D\&file=Architecture%20proposals%20for%20transcription%20modes.docx\&action=default\&mobileredirect=true)