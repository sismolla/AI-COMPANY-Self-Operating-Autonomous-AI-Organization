import json
import tempfile
import os
from typing import Dict, Any, List, Callable

class APITestDataProcessor:
    """Processes and validates API test payloads, responses, and execution logs."""
    
    @staticmethod
    def validate_schema(data: Dict[str, Any], required_keys: List[str]) -> bool:
        """Validates that all required keys are present in the provided dictionary payload."""
        return all(key in data for key in required_keys)

    @staticmethod
    def transform_payload(data: Dict[str, Any], transformer: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        """Applies a transformation function to an API payload deterministically."""
        return transformer(data)

class APIWorkflowAutomation:
    """Manages test workflows with atomic state persistence for test runs."""
    
    def __init__(self, state_file: str):
        self.state_file = state_file

    def save_state(self, state_data: Dict[str, Any]) -> None:
        """Saves test execution state atomically using temporary files."""
        dir_name = os.path.dirname(self.state_file) or '.'
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tf:
            json.dump(state_data, tf, indent=2)
            temp_name = tf.name
        os.replace(temp_name, self.state_file)

    def load_state(self) -> Dict[str, Any]:
        """Loads test execution state safely."""
        if not os.path.exists(self.state_file):
            return {}
        with open(self.state_file, 'r') as f:
            return json.load(f)

if __name__ == '__main__':
    # Basic self-test for sandbox verification
    processor = APITestDataProcessor()
    assert processor.validate_schema({'status': 200, 'data': 'ok'}, ['status', 'data']) == True
    print('Sandbox validation passed successfully.')
