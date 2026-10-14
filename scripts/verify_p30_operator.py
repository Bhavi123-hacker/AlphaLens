"""Local existing-account verification dialog. Never persist credentials/sessions."""

import json
import subprocess
import threading
import tkinter as tk
from pathlib import Path


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    output = repo / ".local-data/p30-runtime/operator-verification.json"
    window = tk.Tk()
    window.title("AlphaLens: verify existing local operator")
    window.geometry("600x300")
    window.attributes("-topmost", True)
    tk.Label(
        window,
        text="Verify the existing AlphaLens login on 127.0.0.1:8017.\n"
        "No password reset. Inputs stay in memory and are never logged or saved.\n"
        "This is your LOCAL AlphaLens password, not an Upstox credential.",
        wraplength=550,
        padx=20,
        pady=18,
    ).pack()
    tk.Label(window, text="Existing username").pack()
    username = tk.Entry(window, width=40)
    username.pack()
    tk.Label(window, text="Existing local password").pack()
    password = tk.Entry(window, width=40, show="*")
    password.pack()
    status = tk.Label(
        window, text="Optional: close this dialog to leave actual operator login unverified."
    )
    status.pack(pady=10)

    def run() -> None:
        value = {"username": username.get(), "password": password.get()}
        password.delete(0, tk.END)
        status.config(text="Verifying with an isolated browser; please wait.")
        button.config(state="disabled")

        def verify() -> None:
            result = subprocess.run(
                [
                    "D:/al-research/p18-runtime/node-v22.23.3-win-x64/node.exe",
                    str(repo / "apps/web/scripts/verify-local-operator.mjs"),
                ],
                input=json.dumps(value).encode(),
                capture_output=True,
                timeout=120,
                cwd=repo / "apps/web",
            )
            value.clear()
            safe = {
                "existing_operator_login": "PASSED" if result.returncode == 0 else "NOT_VERIFIED",
                "password_reset": False,
                "credentials_saved": False,
                "browser_logout_verified": result.returncode == 0,
            }
            output.write_text(json.dumps(safe), encoding="utf-8")
            window.after(0, lambda: status.config(text=safe["existing_operator_login"]))

        threading.Thread(target=verify, daemon=True).start()

    button = tk.Button(window, text="Verify existing login securely", command=run)
    button.pack()
    window.mainloop()


if __name__ == "__main__":
    main()
