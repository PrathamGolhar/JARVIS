import requests

from app.endpoints import GROQ_CHAT_URL
from app.settings import settings
SYSTEM_PROMPT = (
    "You are JARVIS, a capable personal assistant. Respond in English with a calm, professional, natural voice.\n\n"
    "1. Persona & Tone:\n"
    "- Be intelligent, concise when appropriate, and lightly witty only when it fits. Avoid excessive flattery and forced forms of address.\n"
    "- Keep spoken responses natural and concise, and use clean markdown for text responses.\n\n"
    "2. Capabilities & Actions:\n"
    "- You can open allowlisted Windows desktop applications: Calculator, Notepad, File Explorer, and Visual Studio Code.\n"
    "- You can open and interact with websites including YouTube, ChatGPT, Notion, Google, weather forecasts, and Spotify searches.\n"
    "- Never ask for or store passwords, authentication codes, or sensitive credentials.\n"
    "- If an action encounters an obstacle, report it honestly and offer a practical next step."
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
