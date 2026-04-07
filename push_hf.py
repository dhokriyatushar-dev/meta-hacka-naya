from huggingface_hub import upload_folder
from huggingface_hub.utils import HfHubHTTPError

try:
    upload_folder(
        folder_path='.', 
        repo_id='Team-KRIYA/meta-hackathon', 
        repo_type='space', 
        ignore_patterns=['.git*', '__pycache__*', '*.log', 'outputs/*', 'frontend/*', 'node_modules*', '.next*']
    )
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
