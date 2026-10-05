"""Public HTTP(S) only, pinned addresses on every hop, honoring configured proxies.

Run as a bounded child so DNS resolution also has an outer deadline. A proxy is
asked to CONNECT to the already-vetted literal IP; it never re-resolves the target.
No cookies, user credentials, browser state, subresources or JavaScript.
"""
import base64
import http.client
import ipaddress
import json
import socket
import ssl
import sys
import time
from urllib.parse import urlsplit, urlunsplit, urljoin, quote
from urllib.request import getproxies, proxy_bypass

MAX_BYTES = 1024 * 1024


def target(url):
    if not isinstance(url, str) or not 1 <= len(url) <= 2000 or any(ord(c) < 33 for c in url) or '\\' in url:
        raise ValueError('URL은 공백 없는 2000자 이하의 http/https 주소여야 합니다.')
    part = urlsplit(url)
    if part.scheme not in ('http', 'https') or not part.hostname or part.username is not None or part.password is not None:
        raise ValueError('인증 정보 없는 공개 http/https 주소만 받습니다.')
    port = part.port or (443 if part.scheme == 'https' else 80)
    if port != (443 if part.scheme == 'https' else 80):
        raise ValueError('기본 HTTP/HTTPS 포트만 받습니다.')
    host = part.hostname.encode('idna').decode('ascii')
    records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(r[4][0] for r in records))
    if not addresses or any(not ipaddress.ip_address(a).is_global or ipaddress.ip_address(a).is_multicast or '%' in a or
                            getattr(ipaddress.ip_address(a), 'ipv4_mapped', None) is not None for a in addresses):
        raise ValueError('내부·로컬·예약 주소는 자료 URL로 가져오지 않습니다.')
    authority = '[' + host + ']' if ':' in host else host
    path = quote(part.path or '/', safe='/%:@!$&\'()*+,;=-._~')
    query = quote(part.query, safe='/%?:@!$&\'()*+,;=-._~')
    normalized = urlunsplit((part.scheme, authority, path, query, ''))
    if len(normalized) > 2000:
        raise ValueError('인코딩한 URL이 2000자를 넘습니다.')
    return normalized, host, port, addresses[0], path + ('?' + query if query else '')


def connection(scheme, host, port, address, timeout):
    proxies = getproxies()
    proxy = proxies.get(scheme) or proxies.get('all')
    if proxy and not proxy_bypass(host):
        parsed = urlsplit(proxy)
        if parsed.scheme != 'http' or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError('현재 프록시 방식은 지원하지 않습니다. 프록시를 우회하지 않았습니다.')
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=timeout)
        conn.set_tunnel(address, port)
    else:
        conn = http.client.HTTPConnection(address, port, timeout=timeout)
    try:
        conn.connect()
        if scheme == 'https':
            conn.sock = ssl.create_default_context().wrap_socket(conn.sock, server_hostname=host)
        return conn
    except Exception:
        conn.close()
        raise


def fetch(url):
    deadline, chain = time.monotonic() + 6, []
    for hop in range(4):
        normalized, host, port, address, path = target(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('URL 가져오기 제한 시간을 넘겼습니다.')
        conn = connection(urlsplit(normalized).scheme, host, port, address, remaining)
        try:
            conn.request('GET', path, headers={'Host': '[' + host + ']' if ':' in host else host,
                'User-Agent': 'Decision-AI-source-reader/1', 'Accept': 'text/html,text/plain,application/json',
                'Accept-Encoding': 'identity', 'Connection': 'close'})
            response = conn.getresponse()
            chain.append(normalized)
            if response.status in (301, 302, 303, 307, 308):
                destination = response.getheader('Location')
                if not destination or hop == 3:
                    raise ValueError('URL 재지정이 비었거나 상한을 넘겼습니다.')
                url = urljoin(normalized, destination)
                continue
            if response.status != 200:
                raise ValueError(f'자료 서버가 HTTP {response.status}를 반환했습니다.')
            if response.getheader('Content-Encoding', 'identity').lower() not in ('', 'identity'):
                raise ValueError('압축 응답은 지원하지 않습니다. 원문 텍스트 파일을 사용하세요.')
            length = response.getheader('Content-Length')
            if length is not None and (not length.isdecimal() or int(length) > MAX_BYTES):
                raise ValueError('응답이 1 MiB를 넘거나 길이 정보가 잘못됐습니다.')
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError('URL 가져오기 제한 시간을 넘겼습니다.')
                # The worker deadline also covers servers that drip a single byte.
                data = response.read(min(65536, MAX_BYTES + 1 - size))
                if not data:
                    break
                chunks.append(data); size += len(data)
                if size > MAX_BYTES:
                    raise ValueError('응답이 1 MiB를 넘었습니다.')
            raw = b''.join(chunks)
            if length is not None and len(raw) != int(length):
                raise ValueError('응답 본문이 끝까지 도착하지 않았습니다.')
            return {'body': base64.b64encode(raw).decode('ascii'), 'url': normalized, 'redirect_chain': chain,
                    'content_type': response.getheader('Content-Type', '')}
        finally:
            conn.close()
    raise ValueError('URL 재지정 상한을 넘겼습니다.')


if __name__ == '__main__':
    try:
        request = json.loads(sys.stdin.read(12000))
        print(json.dumps(fetch(request['url']), ensure_ascii=True))
    except Exception as exc:
        # Do not return credentials, proxy addresses or raw socket traces.
        print(json.dumps({'error': str(exc) if isinstance(exc, ValueError) else 'URL을 가져오지 못했습니다. 주소·연결·프록시 정책을 확인하세요.'}))
        sys.exit(1)
