import math
import unittest
from unittest.mock import patch

import httpx
from support import configured, real_config
from app.core.errors import CitationValidationError, ProviderError
from app.core.providers import post_json
from app.core.metrics import (
    embedding_tokens_total,
    embedding_estimated_tokens_total,
    record_embedding_usage,
)
from app.services.embeddings import embed, validate_vectors
from app.services.llm import _parse_result, generate
from app.services.reranking import rerank


class EmbeddingTests(unittest.TestCase):
    def test_fixture_is_deterministic_finite_and_normalized(self):
        with configured(embedding_dim=32):
            texts = [f"document-{index}" for index in range(200)]
            with patch("app.services.embeddings.post_json") as transport:
                vectors = embed(texts)
                self.assertEqual(vectors, embed(texts))
                transport.assert_not_called()
            self.assertEqual(len({tuple(v) for v in vectors}), len(texts))
            for vector in vectors:
                self.assertEqual(len(vector), 32)
                self.assertTrue(all(math.isfinite(x) for x in vector))
                self.assertAlmostEqual(math.hypot(*vector), 1)

    def test_invalid_vectors_are_rejected(self):
        for vectors in (
            [],
            [[1, 2], [3, 4]],
            [[1]],
            [[1, 2, 3]],
            [[0, 0]],
            [[float("nan"), 1]],
            [[float("inf"), 1]],
            [[1e100, 1]],
            [["1", 2]],
            [[True, 2]],
            [[10**400, 1]],
            None,
        ):
            with self.subTest(vectors=repr(vectors)), self.assertRaises(ProviderError):
                validate_vectors(vectors, 1, 2)

    def test_openai_request_dimension_and_response_order(self):
        with (
            real_config(embedding_dim=2),
            patch(
                "app.services.embeddings.post_json",
                return_value={
                    "data": [
                        {"index": 1, "embedding": [0, 3]},
                        {"index": 0, "embedding": [3, 0]},
                    ],
                    "usage": {"prompt_tokens": 9},
                },
            ) as transport,
        ):
            self.assertEqual(embed(["one", "two"]), [[1, 0], [0, 1]])
            self.assertEqual(
                transport.call_args.args[0], "https://gateway.example/v1/embeddings"
            )
            self.assertEqual(transport.call_args.kwargs["payload"]["dimensions"], 2)

    def test_missing_duplicate_or_wrong_embedding_indices_fail(self):
        for indices in ([0], [0, 0], [0, 2], [0, True], [0, "1"]):
            data = {"data": [{"index": i, "embedding": [1, 0]} for i in indices]}
            with (
                self.subTest(indices=indices),
                real_config(embedding_dim=2),
                patch(
                    "app.services.embeddings.post_json",
                    return_value=data,
                ),
                self.assertRaises(ProviderError),
            ):
                embed(["one", "two"])

    def test_real_failure_never_uses_fixture(self):
        with (
            real_config(),
            patch("app.services.embeddings.post_json", side_effect=ProviderError()),
            patch("app.services.embeddings._local_embed") as fixture,
            self.assertRaises(ProviderError),
        ):
            embed(["text"])
        fixture.assert_not_called()

    def test_gemini_two_separate_requests_and_task_prefixes(self):
        for input_type, prefix in (
            ("query", "task: question answering | query: "),
            ("document", "title: none | text: "),
        ):
            with (
                real_config(
                    embedding_provider="gemini", gemini_api_key="test", embedding_dim=2
                ),
                patch(
                    "app.services.embeddings.post_json",
                    return_value={"embeddings": [{"values": [1, 0]}]},
                ) as transport,
            ):
                embed(["text"], input_type)
                request = transport.call_args.kwargs["payload"]["requests"][0]
                self.assertNotIn("taskType", request["embedContentConfig"])
                self.assertEqual(
                    request["content"]["parts"][0]["text"], prefix + "text"
                )

    def test_gemini_usage_uses_provider_tokens_without_inventing_missing_values(self):
        for usage, expected in (
            ({"promptTokenCount": 12}, 12),
            ({"promptTokenCount": 0}, 0),
            ({}, None),
            ({"promptTokenCount": -1}, None),
            ({"promptTokenCount": True}, None),
            ("invalid", None),
        ):
            with (
                self.subTest(usage=usage),
                real_config(embedding_provider="gemini", gemini_api_key="test", embedding_dim=2),
                patch("app.services.embeddings.post_json", return_value={
                    "embeddings": [{"values": [1, 0]}], "usageMetadata": usage,
                }),
                patch("app.services.embeddings.record_embedding_usage") as record,
            ):
                embed(["text"], "document")
                record.assert_called_once_with("gemini", "document", expected, ["text"])

    def test_gemini_one_uses_task_type(self):
        with (
            real_config(
                embedding_provider="gemini",
                gemini_api_key="test",
                embedding_model="gemini-embedding-001",
                embedding_dim=2,
            ),
            patch(
                "app.services.embeddings.post_json",
                return_value={"embeddings": [{"values": [1, 0]}]},
            ) as transport,
        ):
            embed(["text"], "query")
            config = transport.call_args.kwargs["payload"]["requests"][0][
                "embedContentConfig"
            ]
            self.assertEqual(config["taskType"], "RETRIEVAL_QUERY")

    def test_ollama_native_vectors_no_truncation_or_padding(self):
        with (
            real_config("ollama", embedding_provider="ollama"),
            patch(
                "app.services.embeddings.post_json",
                return_value={"embeddings": [[1] * 1025]},
            ) as transport,
            self.assertRaises(ProviderError),
        ):
            embed(["text"], "query")
        payload = transport.call_args.kwargs["payload"]
        self.assertFalse(payload["truncate"])
        self.assertNotIn("dimensions", payload)
        self.assertTrue(payload["input"][0].startswith("Represent this sentence"))

    def test_voyage_payload_and_usage(self):
        with (
            real_config(
                embedding_provider="voyage", voyage_api_key="test", embedding_dim=2
            ),
            patch(
                "app.services.embeddings.post_json",
                return_value={
                    "data": [{"index": 0, "embedding": [1, 0]}],
                    "usage": {"total_tokens": 3},
                },
            ) as transport,
        ):
            self.assertEqual(embed(["text"], "query"), [[1, 0]])
            payload = transport.call_args.kwargs["payload"]
            self.assertEqual(payload["input_type"], "query")
            self.assertEqual(payload["output_dimension"], 2)
            self.assertFalse(payload["truncation"])

    def test_batches_have_a_bounded_size(self):
        with (
            real_config(embedding_dim=2, embedding_batch_size=2),
            patch(
                "app.services.embeddings.post_json",
                side_effect=lambda *a, **kw: {
                    "data": [
                        {"index": i, "embedding": [1, 0]}
                        for i in range(len(kw["payload"]["input"]))
                    ]
                },
            ) as transport,
        ):
            self.assertEqual(len(embed(["a", "b", "c", "d", "e"])), 5)
            self.assertEqual(transport.call_count, 3)

    def test_empty_input_is_explicit(self):
        with configured():
            self.assertEqual(embed([]), [])
            with self.assertRaises(ValueError):
                embed([" "])
            with self.assertRaises(ValueError):
                embed(["text"], "typo")

    def test_estimate_and_reported_usage_are_separate(self):
        real = embedding_tokens_total.labels("openai", "query")._value.get()
        estimate = embedding_estimated_tokens_total.labels(
            "openai", "query"
        )._value.get()
        record_embedding_usage("openai", "query", 7, ["one two"])
        self.assertEqual(
            embedding_tokens_total.labels("openai", "query")._value.get(), real + 7
        )
        self.assertEqual(
            embedding_estimated_tokens_total.labels("openai", "query")._value.get(),
            estimate,
        )
        record_embedding_usage("openai", "query", None, ["one two"])
        self.assertGreater(
            embedding_estimated_tokens_total.labels("openai", "query")._value.get(),
            estimate,
        )


