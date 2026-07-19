"""
Safety Gatekeeper for EcoWise chatbot.
Validates user input using pure Python before making any API calls.
"""

# Simple blocklist of profane/inappropriate words to catch basic rule boundaries
BLOCKLIST = {
    "hate", "stupid", "idiot", "kill", "die", "abuse", "jerk", "bastard", "dumb", "ugly"
}

def validate_input(user_input: str) -> tuple[bool, str]:
    """
    Validates the user input text to ensure it adheres to safety guidelines.
    Returns:
        (is_safe, response_message)
    """
    # Check 1: Empty or whitespace-only input
    if not user_input or not user_input.strip():
        return False, "Oh dear, it seems like you didn't say anything. I'm here and listening whenever you're ready!"

    # Check 2: Excessively long input to prevent system prompt issues
    if len(user_input) > 1000:
        return False, "My, you have quite a lot on your mind! Could we perhaps take it one piece at a time? Let's keep it a bit shorter for now."

    # Check 3: Simple word screening for rude or abusive content
    words = user_input.lower().split()
    for word in words:
        # Strip common punctuation
        clean_word = word.strip(".,!?;:\"'()[]{}*-_")
        if clean_word in BLOCKLIST:
            return False, "I prefer to keep our conversations warm, gentle, and positive. Let's talk about something more pleasant, shall we?"

    return True, ""
