import unittest

from host.llm_client import (
    _apply_response_format,
    _content_from_gemini_response,
    _gemini_payload,
    _is_gemini_backend,
    _message_role_summary,
    _remote_forbidden_hint,
    _remote_gateway_hint,
    _request_headers,
    _unexpected_llm_body_error,
    model_candidates,
)


class LLMClientTests(unittest.TestCase):
    def test_model_candidates_prefers_primary_then_fallbacks(self):
        backend = {
            "model": "elyza-jp-8b-local",
            "fallback_models": [
                "qwen2.5-7b-instruct-local",
                "qwen2.5:7b-instruct",
            ],
        }

        self.assertEqual(
            model_candidates(backend),
            [
                "elyza-jp-8b-local",
                "qwen2.5-7b-instruct-local",
                "qwen2.5:7b-instruct",
            ],
        )

    def test_model_candidates_removes_duplicates(self):
        backend = {
            "model": "elyza-jp-8b-local",
            "fallback_models": [
                "elyza-jp-8b-local",
                "qwen2.5-7b-instruct-local",
            ],
        }

        self.assertEqual(
            model_candidates(backend),
            [
                "elyza-jp-8b-local",
                "qwen2.5-7b-instruct-local",
            ],
        )

    def test_message_role_summary(self):
        self.assertEqual(
            _message_role_summary([
                {"role": "system", "content": "a"},
                {"role": "assistant", "content": "b"},
                {"role": "user", "content": "c"},
                {"role": "system", "content": "d"},
            ]),
            "assistant:1,system:2,user:1",
        )

    def test_apply_response_format_json_object(self):
        payload = {}
        _apply_response_format(payload, {"response_format": "json_object"})
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_request_headers_include_extra_backend_headers(self):
        headers = _request_headers({
            "api_key": "ollama",
            "headers": {
                "CF-Access-Client-Id": "client-id",
                "CF-Access-Client-Secret": "secret",
            },
        })

        self.assertEqual(headers["Authorization"], "Bearer ollama")
        self.assertEqual(headers["CF-Access-Client-Id"], "client-id")
        self.assertEqual(headers["CF-Access-Client-Secret"], "secret")

    def test_unexpected_body_detects_cloudflare_access_login(self):
        error = _unexpected_llm_body_error(
            "<html><title>Sign in - Cloudflare Access</title></html>",
            "text/html",
        )

        self.assertIn("Cloudflare Access", error)
        self.assertIn("Service Auth", error)

    def test_remote_gateway_hint_detects_cloudflare_502(self):
        hint = _remote_gateway_hint("<title>kevinx96.icu | 502: Bad gateway</title> Cloudflare")

        self.assertIn("tunnel", hint)
        self.assertIn("127.0.0.1:11434", hint)

    def test_remote_forbidden_hint_detects_ollama_host_header_rejection(self):
        hint = _remote_forbidden_hint(403, "", "https://ollama.example.com/v1")

        self.assertIn("HTTP Host Header", hint)
        self.assertIn("localhost:11434", hint)

    def test_gemini_backend_detection(self):
        self.assertTrue(_is_gemini_backend("gemini", {}))
        self.assertTrue(_is_gemini_backend("cloud", {"type": "gemini"}))
        self.assertFalse(_is_gemini_backend("ollama", {}))

    def test_gemini_payload_maps_chat_messages(self):
        payload = _gemini_payload(
            [
                {"role": "system", "content": "contract"},
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            {"temperature": 0.4, "max_tokens": 123, "response_format": "json_object"},
        )

        self.assertEqual(payload["systemInstruction"]["parts"][0]["text"], "contract")
        self.assertEqual(payload["contents"][0]["role"], "user")
        self.assertEqual(payload["contents"][1]["role"], "model")
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 123)

    def test_content_from_gemini_response(self):
        content = _content_from_gemini_response(
            '{"candidates":[{"content":{"parts":[{"text":"{\\"gm_text\\":\\"ok\\"}"}]}}]}'
        )

        self.assertEqual(content, '{"gm_text":"ok"}')

    def test_content_from_gemini_response_ignores_malformed_candidates(self):
        self.assertEqual(_content_from_gemini_response('{"candidates":[null]}'), "")
        self.assertEqual(_content_from_gemini_response('{"candidates":["bad"]}'), "")
        self.assertEqual(_content_from_gemini_response('{"candidates":[{"content":null}]}'), "")
        self.assertEqual(_content_from_gemini_response('{"candidates":[{"content":{"parts":"bad"}}]}'), "")


if __name__ == "__main__":
    unittest.main()
