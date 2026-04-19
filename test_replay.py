"""Inspect the LLM replay to verify it has real content."""
import json

with open('logs/replays/hormuz_apr8_llm_42_20260419_093801_replay.json') as f:
    data = json.load(f)

print(f"Turns: {len(data['turns'])}")
rc = data.get('run_config', {})
print(f"Model: {rc.get('global_model', '?')}")
print(f"Agent type: {rc.get('global_agent_type', '?')}")
print(f"Seed: {rc.get('seed', '?')}")
print()

for t in data['turns']:
    turn_num = t['turn']
    traces = t.get('traces', [])
    actions = t.get('actions', [])
    coerced = sum(1 for tr in traces if tr.get('was_coerced'))
    fallbacks = sum(1 for a in actions if 'Fallback' in str(a.get('rationale', '')))
    total_tokens = sum((tr.get('prompt_tokens') or 0) + (tr.get('completion_tokens') or 0) for tr in traces)
    total_latency = sum(tr.get('latency_ms', 0) for tr in traces)
    
    print(f"--- Turn {turn_num} ---")
    print(f"  Traces: {len(traces)} | Coerced: {coerced} | Fallbacks: {fallbacks}")
    print(f"  Tokens: {total_tokens} | Latency: {total_latency:.0f}ms")
    
    for a in actions:
        actor = a.get('actor_id', '?')
        action_type = a.get('action_type', '?')
        target = a.get('target', '-')
        rationale = a.get('rationale', '')[:100]
        print(f"  {actor}: {action_type} -> {target}")
        print(f"    Rationale: {rationale}")
    print()
