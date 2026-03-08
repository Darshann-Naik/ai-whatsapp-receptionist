from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter. default_limits can be added here if needed.
limiter = Limiter(key_func=get_remote_address)