#!/usr/bin/env python3
"""gacha.html 자동 새로고침 서버 — 파일 저장 시 브라우저가 알아서 리로드.

기존 방식과 동일 사용법 (기존 문서·습관 그대로 유지):
    cd _tools && python3 -m http.server 8741
    → python3 gacha_server.py [포트]   (기본 8741)

동작 원리: 정적 파일 서빙 + /__gacha_hash 엔드포인트.
gacha.html에 삽입된 스니펫이 1초마다 /__gacha_hash를 폴링하고,
해시가 바뀌면 (사용자 입력 중이 아닌 한) location.reload().
file:// 로 직접 열면 스니펫이 서버를 못 찾아 조용히 스킵 — 기존 방식도 계속 됨.
"""
import hashlib
import http.server
import os
import sys
from functools import partial

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8741
ROOT = os.path.dirname(os.path.abspath(__file__))


class GachaHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        if self.path.split('?')[0].rstrip('/') == '/__gacha_hash':
            target = os.path.join(ROOT, 'gacha.html')
            try:
                with open(target, 'rb') as f:
                    digest = hashlib.sha256(f.read()).hexdigest()[:16]
                self._json(200, f'{{"hash":"{digest}"}}')
            except OSError as ex:
                self._json(500, f'{{"error":"{ex}"}}')
            return
        super().do_GET()

    def _json(self, code, body):
        data = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write('[gacha_server] %s\n' % (fmt % args))


if __name__ == '__main__':
    with http.server.ThreadingHTTPServer(('127.0.0.1', PORT), GachaHandler) as httpd:
        print(f'[gacha_server] http://localhost:{PORT}/gacha.html  (파일 저장 → 자동 리로드)')
        print(f'[gacha_server] 중지: Ctrl+C')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n[gacha_server] 종료')
