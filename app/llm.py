from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


MODEL_NAME = "Qwen/Qwen3-1.7B"


class LocalLLM:

    def __init__(self):
        print("Loading local model...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype="auto",
            device_map="auto"
        )

        print("Model loaded.")

    def generate(self, prompt):

        messages = [
            {
                "role": "system",
                "content": """
You are an API planning model.

Your job is to convert natural language into
a structured API execution plan.

IMPORTANT RULES:

1. Output ONLY valid JSON.
2. Do NOT output reasoning.
3. Do NOT output <think>.
4. Do NOT explain your answer.
5. Do NOT output markdown.
6. Use ONLY APIs provided in the API catalog.
7. Never invent an API.
8. Extract parameters from the user's request.
9. Preserve the required execution order.

Your response MUST start directly with { and
must contain only the JSON object.

Expected format:

{
    "status": "success",
    "steps": [
        {
            "api": "/endpoint",
            "parameters": {}
        }
    ]
}
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )

        inputs = self.tokenizer(
            text,
            return_tensors="pt"
        ).to(self.model.device)

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=False
        )

        response = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True
        )

        return response.strip()