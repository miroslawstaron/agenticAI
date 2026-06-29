#!/usr/bin/env python3
"""
Ollama-specific Agent for SWE-bench testing

Uses Ollama's native API instead of going through LiteLLM
for more reliable communication with Ollama servers.
"""

import sys
import os
import json
import time
import requests
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.abspath('.'))

from agent import AgentAI
from messagequeue import MessageQueue, reset_message_queue
from agent_id_manager import AgentIDManager
import config


class OllamaAgent:
    """Direct Ollama API agent for testing"""

    def __init__(self, server_address: str, model_name: str, my_role: str = ""):
        """Initialize Ollama agent

        Args:
            server_address: Ollama server URL (e.g., http://localhost:11434)
            model_name: Model name (e.g., gpt-oss:20b)
            my_role: System role/prompt
        """
        self.server_address = server_address
        self.model_name = model_name
        self.my_role = my_role
        self.messages: List[Dict[str, str]] = []
        self.session = requests.Session()

    def get_response(self, prompt: str) -> Optional[str]:
        """Get response from Ollama

        Args:
            prompt: User prompt

        Returns:
            Model response or None if failed
        """
        # Add user message
        self.messages.append({"role": "user", "content": prompt})

        # Build system message if role provided
        messages_to_send = []
        if self.my_role:
            messages_to_send.append({"role": "system", "content": self.my_role})
        messages_to_send.extend(self.messages)

        # Prepare payload for Ollama API
        payload = {
            "model": self.model_name,
            "messages": messages_to_send,
            "stream": False,
        }

        # Call Ollama
        try:
            endpoint = f"{self.server_address}/api/chat"

            response = self.session.post(
                endpoint,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()
            result = response.json()

            if "message" in result:
                content = result["message"].get("content", "")
            else:
                content = result.get("response", "")

            if content:
                # Add assistant message
                self.messages.append({"role": "assistant", "content": content})
                return content
            else:
                return None

        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception as e:
            print(f"[ERROR] Ollama request failed: {e}")
            return None

    def close(self):
        """Close the session"""
        self.session.close()


def test_ollama_connection(server: str, model: str) -> bool:
    """Test Ollama connection

    Args:
        server: Ollama server URL
        model: Model name

    Returns:
        True if connection works, False otherwise
    """
    try:
        # Test /api/tags endpoint
        response = requests.get(
            f"{server}/api/tags",
            timeout=10
        )
        response.raise_for_status()

        tags = response.json()
        models = [m.get("name") for m in tags.get("models", [])]

        print(f"[OK] Ollama server is running")
        print(f"[OK] Available models: {', '.join(models)}")

        if model in models:
            print(f"[OK] Model '{model}' is available")
            return True
        else:
            print(f"[WARN] Model '{model}' not found")
            print(f"[WARN] Available: {', '.join(models)}")
            return False

    except Exception as e:
        print(f"[FAIL] Cannot connect to Ollama: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    server = "http://lazythought.cse.chalmers.se"
    model = "gpt-oss:20b"

    print("\n" + "="*80)
    print("OLLAMA AGENT TEST")
    print("="*80 + "\n")

    # Test connection
    print("[1] Testing Ollama connection...")
    if not test_ollama_connection(server, model):
        print("\n[FAIL] Cannot connect to Ollama")
        sys.exit(1)

    # Create agent
    print("\n[2] Creating agent...")
    agent = OllamaAgent(
        server_address=server,
        model_name=model,
        my_role="You are a helpful assistant."
    )
    print("[OK] Agent created")

    # Test response
    print("\n[3] Testing response...")
    response = agent.get_response("What is 2+2?")

    if response:
        print(f"[OK] Response received:")
        print(f"     {response[:100]}...")
    else:
        print("[FAIL] No response received")

    agent.close()
    print("\n" + "="*80 + "\n")
