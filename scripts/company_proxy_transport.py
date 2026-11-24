"""Configured provider health checks and bounded transports for public job pages."""
import json
import os
import re
import threading
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests


def secret_configuration():
    values = dict(os.environ)
    path = values.get("COMPANY_PROXY_CONFIG_PATH")
    if path:
        values.update(json.loads(Path(path).read_text(encoding="utf-8")))
    return values


def parse_values(value):
    if isinstance(value, list):
        return value
    try:
        decoded = json.loads(value or "[]")
        if isinstance(decoded, list):
            return decoded
        if isinstance(decoded, dict):
            for name in ("proxies", "results", "keys", "data"):
                if isinstance(decoded.get(name), list):
                    return decoded[name]
            return list(decoded.values())
    except (ValueError, TypeError):
        pass
    return [item.strip() for item in re.split(r"[,\n]+", value or "") if item.strip()]


def proxy_address(value):
    if isinstance(value, dict):
        host = value.get("proxy_address") or value.get("host")
        port = value.get("port")
        user = value.get("username", "")
        password = value.get("password", "")
        return f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}" if host and port else ""
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"
    return "http://" + value


class ProxyPool:
    def __init__(self, health=None):
        self.configuration = secret_configuration()
        self.keys = []
        for variable in ("SCRAPERAPI_KEY", "SCRAPERAPI_KEY_2", "SCRAPERAPI_KEYS_LIST", "SCRAPERAPI_KEYS"):
            for value in parse_values(self.configuration.get(variable, "")):
                if value and value not in self.keys:
                    self.keys.append(value)
        self.proxies = []
        user = self.configuration.get("OXYLABS_USERNAME")
        password = self.configuration.get("OXYLABS_PASSWORD")
        if user and password:
            host = self.configuration.get("OXYLABS_ENTRYPOINT") or "dc.oxylabs.io"
            for port in (8000, 8001):
                self.proxies.append((f"oxylabs-{port}", f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"))
        for index, value in enumerate(parse_values(self.configuration.get("WEBSHARE_PROXIES", ""))[:3]):
            address = proxy_address(value)
            if address:
                self.proxies.append((f"webshare-{index + 1}", address))
        self.health = health or {}
        self.services = []
        for variable, provider in (("HASDATA_API_KEYS", "hasdata"), ("SCRAPINGANT_API_KEYS", "scrapingant")):
            for index, key in enumerate(parse_values(self.configuration.get(variable, ""))):
                self.services.append((f"{provider}-{index + 1}", provider, key))
        self.lock = threading.Lock()
        self.requests_used = 0

    def check(self):
        result = {}
        for index, key in enumerate(self.keys):
            label = f"scraperapi-{index + 1}"
            try:
                response = requests.get("https://api.scraperapi.com/account", params={"api_key": key}, timeout=(8, 15))
                info = {"http_status": response.status_code, "available": False}
                if response.status_code == 200:
                    data = response.json()
                    used = data.get("requestCount", 0)
                    limit = data.get("requestLimit", 0)
                    info.update(remaining=max(0, limit - used), available=limit > used)
                    info["reason"] = "credits_available" if info["available"] else "quota_exhausted"
                else:
                    info["reason"] = "account_request_rejected"
                result[label] = info
            except (requests.RequestException, ValueError) as error:
                result[label] = {"available": False, "reason": type(error).__name__}
        for label, address in self.proxies:
            try:
                response = requests.get("https://ip.oxylabs.io/location", proxies={"http": address, "https": address}, timeout=(5, 12))
                result[label] = {"available": response.status_code == 200, "http_status": response.status_code}
            except requests.RequestException as error:
                info = {"available": False, "reason": type(error).__name__}
                match = re.search(r"Tunnel connection failed:\s*(\d{3})", str(error))
                if match:
                    info["proxy_http_status"] = int(match.group(1))
                result[label] = info
        for label, provider, key in self.services:
            try:
                response = self.service_request(provider, key, "https://example.com", render=False)
                result[label] = {"available": response.status_code == 200, "http_status": response.status_code}
            except requests.RequestException as error:
                result[label] = {"available": False, "reason": type(error).__name__}
        self.health = result
        return result

    def browser_proxy(self):
        for label, address in self.proxies:
            if self.health.get(label, {}).get("available"):
                parsed = urlsplit(address)
                from urllib.parse import unquote
                return label, {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}", "username": unquote(parsed.username or ""), "password": unquote(parsed.password or "")}
        return None, None

    def service_request(self, provider, key, url, render):
        if provider == "scrapingant":
            return requests.get("https://api.scrapingant.com/v2/general", params={"url": url, "browser": str(render).lower()}, headers={"x-api-key": key}, timeout=(10, 75))
        response = requests.post("https://api.hasdata.com/scrape/web", headers={"x-api-key": key}, json={"url": url, "jsRendering": render}, timeout=(10, 75))
        if response.status_code == 200:
            try:
                data = response.json()
                content = data.get("content") or data.get("data", {}).get("content")
                if isinstance(content, str):
                    response._content = content.encode("utf-8")
                    response.encoding = "utf-8"
                    response.headers["Content-Type"] = "text/html"
            except (ValueError, AttributeError):
                pass
        return response

    def fetch(self, url, render=False, excluded=None):
        excluded = excluded or set()
        with self.lock:
            budget = int(os.environ.get("COMPANY_PROXY_MAX_REQUESTS", "100"))
            if self.requests_used >= budget:
                return None, {"method": "proxy", "outcome": "run_request_budget_spent"}
            self.requests_used += 1
        if not render:
            for label, address in self.proxies:
                if label in excluded or not self.health.get(label, {}).get("available"):
                    continue
                try:
                    response = requests.get(url, proxies={"http": address, "https": address}, headers={"User-Agent": "Mozilla/5.0"}, timeout=(8, 30))
                    return response, {"method": label, "http_status": response.status_code}
                except requests.RequestException as error:
                    return None, {"method": label, "outcome": type(error).__name__}
        for index, key in enumerate(self.keys):
            label = f"scraperapi-{index + 1}"
            info = self.health.get(label, {})
            if label in excluded or not info.get("available"):
                continue
            params = {"api_key": key, "url": url, "max_cost": 10 if render else 1}
            if render:
                params["render"] = "true"
            try:
                response = requests.get("https://api.scraperapi.com/", params=params, timeout=(10, 75))
                if response.status_code in (401, 403):
                    info["available"] = False
                return response, {"method": label + ("-render" if render else "-http"), "http_status": response.status_code}
            except requests.RequestException as error:
                return None, {"method": label, "outcome": type(error).__name__}
        for label, provider, key in self.services:
            if label in excluded or not self.health.get(label, {}).get("available"):
                continue
            try:
                response = self.service_request(provider, key, url, render)
                return response, {"method": label + ("-render" if render else "-http"), "http_status": response.status_code}
            except requests.RequestException as error:
                return None, {"method": label, "outcome": type(error).__name__}
        return None, {"method": "proxy-render" if render else "proxy-http", "outcome": "no_healthy_configured_provider"}

    def attempts(self, url, render=False):
        excluded = set()
        services_tried = set()
        while True:
            response, entry = self.fetch(url, render=render, excluded=excluded)
            yield response, entry
            if entry.get("outcome") in ("no_healthy_configured_provider", "run_request_budget_spent"):
                break
            provider = entry["method"].removesuffix("-render").removesuffix("-http")
            if provider in excluded:
                break
            excluded.add(provider)
            family = provider.split("-")[0]
            if family in ("hasdata", "scrapingant"):
                services_tried.add(family)
                excluded.update(label for label, service, _ in self.services if service == family)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = ProxyPool().check()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    for name, value in result.items():
        print(name, json.dumps(value), flush=True)