class GenerationTests(unittest.TestCase):
    contexts = [
        {"id": 1, "context_id": "chunk:1", "document_id": 1, "source_segment_id": 1,
         "source": "test.txt", "locator": {"type": "paragraph", "value": "1"},
         "chunk_text": "RAG is retrieval augmented generation."}
    ]

    def test_fixture_label_and_usage_truth(self):
        with configured(), patch("app.services.llm.post_json") as transport:
            result = generate("What is RAG?", self.contexts)
        transport.assert_not_called()
        self.assertIn("FIXTURE", result["answer"])
        self.assertEqual(result["mode"], "fixture")
        self.assertEqual(result["usage"]["source"], "unavailable")
        self.assertIsNone(result["usage"]["input_tokens"])

    def test_unknown_citation_is_rejected_before_publication(self):
        raw = '{"status":"Answered","claims":[{"text":"invented","citation_ids":["chunk:999"]}]}'
        with self.assertRaises(CitationValidationError):
            _parse_result(raw, self.contexts)

    def test_no_evidence_contract_has_no_answer_or_citation(self):
        result = _parse_result('{"status":"NoEvidence","claims":[]}', self.contexts)
        self.assertEqual(result, {"status": "NoEvidence", "answer": None, "claims": [], "citation_ids": []})

    def test_every_claim_requires_a_valid_citation(self):
        for raw in (
            '{"status":"Answered","claims":[{"text":"claim","citation_ids":[]}]}',
            '{"status":"Answered","claims":[{"text":" ","citation_ids":["chunk:1"]}]}',
            '{"status":"Answered","claims":[]}',
        ):
            with self.subTest(raw=raw), self.assertRaises(CitationValidationError):
                _parse_result(raw, self.contexts)

    def test_non_json_and_legacy_contract_are_rejected(self):
        for raw in (
            "answer [nguồn: test.txt]",
            '{"status":"Answered","answer":"answer","citation_ids":["chunk:1"]}',
        ):
            with self.subTest(raw=raw), self.assertRaises(ProviderError):
                _parse_result(raw, self.contexts)

    def test_openai_gateway_explicit_endpoint_and_usage(self):
        with (
            real_config(),
            patch(
                "app.services.llm.post_json",
                return_value={
                    "choices": [{"message": {"content": '{"status":"Answered","claims":[{"text":"answer","citation_ids":["chunk:1"]}]}'}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 4},
                },
            ) as transport,
        ):
            result = generate("question", self.contexts)
        self.assertEqual(
            transport.call_args.args[0], "https://gateway.example/v1/chat/completions"
        )
        self.assertEqual(
            result["usage"],
            {"input_tokens": 10, "output_tokens": 4, "source": "provider"},
        )
        self.assertEqual(result["mode"], "real")

    def test_other_chat_provider_contracts(self):
        responses = {
            "gemini": {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "hidden", "thought": True},
                                {"text": '{"status":"Answered","claims":[{"text":"answer","citation_ids":["chunk:1"]}]}'},
                            ]
                        }
                    }
                ],
                "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 3},
            },
            "anthropic": {
                "content": [{"type": "text", "text": '{"status":"Answered","claims":[{"text":"answer","citation_ids":["chunk:1"]}]}'}],
                "usage": {"input_tokens": 2, "output_tokens": 3},
            },
            "ollama": {
                "message": {"content": '{"status":"Answered","claims":[{"text":"answer","citation_ids":["chunk:1"]}]}'},
                "prompt_eval_count": 2,
                "eval_count": 3,
            },
        }
        for provider, response in responses.items():
            with (
                self.subTest(provider=provider),
                real_config(provider, gemini_api_key="test", anthropic_api_key="test"),
                patch("app.services.llm.post_json", return_value=response),
            ):
                result = generate("question", self.contexts)
                self.assertEqual(result["answer"], "answer")
                self.assertEqual(result["usage"]["input_tokens"], 2)

    def test_deepseek_json_contract_uses_its_own_key_and_token_parameter(self):
        response = {
            "choices": [{"finish_reason": "stop", "message": {
                "content": '{"status":"Answered","claims":[{"text":"answer","citation_ids":["chunk:1"]}]}',
                "reasoning_content": "must not be published",
            }}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 7},
        }
        with (
            real_config("deepseek", deepseek_api_key="test-deepseek-key", llm_model="deepseek-flash"),
            patch("app.services.llm.post_json", return_value=response) as transport,
        ):
            result = generate("question", self.contexts)
        self.assertEqual(transport.call_args.args[0], "https://api.deepseek.com/chat/completions")
        self.assertEqual(transport.call_args.kwargs["headers"], {"Authorization": "Bearer test-deepseek-key"})
        payload = transport.call_args.kwargs["payload"]
        self.assertIn("max_tokens", payload)
        self.assertNotIn("max_completion_tokens", payload)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(result["provider"], "deepseek")
        self.assertEqual(result["answer"], "answer")
        self.assertEqual(result["usage"], {"input_tokens": 12, "output_tokens": 7, "source": "provider"})
        self.assertNotIn("reasoning_content", result)

    def test_deepseek_rejects_incomplete_empty_or_invalid_outputs(self):
        valid = '{"status":"Answered","claims":[{"text":"answer","citation_ids":["chunk:1"]}]}'
        for finish, content in (("length", valid), ("content_filter", valid), ("aborted", valid),
                                ("stop", ""), ("stop", "not json")):
            with (
                self.subTest(finish=finish, content=content),
                real_config("deepseek", deepseek_api_key="test-deepseek-key"),
                patch("app.services.llm.post_json", return_value={
                    "choices": [{"finish_reason": finish, "message": {"content": content}}],
                }),
                self.assertRaises(ProviderError),
            ):
                generate("question", self.contexts)

    def test_failure_or_empty_real_answer_is_not_fixture(self):
        for response in (
            {},
            {"choices": []},
            {"choices": [{"message": {"content": ""}}]},
        ):
            with (
                self.subTest(response=response),
                real_config(),
                patch(
                    "app.services.llm.post_json",
                    return_value=response,
                ),
                self.assertRaises(ProviderError),
            ):
                generate("question", self.contexts)

    def test_missing_usage_is_not_reported_as_zero(self):
        with (
            real_config(),
            patch(
                "app.services.llm.post_json",
                return_value={
                    "choices": [{"message": {"content": '{"status":"Answered","claims":[{"text":"answer","citation_ids":["chunk:1"]}]}'}}],
                },
            ),
        ):
            result = generate("question", self.contexts)
        self.assertIsNone(result["usage"]["input_tokens"])
        self.assertEqual(result["usage"]["source"], "unavailable")

    def test_transport_errors_and_bodies_are_sanitized(self):
        request = httpx.Request("POST", "https://provider.example/secret")
        for response in (
            httpx.Response(
                401,
                json={"error": "api-key=test-secret private-document"},
                request=request,
            ),
            httpx.Response(200, content="invalid secret JSON", request=request),
            httpx.Response(
                302, headers={"Location": "https://other.example"}, request=request
            ),
        ):
            with (
                self.subTest(status=response.status_code),
                configured(),
                patch("app.core.providers.httpx.Client") as factory,
                self.assertRaises(ProviderError) as raised,
            ):
                factory.return_value.__enter__.return_value.post.return_value = response
                post_json(
                    "https://provider.example",
                    headers={"Authorization": "test-secret"},
                    payload={},
                )
            self.assertNotIn("secret", str(raised.exception))
            self.assertFalse(factory.call_args.kwargs["follow_redirects"])
            self.assertFalse(factory.call_args.kwargs["trust_env"])

    def test_timeout_is_sanitized(self):
        with (
            configured(),
            patch("app.core.providers.httpx.Client") as factory,
            self.assertRaises(ProviderError),
        ):
            factory.return_value.__enter__.return_value.post.side_effect = (
                httpx.ReadTimeout("test-secret")
            )
            post_json("https://provider.example", headers={}, payload={})


