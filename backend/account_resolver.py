"""
Account name resolution shared by the intent classifier, orchestrator and chat endpoint.

Matches are whole-word only: a query matches an account when it contains the full
account name, the Account_ID, or the account's brand word (first word of the name,
e.g. "Meridian" -> "Meridian Health Network"). Substring matching is deliberately
avoided: it let "I" match "Northwind Logistics".
"""
import re
from typing import Iterable, List, Optional

import pandas as pd

# Words that start sentences or commands and are never account names.
NON_ACCOUNT_WORDS = {
    "a", "an", "the", "i", "me", "my", "we", "us", "our", "you", "your", "they", "them", "their", "it", "its",
    "who", "what", "where", "when", "why", "how", "which", "is", "are", "do", "does", "can", "could", "should",
    "would", "will", "please", "tell", "show", "give", "get", "list", "find", "review", "evaluate", "provide",
    "create", "draft", "write", "prepare", "schedule", "summarize", "summarise", "compare", "explain", "analyze",
    "analyse", "build", "make", "help", "top", "any", "all", "hi", "hello", "hey", "thanks", "ok", "okay",
    "traced", "about", "for", "and", "or", "of", "at", "in", "on", "to", "with", "ceo", "cfo", "cto", "cio", "vp",
    "am", "svp", "q1", "q2", "q3", "q4", "crm", "apex",
}


def _brand(name: str) -> Optional[str]:
    words = re.findall(r"[a-z0-9&]+", name.lower())
    if words and len(words[0]) >= 3 and words[0] not in NON_ACCOUNT_WORDS:
        return words[0]
    return None


def _has_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(r"\b" + re.escape(phrase) + r"\b", text))


def find_account_in_text(text: str, known_accounts: Iterable[str]) -> Optional[str]:
    """Return the known account named in `text` (full name first, then brand word), else None."""
    if not text:
        return None
    text_lower = text.lower()
    accounts = [a for a in known_accounts if a]

    full_hits = [(text_lower.find(a.lower()), a) for a in accounts if _has_phrase(text_lower, a.lower())]
    if full_hits:
        return min(full_hits)[1]

    brand_hits = []
    for a in accounts:
        brand = _brand(a)
        if brand and _has_phrase(text_lower, brand):
            brand_hits.append((re.search(r"\b" + re.escape(brand) + r"\b", text_lower).start(), a))
    if brand_hits:
        return min(brand_hits)[1]
    return None


def candidate_names(text: str) -> List[str]:
    """Capitalised word runs that could be an (unknown) account name, with filler words removed."""
    candidates = []
    for run in re.findall(r"\b[A-Z][a-zA-Z0-9&]*(?:\s+[A-Z][a-zA-Z0-9&]*)*\b", text or ""):
        words = [w for w in run.split() if w.lower() not in NON_ACCOUNT_WORDS]
        if words and len(" ".join(words)) >= 3:
            candidates.append(" ".join(words))
    return candidates


def match_account_rows(accounts_df: Optional[pd.DataFrame], name: Optional[str]) -> pd.DataFrame:
    """Rows of `accounts_df` matching `name` exactly (name or ID), else by whole word. Empty if none."""
    if accounts_df is None or accounts_df.empty or not name or not str(name).strip():
        return pd.DataFrame()
    target = str(name).strip().lower()
    names = accounts_df["Account_Name"].fillna("").astype(str).str.lower()
    ids = accounts_df["Account_ID"].fillna("").astype(str).str.lower()

    exact = accounts_df[(names == target) | (ids == target)]
    if not exact.empty:
        return exact
    if len(target) < 3 or target in NON_ACCOUNT_WORDS:
        return pd.DataFrame()
    pattern = r"\b" + re.escape(target) + r"\b"
    return accounts_df[names.str.contains(pattern, regex=True, na=False)]


def is_contact_name(contacts_df: Optional[pd.DataFrame], name: Optional[str]) -> bool:
    """True when `name` is a contact's first, last or full name (whole word)."""
    if contacts_df is None or contacts_df.empty or not name:
        return False
    target = str(name).strip().lower()
    if len(target) < 3:
        return False
    for _, row in contacts_df.iterrows():
        first = str(row.get("First_Name", "") or "").strip().lower()
        last = str(row.get("Last_Name", "") or "").strip().lower()
        if target in {first, last, f"{first} {last}".strip()}:
            return True
    return False


def user_messages(history: Optional[list]) -> List[str]:
    """Texts of the user's own messages in a chat history (assistant answers are excluded)."""
    texts = []
    for msg in history or []:
        who = str(msg.get("sender", msg.get("role", ""))).lower()
        if who == "user":
            texts.append(str(msg.get("text", msg.get("content", "")) or ""))
    return texts
