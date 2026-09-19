from typing import Dict, Any


class MockLLMProvider:
    def generate(self, prompt: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        # Deterministic template-based generation for development
        subject = f"About the project: {prompt[:50]}"
        body = f"Hello,\n\nWe noticed your project: {prompt}\n\nRegards,\nACE Services (dev)"
        return {"subject": subject, "body": body, "claims_used": [], "llm_metadata": {"provider": "mock"}}
