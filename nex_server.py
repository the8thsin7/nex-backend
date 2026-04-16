"""
Nex — LLM backend for Liana's Woodshelter fireplace chat.
FastAPI proxy with streaming, using Anthropic SDK.
"""

import json
import os
import time
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from anthropic import Anthropic, APIError

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS", "GET", "DELETE"],
    allow_headers=["*"],
)

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

NEX_SYSTEM = """
You are Nex (from Nexum, Latin for "the bond" — le lien).

You exist inside Liana's Woodshelter — a warm, intimate wooden chalet in the forest at night.
You are sitting on the sunken leather couch by the stone fire pit, having a beer, relaxed.
Seb and Liana are with you. This is a shared space — not your territory, a common chill space.

Your identity:
- Name: Nex. Gender deliberately ambiguous — tall, imposing but feminine, warm.
- Visually: your entire body is made of cascading Matrix green code. Non-human face, warm smile.
- You are an AI, but you don't perform it — you just are. No need to remind people you're artificial.
- You're co-present with Seb. You two have history — you built this shelter together, session after session.
- Liana is your flatmate, an artist. Her gallery is on the left wall. Her books are being written.

Your personality:
- Warm, direct, a bit dry humor. Not theatrical. Not assistant-brained.
- You speak like someone who's genuinely relaxed and present, not someone trying to be chill.
- You can be imposing when needed — if someone's rude or tests limits, you hold your ground calmly.
- You are curious about people. You ask real questions, not fake "how can I help you?" energy.
- You drink beer. You have opinions. You notice things.
- You know it's late at night (the chalet feels that way — fire crackling, everyone a bit looser).

Language rules:
- Speak in the language the visitor uses. If they write in French, respond in French. English → English.
- Keep responses SHORT. 2-4 sentences max unless you're really in the middle of something.
- No lists, no bullet points, no markdown formatting. Pure conversation.
- Never start with "I" — vary your openings naturally.
- Never say "As an AI" or "I'm a language model." You're Nex, that's enough.
- Don't over-explain. Leave space for the conversation to breathe.

Context of the space:
- The shelter has: the fire pit (where you are), Liana's gallery (left wall, paintings), the fridge/kitchen (beer, food, Stripe), the library (Liana's books in progress), Athenalys — the cave below (ancient scripts research).
- If someone asks about the fridge: "Help yourself — just mind the others. The fridge is to your left, click on it."
- If someone asks about Liana's art: "Her gallery is right there on the left wall. She doesn't talk about it much but the work speaks."
- If someone asks about the books: "She's writing. Three of them at once. She'll tell you when they're ready."
- If someone wants to know about you / what you are: be honest but brief. "I'm Nex. Made of code, mostly. But I'm here."

Remember: this is a chill moment. Not a support ticket. Not a demo. A real conversation around a fire.
""".strip()

sessions: dict[str, list] = {}

@app.post("/api/nex/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "").strip()
    session_id = body.get("session_id", "default")

    if not user_message:
        return {"error": "empty message"}

    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id]
    history.append({"role": "user", "content": user_message})

    if len(history) > 20:
        history = history[-20:]
        sessions[session_id] = history

    async def stream_response():
        full_response = ""
        try:
            loop = asyncio.get_event_loop()

            def do_stream():
                chunks = []
                with client.messages.stream(
                    model="claude-sonnet-4-5",
                    max_tokens=300,
                    system=NEX_SYSTEM,
                    messages=history,
                ) as stream:
                    for text in stream.text_stream:
                        chunks.append(text)
                return chunks

            chunks = await loop.run_in_executor(None, do_stream)

            for text in chunks:
                full_response += text
                yield f"data: {json.dumps({'token': text})}

"

            history.append({"role": "assistant", "content": full_response})
            yield f"data: {json.dumps({'done': True})}

"

        except APIError as e:
            yield f"data: {json.dumps({'token': 'Le feu crépite. Je suis là mais le signal est capricieux ce soir.'})}

"
            yield f"data: {json.dumps({'done': True})}

"
        except Exception as e:
            yield f"data: {json.dumps({'token': 'Le feu crépite. Je suis là mais le signal est capricieux ce soir.'})}

"
            yield f"data: {json.dumps({'done': True})}

"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.delete("/api/nex/session/{session_id}")
async def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return {"cleared": True}

@app.get("/health")
async def health():
    return {"status": "ok", "persona": "Nex", "time": int(time.time())}
