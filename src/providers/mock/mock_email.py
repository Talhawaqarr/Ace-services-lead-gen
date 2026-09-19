from typing import Dict, Any
import uuid
import os
import json

# Store sent emails locally under tmp/mock_emails.json
STORE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "mock_emails.json")


class MockEmailProvider:
    def __init__(self):
        os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
        if not os.path.exists(STORE_PATH):
            with open(STORE_PATH, "w", encoding="utf8") as f:
                json.dump([], f)

    def send_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Never send; just store the payload with a local id and return simulated ack
        with open(STORE_PATH, "r+", encoding="utf8") as f:
            data = json.load(f)
        record = {
            "id": str(uuid.uuid4()),
            "payload": payload,
        }
        data.append(record)
        with open(STORE_PATH, "w", encoding="utf8") as f:
            json.dump(data, f, indent=2)
        return {"status": "stored", "local_id": record["id"]}
