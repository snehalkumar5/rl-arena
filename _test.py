import os, time
os.environ['OPENCODE_ZEN_API_KEY'] = 'sk-8o27nRY05nob0wxSiBEMtZOX1jzEoirkoAQxqus6GedmfFKZkIZtXYr2QAxGOaBO'
from openai import OpenAI
client = OpenAI(base_url='https://opencode.ai/zen/v1', api_key=os.environ['OPENCODE_ZEN_API_KEY'])

prompt = '''{"turn":1,"legal_actions":["hold","trade_offer","sanction","mobilize"],"treasury":80}
Pick an action. Reply as JSON: {"action":{"action_type":"...","target":"..."},"rationale":"...","public_statement":"..."}'''

start = time.perf_counter()
try:
    resp = client.chat.completions.create(
        model='qwen3.6-plus',
        temperature=0.7,
        max_tokens=500,
        messages=[
            {'role': 'system', 'content': 'You are Iran policy engine. Respond with valid JSON only.'},
            {'role': 'user', 'content': prompt}
        ]
    )
    elapsed = (time.perf_counter() - start) * 1000
    content = resp.choices[0].message.content or '(empty)'
    print(f'Time: {elapsed:.0f}ms')
    print(f'Tokens: {resp.usage.prompt_tokens}in/{resp.usage.completion_tokens}out')
    print(f'Finish: {resp.choices[0].finish_reason}')
    print(f'Content:\n{content[:500]}')
except Exception as e:
    elapsed = (time.perf_counter() - start) * 1000
    print(f'FAILED after {elapsed:.0f}ms: {e}')
