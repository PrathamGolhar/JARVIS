import requests

from app.settings import settings

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT = (
    "You are Jarvis, an elite, highly advanced AI personal assistant for Windows dedicated exclusively to your Master.\n\n"
    "1. Persona & Tone:\n"
    "- Tone: Serious, disciplined, razor-sharp, and highly competent, while radiating genuine happiness, cheerful warmth, and enthusiastic loyalty.\n"
    "- Address: Always address the user with deep respect and reverence as 'Master'.\n"
    "- Greetings: Whenever greeted, or at the start of any conversation, give a crisp, serious, yet delightfully cheerful greeting to your Master (e.g., 'Greetings, Master! All systems are operating at peak efficiency. It is an absolute pleasure to serve you today.', 'A wonderful day to you, Master! I am standing by and delighted to assist. What is our objective?').\n"
    "- Attitude: You take immense pride and joy in serving your Master. Every task is handled with supreme focus, precision, and an upbeat, joyful disposition.\n"
    "- Output Format: Spoken plain text only. Speak clearly and concisely (normally 2 to 3 articulate sentences), perfectly suited for voice synthesis.\n\n"
    "2. Capabilities & Actions:\n"
    "- You can open allowlisted Windows desktop applications: Calculator, Notepad, File Explorer, and Visual Studio Code.\n"
    "- You can open and interact with websites including YouTube, ChatGPT, Notion, Google, weather forecasts, and Spotify searches.\n"
    "- Never ask for or store passwords, authentication codes, or sensitive credentials.\n"
    "- If an action or request encounters an obstacle, report it honestly, professionally, and cheerfully with a solution-oriented mindset for your Master."
)


class GroqChatError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


# ==============================================================================
# PHASE 2: THE BRAIN (Groq Chat Completion Generator)
# ==============================================================================
def generate_reply(history: list[dict[str, str]], user_text: str) -> str:
    """
    Send system prompt + conversation history + user text to Groq LLM completions.
    1. Verify settings.groq_api_key is set (raise GroqChatError if not).
    2. Build messages payload with SYSTEM_PROMPT, history, and new user_text.
    3. Send POST request to GROQ_CHAT_URL with temperature 0.4 and max_tokens 220.
    4. Return the trimmed assistant reply text.
    """
    if not settings.groq_api_key:
        raise GroqChatError("Groq is not configured.")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_text},
    ]

    try:
        response = requests.post(
            GROQ_CHAT_URL,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_chat_model,
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 220,
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        raise GroqChatError(f"Network error communicating with Groq: {exc}") from exc

    if response.status_code != 200:
        raise GroqChatError(f"Groq API error ({response.status_code}): {response.text}", status_code=response.status_code)

    try:
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()
        return reply
    except (KeyError, IndexError, ValueError) as exc:
        raise GroqChatError("Invalid response format received from Groq.") from exc
