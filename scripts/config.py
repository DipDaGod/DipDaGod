"""
=============================================================================
 CONFIG.PY
 -----------------------------------------------------------------------
 This is the ONE file you edit with your own information. Every other
 script in this folder (make_info_card.py, make_ascii_svg.py,
 update_contributions.py) imports from here, so you never have to touch
 the actual generator scripts -- just fill in the values below and run
 them (see how_to_use.txt).
=============================================================================
"""

# ---------------------------------------------------------------------------
# GITHUB USERNAME
# Used by update_contributions.py to pull your public contribution
# calendar, and as the default handle shown on the info card / ascii card.
# ---------------------------------------------------------------------------
GITHUB_USERNAME = "DipDaGod"


# ---------------------------------------------------------------------------
# INFO CARD  (the terminal / "neofetch"-style card -> info-card.svg)
# ---------------------------------------------------------------------------
INFO_CARD = {
    "username": GITHUB_USERNAME,
    "host": "github",
    "command": "neofetch",

    # Shown as plain rows right under the header line.
    "identity": [
        ("Name", "<YOUR_NAME>"),
        ("Role", "<YOUR_ROLE>"),
        ("Education", "<YOUR_EDUCATION>"),
    ],

    # Each section is either a {"kv": {...}} block (key/value rows) or a
    # {"bullets": [...]} block (bullet list). Add, remove, or reorder
    # sections freely -- the card resizes itself automatically.
    "sections": [
        {
            "title": "Languages",
            "kv": {
                "<LANGUAGE_1>": "<PROFICIENCY_1>",
                "<LANGUAGE_2>": "<PROFICIENCY_2>",
                "<LANGUAGE_3>": "<PROFICIENCY_3>",
                "<LANGUAGE_4>": "<PROFICIENCY_4>",
            },
        },
        {
            "title": "Interests",
            "bullets": [
                "<INTEREST_1>",
                "<INTEREST_2>",
                "<INTEREST_3>",
            ],
        },
        {
            # Put every link for your info hub here -- GitHub, LinkedIn,
            # portfolio, socials, whatever you want visible on the card.
            "title": "Links",
            "kv": {
                "GitHub": f"github.com/{GITHUB_USERNAME}",
                "<LINK_LABEL>": "<LINK_VALUE>",
            },
        },
    ],
}


# ---------------------------------------------------------------------------
# ASCII PORTRAIT  (writes "ascii-img.svg" at the repo root)
# Drop a background-stripped photo named "source_photo" (any extension,
# e.g. source_photo.png) in the repo root and run make_ascii_svg.py --
# no other prep step needed, see how_to_use.txt.
# ---------------------------------------------------------------------------
ASCII_COLUMNS = 100
ASCII_OUTPUT = "ascii-img.svg"
