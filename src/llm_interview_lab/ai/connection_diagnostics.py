"""Small, allowlisted connection diagnostics; never serialize exception text."""
from __future__ import annotations

import platform
import re
import socket
import ssl
from uuid import uuid4

from .. import __version__


STAGES = {
    "save_key": "保存 API Key", "read_key": "读取 API Key",
    "save_config": "保存连接配置", "read_config": "读取连接配置", "refresh_config": "刷新连接状态",
    "init_client": "初始化网络客户端", "request": "请求 AI 服务",
}


def connection_diagnostic(error: Exception, stage: str = "request") -> dict:
    chain = []
    cause = error
    while cause is not None and all(cause is not item for item in chain):
        chain.append(cause)
        cause = cause.__cause__ or cause.__context__
    names = {type(item).__name__ for item in chain}
    # Used only to classify known messages. These strings NEVER leave this function.
    detail = " ".join(str(item).lower() for item in chain)
    status = next((getattr(getattr(item, "response", None), "status_code", None)
                   or getattr(item, "status_code", None) for item in chain
                   if isinstance(getattr(getattr(item, "response", None), "status_code", None)
                                 or getattr(item, "status_code", None), int)), None)
    if "CredentialError" in names or detail.startswith("system keyring"):
        stage = "save_key" if "read-back" in detail else "read_key" if "read" in detail or "missing" in detail else "save_key"
        code, message = "KEY_STORE", "系统密钥环无法保存或读取 Key。请解锁登录钥匙串，并允许此应用访问后重试。"
        if "missing" in detail:
            code, message = "KEY_MISSING", "系统密钥环中找不到此连接的 Key，请点击“修改模型 / Key”重新保存。"
        elif "read-back" in detail:
            code, message = "KEY_NOT_PERSISTED", "Key 写入后未能读回，尚未保存成功。请检查系统钥匙串是否可用或被拒绝访问。"
    elif status == 401 or "AuthenticationError" in names or "authentication failed" in detail:
        code, message = "AUTH_REJECTED", "服务拒绝了 API Key（401）。请核对所选服务与 Key 是否匹配，或检查 Key 是否已撤销。"
    elif status == 403:
        code, message = "ACCESS_DENIED", "服务拒绝访问（403）。请检查账号权限、地区限制或网络代理；不要反复重新保存同一 Key。"
    elif status == 402:
        code, message = "BALANCE", "服务账户余额不足（402），请到对应服务控制台检查。"
    elif status in {400, 404, 422}:
        code, message = "REQUEST_REJECTED", f"服务拒绝请求（{status}）。请核对服务类型、地址和模型 ID；兼容服务也可能不支持所选参数。"
    elif status == 429:
        code, message = "RATE_LIMIT", "请求被限流（429），请稍后再测试，并检查账号配额。"
    elif status is not None and status >= 500:
        code, message = "UPSTREAM", f"AI 服务端暂时出错（{status}），请稍后重试。"
    elif any(isinstance(item, ssl.SSLError) for item in chain) or "certificate_verify_failed" in detail:
        code, message = "TLS_CERTIFICATE", "HTTPS 证书验证失败。请检查系统时间、代理证书或网络环境；不要关闭证书验证。"
    elif any(isinstance(item, socket.gaierror) for item in chain):
        code, message = "DNS", "无法解析服务地址。请核对地址并检查 DNS 或网络连接。"
    elif any("Timeout" in name for name in names) or "timed out" in detail:
        code, message = "TIMEOUT", "连接测试超时，请检查网络、代理或服务状态后重试；无需重复保存 Key。"
    elif "ProxyError" in names:
        code, message = "PROXY", "代理连接失败，请检查当前代理地址、端口及认证设置。"
    elif names & {"ConnectError", "ConnectionRefusedError", "ConnectionResetError", "ConnectionError"}:
        code, message = "NETWORK", "无法建立或维持网络连接，请检查服务地址、网络与代理。Key 是否有效尚未得到验证。"
    elif names & {"ImportError", "ModuleNotFoundError"}:
        code, message = "DEPENDENCY", "连接组件缺失或未能加载，这是应用安装或打包问题。请复制诊断信息反馈维护者。"
    elif stage == "init_client":
        code, message = "CLIENT_INIT", "网络客户端初始化失败，请检查证书或代理配置，并将诊断信息反馈维护者。请求尚未发送。"
    elif names & {"ConnectionConfigError", "ValueError"}:
        code, message = "CONFIG", "连接配置未通过校验，请检查连接 ID、服务、模型、地址与推理选项。"
    elif any(isinstance(item, OSError) for item in chain) and stage in {"save_config", "read_config", "refresh_config"}:
        code, message = "LOCAL_STORAGE", "本地连接配置无法保存或读取，请检查数据目录权限和剩余磁盘空间。"
    else:
        code, message = "UNEXPECTED", "连接操作发生未识别错误，请复制诊断信息反馈维护者；不要重复提交 Key。"
    exception_type = type(chain[-1]).__name__
    return {"code": "AI_CONN_" + code, "stage": stage,
            "stage_label": STAGES.get(stage, "连接操作"), "message": message,
            "http_status": status, "exception_type": exception_type if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", exception_type) else "Exception",
            "operation_id": uuid4().hex[:12], "app_version": __version__,
            "platform": platform.system(), "architecture": platform.machine()}
