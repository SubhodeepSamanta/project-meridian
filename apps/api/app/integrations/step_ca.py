from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes


class StepCaError(RuntimeError):
    pass


@dataclass(frozen=True)
class IssuedCertificate:
    certificate_path: str
    key_path: str
    serial_number: str
    subject: str
    issuer: str
    not_before: datetime
    not_after: datetime
    key_algorithm: str
    fingerprint: str


def _safe_name(value: str) -> str:
    safe_value = re.sub(r"[^a-zA-Z0-9._-]", "-", value).strip("-")
    return safe_value or "identity"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serial_for_revoke(serial_number: str) -> str:
    """Accept legacy hex inventory values while using step's decimal CLI form."""
    if re.search(r"[a-fA-F]", serial_number):
        return str(int(serial_number, 16))
    return serial_number


class StepCaClient:
    def __init__(
        self,
        ca_url: str,
        root_path: str,
        password_file: str,
        certificate_directory: str,
        runner=subprocess.run,
    ) -> None:
        self.ca_url = ca_url
        self.root_path = root_path
        self.password_file = password_file
        self.certificate_directory = Path(certificate_directory)
        self.runner = runner

    def _run(self, command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise StepCaError("certificate authority command was unavailable") from error

    def health(self) -> bool:
        try:
            result = self.runner(
                [
                    "step",
                    "ca",
                    "health",
                    "--ca-url",
                    self.ca_url,
                    "--root",
                    self.root_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0 and (result.stdout or "").strip() == "ok"

    def issue_certificate(
        self,
        subject: str,
        sans: Sequence[str],
        validity: str = "24h",
    ) -> IssuedCertificate:
        try:
            self.certificate_directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise StepCaError("certificate output directory is unavailable") from error
        certificate_path = self.certificate_directory / f"{_safe_name(subject)}-{uuid4()}.crt"
        key_path = self.certificate_directory / f"{_safe_name(subject)}-{uuid4()}.key"
        command = [
            "step",
            "ca",
            "certificate",
            subject,
            str(certificate_path),
            str(key_path),
            "--ca-url",
            self.ca_url,
            "--root",
            self.root_path,
            "--provisioner",
            "meridian-admin",
            "--provisioner-password-file",
            self.password_file,
            "--not-after",
            validity,
            "--force",
        ]
        for san in sans:
            command.extend(["--san", san])

        result = self._run(command, timeout=30)
        if result.returncode != 0:
            raise StepCaError("certificate issuance failed: " + (result.stderr or "")[-500:])

        try:
            certificate = x509.load_pem_x509_certificate(certificate_path.read_bytes())
        except Exception as error:
            raise StepCaError("issued certificate could not be parsed") from error

        return IssuedCertificate(
            certificate_path=str(certificate_path),
            key_path=str(key_path),
            serial_number=str(certificate.serial_number),
            subject=certificate.subject.rfc4514_string(),
            issuer=certificate.issuer.rfc4514_string(),
            not_before=_as_utc(certificate.not_valid_before_utc),
            not_after=_as_utc(certificate.not_valid_after_utc),
            key_algorithm=certificate.public_key().__class__.__name__,
            fingerprint=certificate.fingerprint(hashes.SHA256()).hex(),
        )

    def revoke_certificate(self, serial_number: str) -> None:
        cli_serial = _serial_for_revoke(serial_number)
        token_result = self._run(
            [
                "step",
                "ca",
                "token",
                cli_serial,
                "--revoke",
                "--ca-url",
                self.ca_url,
                "--root",
                self.root_path,
                "--provisioner",
                "meridian-admin",
                "--provisioner-password-file",
                self.password_file,
            ],
            timeout=30,
        )
        if token_result.returncode != 0:
            raise StepCaError(
                "certificate revocation authorization failed: "
                + (token_result.stderr or "")[-500:]
            )

        token_matches = re.findall(
            r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
            token_result.stdout or "",
        )
        if not token_matches:
            raise StepCaError("certificate revocation authorization returned no token")

        result = self._run(
            [
                "step",
                "ca",
                "revoke",
                cli_serial,
                "--token",
                token_matches[-1],
                "--ca-url",
                self.ca_url,
                "--root",
                self.root_path,
            ],
            timeout=30,
        )
        if result.returncode != 0:
            raise StepCaError("certificate revocation failed: " + (result.stderr or "")[-500:])
