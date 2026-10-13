import json
import ollama


MODEL_NAME = "qwen3:1.7b"
MAX_NEW_TOKENS = 256
MAX_RETRIES = 1


class LocalLLM:

    def __init__(self):
        print("Connecting to local Ollama model...")

        models = ollama.list()
        available_models = {
            item.model for item in models.models
        }

        if MODEL_NAME not in available_models:
            raise RuntimeError(
                f"Model {MODEL_NAME} is not available. "
                "Run: ollama pull qwen3:1.7b"
            )

        print(f"Model ready: {MODEL_NAME}")

    def generate(self, prompt):
        system_prompt = """
You are an API planning model for a banking application.

Convert the user's request into a structured API execution plan.

Rules:
1. Return exactly one valid JSON object.
2. Do not include Markdown, explanations, or reasoning.
3. Use only endpoints and parameters present in the API catalog
   provided in the user's prompt.
4. Never invent an endpoint, parameter, customer ID, or account ID.
5. Extract only values explicitly supplied or established by context.
6. Preserve the required execution order.
7. If information is missing, do not guess it.
8. Do not claim that an operation has been executed.
9. The application, not you, validates and executes the plan.

Required JSON structure:
{
  "status": "success",
  "steps": [
    {
      "api": "/actual/catalog/endpoint",
      "parameters": {}
    }
  ]
}
"""

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        for attempt in range(MAX_RETRIES + 1):
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages,
                format="json",
                options={
                    "temperature": 0,
                    "num_predict": MAX_NEW_TOKENS,
                },
                think=False,
            )

            content = response.message.content.strip()

            try:
                parsed = json.loads(content)

                if not isinstance(parsed, dict):
                    raise ValueError(
                        "Model output must be a JSON object."
                    )

                if "steps" not in parsed:
                    raise ValueError(
                        "Model output is missing the 'steps' field."
                    )

                if not isinstance(parsed["steps"], list):
                    raise ValueError(
                        "The 'steps' field must be a JSON list."
                    )

                # Return normalized JSON after structural checks.
                return json.dumps(parsed)

            except (json.JSONDecodeError, ValueError) as exc:
                print(
                    f"Invalid model output on attempt "
                    f"{attempt + 1}: {exc}"
                )
                print("Model output:", repr(content))

                if attempt >= MAX_RETRIES:
                    raise ValueError(
                        "The local model failed to return a valid "
                        "JSON execution plan after retrying."
                    ) from exc

                # Ask for a fresh JSON response.
                messages.append(
                    {
                        "role": "assistant",
                        "content": content,
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was invalid. "
                            "Return a corrected JSON object only. "
                            "Follow the original instructions and "
                            "use the exact API catalog from the "
                            "original request. Do not invent "
                            "endpoints or parameters."
                        ),
                    }
                )

        raise RuntimeError("Unexpected model-generation failure.")