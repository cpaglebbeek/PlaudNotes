"""Token refresh helper for Plaud Notes MCP.

Opens web.plaud.ai in the browser, monitors for the auth token,
and saves it to ~/.config/plaud/token.

Usage: plaud-refresh-token
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TOKEN_PATH = Path.home() / ".config" / "plaud" / "token"
PLAUD_WEB = "https://web.plaud.ai"


def decode_token_expiry(token: str) -> tuple[datetime | None, int | None]:
    """Decode JWT and return (expiry_datetime, days_left)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None, None
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        exp = payload.get("exp")
        if not exp:
            return None, None
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        days_left = (exp_dt - datetime.now(tz=timezone.utc)).days
        return exp_dt, days_left
    except Exception:
        return None, None


def show_current_status() -> None:
    """Show current token status."""
    if TOKEN_PATH.exists():
        token = TOKEN_PATH.read_text().strip()
        exp_dt, days_left = decode_token_expiry(token)
        if exp_dt and days_left is not None:
            if days_left < 0:
                print(f"  Token VERLOPEN op {exp_dt.strftime('%Y-%m-%d')} ({abs(days_left)} dagen geleden)")
            elif days_left < 30:
                print(f"  Token verloopt over {days_left} dagen ({exp_dt.strftime('%Y-%m-%d')})")
            else:
                print(f"  Token geldig tot {exp_dt.strftime('%Y-%m-%d')} ({days_left} dagen)")
        else:
            print("  Token gevonden maar expiry onbekend")
    else:
        print("  Geen token gevonden")


def save_token(token: str) -> None:
    """Save token to config file with secure permissions."""
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(token.strip())
    os.chmod(TOKEN_PATH, 0o600)

    exp_dt, days_left = decode_token_expiry(token)
    print(f"\n  Token opgeslagen in {TOKEN_PATH}")
    if exp_dt and days_left:
        print(f"  Geldig tot {exp_dt.strftime('%Y-%m-%d')} ({days_left} dagen)")


def main() -> None:
    """Main entry point."""
    print("=== Plaud Notes Token Refresh ===\n")
    print("Huidige status:")
    show_current_status()
    print()

    print("Stappen om een nieuw token te verkrijgen:")
    print("  1. Open web.plaud.ai in je browser")
    print("  2. Log in met Google (als je niet al ingelogd bent)")
    print("  3. Open DevTools (F12 of Cmd+Option+I)")
    print("  4. Ga naar Network tab")
    print("  5. Zoek een API request (bijv. /file/simple/web)")
    print("  6. Kopieer de 'Authorization: Bearer ...' header waarde")
    print("  7. Plak het token hieronder\n")

    # Open browser
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", PLAUD_WEB], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == "linux":
            subprocess.Popen(["xdg-open", PLAUD_WEB], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  Browser geopend: {PLAUD_WEB}\n")
    except Exception:
        print(f"  Open handmatig: {PLAUD_WEB}\n")

    # Prompt for token
    try:
        token = input("Plak je token (Bearer ... of alleen het token): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nGeannuleerd.")
        return

    if not token:
        print("Geen token ingevoerd. Geannuleerd.")
        return

    # Clean up
    token = token.removeprefix("Bearer ").removeprefix("bearer ").strip()

    # Validate it's a JWT
    parts = token.split(".")
    if len(parts) != 3:
        print("Ongeldig token formaat (verwacht JWT met 3 delen).")
        return

    # Check expiry
    exp_dt, days_left = decode_token_expiry(token)
    if exp_dt and days_left is not None:
        if days_left < 0:
            print(f"Dit token is al verlopen ({exp_dt.strftime('%Y-%m-%d')}). Probeer opnieuw.")
            return
        print(f"\n  Token geldig tot {exp_dt.strftime('%Y-%m-%d')} ({days_left} dagen)")
    else:
        print("\n  Kan expiry niet bepalen, token wordt toch opgeslagen")

    # Save
    save_token(token)

    # Test connection
    print("\n  Verbinding testen...")
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from plaud_notes_mcp.plaud_client import PlaudClient
        client = PlaudClient(token=token)
        info = client.get_user_info()
        user_data = info.get("data_user", info)
        name = user_data.get("nickname", "Onbekend")
        print(f"  Verbonden als: {name}")
        client.close()
    except Exception as e:
        print(f"  Verbindingstest mislukt: {e}")

    print("\nKlaar! Herstart je MCP server om het nieuwe token te gebruiken.")


if __name__ == "__main__":
    main()
