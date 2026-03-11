"""
Test the simplified dict-based LLM client interface.
"""

from infrastructure.llm.gemini import LLMClient


def test_simple_prompt():
    """Test basic prompt without system message or schema."""
    client = LLMClient()

    prompt = {
        "user": "What is the capital of France? Answer with just the city name."
    }

    response = client.chat(prompt)
    print("Simple prompt response:", response)
    assert response
    assert len(response) > 0


def test_prompt_with_system():
    """Test prompt with system message."""
    client = LLMClient()

    prompt = {
        "system": "You are a helpful geography assistant. Be concise.",
        "user": "What is the capital of France? Answer with just the city name."
    }

    response = client.chat(prompt)
    print("System+user prompt response:", response)
    assert response
    assert len(response) > 0


def test_prompt_with_schema():
    """Test prompt with JSON schema for structured output."""
    client = LLMClient()

    prompt = {
        "system": "You are a data extraction assistant.",
        "user": "Extract the country and capital: France has Paris as its capital.",
        "schema": {
            "type": "object",
            "properties": {
                "country": {"type": "string"},
                "capital": {"type": "string"}
            },
            "required": ["country", "capital"]
        }
    }

    response = client.chat(prompt)
    print("Schema prompt response:", response)
    assert response
    assert len(response) > 0


def test_prompt_with_temperature():
    """Test prompt with custom generation parameters."""
    client = LLMClient()

    prompt = {
        "user": "Write a creative name for a French restaurant."
    }

    response = client.chat(prompt, temperature=0.9)
    print("High temperature response:", response)
    assert response
    assert len(response) > 0


if __name__ == "__main__":
    print("Testing simplified dict-based LLM client interface\n")
    print("=" * 60)

    try:
        print("\n1. Testing simple prompt...")
        test_simple_prompt()
        print("✓ Simple prompt test passed")

        print("\n2. Testing prompt with system message...")
        test_prompt_with_system()
        print("✓ System message test passed")

        print("\n3. Testing prompt with schema...")
        test_prompt_with_schema()
        print("✓ Schema test passed")

        print("\n4. Testing prompt with custom parameters...")
        test_prompt_with_temperature()
        print("✓ Custom parameters test passed")

        print("\n" + "=" * 60)
        print("All tests passed! ✓")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
