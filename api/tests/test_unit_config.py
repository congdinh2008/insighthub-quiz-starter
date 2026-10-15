import unittest
from unittest.mock import patch

from support import configured, real_config
from pydantic import ValidationError
from app.core.config import Settings
from app.services.chunking import chunk_text


class ConfigTests(unittest.TestCase):
    def test_minimal_fixture_stays_offline_even_when_key_is_present(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(_env_file=None, gemini_api_key="test-not-real", deepseek_api_key="test-not-real")
        self.assertEqual((settings.rag_mode, settings.llm_provider, settings.embedding_provider),
                         ("fixture", "fixture", "fixture"))
        self.assertEqual(settings.reranker_provider, "none")
        self.assertEqual(settings.rag_profile, "fixture-offline")
        self.assertEqual(settings.retrieval_min_similarity, -1)

    def test_minimal_real_configuration_requires_both_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None, rag_mode="real")
            for key in ("gemini_api_key", "deepseek_api_key"):
                with self.subTest(missing_other_key=key), self.assertRaises(ValidationError):
                    Settings(_env_file=None, rag_mode="real", **{key: "test-not-real"})
            settings = Settings(_env_file=None, rag_mode="real", gemini_api_key="test-not-real", deepseek_api_key="test-not-real")
        self.assertEqual((settings.llm_provider, settings.embedding_provider), ("deepseek", "gemini"))
        self.assertEqual(settings.rag_profile, "classroom-deepseek-gemini")
        self.assertEqual(settings.resolved_chat_model, "deepseek-flash")
        self.assertEqual(settings.resolved_embedding_model, "gemini-embedding-2")
        self.assertEqual(settings.retrieval_min_similarity, 0.20)
        self.assertEqual(settings.reranker_provider, "none")
        self.assertIn("Gemini", settings.ai_data_usage_notice)
        self.assertNotIn("test-not-real", repr(settings))

    def test_empty_compose_passthrough_does_not_override_mode_defaults(self):
        with patch.dict("os.environ", {
            "RAG_MODE": "real", "GEMINI_API_KEY": "test-not-real", "DEEPSEEK_API_KEY": "test-not-real",
            "LLM_PROVIDER": "", "EMBEDDING_PROVIDER": "", "RAG_PROFILE": "",
            "DEEPSEEK_CHAT_MODEL": "", "RETRIEVAL_MIN_SIMILARITY": "",
            "PROVIDER_TIMEOUT_SECONDS": "", "AI_DATA_USAGE_NOTICE": "",
        }, clear=True):
            settings = Settings(_env_file=None)
        self.assertEqual(settings.llm_provider, "deepseek")
        self.assertEqual(settings.retrieval_min_similarity, 0.20)
        self.assertEqual(settings.provider_timeout_seconds, 60)
        self.assertIn("Gemini", settings.ai_data_usage_notice)

    def test_explicit_overrides_preserve_identity_and_validate_conflicts(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(_env_file=None, rag_mode="real", gemini_api_key="test-not-real", deepseek_api_key="test-not-real",
                                retrieval_min_similarity=0.35, llm_model="classroom-override",
                                reranker_provider="cohere", cohere_api_key="test-not-real")
            baseline = Settings(_env_file=None, rag_mode="real", gemini_api_key="test-not-real", deepseek_api_key="test-not-real")
            with self.assertRaises(ValidationError):
                Settings(_env_file=None, rag_mode="fixture", llm_provider="gemini",
                         embedding_provider="gemini", gemini_api_key="test-not-real")
        self.assertEqual(settings.retrieval_min_similarity, 0.35)
        self.assertEqual(settings.resolved_chat_model, "classroom-override")
        self.assertEqual(settings.rag_profile, "classroom-deepseek-gemini-cohere")
        self.assertEqual(settings.embedding_identity_id, baseline.embedding_identity_id)

    def test_explicit_provider_conflicts_are_rejected(self):
        for values in (
            {"rag_mode": "fixture", "llm_provider": "gemini"},
            {"rag_mode": "real"},
            {"rag_mode": "typo"},
            {"llm_provider": "bedrock"},
            {"embedding_provider": "local"},
            {"llm_provider": "unknown"},
            {"embedding_provider": "unknown"},
            {"embedding_model": "fake-model"},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                with configured(**values):
                    pass

    def test_real_requires_credentials_explicit_model_and_endpoint(self):
        for values in (
            {"openai_api_key": ""},
            {"openai_base_url": ""},
            {"openai_base_url": "https://user:secret@host/v1"},
            {"openai_base_url": "https://host/v1?key=secret"},
            {"openai_base_url": "https://host/v1#fragment"},
            {"openai_base_url": "file:///tmp/gateway"},
            {"openai_base_url": "https://host:bad/v1"},
            {"llm_model": ""},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                with real_config(**values):
                    pass

    def test_settings_errors_hide_secrets(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValidationError) as raised:
                Settings(
                    _env_file=None, llm_provider="bad", openai_api_key="super-secret"
                )
        self.assertNotIn("super-secret", str(raised.exception))

    def test_invalid_numeric_configuration(self):
        for key, value in (
            ("chunk_size", 1),
            ("chunk_overlap", 800),
            ("embedding_dim", 0),
            ("embedding_dim", 2001),
            ("retrieval_top_k", 21),
            ("retrieval_candidate_k", 0),
            ("retrieval_min_similarity", 2),
            ("context_max_tokens", 1),
            ("hnsw_ef_search", 0),
            ("provider_timeout_seconds", "nan"),
            ("embedding_batch_size", 0),
            ("max_upload_bytes", -1),
        ):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                with configured(**{key: value}):
                    pass

    def test_reranker_profiles_are_explicit_and_safe(self):
        with real_config(reranker_provider="cohere", cohere_api_key="test") as settings:
            self.assertEqual(settings.resolved_reranker_model, "rerank-v4.0-fast")
        with real_config(reranker_provider="local", local_reranker_url="http://reranker:80") as settings:
            self.assertIn("multilingual", settings.resolved_reranker_model)
        for values in (
            {"reranker_provider": "cohere", "cohere_api_key": ""},
            {"reranker_provider": "local", "local_reranker_url": "https://remote.example"},
            {"reranker_provider": "local", "local_reranker_url": "http://user:secret@localhost"},
            {"retrieval_candidate_k": 4, "retrieval_top_k": 5},
            {"reranker_top_n": 20, "retrieval_candidate_k": 10},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                with real_config(**values):
                    pass

    def test_ollama_uses_dedicated_native_dimension(self):
        with real_config("ollama", embedding_provider="ollama") as settings:
            self.assertEqual(settings.resolved_embedding_model, "mxbai-embed-large")
        for values in (
            {"embedding_model": "deepseek-r1:14b"},
            {"embedding_dim": 768},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                with real_config("ollama", embedding_provider="ollama", **values):
                    pass

    def test_identity_changes_with_vector_space_but_not_chat_model_or_key(self):
        with real_config() as settings:
            baseline = settings.embedding_identity_id
        for values in (
            {"embedding_model": "other"},
            {"embedding_dim": 768},
            {"embedding_revision": "2"},
            {"openai_base_url": "https://other.example/v1"},
        ):
            with real_config(**values) as settings:
                self.assertNotEqual(baseline, settings.embedding_identity_id)
        with real_config(llm_model="other-chat", openai_api_key="rotated") as settings:
            self.assertEqual(baseline, settings.embedding_identity_id)
        with configured() as settings:
            self.assertNotEqual(baseline, settings.embedding_identity_id)

    def test_chunking_progress_overlap_and_empty(self):
        with configured(chunk_size=4, chunk_overlap=2):
            self.assertEqual(chunk_text("a b c d e f g"), ["a b c", "c d e", "e f g"])
            self.assertEqual(chunk_text(" \n "), [])
