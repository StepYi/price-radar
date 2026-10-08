"""极简 HTTP 客户端（标准库）：重试、退避、限速、429/额度识别。"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "PriceRadar/1.0 (daily price-research digest)"

_last_call = [0.0]


class HttpError(RuntimeError):
    """普通请求失败。"""


class RateLimited(HttpError):
    """被限流，但可以稍后重试。"""


class BudgetExhausted(HttpError):
    """配额/额度彻底用尽（如 OpenAlex 匿名每日预算），本次运行内不要再调用。"""


def build_url(base: str, params: dict | None = None) -> str:
    if not params:
        return base
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    return base + "?" + urllib.parse.urlencode(clean, doseq=True)


def _request(
    url: str,
    *,
    method: str = "GET",
    payload: dict | list | None = None,
    headers: dict | None = None,
    timeout: int = 45,
):
    data = None
    head = {"User-Agent": USER_AGENT, "Accept": "application/json",
            "Accept-Encoding": "identity"}
    if headers:
        head.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        head["Content-Type"] = "application/json"
    return urllib.request.Request(url, data=data, headers=head, method=method)


def _call(
    url: str,
    *,
    method: str,
    payload: dict | list | None,
    headers: dict | None,
    timeout: int,
    interval: float,
    retries: int,
    tolerant_429: bool,
) -> dict | list:
    delay = 2.0
    last_err: Exception | None = None

    for attempt in range(retries + 1):
        wait = interval - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        req = _request(
            url, method=method, payload=payload, headers=headers, timeout=timeout
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                _last_call[0] = time.time()
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            _last_call[0] = time.time()
            last_err = exc
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass

            if exc.code in (400, 401, 403, 404, 422):
                raise HttpError(f"HTTP {exc.code} :: {url} :: {body[:200]}") from exc

            if exc.code == 429:
                low = body.lower()
                if "budget" in low or "insufficient" in low or "api key" in low:
                    raise BudgetExhausted(
                        "免费额度已用尽（建议配置自己的 API Key）：" + body[:200]
                    ) from exc
                # 尊重服务端给出的 Retry-After，但最多等 30 秒
                retry_after = 0.0
                try:
                    retry_after = float(exc.headers.get("Retry-After") or 0)
                except Exception:
                    retry_after = 0.0
                if retry_after > 30:
                    if tolerant_429:
                        raise RateLimited(f"限流（Retry-After={retry_after:.0f}s）") from exc
                    raise HttpError(
                        f"限流且等待时间过长（Retry-After={retry_after:.0f}s）"
                    ) from exc
                delay = max(delay, retry_after, 3.0)
            if attempt >= retries:
                break
        except Exception as exc:
            _last_call[0] = time.time()
            last_err = exc
            if attempt >= retries:
                break

        time.sleep(delay)
        delay = min(delay * 2, 30.0)

    raise HttpError(f"请求失败：{url} :: {last_err}")


def get_json(
    base: str,
    params: dict | None = None,
    *,
    mailto: str = "",
    timeout: int = 45,
    interval: float = 0.2,
    retries: int = 4,
    headers: dict | None = None,
    tolerant_429: bool = False,
) -> dict | list:
    params = dict(params or {})
    if mailto:
        params.setdefault("mailto", mailto)
    return _call(
        build_url(base, params),
        method="GET",
        payload=None,
        headers=headers,
        timeout=timeout,
        interval=interval,
        retries=retries,
        tolerant_429=tolerant_429,
    )


def post_json(
    url: str,
    payload: dict | list,
    *,
    timeout: int = 90,
    interval: float = 0.0,
    retries: int = 5,
    headers: dict | None = None,
    tolerant_429: bool = True,
) -> dict | list:
    return _call(
        url,
        method="POST",
        payload=payload,
        headers=headers,
        timeout=timeout,
        interval=interval,
        retries=retries,
        tolerant_429=tolerant_429,
    )
