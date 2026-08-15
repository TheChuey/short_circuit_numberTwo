import ollama

CHARS_PER_TOKEN = 4


class TokenCounter:
    def __init__(self, scanner=None):
        self.scanner = scanner

    def count(self, text, model=None):
        if not text:
            return 0
        resolved = model or self._first_installed_model()
        if resolved:
            try:
                response = ollama.generate(
                    model=resolved,
                    prompt=text,
                    raw=True,
                    options={"num_predict": 1},
                )
                count = response.get("prompt_eval_count")
                if count is not None:
                    return int(count)
            except Exception as exc:
                print(f"[TOKENS] Ollama count failed for {resolved}: {exc}")
        return self.estimate(text)

    def estimate(self, text):
        return max(1, len(text) // CHARS_PER_TOKEN)

    def count_messages(self, messages, model=None):
        total = 0
        for message in messages:
            total += self.count(message.get("content", ""), model=model)
        return total

    def model_context_window(self, model):
        if not model:
            return None
        try:
            info = ollama.show(model=model).model_dump()
            model_info = info.get("modelinfo") or info.get("model_info") or {}
            return model_info.get("llama.context_length")
        except Exception as exc:
            print(f"[TOKENS] context lookup failed for {model}: {exc}")
            return None

    def _first_installed_model(self):
        if self.scanner is not None:
            try:
                result = self.scanner.scan()
                if result["models"]:
                    return result["models"][0]["id"]
            except Exception as exc:
                print(f"[TOKENS] scanner failed: {exc}")
        try:
            data = ollama.list()
            for m in data.get("models", []):
                if isinstance(m, dict):
                    model_id = m.get("model")
                else:
                    model_id = getattr(m, "model", None)
                if model_id:
                    return model_id
        except Exception as exc:
            print(f"[TOKENS] model list failed: {exc}")
        return None
