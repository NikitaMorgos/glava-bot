import sys, json, subprocess

# Check current ghostwriter in pipeline_config on server
result = subprocess.run(
    ["ssh", "glava", "cat /opt/glava/prompts/pipeline_config.json"],
    capture_output=True, text=True
)
cfg = json.loads(result.stdout)
gw = cfg.get("ghostwriter", {})
print("ghostwriter prompt_file:", gw.get("prompt_file"))
print("ghostwriter model:", gw.get("model"))
print("last_uploaded:", gw.get("_last_uploaded", "never"))
print("uploaded_filename:", gw.get("_uploaded_filename", "n/a"))
print()

# Also check file sizes
for role, info in cfg.items():
    if isinstance(info, dict) and "prompt_file" in info:
        print(f"{role}: {info['prompt_file']}")
