import json
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.calls: List[float] = []

    def acquire(self) -> bool:
        now = time.time()
        self.calls = [t for t in self.calls if now - t < self.period_seconds]
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False

class ContentPipeline:
    def __init__(self, storage_path: str = "pipeline_state.json"):
        self.storage_path = Path(storage_path)
        self.queue: List[Dict[str, Any]] = []
        self.rate_limiters = {
            "linkedin": RateLimiter(max_calls=5, period_seconds=60.0),
            "x": RateLimiter(max_calls=15, period_seconds=60.0),
            "telegram": RateLimiter(max_calls=30, period_seconds=60.0)
        }
        self.load_state()

    def load_state(self) -> None:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.queue = data.get("queue", [])
            except Exception:
                self.queue = []

    def save_state(self) -> None:
        temp_dir = self.storage_path.parent
        temp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', dir=temp_dir, delete=False, encoding="utf-8") as tf:
            json.dump({"queue": self.queue}, tf, indent=2)
            temp_name = tf.Name if hasattr(tf, 'Name') else tf.name
        
        import os
        os.replace(temp_name, self.storage_path)

    def add_post(self, content: str, channels: List[str]) -> str:
        post_id = f"post_{int(time.time())}_{len(self.queue)}"
        post_item = {
            "id": post_id,
            "content": content,
            "channels": channels,
            "status": "pending",
            "attempts": {ch: 0 for ch in channels},
            "errors": {}
        }
        self.queue.append(post_item)
        self.save_state()
        return post_id

    def publish_post(self, post_id: str, channel: str) -> bool:
        for item in self.queue:
            if item["id"] == post_id:
                if channel not in item["channels"]:
                    return False
                
                limiter = self.rate_limiters.get(channel)
                if limiter and not limiter.acquire():
                    item["errors"][channel] = "Rate limit exceeded"
                    self.save_state()
                    return False

                # Simulate API call
                item["attempts"][channel] += 1
                success = True # Simulated successful publish
                
                if success:
                    item["channels"].remove(channel)
                    if not item["channels"]:
                        item["status"] = "published"
                else:
                    item["errors"][channel] = "API delivery failed"
                
                self.save_state()
                return success
        return False
