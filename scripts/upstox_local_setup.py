"""Local category confirmation only; no credential values read by the dialog."""

import json
import tkinter as tk
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    output = Path(__file__).resolve().parents[1] / ".local-data/p30-token-category.json"
    if output.exists():
        return
    window = tk.Tk()
    window.title("AlphaLens: Upstox token category")
    window.geometry("600x290")
    window.attributes("-topmost", True)
    tk.Label(
        window,
        text=(
            "The token is securely stored. No secret is shown or requested.\n\n"
            "Identify where you generated the token in Upstox Developer Apps.\n"
            "Read-only API validation can proceed with either category.\n"
            "This selection does not grant data retention or automation rights."
        ),
        wraplength=560,
        justify="left",
        padx=20,
        pady=20,
    ).pack()

    def choose(category: str) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(
                {
                    "category": category,
                    "evidence": "LOCAL_OPERATOR_CONFIRMATION",
                    "confirmed_at": datetime.now(UTC).isoformat(),
                },
                stream,
            )
        window.destroy()

    for label, category in (
        ("Analytics tab — Analytics Token", "ANALYTICS_OPERATOR_CONFIRMED"),
        ("App OAuth / access token", "OAUTH_OPERATOR_CONFIRMED"),
        ("Unsure — keep category unverified", "UNDETERMINED"),
    ):
        tk.Button(window, text=label, command=lambda c=category: choose(c)).pack(pady=4)
    window.mainloop()


if __name__ == "__main__":
    main()
