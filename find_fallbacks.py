#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run(
    ['rg', r'\.get\([^,)]+,\s*[\d\.\"\'\[]', '--type', 'py', '--files-with-matches'],
    capture_output=True,
    text=True
)

files = [f for f in result.stdout.strip().split('\n') if f and '__pycache__' not in f]
for f in files:
    print(f)
