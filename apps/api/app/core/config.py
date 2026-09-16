from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("MERIDIAN_DATABASE_URL", "sqlite:///./meridian.db")
    step_ca_url: str = os.getenv("MERIDIAN_STEP_CA_URL", "https://localhost:9000")
    step_ca_root: str = os.getenv("MERIDIAN_STEP_CA_ROOT", "./root_ca.crt")
    step_ca_password_file: str = os.getenv(
        "MERIDIAN_STEP_CA_PASSWORD_FILE", "./step_ca_password"
    )
    certificate_directory: str = os.getenv(
        "MERIDIAN_CERTIFICATE_DIRECTORY", "./certificates"
    )
    hsm_ca_url: str = os.getenv("MERIDIAN_HSM_CA_URL", "")
    hsm_ca_root: str = os.getenv("MERIDIAN_HSM_CA_ROOT", "")


settings = Settings()
