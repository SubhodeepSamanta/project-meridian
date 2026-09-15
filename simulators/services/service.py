from __future__ import annotations

import http.client
import json
import os
import ssl
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


SERVICE_NAME = os.environ["SERVICE_NAME"]
SERVICE_PORT = int(os.environ["SERVICE_PORT"])
PEER_HOST = os.environ["PEER_HOST"]
PEER_PORT = int(os.environ["PEER_PORT"])
CERT_FILE = os.environ["CERT_FILE"]
KEY_FILE = os.environ["KEY_FILE"]
CA_FILE = os.environ["CA_FILE"]


def client_common_name(connection: ssl.SSLSocket) -> str | None:
    certificate = connection.getpeercert()
    for relative_name in certificate.get("subject", ()):
        for attribute, value in relative_name:
            if attribute == "commonName":
                return value
    return None


def call_peer() -> dict[str, Any]:
    context = ssl.create_default_context(cafile=CA_FILE)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    connection = http.client.HTTPSConnection(
        PEER_HOST,
        PEER_PORT,
        context=context,
        timeout=5,
    )
    try:
        connection.request("GET", "/health")
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        return {"status_code": response.status, "body": body}
    finally:
        connection.close()


class ServiceHandler(BaseHTTPRequestHandler):
    def send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded_payload = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded_payload)))
        self.end_headers()
        self.wfile.write(encoded_payload)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(
                HTTPStatus.OK,
                {
                    "service": SERVICE_NAME,
                    "status": "healthy",
                    "client_identity": client_common_name(self.connection),
                },
            )
            return

        if self.path == "/call-peer":
            try:
                result = call_peer()
            except Exception as error:
                self.send_json(
                    HTTPStatus.BAD_GATEWAY,
                    {
                        "service": SERVICE_NAME,
                        "status": "peer_call_failed",
                        "error": str(error),
                    },
                )
                return

            self.send_json(
                HTTPStatus.OK,
                {"service": SERVICE_NAME, "status": "peer_call_succeeded", "peer": result},
            )
            return

        self.send_json(HTTPStatus.NOT_FOUND, {"error": "route_not_found"})

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"{SERVICE_NAME}: {format_string % args}", flush=True)


def create_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", SERVICE_PORT), ServiceHandler)
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    context.load_verify_locations(cafile=CA_FILE)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


if __name__ == "__main__":
    with create_server() as server:
        print(f"{SERVICE_NAME}: listening on https://0.0.0.0:{SERVICE_PORT}", flush=True)
        server.serve_forever()