class RerankerTests(unittest.TestCase):
    candidates = [
        {"id": 1, "chunk_text": "first", "similarity": 0.8},
        {"id": 2, "chunk_text": "second", "similarity": 0.7},
    ]

    def test_none_keeps_dense_order_without_transport(self):
        with configured(), patch("app.services.reranking.post_json") as transport:
            result = rerank("question", list(reversed(self.candidates)))
        transport.assert_not_called()
        self.assertEqual([item["id"] for item in result], [1, 2])
        self.assertIsNone(result[0]["rerank_score"])

    def test_local_tei_and_cohere_contracts(self):
        profiles = (
            ({"reranker_provider": "local", "local_reranker_url": "http://reranker:80"}, "http://reranker:80/rerank", "score"),
            ({"reranker_provider": "cohere", "cohere_api_key": "test"}, "https://api.cohere.com/v2/rerank", "relevance_score"),
        )
        for values, expected_url, score_key in profiles:
            response = [
                {"index": 1, score_key: 0.95},
                {"index": 0, score_key: 0.2},
            ]
            if values["reranker_provider"] == "cohere":
                response = {"results": response}
            with (
                self.subTest(provider=values["reranker_provider"]),
                real_config(**values),
                patch("app.services.reranking.post_json", return_value=response) as transport,
            ):
                result = rerank("question", self.candidates)
                self.assertEqual([item["id"] for item in result], [2, 1])
                self.assertEqual(result[0]["rerank_score"], 0.95)
                self.assertEqual(transport.call_args.args[0], expected_url)
                if values["reranker_provider"] == "local":
                    self.assertIs(transport.call_args.kwargs["response_type"], list)

    def test_invalid_reranker_indices_are_rejected(self):
        with (
            real_config(reranker_provider="cohere", cohere_api_key="test"),
            patch("app.services.reranking.post_json", return_value={
                "results": [
                    {"index": 0, "relevance_score": 1},
                    {"index": 0, "relevance_score": 0.5},
                ]
            }),
            self.assertRaises(ProviderError),
        ):
            rerank("question", self.candidates)
