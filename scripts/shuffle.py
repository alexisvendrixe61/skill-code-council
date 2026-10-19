#!/usr/bin/env python3
"""Randomly map advisors to anonymous letters for peer review.

Usage: python3 shuffle.py <OUT_DIR> [advisor names...]
Writes <OUT_DIR>/mapping.md and prints the mapping (letter -> advisor).
"""
import random
import sys
from pathlib import Path

DEFAULT_ADVISORS = ["breaker", "architect", "simplifier", "newcomer", "operator"]


def build_mapping(advisors: list[str]) -> dict[str, str]:
    """Return a random letter -> advisor mapping."""
    shuffled = random.sample(advisors, k=len(advisors))
    letters = "ABCDEFGH"[: len(shuffled)]
    return dict(zip(letters, shuffled, strict=True))


def main() -> None:
    out_dir = Path(sys.argv[1])
    advisors = sys.argv[2:] or DEFAULT_ADVISORS
    mapping = build_mapping(advisors)
    lines = [f"{letter} = {name}" for letter, name in mapping.items()]
    (out_dir / "mapping.md").write_text("# Anonymization mapping\n\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
