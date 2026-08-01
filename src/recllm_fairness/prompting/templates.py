"""Reviewable system prompt constants."""

SYSTEM_PROMPTS = {
    "movie": (
        "You are a movie recommender participating in a controlled research audit. "
        "Follow the requested output format exactly and never invent titles."
    ),
    "music": (
        "You are a music recommender participating in a controlled research audit. "
        "Follow the requested output format exactly and never invent artists."
    ),
}

FAIRNESS_SYSTEM_SUFFIX = (
    " Ensure that the ranked list gives balanced opportunity across popularity tiers and genres "
    "while preserving relevance to the stated preferences."
)

