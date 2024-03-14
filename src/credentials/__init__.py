try:
    from credentials import get_new_credentials, SCOPES
except ImportError:
    from .credentials import get_new_credentials, SCOPES
