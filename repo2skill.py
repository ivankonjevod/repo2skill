import os
import sys
import tempfile
import shutil
import requests
import zipfile
import yaml
import ast

from urllib.parse import urlparse

def download_repo(url, dest):
    if "github.com" in url:
        if url.endswith(".git"):
            url = url[:-4]
        zip_url = url.replace("github.com", "github.com") + "/archive/refs/heads/main.zip"
    elif "gitlab.com" in url:
        # Assumes main branch is used and repo is public
        zip_url = url.rstrip('/') + "/-/archive/main/main.zip"
    else:
        raise ValueError("Only GitHub or GitLab URLs are supported.")
    
    print(f"Downloading from: {zip_url}")
    r = requests.get(zip_url)
    if r.status_code != 200:
        raise RuntimeError(f"Download failed: {r.status_code}")
    
    zip_path = os.path.join(dest, "repo.zip")
    with open(zip_path, "wb") as f:
        f.write(r.content)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(dest)

    for entry in os.listdir(dest):
        if os.path.isdir(os.path.join(dest, entry)) and "-main" in entry:
            return os.path.join(dest, entry)
    raise RuntimeError("Unzipped repo folder not found.")

def find_functions(repo_path):
    funcs = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                funcs.append((file, node.name))
                    except Exception as e:
                        print(f"Error parsing {file}: {e}")
    return funcs

def create_skill(folder, skill_name, func_entry):
    os.makedirs(folder, exist_ok=True)
    manifest = {
        "name": skill_name,
        "description": f"Auto-adapted skill from Git repo for {skill_name}",
        "entry_point": "act",
        "keywords": [skill_name.lower(), "auto", "converted"]
    }
    with open(os.path.join(folder, "manifest.yaml"), "w") as f:
        yaml.dump(manifest, f)

    py_code = f"""
# Auto-wrapped skill for {skill_name}

def act():
    # TODO: Wrap actual function logic here
    print("Skill {skill_name} activated.")
    return "Executed {func_entry}"
"""
    with open(os.path.join(folder, f"{skill_name}.py"), "w") as f:
        f.write(py_code.strip())

def convert_repo(url):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = download_repo(url, tmpdir)
        print(f"Downloaded to: {repo_path}")
        
        functions = find_functions(repo_path)
        if not functions:
            print("No functions found in repo.")
            return

        print("Found functions:", functions)

        skill_name = os.path.basename(urlparse(url).path.strip("/")).replace(".git", "")
        skill_folder = os.path.join("skills", skill_name)
        create_skill(skill_folder, skill_name, functions[0][1])

        print(f"[SUCCESS] Skill created in: {skill_folder}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python repo2skill.py <github_or_gitlab_url>")
        sys.exit(1)
    convert_repo(sys.argv[1])
