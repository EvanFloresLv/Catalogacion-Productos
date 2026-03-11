"""
Quick test to verify schema is being properly sent to Gemini API
"""

from infrastructure.llm.gemini import LLMClient
from infrastructure.prompts import Prompt

def test_schema_with_prompt_service():
    """Test that schema from prompt service is properly used."""

    # Load prompt with schema
    prompt_service = Prompt(
        file_path="./src/prompts/predict_sheet_data.yaml",
    )

    # Sample data
    input_data = {
        "Playeras Hombre": {
            "palabras_clave": ["playera", "hombre", "casual", "manga corta"]
        },
        "Zapatos Mujer": {
            "palabras_clave": ["zapatos", "mujer", "tacones", "elegante"]
        }
    }

    # Get prompt with schema
    prompt = prompt_service.get_prompt(input_data=input_data)

    print("=" * 60)
    print("PROMPT STRUCTURE:")
    print("=" * 60)
    print(f"Keys in prompt: {prompt.keys()}")
    print(f"\nSystem message (first 100 chars): {prompt.get('system', '')[:100]}...")
    print(f"\nUser message (first 100 chars): {prompt.get('user', '')[:100]}...")
    print(f"\nSchema present: {'schema' in prompt}")
    if 'schema' in prompt:
        print(f"Schema type: {prompt['schema'].get('type')}")
        print(f"Schema properties: {prompt['schema'].get('properties', {}).keys() if 'properties' in prompt['schema'] else 'Using additionalProperties'}")

    # Call LLM
    print("\n" + "=" * 60)
    print("CALLING LLM WITH SCHEMA:")
    print("=" * 60)

    llm_client = LLMClient()

    # Test 1: Just pass the prompt (schema should be used from prompt dict)
    print("\nTest 1: Using schema from prompt dict")
    response = llm_client.chat(prompt, mime_type="application/json")
    print(f"\nResponse:\n{response}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_schema_with_prompt_service()
