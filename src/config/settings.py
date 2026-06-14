import os
from dotenv import load_dotenv

load_dotenv()

FAST_MODEL = "openrouter/google/gemini-2.5-flash"
DEEP_MODEL = "openrouter/google/gemini-2.5-flash"
BACKUP_MODEL = "openrouter/google/gemini-2.5-flash"

def _params(model: str, timeout: float = 30.0) -> dict:
    return {
        "model": model,
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "api_base": "https://openrouter.ai/api/v1",
        "timeout": timeout,
    }

def get_router(primary: str = FAST_MODEL, backup: str = BACKUP_MODEL):
    """Returns a litellm Router configured with fallback."""
    import litellm
    from litellm import Router

    litellm.suppress_debug_info = True
    return Router(
        model_list=[
            {"model_name": "primary", "litellm_params": _params(primary)},
            {"model_name": "backup",  "litellm_params": _params(backup)},
        ],
        fallbacks=[{"primary": ["backup"]}],
        num_retries=1,
    )


def get_fast_router():
    return get_router(primary=FAST_MODEL, backup=BACKUP_MODEL)


def get_deep_router():
    return get_router(primary=DEEP_MODEL, backup=BACKUP_MODEL)


fast_router = None
deep_router = None
