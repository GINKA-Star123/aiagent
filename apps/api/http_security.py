from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlsplit

class HttpSecurityConfigError(ValueError):
     """
     HTTP 安全配置错误

     该错误应在API启动阶段直接暴露
     避免服务带着危险的CORS或代理配置继续运行
     """

@dataclass(frozen=True)
class CorsPolicy:
     origins: tuple[str, ...]
     allow_credentials: bool
     allow_methods: tuple[str, ...]
     allow_headers: tuple[str, ...]
     expose_headers: tuple[str, ...]

@dataclass(frozen=True)
class TrustedProxyPolicy:
     networks: tuple[
          ipaddress.IPv4Network | ipaddress.IPv6Network,
          ...
     ]

     def trusts(self, address: str | None) -> bool:
        ip = parse_ip_address(address)

        if ip is None:
            return False

        return any(
            ip in network
            for network in self.networks
        )

DEFAULT_CORS_METHODS = (
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
)

DEFAULT_CORS_HEADERS = (
    "Accept",
    "Authorization",
    "Content-Type",
    "X-Request-ID",
    "X-User-ID",
    "X-Cloud-Admin-Token",
)

DEFAULT_EXPOSE_HEADERS = (
    "X-Request-ID",
    "X-Response-Time-As",
    "X-Cloud-Route-Bucket"
)

def split_csv(value: str | None) -> list[str]:
    """
    将逗号分隔配置解析为去重列表,并保持原始顺序
    """

    result: list[str] = []
    seen: set[str] = set()

    for item in (value or "").split(","):
        normalized = item.strip()

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        result.append(normalized)

    return result

def normalize_origin(value: str) -> str:
    """
    规范化单个 CORS Origin。

    合法 Origin 只能包含：

    - scheme
    - hostname
    - 可选 port

    不允许 path、query、fragment、userinfo。
    """

    origin = value.strip()

    if origin == "*":
        return origin

    parsed = urlsplit(origin)

    if parsed.scheme not in {"http", "https"}:
        raise HttpSecurityConfigError(
            f"CORS origin must use http or https: {origin}"
        )

    if not parsed.hostname:
        raise HttpSecurityConfigError(
            f"CORS origin is missing hostname: {origin}"
        )

    if parsed.username or parsed.password:
        raise HttpSecurityConfigError(
            f"CORS origin must not contain userinfo: {origin}"
        )

    if parsed.path not in {"", "/"}:
        raise HttpSecurityConfigError(
            f"CORS origin must not contain a path: {origin}"
        )

    if parsed.query or parsed.fragment:
        raise HttpSecurityConfigError(
            f"CORS origin must not contain query or fragment: {origin}"
        )

    host = parsed.hostname.lower()

    if ":" in host:
        host = f"[{host}]"

    try:
        port = parsed.port
    except ValueError as exc:
        raise HttpSecurityConfigError(
            f"CORS origin contains an invalid port: {origin}"
        ) from exc

    default_port = (
        parsed.scheme == "http" and port == 80
    ) or (
        parsed.scheme == "https" and port == 443
    )

    if port is not None and not default_port:
        return f"{parsed.scheme}://{host}:{port}"

    return f"{parsed.scheme}://{host}"

def build_cors_policy(
    origins_value: str | None,
    *,
    app_env: str,
    cloud_mode: bool,
    allow_credentials: bool,
) -> CorsPolicy:
    """
    构建并校验 CORS 策略。

    production 或 cloud 模式下：

    - Origin 不允许为空。
    - 不允许使用 *。
    - 不允许使用 localhost / loopback。
    """

    production = (
        app_env.strip().lower()
        in {"production", "prod"}
        or cloud_mode
    )

    origins = tuple(
        dict.fromkeys(
            normalize_origin(item)
            for item in split_csv(origins_value)
        )
    )

    if production and not origins:
        raise HttpSecurityConfigError(
            "API_CORS_ORIGINS must be configured in production"
        )

    if "*" in origins and allow_credentials:
        raise HttpSecurityConfigError(
            "wildcard CORS origin cannot be used with credentials"
        )

    if production and "*" in origins:
        raise HttpSecurityConfigError(
            "wildcard CORS origin is forbidden in production"
        )

    if production:
        local_origins = [
            origin
            for origin in origins
            if is_local_origin(origin)
        ]

        if local_origins:
            raise HttpSecurityConfigError(
                "localhost CORS origins are forbidden in production: "
                + ", ".join(local_origins)
            )

    return CorsPolicy(
        origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=DEFAULT_CORS_METHODS,
        allow_headers=DEFAULT_CORS_HEADERS,
        expose_headers=DEFAULT_EXPOSE_HEADERS,
    )


def is_local_origin(origin: str) -> bool:
    if origin == "*":
        return False

    hostname = urlsplit(origin).hostname

    if hostname is None:
        return False

    normalized = hostname.lower()

    if normalized == "localhost":
        return True

    ip = parse_ip_address(normalized)

    return bool(ip and ip.is_loopback)


def build_trusted_proxy_policy(
    value: str | None,
) -> TrustedProxyPolicy:
    """
    解析可信代理地址。

    每一项可以是单个 IP 或 CIDR，例如：

    127.0.0.1
    ::1
    172.18.0.0/16
    """

    networks: list[
        ipaddress.IPv4Network | ipaddress.IPv6Network
    ] = []

    for item in split_csv(value):
        try:
            network = ipaddress.ip_network(
                item,
                strict=False,
            )
        except ValueError as exc:
            raise HttpSecurityConfigError(
                f"invalid trusted proxy address: {item}"
            ) from exc

        networks.append(network)

    return TrustedProxyPolicy(
        networks=tuple(networks)
    )


def resolve_client_ip(
    *,
    peer_address: str | None,
    forwarded_for: str | None,
    trusted_proxies: TrustedProxyPolicy,
) -> str:
    """
    解析真实客户端 IP。

    仅当直接连接方 peer_address 是可信代理时，
    才会读取 X-Forwarded-For。

    解析代理链时从右向左跳过可信代理，
    第一个不可信地址视为真正客户端。
    """

    peer_ip = parse_ip_address(peer_address)

    if peer_ip is None:
        return "unknown"

    peer_text = str(peer_ip)

    if not trusted_proxies.trusts(peer_text):
        return peer_text

    forwarded_addresses = parse_forwarded_for(
        forwarded_for
    )

    if not forwarded_addresses:
        return peer_text

    chain = [
        *forwarded_addresses,
        peer_text,
    ]

    for address in reversed(chain):
        if trusted_proxies.trusts(address):
            continue

        return address

    return forwarded_addresses[0]


def parse_forwarded_for(
    value: str | None,
) -> list[str]:
    """
    解析 X-Forwarded-For，只保留合法 IP。

    一旦出现非法成员，整条 Header 作废，
    防止攻击者构造部分合法、部分畸形的代理链。
    """

    if not value:
        return []

    result: list[str] = []

    for item in value.split(","):
        normalized = item.strip()
        ip = parse_ip_address(normalized)

        if ip is None:
            return []

        result.append(str(ip))

    return result


def parse_ip_address(
    value: str | None,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    if not value:
        return None

    normalized = value.strip()

    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]

    try:
        return ipaddress.ip_address(normalized)
    except ValueError:
        return None


def csv_value(values: Iterable[str]) -> str:
    """
    将配置列表重新序列化，主要用于诊断输出。
    """

    return ",".join(values)
        