from __future__ import annotations

import argparse
from typing import Any

from src.user_context import save_profile, set_active_user


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or default


def _ask_int(prompt: str, default: int = 0) -> int:
    while True:
        answer = _ask(prompt, str(default))
        try:
            return int(answer)
        except ValueError:
            print("Please enter a number.")


def collect_context_interactive() -> dict[str, Any]:
    print("PM Job Search Copilot - User Onboarding")
    print("Fill this once per person. You can edit YAML later.")
    print("")

    user_id = _ask("User id (short slug)", "default")
    display_name = _ask("Display name", user_id)
    target_roles = _split_csv(
        _ask("Target roles (comma-separated)", "Product Manager, Senior Product Manager")
    )
    preferred_locations = _split_csv(
        _ask("Preferred locations (comma-separated)", "Remote US, Seattle, Bellevue")
    )
    excluded_locations = _split_csv(_ask("Excluded locations (comma-separated)", ""))
    work_modes = _split_csv(_ask("Work modes: remote/hybrid/onsite", "remote, hybrid"))
    years_experience = _ask_int("Years of experience", 5)
    target_seniority = _split_csv(_ask("Target seniority bands", "mid, senior"))
    domains = _split_csv(_ask("Domain focus keywords", ""))
    skills = _split_csv(_ask("Top skills keywords", "roadmap, stakeholder, metrics"))
    must_have_keywords = _split_csv(_ask("Must-have JD keywords", ""))
    nice_to_have_keywords = _split_csv(_ask("Nice-to-have JD keywords", ""))
    avoid_keywords = _split_csv(_ask("Avoid keywords / red flags", ""))
    visa_requirements = _split_csv(_ask("Visa/sponsorship needs", ""))
    compensation_min_usd = _ask_int("Minimum compensation in USD (0 if no filter)", 0)

    return {
        "user_id": user_id,
        "display_name": display_name,
        "target_roles": target_roles,
        "preferred_locations": preferred_locations,
        "excluded_locations": excluded_locations,
        "work_modes": work_modes,
        "years_experience": years_experience,
        "target_seniority": target_seniority,
        "domains": domains,
        "skills": skills,
        "must_have_keywords": must_have_keywords,
        "nice_to_have_keywords": nice_to_have_keywords,
        "avoid_keywords": avoid_keywords,
        "visa_requirements": visa_requirements,
        "compensation_min_usd": compensation_min_usd,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or update a user job-search profile")
    parser.add_argument(
        "--set-active",
        action="store_true",
        help="Set this user as active after saving.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    context = collect_context_interactive()
    path = save_profile(context)
    print(f"Saved profile to: {path}")

    if args.set_active:
        set_active_user(str(context["user_id"]))
        print(f"Set active user: {context['user_id']}")


if __name__ == "__main__":
    main()

