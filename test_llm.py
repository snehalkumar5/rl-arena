"""Single LLM call test."""
import os
os.environ['OPENCODE_ZEN_API_KEY'] = 'sk-aERsS8B5YDbDKS8lpmShxIRNSPzL5N78Y45DJ0vnMDecT0IlV29eJli1MfdjzhZ8'

from openai import OpenAI
client = OpenAI(base_url='https://opencode.ai/zen/v1', api_key=os.environ['OPENCODE_ZEN_API_KEY'])

print("Testing single call to big-pickle...")
try:
    resp = client.chat.completions.create(
        model='big-pickle',
        temperature=0.7,
        max_tokens=100,
        messages=[{'role': 'user', 'content': 'Say hello in one sentence.'}]
    )
    content = resp.choices[0].message.content
    print(f"SUCCESS: {content}")
    print(f"Tokens: {resp.usage.prompt_tokens}in / {resp.usage.completion_tokens}out")
except Exception as e:
    print(f"FAILED: {e}")
