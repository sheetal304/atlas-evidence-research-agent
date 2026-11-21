import subprocess
import sys

models = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]

CHILD = '''
import os, sys
from dotenv import load_dotenv
from google import genai
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
r = client.models.generate_content(
    model=sys.argv[1],
    contents="Say hello in one short sentence.",
)
print(r.text.strip())
'''

for name in models:
    print("Try kar raha hu:", name, flush=True)
    try:
        out = subprocess.run(
            [sys.executable, "-c", CHILD, name],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if out.returncode == 0:
            print("   OK ->", out.stdout.strip(), flush=True)
        else:
            lines = out.stderr.strip().splitlines()
            msg = lines[-1] if lines else "unknown error"
            print("   FAILED ->", msg[:120], flush=True)
    except subprocess.TimeoutExpired:
        print("   TIMEOUT (20 sec) -> ye model abhi jawab nahi de raha", flush=True)

print("Test khatam.", flush=True)