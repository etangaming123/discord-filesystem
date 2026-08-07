import json
import os

from cryptography.fernet import Fernet, InvalidToken

DEFAULT_KEY_ENV_VAR = "FS_BOT_TOKEN_ENCRYPTION_KEY"
DEFAULT_KEY_FILE = "bot_token.key"


def generate_key() -> bytes:
    return Fernet.generate_key()


def _resolve_active_key(key_env_var: str, key_file: str):
    env_val = os.environ.get(key_env_var)
    if env_val:
        return env_val.encode(), "env"

    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            key = f.read().strip()
    else:
        key = generate_key()
        with open(key_file, "wb") as f:
            f.write(key)

    return key, "file"


def _try_decrypt(fernet: Fernet, value: str):
    try:
        return fernet.decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return None


def secure_token(
    config_path: str = "config.json",
    token_field: str = "token",
    key_env_var: str = DEFAULT_KEY_ENV_VAR,
    key_file: str = DEFAULT_KEY_FILE,
) -> str:
    with open(config_path) as f:
        cfg = json.load(f)

    raw = cfg[token_field]

    active_key, source = _resolve_active_key(key_env_var, key_file)
    fernet = Fernet(active_key)

    plaintext = _try_decrypt(fernet, raw)
    if plaintext is not None:
        return plaintext

    if source == "env" and os.path.exists(key_file):
        with open(key_file, "rb") as f:
            legacy_key = f.read().strip()
        legacy_fernet = Fernet(legacy_key)
        plaintext = _try_decrypt(legacy_fernet, raw)
        if plaintext is not None:
            cfg[token_field] = fernet.encrypt(plaintext.encode()).decode()
            with open(config_path, "w") as f:
                json.dump(cfg, f, indent=4)
            return plaintext

    plaintext = raw
    cfg[token_field] = fernet.encrypt(plaintext.encode()).decode()
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=4)
    return plaintext
