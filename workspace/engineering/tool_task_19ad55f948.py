"""
Executive KPI Tracking & Performance Optimization Tool
Author: Principal Software Engineer & Tool Architect
Description: Pure Python data processor for executive KPIs, metric aggregation, and atomic state tracking.
"""

import json
import math
from datetime import datetime
from typing import Dict, Any, List

class KPITrackerEngine:
    def __init__(self, state_file: str = "kpi_state.json"):
        self.state_file = state_file
        self.metrics: Dict[str, List[Dict[str, Any]]] = self._load_state()

    def _load_state(self) -> Dict[str, List[Dict[str, Any]]]:
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_state(self) -> None:
        temp_file = self.state_file + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2)
        with open(temp_file, "r", encoding="utf-8") as rf:
            data = rf.read()
        with open(self.state_file, "w", encoding="utf-8") as wf:
            wf.write(data)

    def ingest_metric(self, kpi_name: str, value: float, timestamp: str = None) -> None:
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        if kpi_name not in self.metrics:
            self.metrics[kpi_name] = []
        self.metrics[kpi_name].append({"value": value, "timestamp": timestamp})
        self._save_state()

    def compute_statistics(self, kpi_name: str) -> Dict[str, float]:
        records = self.metrics.get(kpi_name, [])
        if not records:
            return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "std_dev": 0.0}
        
        values = [r["value"] for r in records]
        count = len(values)
        mean = sum(values) / count
        variance = sum((v - mean) ** 2 for v in values) / count if count > 0 else 0.0
        std_dev = math.sqrt(variance)

        return {
            "count": count,
            "mean": round(mean, 4),
            "min": min(values),
            "max": max(values),
            "std_dev": round(std_dev, 4)
        }

    def evaluate_performance(self, kpi_name: str, target: float, threshold_pct: float = 0.10) -> Dict[str, Any]:
        stats = self.compute_statistics(kpi_name)
        if stats["count"] == 0:
            return {"status": "no_data", "achievement_rate": 0.0}
        
        mean_val = stats["mean"]
        achievement = mean_val / target if target != 0 else 0.0
        is_optimized = achievement >= (1.0 - threshold_pct)

        return {
            "kpi": kpi_name,
            "mean_value": mean_val,
            "target": target,
            "achievement_rate": round(achievement * 100, 2),
            "optimized": is_optimized,
            "status": "optimal" if is_optimized else "suboptimal"
        }
