"""Explicit, narrow publication transforms.

Each transform is a named function taking and returning text. There is deliberately no
general "scrub anything personal" pass: every rule below exists because a specific skill
needed it, and each is covered by a focused test.

Order matters and is fixed by the policy list. `omit_private_context` runs first (it deletes
whole lines), then name/pronoun rules, then path rules longest-prefix-first.
"""
import re

PERSONAL_FIRST = "Courtney"
PERSONAL_FULL = "Courtney Robertson"
HOME = "/Users/courtneyrobertson"
VAULT_ABS = f"{HOME}/Documents/2nd Brain"

# --- private context removal -------------------------------------------------------------
# Lines that exist only to describe this machine. Narrow: a bullet whose payload is a private
# absolute vault path, or an explicitly marked private line.
_PRIVATE_LINE = re.compile(
    r"^\s*(?:[-*]|\d+\.)\s+.*(?:" + re.escape(VAULT_ABS) + r"|<!--\s*private\s*-->).*$",
    re.MULTILINE,
)

def omit_private_context(t: str) -> str:
    return "\n".join(l for l in t.split("\n") if not _PRIVATE_LINE.match(l))

# --- identity ----------------------------------------------------------------------------
def full_name_and_agreement(t: str) -> str:
    """Full name before first name, so 'Courtney Robertson' never becomes 'the user Robertson'."""
    t = re.sub(rf"\b{PERSONAL_FULL}'s\b", "the user's", t)
    t = re.sub(rf"\b{PERSONAL_FULL}\b", "the user", t)
    return t

def replace_personal_name(t: str) -> str:
    t = re.sub(rf"\b{PERSONAL_FIRST}'s\b", "the user's", t)
    t = re.sub(rf"\b{PERSONAL_FIRST}\b", "the user", t)
    return t

# --- pronouns, grammar-preserving --------------------------------------------------------
# Verb agreement is part of the rule. A bare she->you yields "you is" / "you says".
_IRREGULAR = [
    (r"\bshe is\b", "you are"), (r"\bShe is\b", "You are"),
    (r"\bshe's\b", "you're"), (r"\bShe's\b", "You're"),
    (r"\bshe was\b", "you were"), (r"\bShe was\b", "You were"),
    (r"\bshe has\b", "you have"), (r"\bShe has\b", "You have"),
    (r"\bshe does\b", "you do"), (r"\bShe does\b", "You do"),
    (r"\bherself\b", "yourself"),
]
# third-person -s verbs following the pronoun: "she says" -> "you say"
_VERB_S = re.compile(r"\b([Ss])he ([a-z]+)s\b")

def _deconjugate(m):
    stem = m.group(2)                      # "she approves" -> stem "approve"
    if stem.endswith("ie"):                # tries -> try
        stem = stem[:-2] + "y"
    elif stem.endswith("e") and stem[:-1].endswith(("s", "x", "z", "ch", "sh")):
        stem = stem[:-1]                   # watches -> watch
    return f"you {stem}"

def second_person_owner(t: str) -> str:
    for pat, rep in _IRREGULAR:
        t = re.sub(pat, rep, t)
    t = _VERB_S.sub(_deconjugate, t)
    t = re.sub(r"\bShe\b", "You", t)
    t = re.sub(r"\bshe\b", "you", t)
    t = re.sub(r"\bHer\b", "Your", t)          # possessive determiner
    t = re.sub(r"\bhers\b", "yours", t)
    t = re.sub(r"\bher\b", "your", t)
    return t

# --- paths, longest prefix first ---------------------------------------------------------
VAULT_TILDE = "~/Documents/2nd Brain"

def vault_dir_variable(t: str) -> str:
    for v in (VAULT_ABS, VAULT_TILDE):
        t = t.replace(v + "/", "$VAULT_DIR/").replace(v, "$VAULT_DIR")
    return t

OLD_HOME = "/Users/crobertson"   # previous laptop; appears in historical notes

def normalize_home_path(t: str) -> str:
    for h in (HOME, OLD_HOME):
        t = t.replace(h + "/", "$HOME/").replace(h, "$HOME")
    return t

def genericize_vault_name(t: str) -> str:
    return re.sub(r"\b2nd Brain\b", "your vault", t)

def strip_para_number_prefix(t: str) -> str:
    """PARA numbering is this vault's convention, not a portable one."""
    t = re.sub(r"\b[1-6]\.\s(Projects|Areas|Resources|Inbox|Templates|Archives)/", r"\1/", t)
    return re.sub(r"([\"'`])[1-6]\.\s(Projects|Areas|Resources|Inbox|Templates|Archives)\1", r"\1\2\1", t)

# --- identifiers -------------------------------------------------------------------------
def genericize_domain(t: str) -> str:
    return t.replace("courtneyr.dev", "example.com")

def genericize_identifiers(t: str) -> str:
    t = t.replace("com.courtneyr.", "com.you.").replace("com.courtney.", "com.you.")
    t = t.replace("courtneyr-dev/", "your-org/")
    return t

def genericize_personal_site(t: str) -> str:
    return t.replace("Robertson's Home", "a separate personal site")

def placeholder_private_example(t: str) -> str:
    """Private example paths become placeholders; the surrounding instruction survives."""
    return re.sub(r"Projects/llm-wiki-[a-z0-9-]+/", "Projects/<your-wiki>/", t)

def collapse_loop_reports_path(t: str) -> str:
    """`2. Areas/Loop Reports/` is this vault's folder; the public edition calls it `Reports/`."""
    return re.sub(r"\b(?:[1-6]\.\s)?Areas/Loop Reports/", "Reports/", t)

REGISTRY = {f.__name__: f for f in [
    collapse_loop_reports_path,
    omit_private_context, full_name_and_agreement, replace_personal_name, second_person_owner,
    vault_dir_variable, normalize_home_path, genericize_vault_name, strip_para_number_prefix,
    genericize_domain, genericize_identifiers, genericize_personal_site, placeholder_private_example,
]}

def apply_all(text: str, names):
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        raise KeyError(f"unknown transform(s): {unknown}")
    for n in names:
        text = REGISTRY[n](text)
    return text
