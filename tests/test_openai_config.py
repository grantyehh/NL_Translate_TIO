import os
import unittest
from unittest.mock import Mock, patch

import openai_config


class TestOpenAIConfig(unittest.TestCase):
    def setUp(self) -> None:
        self._env = os.environ.copy()
        for key in (
            "OPENAI_PROVIDER",
            "OPENAI_API_KEY",
            "GRAPHRAG_API_KEY",
            "OPENAI_CHAT_MODEL",
            "OPENAI_EMBEDDING_MODEL",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT",
            "AZURE_OPENAI_EMBEDDING_ENDPOINT",
            "AZURE_OPENAI_EMBEDDING_API_KEY",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
            "AZURE_OPENAI_TOKEN_SCOPE",
            "DOTENV_OVERRIDE_CHECK",
        ):
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)

    def test_default_provider_uses_openai_key_and_default_models(self) -> None:
        os.environ["OPENAI_API_KEY"] = "test-key"
        mock_client = Mock()

        with patch.object(openai_config, "OpenAI", return_value=mock_client) as openai_cls:
            client = openai_config.create_client()

        self.assertIs(client, mock_client)
        openai_cls.assert_called_once_with(api_key="test-key")
        self.assertEqual(openai_config.chat_model(), "gpt-5.4")
        self.assertEqual(openai_config.embedding_model(), "text-embedding-3-small")

    def test_azure_provider_uses_endpoint_token_provider_and_deployment_names(self) -> None:
        os.environ["OPENAI_PROVIDER"] = "azure"
        os.environ["AZURE_OPENAI_ENDPOINT"] = "https://cht-tio.services.ai.azure.com/openai/v1"
        os.environ["AZURE_OPENAI_DEPLOYMENT"] = "gpt-5.4-nano"
        os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"] = "text-embedding-3-small"
        token_provider = Mock(name="token_provider")
        mock_client = Mock()

        with patch.object(openai_config, "OpenAI", return_value=mock_client) as openai_cls, patch.object(
            openai_config,
            "_azure_token_provider",
            return_value=token_provider,
        ) as provider_fn:
            client = openai_config.create_client()

        self.assertIs(client, mock_client)
        provider_fn.assert_called_once_with()
        openai_cls.assert_called_once_with(
            base_url="https://cht-tio.services.ai.azure.com/openai/v1",
            api_key=token_provider,
        )
        self.assertEqual(openai_config.chat_model(), "gpt-5.4-nano")
        self.assertEqual(openai_config.embedding_model(), "text-embedding-3-small")

    def test_azure_provider_can_use_api_key_instead_of_entra_token(self) -> None:
        os.environ["OPENAI_PROVIDER"] = "azure"
        os.environ["AZURE_OPENAI_ENDPOINT"] = "https://cht-tio.services.ai.azure.com/openai/v1"
        os.environ["AZURE_OPENAI_API_KEY"] = "azure-key"
        mock_client = Mock()

        with patch.object(openai_config, "OpenAI", return_value=mock_client) as openai_cls:
            client = openai_config.create_client()

        self.assertIs(client, mock_client)
        openai_cls.assert_called_once_with(
            base_url="https://cht-tio.services.ai.azure.com/openai/v1",
            api_key="azure-key",
        )

    def test_azure_embedding_client_prefers_embedding_key_and_endpoint(self) -> None:
        os.environ["OPENAI_PROVIDER"] = "azure"
        os.environ["AZURE_OPENAI_ENDPOINT"] = "https://chat.example/openai/v1"
        os.environ["AZURE_OPENAI_API_KEY"] = "chat-key"
        os.environ["AZURE_OPENAI_EMBEDDING_ENDPOINT"] = "https://embedding.example/openai/v1"
        os.environ["AZURE_OPENAI_EMBEDDING_API_KEY"] = "embedding-key"
        mock_client = Mock()

        with patch.object(openai_config, "OpenAI", return_value=mock_client) as openai_cls:
            client = openai_config.create_embedding_client()

        self.assertIs(client, mock_client)
        openai_cls.assert_called_once_with(
            base_url="https://embedding.example/openai/v1",
            api_key="embedding-key",
        )

    def test_load_project_env_overrides_existing_shell_env(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("DOTENV_OVERRIDE_CHECK=from_file\n", encoding="utf-8")
            os.environ["DOTENV_OVERRIDE_CHECK"] = "from_shell"

            openai_config.load_project_env(env_path)

        self.assertEqual(os.environ["DOTENV_OVERRIDE_CHECK"], "from_file")


if __name__ == "__main__":
    unittest.main()
