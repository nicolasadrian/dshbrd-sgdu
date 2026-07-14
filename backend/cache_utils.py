import time
import threading
from typing import Dict, Any

_response_cache: Dict[str, Any] = {}
_response_cache_lock = threading.Lock()

def cached_response(key: str, ttl_seconds: int = 120):
    """Devuelve (hit, data). Si hit=True, data es la respuesta cacheada."""
    with _response_cache_lock:
        entry = _response_cache.get(key)
        if entry and (time.time() - entry["ts"]) < ttl_seconds:
            return True, entry["data"]
    return False, None

def set_cache(key: str, data):
    """Guarda una respuesta en caché con timestamp."""
    with _response_cache_lock:
        # Limitar tamaño del caché (evitar memory leak)
        if len(_response_cache) > 200:
            oldest = sorted(_response_cache.items(), key=lambda x: x[1]["ts"])[:50]
            for k, _ in oldest:
                _response_cache.pop(k, None)
        _response_cache[key] = {"ts": time.time(), "data": data}
