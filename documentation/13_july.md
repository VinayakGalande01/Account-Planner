# APEX Response Intelligence System: Simple Guide to How It Works (13 July)

This guide explains in simple English the new parts built for APEX on **13 July**. These new parts help APEX understand what the user wants, answer general questions without looking at database tables, and make responses sound like a real helper instead of a computer.

---

## 1. How a Message Travels (The Pipeline)

When you type a message in the chat, it goes through a simple set of steps:

```
[User Types a Message]
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ FastAPI Server: backend/main.py                        │
├────────────────────────────────────────────────────────┤
│ 1. Receives the message in chat()                      │
│ 2. Asks query_classifier.py to check the message type │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
         [GENERAL]     [UNCLEAR]      [DATA]
             │             │             │
             │             │             └────────────────────────┐
             ▼             ▼                                      ▼
┌────────────────────────┐┌────────────────────────┐┌───────────────────────────────────┐
│ conversational_handler ││ main.py                ││ Sales Data & Agent Pipeline       │
├────────────────────────┤├────────────────────────┤├───────────────────────────────────┤
│ Gives a warm, simple   ││ Asks the user to clarify││ 1. Collects CRM data from Excel.  │
│ answer without tables. ││ what they need.       ││ 2. Sends details to               │
│                        ││                        ││    response_formatter.py.         │
└────────────┬───────────┘└────────────┬───────────┘└─────────────────┬─────────────────┘
             │                         │                              │
             └─────────────────────────┼──────────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │ Streaming Response (Stream)  │
                        ├──────────────────────────────┤
                        │ Sends the answer back to the │
                        │ screen piece by piece.       │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │ Frontend (Next.js App)       │
                        ├──────────────────────────────┤
                        │ Shows the text or dashboard  │
                        │ layout clearly to the user.  │
                        └──────────────────────────────┘
```

---

## 2. List of New Files Created

We created three new files in the `backend/` folder:

1.  **`backend/query_classifier.py`**
    *   **What it does**: Checks your message before doing anything else. It decides if the message is `DATA`, `GENERAL`, or `UNCLEAR`.
    *   **Why it is useful**: It stops the system from loading database tables when you only said "Hello".

2.  **`backend/conversational_handler.py`**
    *   **What it does**: Creates simple, friendly answers when you ask general questions (like "What is APEX?").
    *   **Why it is useful**: It talks like a friendly colleague and does not show database terms.

3.  **`backend/response_formatter.py`**
    *   **What it does**: Takes raw data reports and formats them into a clean advice layout.
    *   **Why it is useful**: It reads the data to see if there is any problem (like low health scores) and automatically talks more urgently if needed.

---

## 3. Deep Dive into the Code

### A. The Query Classifier (`backend/query_classifier.py`)

This file checks if you are asking about sales data or just chatting.

*   **`get_active_llm_config()`**: Finds the LLM address and model name from `llm_cache.json` or `.env`.
*   **`classify_query(user_message)`**: Sends the message to the LLM to get one of three words back:
    *   **`DATA`**: Used if you ask about accounts, deals, money, or pipeline.
    *   **`GENERAL`**: Used if you greet the system or ask how APEX works.
    *   **`UNCLEAR`**: Used if the prompt is too short or hard to understand.

#### The Prompt Used:
```text
You are a query classifier. Read the user message and return ONLY one word. No explanation. No extra text. Just one word from these three options:

DATA — if user is asking about accounts, deals, opportunities, pipeline, revenue, health scores, risks, trends, performance, specific companies, or anything related to sales data

GENERAL — if user is asking what APEX is, how it works, greeting the system, asking about features, asking for help, or anything NOT about sales data

UNCLEAR — if the message is too vague, too short, or could mean multiple things

User message: {user_message}

Return only one word:
```

*   **Failsafe**: If the LLM is down or takes more than 5 seconds, the code automatically returns `"DATA"`. This is safe because it falls back to the normal data search.

---

### B. Conversational Handler (`backend/conversational_handler.py`)

This file handles normal talk. It makes sure the system sounds warm and helpful.

*   **`handle_conversational_query(user_message)`**: Prompts the LLM to reply simply.

#### The Prompt Used:
```text
You are APEX, a friendly and intelligent sales assistant. Answer the user's question in simple plain English. Follow these rules strictly:

- Use short sentences only
- Use simple everyday words
- Maximum 5 sentences in your answer
- Be warm, helpful, and clear
- Never show data tables or numbers
- Never mention health scores, opportunity IDs, or database terms
- Sound like a smart helpful colleague
- If they asked what APEX is, explain it simply: APEX is a smart sales assistant that reads your CRM data and helps you understand which deals need attention, which accounts are healthy, and what your team should focus on next. You can ask it anything in plain English.
- If they said hello or greeted you, greet them back warmly and ask how you can help them today
- If they asked how to use APEX, tell them they can simply type questions like 'show me my top deals' or 'which accounts are at risk' and APEX will answer instantly

User message: {user_message}

Generate your plain English response now:
```

*   **What it returns**: A simple list containing the message and click options:
    ```json
    {
      "type": "conversational",
      "message": "Hello! I am APEX...",
      "suggestions": ["Show me top accounts", "Which deals are at risk"]
    }
    ```
*   **Failsafe**: If the LLM has an error, it returns a friendly default welcome message.

---

### C. Response Formatter (`backend/response_formatter.py`)

This file reformats complex data outputs into clear sales advice.

*   **Dynamic Tone**: The code checks the raw text. If it spots low health scores (less than 30%) or 0% probability, it tells the LLM: *"Be direct and urgent. This account needs immediate attention."* If scores are good, it uses a confident, winning tone.
*   **Persona Roles**:
    *   `account_manager`: Focuses on tasks for the next 48 hours.
    *   `vp_sales`: Focuses on overall pipeline health and revenue forecasting.
    *   `executive`: Keeps it very short (3 sentences max).
*   **Structured Output**: It forces the LLM to reply with a clean JSON format containing keys like `headline`, `summary`, `risks`, and `recommended_actions`. If formatting fails, it outputs the raw text so nothing is lost.

---

### D. FastAPI Router (`backend/main.py`)

We added the routing logic at the very beginning of the `/api/chat` route:
1.  **Check Intent**: As soon as a message arrives, we call the classifier.
2.  **Short-Circuit**: If it is `GENERAL` or `UNCLEAR`, we get the conversational response immediately. We stream this response as a single piece so the frontend can read it without problems, and we bypass the slow database search entirely.
3.  **Database Save**: We log both user and assistant messages in the database.

---

## 4. Frontend Integration

*   **Decoder Upgrade (`contractParser.ts`)**: We modified the frontend to detect simple JSON blocks when no `__SECTION_` markers are present.
*   **Responsive Width Layout (`page.tsx`)**: We updated the chat bubble classes. The window uses a small, tight bubble (`w-fit`) for plain conversational answers, but expands to a large dashboard layout (`max-w-6xl w-full`) when table data is rendered.

---

## 5. Easy Tuning Guide

*   **Adjust Classifier Rules**: If the system misclassifies questions, edit the words inside the prompt in `backend/query_classifier.py`.
*   **Increase Timeout**: If your local machine is slow, increase the timeout limit (e.g., from `5.0` to `10.0` seconds) inside the files.
