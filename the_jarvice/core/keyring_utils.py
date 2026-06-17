"""
Keyring utilities for The Jarvice.

Cross-platform credential storage using Python keyring.
On macOS: macOS Keychain
On Linux: libsecret / SecretService

All service names are prefixed with "the-jarvice." for namespace isolation.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

# Namespace prefix for all keyring entries
SERVICE_PREFIX = "the-jarvice."

# Known service names (canonical list for enumeration)
KNOWN_SERVICES = [
    "the-jarvice.exchange",
    "the-jarvice.teams",
    "the-jarvice.telegram",
    "the-jarvice.telegram-bot",
]


def _ensure_prefix(service: str) -> str:
    """Ensure service name has the the-jarvice. prefix."""
    if not service.startswith(SERVICE_PREFIX):
        service = f"{SERVICE_PREFIX}{service}"
    return service





def list_credentials(prefix: str = "the-jarvice") -> list[tuple[str, str]]:
    """List all credentials matching a prefix.

    On macOS, uses the security command to enumerate Keychain entries.
    On Linux, uses SecretStorage API.

    Args:
        prefix: Service name prefix to filter by. Default: "the-jarvice".

    Returns:
        List of (service, account) tuples for matching credentials.
    """
    if not prefix.endswith("."):
        prefix = f"{prefix}."

    if platform.system() == "Darwin":
        credentials = _list_macos_keychain(prefix)
    else:
        credentials = _list_linux_keyring(prefix)

    logger.debug(f"Found {len(credentials)} credentials matching prefix '{prefix}'")
    return credentials


def _list_macos_keychain(prefix: str) -> list[tuple[str, str]]:
    """List credentials in macOS Keychain matching a prefix."""
    credentials: list[tuple[str, str]] = []

    try:
        result = subprocess.run(
            ["security", "dump-keychain"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            logger.warning(f"security dump-keychain failed: {result.stderr}")
            return _list_known_services(prefix)

        import keyring

        for known_service in KNOWN_SERVICES:
            if not known_service.startswith(prefix):
                continue
            try:
                cred = keyring.get_credential(known_service, None)
                if cred and cred.password:
                    credentials.append((known_service, cred.username))
            except Exception:
                credentials.append((known_service, ""))

    except FileNotFoundError:
        logger.warning("security command not found (not macOS?)")
        return _list_known_services(prefix)
    except subprocess.TimeoutExpired:
        logger.warning("security dump-keychain timed out")
        return _list_known_services(prefix)
    except Exception as e:
        logger.warning(f"Error listing macOS Keychain: {e}")
        return _list_known_services(prefix)

    return credentials


def _list_linux_keyring(prefix: str) -> list[tuple[str, str]]:
    """List credentials on Linux using SecretStorage."""
    credentials: list[tuple[str, str]] = []

    try:
        import secretstorage

        bus = secretstorage.dbus_init()
        collection = secretstorage.get_default_collection(bus)
        if collection.is_locked():
            collection.unlock()
        for item in collection.get_all_items():
            label = item.get_label()
            if label.startswith(prefix):
                for known_service in KNOWN_SERVICES:
                    if known_service.startswith(prefix):
                        try:
                            import keyring

                            cred = keyring.get_credential(known_service, None)
                            if cred and cred.password:
                                credentials.append((known_service, cred.username))
                        except Exception:
                            credentials.append((known_service, ""))
        bus.close()
    except ImportError:
        logger.debug("secretstorage not available, falling back to known services")
        credentials = _list_known_services(prefix)
    except Exception as e:
        logger.debug(f"SecretStorage error: {e}, falling back to known services")
        credentials = _list_known_services(prefix)

    return credentials


def test_keyring() -> tuple[bool, str]:
    """Backward-compatible alias for check_keyring()."""
    return check_keyring()


def _list_known_services(prefix: str) -> list[tuple[str, str]]:
    """Fallback: check known services for existing credentials."""
    import keyring

    credentials: list[tuple[str, str]] = []

    for service in KNOWN_SERVICES:
        if not service.startswith(prefix):
            continue
        try:
            cred = keyring.get_credential(service, None)
            if cred and cred.password:
                credentials.append((service, cred.username))
        except Exception:
            pass

    return credentials


def _env_var_for_service(service: str) -> str:
    """Derive the environment variable name for a keyring service.

    Converts a service like 'the-jarvice.exchange' to 'JARVICE_EXCHANGE_PASSWORD'.
    Strips the 'the-jarvice.' prefix, uppercases, and appends _PASSWORD.

    Args:
        service: Keyring service name.

    Returns:
        Environment variable name (e.g. 'JARVICE_EXCHANGE_PASSWORD').
    """
    # Strip prefix if present
    name = service
    if name.startswith(SERVICE_PREFIX):
        name = name[len(SERVICE_PREFIX):]
    # Convert to env var format: JARVICE_{NAME}_PASSWORD
    return f"JARVICE_{name.upper()}_PASSWORD"


def get_credential(service: str, account: str) -> Optional[str]:
    """Retrieve a credential from the keyring, falling back to env vars.

    Resolution order:
      1. Keyring (macOS Keychain / Linux libsecret)
      2. Environment variable JARVICE_{SERVICE}_PASSWORD
      3. None

    Args:
        service: Keyring service name (will be prefixed with "the-jarvice." if not already).
        account: Account/username identifier.

    Returns:
        The stored password, or None if not found or error.
    """
    import keyring

    service = _ensure_prefix(service)

    # 1. Try keyring
    try:
        password = keyring.get_password(service, account)
        if password is not None:
            logger.debug(f"Credential retrieved from keyring: {service}/{account}")
            return password
    except keyring.errors.KeyringError as e:
        logger.debug(f"Keyring retrieval failed for {service}/{account}: {e}")
    except Exception as e:
        logger.debug(f"Unexpected keyring error for {service}/{account}: {e}")

    # 2. Try environment variable fallback
    env_var = _env_var_for_service(service)
    env_value = os.environ.get(env_var)
    if env_value:
        logger.info(f"Credential retrieved from env var: {env_var}")
        return env_value

    # Also check with account suffix for special cases
    if account and account != "default":
        env_var_with_account = f"{env_var}_{account.upper()}"
        env_value = os.environ.get(env_var_with_account)
        if env_value:
            logger.info(f"Credential retrieved from env var: {env_var_with_account}")
            return env_value

    logger.debug(f"Credential not found: {service}/{account}")
    return None


def save_credential(service: str, account: str, password: str) -> bool:
    """Save a credential to the keyring.

    If keyring is unavailable, logs a suggestion to use env vars
    and returns False.

    Args:
        service: Keyring service name (will be prefixed with "the-jarvice." if not already).
        account: Account/username identifier.
        password: The secret value to store.

    Returns:
        True if saved successfully to keyring, False if keyring unavailable.
    """
    import keyring

    service = _ensure_prefix(service)

    try:
        keyring.set_password(service, account, password)
        logger.info(f"Credential saved: {service}/{account}")
        return True
    except keyring.errors.KeyringError as e:
        env_var = _env_var_for_service(service)
        logger.warning(
            f"Failed to save credential {service}/{account} to keyring: {e}. "
            f"Set environment variable {env_var} instead."
        )
        if platform.system() == "Linux":
            logger.warning(
                "On Linux, install libsecret: sudo apt install libsecret-1-0 "
                "or set JARVICE_*_PASSWORD environment variables."
            )
        return False
    except Exception as e:
        env_var = _env_var_for_service(service)
        logger.error(
            f"Unexpected error saving credential {service}/{account}: {e}. "
            f"Set environment variable {env_var} instead."
        )
        return False


def check_keyring() -> tuple[bool, str]:
    """Pre-flight check for keyring availability.

    Tests keyring read/write and provides platform-specific guidance
    if keyring is unavailable.

    Returns:
        Tuple of (available: bool, message: str).
        Message includes fix instructions if keyring is not available.
    """
    import keyring

    test_service = "the-jarvice.preflight"
    test_account = "test"
    test_password = "preflight_check_2026"

    try:
        keyring.set_password(test_service, test_account, test_password)
        retrieved = keyring.get_password(test_service, test_account)
        keyring.delete_password(test_service, test_account)

        if retrieved != test_password:
            return False, "Keyring read/write mismatch (credentials may not persist)"

        backend_name = type(keyring.get_keyring()).__name__
        return True, f"Keyring accessible ({backend_name})"

    except keyring.errors.NoKeyringError:
        msg = "No keyring backend available"
        if platform.system() == "Linux":
            msg += ". Install: sudo apt install libsecret-1-0"
        msg += ". Alternatively, set JARVICE_*_PASSWORD environment variables."
        return False, msg

    except keyring.errors.KeyringLocked:
        return False, "Keyring is locked. Unlock your keychain and try again."

    except keyring.errors.KeyringError as e:
        msg = f"Keyring error: {e}"
        if platform.system() == "Linux":
            msg += " Install: sudo apt install libsecret-1-0"
        msg += " Alternatively, set JARVICE_*_PASSWORD environment variables."
        return False, msg

    except Exception as e:
        return False, f"Unexpected keyring error: {e}. Set JARVICE_*_PASSWORD env vars as fallback."


def delete_credential(service: str, account: str) -> bool:
    """Delete a credential from the keyring.

    Args:
        service: Keyring service name (will be prefixed with "the-jarvice." if not already).
        account: Account/username identifier.

    Returns:
        True if deleted successfully, False if not found or error.
    """
    import keyring

    service = _ensure_prefix(service)

    try:
        keyring.delete_password(service, account)
        logger.info(f"Credential deleted: {service}/{account}")
        return True
    except keyring.errors.PasswordDeleteError:
        logger.debug(f"Credential not found for deletion: {service}/{account}")
        return False
    except keyring.errors.KeyringError as e:
        logger.error(f"Failed to delete credential {service}/{account}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting credential {service}/{account}: {e}")
        return False