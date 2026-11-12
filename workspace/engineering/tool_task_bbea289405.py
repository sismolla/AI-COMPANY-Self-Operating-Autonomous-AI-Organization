import json
import os
import tempfile
import time
from typing import Dict, List, Any, Callable

class APITestRunner:
    def __init__(self, state_file: str = "test_execution_state.json"):
        self.state_file = state_file
        self.results: List[Dict[str, Any]] = []

    def run_test(self, name: str, test_func: Callable[[], bool]) -> Dict[str, Any]:
        start_time = time.time()
        success = False
        error_message = None
        try:
            success = test_func()
        except Exception as e:
            error_message = str(e)
        duration = time.time() - start_time
        
        result = {
            "name": name,
            "success": success,
            "duration": duration,
            "error": error_message,
            "timestamp": time.time()
        }
        self.results.append(result)
        self._persist_state()
        return result

    def _persist_state(self) -> None:
        dir_name = os.path.dirname(os.path.abspath(self.state_file)) or "."
        fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(self.results, f, indent=2)
            os.replace(temp_path, self.state_file)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0.0
        }

def test_api_harness_suite():
    runner = APITestRunner(state_file="test_state_sandbox.json")
    
    # Sample mock test cases
    res1 = runner.run_test("test_mock_endpoint_success", lambda: True)
    assert res1["success"] is True
    
    res2 = runner.run_test("test_mock_assertion_failure", lambda: False)
    assert res2["success"] is False
    
    summary = runner.get_summary()
    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    
    # Cleanup
    if os.path.exists("test_state_sandbox.json"):
        os.remove("test_state_sandbox.json")
    return True

if __name__ == "__main__":
    assert test_api_harness_suite()
    print("All API test suite harness tests passed successfully.")