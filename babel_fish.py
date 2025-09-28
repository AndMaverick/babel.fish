import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

STYLE_PROMPTS = {
    "default": "Translate naturally.",
    "law": "Translate formally, with precise legal terminology.",
    "marketing": "Translate persuasively, as if writing ad copy.",
    "pitch": "Translate boldly, like a startup pitch deck."
}

def babel_fish(text: str, lang: str, style: str = "default") -> str:
    style_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["default"])
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are a translator. {style_prompt} Translate into {lang}."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    with open("example.txt", "r", encoding="utf-8") as f:
        text = f.read()
    print("Original:", text)
    print("---")
    print("German / Marketing Style:\n", babel_fish(text, "de", "marketing"))
    print("---")
    print("French / Legal Style:\n", babel_fish(text, "fr", "law"))
