"""
Processes user feedback from GitHub issues and appends it to state/preference_memory.yaml.
"""
import os
import re
import sys
import yaml
from datetime import datetime

def main():
    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "")
    
    # Resolve state directory path relative to project folder
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    state_dir = os.path.join(base_dir, "state")
    
    # Regex match to parse issue title format: feedback:{item_id}:{vote}
    # E.g., feedback:a1b2c3d4:not-useful
    match = re.match(r"^feedback:([a-f0-9]{8}):(useful|not-useful)$", title.strip())
    if not match:
        print("Error: Issue title does not match feedback format 'feedback:{item_id}:{vote}'")
        sys.exit(1)
        
    item_id = match.group(1)
    vote = match.group(2)
    
    # Parse selected reasons from checkbox lines, e.g. "- [x] already knew this"
    reasons = []
    for line in body.splitlines():
        # Match checkboxes where user checked them with an 'x' or 'X'
        checkbox_match = re.match(r"^\s*-\s*\[[xX]\]\s*(.+)$", line)
        if checkbox_match:
            reason = checkbox_match.group(1).strip()
            reasons.append(reason)
            
    print(f"Parsed Feedback: Item ID={item_id}, Vote={vote}, Reasons={reasons}")
    
    os.makedirs(state_dir, exist_ok=True)
    memory_path = os.path.join(state_dir, "preference_memory.yaml")
    
    memory = []
    if os.path.exists(memory_path):
        with open(memory_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                if isinstance(data, list):
                    memory = data
            except Exception as e:
                print(f"Warning: Failed to parse preference_memory.yaml: {e}. Starting fresh.")
                
    # Append the new feedback entry
    memory.append({
        "item_id": item_id,
        "vote": vote,
        "reasons": reasons,
        "timestamp": datetime.now().isoformat()
    })
    
    # Write memory back to disk
    with open(memory_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(memory, f, default_flow_style=False)
        
    print(f"Successfully recorded feedback into {memory_path}")

if __name__ == "__main__":
    main()
