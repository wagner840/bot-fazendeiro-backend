import os
import json
import sys

# Usage: python gather_files.py [backend|frontend]

mode = sys.argv[1] if len(sys.argv) > 1 else 'backend'

files_list = []

base_path = "."
if mode == 'frontend':
    base_path = "frontend"

# Global skips
skip_dirs = {'.git', '.venv', '__pycache__', 'node_modules', 'dist', 'build', '.idea', '.vscode', '__MACOSX'}
# Files to skip
skip_files = {'.env', 'gather_files.py', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', '.DS_Store', 'Thumbs.db'}

# Extensions to include (source code)
extensions = {'.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.css', '.html', '.md', '.txt', '.gitignore', '.env.example', '.sql'}

# Backend specific: Exclude the whole frontend folder
backend_skip_dirs = {'frontend'}

for root, dirs, files in os.walk(base_path):
    # Filter directories in-place
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    
    if mode == 'backend':
        dirs[:] = [d for d in dirs if d not in backend_skip_dirs]
        
    for file in files:
        if file in skip_files:
            continue
        
        # Special case: .env is skipped, but .env.example is allowed
        if file.startswith('.') and file != '.gitignore' and file != '.env.example':
            continue
            
        ext = os.path.splitext(file)[1]
        # Include known extensions OR specific filenames like Dockerfile
        if ext not in extensions and file not in ['Dockerfile', 'LICENSE']:
            continue
            
        full_path = os.path.join(root, file)
        
        try:
            # Try reading as text
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            # Skip binary files
            continue
            
        # Calculate relative path for the repo
        if mode == 'backend':
            rel_path = os.path.relpath(full_path, ".")
        else: # frontend
            rel_path = os.path.relpath(full_path, "frontend")
            
        # Git uses forward slashes
        rel_path = rel_path.replace("\\", "/")
        
        files_list.append({"path": rel_path, "content": content})

# Output formatted JSON to file to avoid shell encoding issues
output_file = f"{mode}_files.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(files_list, f, indent=2)

print(f"Saved to {output_file}")
