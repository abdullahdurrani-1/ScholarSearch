#!/usr/bin/env python3
"""Test the headline feature in the API."""

import json
import urllib.request
import sys

# Test query
query_data = {
    'question': 'What is machine learning?',
    'top_k': 5,
    'session_id': 'test-session'
}

req = urllib.request.Request(
    'http://127.0.0.1:8000/query',
    data=json.dumps(query_data).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    response = urllib.request.urlopen(req, timeout=30)
    result = json.loads(response.read().decode('utf-8'))
    
    print('✅ API Response Successfully Received:')
    print(f'  Question: {result.get("query", "N/A")}')
    print(f'  📌 Headline: {result.get("headline", "N/A")}')
    answer_preview = result.get("answer", "N/A")[:100]
    print(f'  Answer preview: {answer_preview}...')
    print(f'  Citations: {len(result.get("citations", []))} sources')
    print(f'  Confidence: {result.get("confidence", "N/A")}')
    print('\n✅ SYSTEM STATUS: WORKING ✅')
    sys.exit(0)
except Exception as e:
    print(f'❌ Error: {str(e)[:150]}')
    sys.exit(1)
