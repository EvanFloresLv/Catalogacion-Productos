from infrastructure.llm.gemini.client import LLMClient, Message


def test_simple_chat():
    """Test basic chat functionality."""
    print("\n" + "="*60)
    print("Test 1: Simple Chat")
    print("="*60)

    client = LLMClient()

    response = client.chat("What is 2+2? Answer in one sentence.")
    print(f"Response: {response}")


def test_conversation():
    """Test conversation with messages."""
    print("\n" + "="*60)
    print("Test 2: Conversation")
    print("="*60)

    client = LLMClient(temperature=0.5)

    messages = [
        Message(role="system", content="You are a helpful Python expert."),
        Message(role="user", content="What is a list comprehension?"),
    ]

    response = client.chat(messages)
    print(f"Response: {response}")


def test_custom_config():
    """Test with custom configuration."""
    print("\n" + "="*60)
    print("Test 4: Custom Configuration")
    print("="*60)

    client = LLMClient(
        model="gemini-2.5-flash",
        temperature=0.3,
        max_tokens=100,
    )

    response = client.chat(
        "Explain machine learning in one sentence.",
        max_tokens=50,  # Override
    )
    print(f"Response: {response}")


def test_error_handling():
    """Test error handling."""
    print("\n" + "="*60)
    print("Test 5: Error Handling")
    print("="*60)

    from infrastructure.llm.errors import ValidationLLMError

    client = LLMClient()

    try:
        # Empty message should fail validation
        _response = client.chat([])
    except ValidationLLMError as e:
        print(f"✓ Caught expected error: {e}")


if __name__ == "__main__":
    print("\n🚀 Starting Gemini LLM Client Tests\n")

    try:
        test_simple_chat()
        test_conversation()
        test_custom_config()
        test_error_handling()

        print("\n" + "="*60)
        print("✅ All tests completed successfully!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
