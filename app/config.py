import os

from dotenv import load_dotenv, set_key, find_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

if not os.path.exists(ENV_PATH):
    open(ENV_PATH, "a").close()

load_dotenv(ENV_PATH)


def get_api_key():
    return os.environ.get("ANTHROPIC_API_KEY", "")


def save_api_key(key):
    key = key.strip()
    set_key(ENV_PATH, "ANTHROPIC_API_KEY", key)
    os.environ["ANTHROPIC_API_KEY"] = key


def get_access_password():
    """社内共有用の合言葉。未設定ならログイン不要（1人利用モード）。"""
    return os.environ.get("ACCESS_PASSWORD", "")


def save_access_password(pw):
    pw = pw.strip()
    set_key(ENV_PATH, "ACCESS_PASSWORD", pw)
    os.environ["ACCESS_PASSWORD"] = pw


def get_secret_key():
    """Flaskセッション用シークレット。無ければ生成して.envに保存する。"""
    key = os.environ.get("FLASK_SECRET_KEY", "")
    if not key:
        import secrets

        key = secrets.token_hex(32)
        set_key(ENV_PATH, "FLASK_SECRET_KEY", key)
        os.environ["FLASK_SECRET_KEY"] = key
    return key


def get_model():
    return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")


def save_model(model_name):
    model_name = model_name.strip()
    set_key(ENV_PATH, "ANTHROPIC_MODEL", model_name)
    os.environ["ANTHROPIC_MODEL"] = model_name


# ---- AIプロバイダー切り替え（anthropic: 高精度・有料 / gemini: 無料枠あり） ----

def get_provider():
    return os.environ.get("AI_PROVIDER", "anthropic")


def save_provider(provider):
    provider = provider.strip().lower()
    if provider not in ("anthropic", "gemini"):
        provider = "anthropic"
    set_key(ENV_PATH, "AI_PROVIDER", provider)
    os.environ["AI_PROVIDER"] = provider


def get_gemini_key():
    return os.environ.get("GEMINI_API_KEY", "")


def save_gemini_key(key):
    key = key.strip()
    set_key(ENV_PATH, "GEMINI_API_KEY", key)
    os.environ["GEMINI_API_KEY"] = key


def get_gemini_model():
    return os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")


def save_gemini_model(model_name):
    model_name = model_name.strip()
    set_key(ENV_PATH, "GEMINI_MODEL", model_name)
    os.environ["GEMINI_MODEL"] = model_name


def active_api_key():
    """現在選択中のプロバイダーのAPIキーを返す。"""
    if get_provider() == "gemini":
        return get_gemini_key()
    return get_api_key()


def active_model():
    if get_provider() == "gemini":
        return get_gemini_model()
    return get_model()
