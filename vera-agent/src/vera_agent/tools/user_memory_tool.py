"""Model-callable tool for recording stable user profile memories."""

REMEMBER_USER_TOOL = {
    "type": "function",
    "function": {
        "name": "remember_user",
        "description": (
            "Record a stable, useful fact about the user's profile, preferences, habits, "
            "or explicit feedback for future conversations. Use sparingly: do not store "
            "temporary task state, project facts, secrets, or sensitive personal data. "
            "Only save information the user stated or clearly confirmed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["profile", "preference", "habit", "feedback"]},
                "content": {"type": "string", "description": "One concise, durable user-profile memory, at most 500 characters."},
                "memory_id": {"type": "string", "description": "Existing memory ID to revise when this updates or corrects a remembered item."},
            },
            "required": ["category", "content"],
        },
    },
}

FORGET_USER_MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": "forget_user_memory",
        "description": "Delete a saved user-profile memory when the user explicitly asks you to forget or remove it.",
        "parameters": {
            "type": "object",
            "properties": {"memory_id": {"type": "string", "description": "ID of the memory to delete."}},
            "required": ["memory_id"],
        },
    },
}
