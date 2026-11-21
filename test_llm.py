from core.llm import generate, generate_json, LLMError

try:
    text, model = generate("Say hello in one short sentence.")
    print("TEXT OK from", model, "->", text.strip())

    data, model = generate_json(
        'Return a JSON object with keys "city" and "country" for Mumbai.'
    )
    print("JSON OK from", model, "->", data)
except LLMError as e:
    print("LLM FAILED:", e)