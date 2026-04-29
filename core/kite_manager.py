"""
core/kite_manager.py
Handles Kite authentication and API wrapper.
"""

import os
from dotenv import load_dotenv, set_key
from kiteconnect import KiteConnect

load_dotenv()

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")


def get_kite() -> KiteConnect | None:
    """Returns an authenticated KiteConnect instance, or None if not logged in."""
    api_key = os.getenv("KITE_API_KEY", "").strip()
    access_token = os.getenv("KITE_ACCESS_TOKEN", "").strip()

    if not api_key or not access_token:
        return None

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    return kite


def generate_login_url() -> str:
    api_key = os.getenv("KITE_API_KEY", "").strip()
    if not api_key:
        return ""
    kite = KiteConnect(api_key=api_key)
    return kite.login_url()


def complete_login(request_token: str) -> dict:
    """Exchange request_token for access_token. Saves to .env."""
    api_key = os.getenv("KITE_API_KEY", "").strip()
    api_secret = os.getenv("KITE_API_SECRET", "").strip()

    kite = KiteConnect(api_key=api_key)
    data = kite.generate_session(request_token, api_secret=api_secret)
    access_token = data["access_token"]

    # Persist to .env
    set_key(ENV_PATH, "KITE_ACCESS_TOKEN", access_token)
    os.environ["KITE_ACCESS_TOKEN"] = access_token

    kite.set_access_token(access_token)
    return data


def get_profile(kite: KiteConnect) -> dict:
    try:
        return kite.profile()
    except Exception as e:
        return {"error": str(e)}
