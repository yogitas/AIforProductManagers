"""
Manages state persistence (seen items and preference memory) using YAML files.
Handles deduplication hashing and state backup routines.

PEDAGOGICAL NOTE FOR READERS:
Production agents must be resilient to state loss and corruption. Instead of deleting
or overwriting state files blindly, we backup old state files with a timestamp prefix
whenever a state reset is triggered. This models the practice of maintaining audit trails
and disaster recovery capabilities.
"""
import os
import yaml
import shutil
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Set

def get_item_id(url: str, title: str) -> str:
    """
    Generates a unique 8-character ID for an item based on its source URL or title.
    Used for both deduplication and routing feedback issues.
    """
    # COULD USE A LIBRARY HERE: e.g. `rapidfuzz` for fuzzy near-duplicate matching.
    # Done with simple content hashing below instead, since exact-hash dedup is
    # easier to trace and explain for a teaching repo — upgrade to fuzzy matching
    # if near-duplicate (not just identical) items become a real problem.
    key = url.strip() if url and url.strip() else title.strip()
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:8]

def backup_state(state_dir: str):
    """
    Backs up seen_items.yaml and preference_memory.yaml to timestamped files
    instead of deleting them. Essential for auditability and recovery.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for filename in ["seen_items.yaml", "preference_memory.yaml"]:
        src_path = os.path.join(state_dir, filename)
        if os.path.exists(src_path):
            backup_path = f"{src_path}.bak-{timestamp}"
            try:
                shutil.copy2(src_path, backup_path)
                print(f"Backed up state file: {src_path} -> {backup_path}")
            except Exception as e:
                print(f"Warning: Failed to back up {src_path}: {e}")

def load_seen_items(state_dir: str) -> Set[str]:
    """
    Loads list of previously seen item IDs. Returns an empty set if not found.
    """
    path = os.path.join(state_dir, "seen_items.yaml")
    if not os.path.exists(path):
        return set()
    
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
            return set(data) if isinstance(data, list) else set()
        except Exception:
            # Safe fallback if file is corrupted
            return set()

def save_seen_items(state_dir: str, seen_ids: Set[str]):
    """
    Saves the list of seen item IDs.
    """
    os.makedirs(state_dir, exist_ok=True)
    path = os.path.join(state_dir, "seen_items.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(list(seen_ids), f, default_flow_style=False)

def load_preference_memory(state_dir: str) -> List[Dict[str, Any]]:
    """
    Loads the preference memory list of feedback.
    """
    path = os.path.join(state_dir, "preference_memory.yaml")
    if not os.path.exists(path):
        return []
    
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
            if isinstance(data, list):
                # GUARDRAIL: Sliding Window Memory
                # We limit preference memory to the last 15 entries to prevent LLM prompt context bloat
                # and ensure the agent stays responsive to recent changes in user preference.
                return data[-15:]
            return []
        except Exception:
            return []

def save_preference_memory(state_dir: str, memory: List[Dict[str, Any]]):
    """
    Saves the preference memory list.
    """
    os.makedirs(state_dir, exist_ok=True)
    path = os.path.join(state_dir, "preference_memory.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(memory, f, default_flow_style=False)
