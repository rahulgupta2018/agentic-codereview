import requests
import json

session_id = 'ce37872f-777b-4b5c-a60d-40c7d558acf7'
r = requests.get(f'http://localhost:8000/apps/orchestrator_agent/users/rahulgupta/sessions/{session_id}')
session = r.json()

print('=== SECURITY ANALYSIS ===')
sa = session['state'].get('security_analysis', '')
print('First 500 chars:')
print(sa[:500])
print()
print('Type:', type(sa))
print('Starts with backticks:', sa.strip().startswith('`'))
print('Starts with ```json:', sa.strip().startswith('```json'))
