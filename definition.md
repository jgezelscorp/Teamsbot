# Architecture and Implementation Plan for a Teams Meeting Assistant with Copilot Studio Integration

## Goal
I want to build a custom Microsoft Teams application that functions as an intelligent meeting assistant. The application needs to join meetings, analyze the conversation in real-time, and fetch answers from an existing agent hosted in Microsoft Copilot Studio.

## Functional Requirements

### 1. Meeting Participation
The bot must be able to join a Teams meeting as a participant (via invitation or ad-hoc).

### 2. Real-Time Context
It needs to access the conversation stream. Please clarify the best technical approach for this:
*   Should I use a **Real-time Media Bot** (Graph Communications API) to process raw audio?
*   Is there a way to access the **Real-time Transcript** stream directly?

### 3. Intent Detection
The bot needs to continuously listen for questions or specific triggers in the conversation and use **Azure OpenAI** (or similar Azure AI service) to extract the intent.

### 4. Copilot Studio Integration
Once a question is isolated, the bot must query an external agent hosted in **Microsoft Copilot Studio**.
*   **Constraint:** I have the Copilot Studio agent already. Tell me exactly what connection parameters (e.g., Bot Application ID, Direct Line Secret, Tenant ID) are required to bridge the two.

### 5. Private Response (Human-in-the-Loop)
The answer must **not** be posted to the public meeting chat. It should be delivered privately to the meeting host (me) via a targeted notification, an ephemeral message, or a private Side Panel / Stage View component.

## Deliverables
Please propose a comprehensive technical solution including:

*   **Architecture Diagram:** showing the flow between Teams Client, Azure Bot Service, the Media processing layer, and Copilot Studio.
*   **Tech Stack:** Recommendations for the SDKs (e.g., Bot Framework SDK vs Teams Toolkit), hosting (Azure Functions vs Container Apps), and AI services. **Constraint: The solution must exclusively use Azure technologies.**
*   **Permissions:** Managing sensitive scopes (e.g., `Calls.JoinGroupCall.AsGuest`, `OnlineMeetings.ReadWrite`).
*   **Step-by-Step Implementation Plan:** A roadmap for building, testing, and deploying this solution.
