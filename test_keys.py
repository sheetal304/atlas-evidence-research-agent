import os
from dotenv import load_dotenv

load_dotenv()

tavily_key = os.getenv("TAVILY_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

print("Tavily key mili:", bool(tavily_key))
print("Gemini key mili:", bool(gemini_key))
print()

# ---- Tavily test ----
try:
    from tavily import TavilyClient

    tavily = TavilyClient(api_key=tavily_key)
    result = tavily.search("What is retrieval augmented generation?", max_results=3)
    print("TAVILY OK. Results mile:", len(result["results"]))
    for r in result["results"]:
        print("  -", r["url"])
except Exception as e:
    print("TAVILY FAILED:", e)

print()

# ---- Gemini test ----
try:
    from google import genai

    client = genai.Client(api_key=gemini_key)
    try:
        resp = client.models.generate_content(
            model="gemini-3.7-flash",
            contents="Say hello in one short sentence.",
        )
        print("GEMINI OK:", resp.text)
    except Exception as e:
        print("GEMINI FAILED:", e)
        print("Aapki key par ye models available hain:")
        for m in client.models.list():
            print("  -", m.name)
except Exception as e:
    print("GEMINI SETUP FAILED:", e)