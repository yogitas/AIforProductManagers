"""
Interactive feedback tool for recording user preferences into state/preference_memory.yaml.

Usage:
  1. Interactive CLI mode:
     python src/feedback.py

  2. Direct command mode:
     python src/feedback.py --id <item_id> --vote useful
     python src/feedback.py --id <item_id> --vote not-useful --reason "Routine PR noise"
"""
import os
import sys
import yaml
import argparse
from datetime import datetime

def load_memory(memory_path: str) -> list:
    if os.path.exists(memory_path):
        with open(memory_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                if isinstance(data, list):
                    return data
            except Exception:
                pass
    return []

def save_memory(memory_path: str, memory: list):
    os.makedirs(os.path.dirname(memory_path), exist_ok=True)
    with open(memory_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(memory, f, default_flow_style=False)

def record_vote(state_dir: str, item_id: str, vote: str, reasons: list = None):
    memory_path = os.path.join(state_dir, "preference_memory.yaml")
    memory = load_memory(memory_path)
    
    entry = {
        "item_id": item_id,
        "vote": vote,
        "reasons": reasons or [],
        "timestamp": datetime.now().isoformat()
    }
    
    memory.append(entry)
    save_memory(memory_path, memory)
    print(f"\n✅ Successfully recorded feedback for item '{item_id}' ({vote.upper()}) into state/preference_memory.yaml!")

def interactive_mode(state_dir: str):
    report_path = os.path.join(state_dir, "latest_report.md")
    if not os.path.exists(report_path):
        print(f"Error: No report found at {report_path}. Run 'python src/run_agent.py' first to generate a report.")
        sys.exit(1)
        
    print("==================================================")
    print(" 🤖 Competitive Intelligence Digest - Local Feedback")
    print("==================================================")
    
    # Parse items from latest_report.md
    items = []
    current_comp = ""
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for line in lines:
        line_s = line.strip()
        if line_s.startswith("### ") and not line_s.startswith("### Active"):
            current_comp = line_s.replace("### ", "").strip()
        elif line_s.startswith("#### "):
            title = line_s.replace("#### ", "").replace("⭐ **[FOCUS SUBDOMAIN]** ", "").strip()
            items.append({"competitor": current_comp, "title": title})
            
    if not items:
        print("No items found in the latest report.")
        return

    print("\nRecent Featured Updates in Digest:")
    for idx, item in enumerate(items, 1):
        print(f" [{idx}] {item['competitor']} - {item['title']}")
        
    print("\nSelect an item number to rate (or 0 to exit): ", end="")
    try:
        choice = int(input().strip())
        if choice == 0:
            print("Exiting feedback tool.")
            return
        if choice < 1 or choice > len(items):
            print("Invalid choice.")
            return
            
        selected_item = items[choice - 1]
        print(f"\nSelected: {selected_item['competitor']} - {selected_item['title']}")
        print("Vote: [1] 👍 Useful   [2] 👎 Not Useful")
        vote_choice = input("Enter choice (1/2): ").strip()
        
        vote = "useful" if vote_choice == "1" else "not-useful"
        reasons = []
        
        if vote == "not-useful":
            print("\nSelect reason for marking as Not Useful:")
            print(" [1] Routine PR or thought-leadership noise")
            print(" [2] Irrelevant or low-priority competitor")
            print(" [3] Custom reason")
            r_choice = input("Choice (1-3): ").strip()
            if r_choice == "1":
                reasons.append("Routine PR or thought-leadership noise")
            elif r_choice == "2":
                reasons.append("Irrelevant or low-priority competitor")
            elif r_choice == "3":
                custom = input("Type custom reason: ").strip()
                if custom:
                    reasons.append(custom)
                    
        # Derive simple ID hash from title
        from src.state_store import get_item_id
        item_id = get_item_id("", selected_item['title'])
        record_vote(state_dir, item_id, vote, reasons)
        
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled.")

def main():
    parser = argparse.ArgumentParser(description="Record user feedback for preference memory.")
    parser.add_argument("--id", help="Item ID or title hash")
    parser.add_argument("--vote", choices=["useful", "not-useful"], help="Vote type")
    parser.add_argument("--reason", help="Optional reason for vote")
    parser.add_argument("--state-dir", default="state", help="Path to state directory")
    
    args = parser.parse_args()
    
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    state_dir = os.path.join(base_dir, args.state_dir)
    
    if args.id and args.vote:
        reasons = [args.reason] if args.reason else []
        record_vote(state_dir, args.id, args.vote, reasons)
    else:
        interactive_mode(state_dir)

if __name__ == "__main__":
    main()
