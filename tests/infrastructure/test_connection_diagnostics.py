import asyncio
import json
import socket
import ssl

import httpx
import pytest

from llm_interview_lab.ai.connection_diagnostics import connection_diagnostic
from llm_interview_lab.ai.credentials import CredentialError, KeyringCredentialStore
from llm_interview_lab.ai.providers import OpenAICompatibleChatProvider, ProviderConfig
from llm_interview_lab.desktop.i18n import friendly_error


@pytest.mark.parametrize("status,code", [(401, "AUTH_REJECTED"), (402, "BALANCE"),
    (403, "ACCESS_DENIED"), (404, "REQUEST_REJECTED"), (429, "RATE_LIMIT"), (503, "UPSTREAM")])
def test_http_diagnostics_do_not_echo_response_or_key(status, code):
    request = httpx.Request("POST", "https://private.example/private?key=secret-value",
                           headers={"Authorization": "Bearer secret-value"})
    error = httpx.HTTPStatusError("secret-value private resume", request=request,
                                 response=httpx.Response(status, request=request))
    data = connection_diagnostic(error)
    assert data["code"] == "AI_CONN_" + code and data["http_status"] == status
    assert all(token not in json.dumps(data) for token in ("secret-value", "private", "Authorization"))


@pytest.mark.parametrize("error,code", [(ssl.SSLCertVerificationError("private"), "TLS_CERTIFICATE"),
    (socket.gaierror("private"), "DNS"), (httpx.ConnectTimeout("private"), "TIMEOUT"),
    (httpx.ProxyError("private"), "PROXY"), (httpx.ConnectError("private"), "NETWORK"),
    (ModuleNotFoundError("private"), "DEPENDENCY")])
def test_network_causes_survive_wrapper(error, code):
    wrapper = RuntimeError("outer private")
    wrapper.__cause__ = error
    data = connection_diagnostic(wrapper)
    assert data["code"] == "AI_CONN_" + code
    assert "private" not in json.dumps(data)


def test_client_initialization_failure_is_a_connection_result():
    def factory(**kwargs):
        raise FileNotFoundError("private CA path")
    provider = OpenAICompatibleChatProvider(ProviderConfig("test", "deepseek", "test", "test"),
                                           api_key="synthetic", client_factory=factory)
    result = asyncio.run(provider.test_connection())
    assert not result.ok and result.diagnostic["stage"] == "init_client"
    assert result.diagnostic["code"] == "AI_CONN_CLIENT_INIT"


def test_null_keyring_cannot_report_key_as_saved():
    class NullStore:
        def set_password(self, *args): pass
        def get_password(self, *args): return None
    with pytest.raises(CredentialError) as caught:
        KeyringCredentialStore(NullStore()).save("synthetic", "test", "secret-value")
    data = connection_diagnostic(caught.value, "save_config")
    assert data["code"] == "AI_CONN_KEY_NOT_PERSISTED"
    assert "secret-value" not in json.dumps(data)


def test_legacy_auth_message_is_actionable():
    assert "401" in friendly_error("authentication failed; check the stored API key")
