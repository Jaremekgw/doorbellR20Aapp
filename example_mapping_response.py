TURN_ON_SYNONYMS = {"załącz", "włącz", "zapal"}
TURN_OFF_SYNONYMS = {"wyłącz", "zgaś"}
LIGHT_SYNONYMS = {"lampę", "lampy", "światło"}

"""
    Example:
     App demonstrating how you might use the TURN_ON_CONFIRMATION dictionary
     to create a natural-sounding confirmation message based on the command the user spoke.
     Suppose you want to confirm “turn on the light” actions with a verb form similar
     to what the user used (“załączono,” “włączono,” or “zapalono”).

"""

# Mapping from recognized synonyms to a correct "past tense" version
TURN_ON_CONFIRMATION = {
    "załącz": "załączono",
    "włącz": "włączono",
    "zapal": "zapalono"
}

def reasoning_pl(self, command: str):
    # 1. Normalize input
    command_lower = command.lower()

    # 2. Check if this is a "turn on the light" request
    if any(verb in command_lower for verb in TURN_ON_SYNONYMS) and \
       any(obj in command_lower for obj in LIGHT_SYNONYMS):
        # Identify which verb the user used (pick the first match)
        used_verb = next(verb for verb in TURN_ON_SYNONYMS if verb in command_lower)
        # Convert to confirmation form, with a fallback if something unexpected
        confirmation_verb = TURN_ON_CONFIRMATION.get(used_verb, "włączono")

        if self.lamp.turnOn():
            self.play_response(f"{confirmation_verb} światło.")
        else:
            self.play_response("Światło jest już załączone.")
        return

    # 3. Check if it's a "turn off the light" request
    if any(verb in command_lower for verb in TURN_OFF_SYNONYMS) and \
       any(obj in command_lower for obj in LIGHT_SYNONYMS):
        if self.lamp.turnOff():
            self.play_response("Wyłączono światło.")
        else:
            self.play_response("Światło jest już wyłączone.")
        return

    # 4. Otherwise, unrecognized
    self.play_response("Przepraszam, proszę mówić wyraźnie, jednym zdaniem.")


