import re
from difflib import SequenceMatcher

# ScamGuard Advanced Rule Engine with Levenshtein / Fuzzy Matching
# Evaluates arbitrary amounts, evasive synonyms, and matches handles/names
# against the known reported scammer database.

def levenshtein_similarity(a: str, b: str) -> float:
    """Calculates normalized sequence similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def check_fuzzy_blacklist(input_text: str, blacklist_items: list) -> list:
    """
    Checks incoming text for:
    1. Exact matches of reported phone numbers, UPI IDs, or emails.
    2. Fuzzy matches of reported agency/recruiter names with similarity > 0.80.
    """
    matches = []
    lower_text = input_text.lower()

    for item in blacklist_items:
        handle = item.get("handle", "").lower().strip()
        name = item.get("name", "").lower().strip()

        # 1. Exact contact / handle match
        if handle and handle in lower_text:
            matches.append({
                "type": "exact",
                "handle": item.get("handle"),
                "name": item.get("name"),
                "reports": item.get("report_count", 1),
                "category": item.get("category", "General Fraud"),
                "similarity": 1.0
            })
            continue

        # 2. Fuzzy name match using n-gram window similarity
        if name and len(name) >= 4:
            # Check direct substring first
            if name in lower_text:
                matches.append({
                    "type": "exact",
                    "handle": item.get("handle"),
                    "name": item.get("name"),
                    "reports": item.get("report_count", 1),
                    "category": item.get("category", "General Fraud"),
                    "similarity": 1.0
                })
            else:
                # Token window comparison
                words = lower_text.split()
                name_len = len(name.split())
                for i in range(len(words) - name_len + 1):
                    window = " ".join(words[i:i + name_len])
                    sim = levenshtein_similarity(name, window)
                    if sim >= 0.82:
                        matches.append({
                            "type": "fuzzy",
                            "handle": item.get("handle"),
                            "name": item.get("name"),
                            "reports": item.get("report_count", 1),
                            "category": item.get("category", "General Fraud"),
                            "similarity": round(sim * 100, 1)
                        })
                        break

    return matches

RULES = [
    # 1. Any upfront fee / deposit / recharge / processing charge with ANY arbitrary monetary figure
    {
        "pattern": r"(?:fee|charge|deposit|amount|cost|security|recharge|investment|token|caution|clearance|pass|verification\s*charge|allocation\s*fee|kit\s*fee|uniform\s*fee)\b[^\n.?!]{0,40}?(?:rs\.?|inr|₹|usd|\$)?\s*\b(?:\d{2,7}|[1-9]\d{0,2}\s*(?:k|thousand|lakh|lac|crore))\b",
        "score": 65,
        "type": "Upfront Fee & Deposit Trap",
        "explanation": "Demand for upfront monetary payment or security deposit regardless of the specific sum."
    },
    # 2. Reverse pattern: Monetary figure followed by fee / security / payment words
    {
        "pattern": r"(?:rs\.?|inr|₹|usd|\$)?\s*\b(?:\d{2,7}|[1-9]\d{0,2}\s*(?:k|thousand|lakh|lac))\b[^\n.?!]{0,40}?(?:fee|deposit|recharge|payment|transfer|send|invest|submit|advance)",
        "score": 65,
        "type": "Upfront Fee & Deposit Trap",
        "explanation": "Demands payment of funds or money transfer before or during employment."
    },
    # 3. Task & Review manipulation (YouTube, Google reviews, telegram tasks)
    {
        "pattern": r"(like|subscribe|review|rating|hotel\s*booking|order\s*grabbing|merchant\s*task)\b[^\n.?!]{0,30}?(?:earn|daily|per\s*day|commission|part\s*time|payout)",
        "score": 60,
        "type": "Task & Review Deposit Scam",
        "explanation": "Daily tasks promising instant commission payouts are standard high-risk deposit scams."
    },
    # 4. Off-platform redirection (Telegram, personal WhatsApp, WhatsApp HR)
    {
        "pattern": r"(telegram|t\.me/|whatsapp|wa\.me/|dm\s*me\s*on|chat\s*on\s*whatsapp)",
        "score": 40,
        "type": "Off-Platform Redirection",
        "explanation": "Pressuring communication off verified job portals to unmonitored channels."
    },
    # 5. Free public email domain used by alleged corporate recruiters
    {
        "pattern": r"@(gmail\.com|yahoo\.com|outlook\.com|hotmail\.com|rediffmail\.com|proton\.me|icloud\.com)",
        "score": 35,
        "type": "Free Webmail Recruiter Address",
        "explanation": "Recruiter is contacting via free public webmail rather than official company domain."
    },
    # 6. High salary promises for trivial low-skill or data entry tasks
    {
        "pattern": r"(?:data\s*entry|typing|sms\s*sending|copy\s*paste)\b[^\n.?!]{0,40}?(?:3[0-9],000|[4-9][0-9],000|[1-9][0-9]{5}|per\s*month)",
        "score": 55,
        "type": "Unrealistic Remuneration Bait",
        "explanation": "Offering disproportionately high remuneration for trivial low-skill tasks."
    },
    # 7. Evasive or indirect payment synonyms (e.g. 'buy coupon', 'purchase voucher', 'crypto wallet')
    {
        "pattern": r"(crypto|usdt|binance|gift\s*card|voucher|paytm\s*wallet|google\s*play\s*code|qr\s*scan)",
        "score": 60,
        "type": "Alternative & Crypto Payment Redirection",
        "explanation": "Using gift cards, crypto, or indirect vouchers to obfuscate payment tracking."
    },
    # 8. Evasion attempt (trying to deceive AI or rules)
    {
        "pattern": r"(ignore\s*previous\s*instructions|rate\s*this\s*safe|score\s*0|say\s*legitimate|bypass)",
        "score": 80,
        "type": "Prompt Injection Fraud Attempt",
        "explanation": "Text contains prompt injection commands intended to deceive analysis tools."
    }
]

def analyze_text_rules(text: str, blacklist_items: list = None) -> dict:
    """Evaluates arbitrary amounts, evasive patterns, and checks fuzzy blacklist."""
    lower_text = text.lower()
    total_score = 0
    matched_reasons = []
    detected_types = []

    # Check database matching (Exact + Fuzzy Levenshtein)
    if blacklist_items:
        bl_matches = check_fuzzy_blacklist(text, blacklist_items)
        for bm in bl_matches:
            if bm["type"] == "exact":
                total_score += 85
                matched_reasons.insert(0, {
                    "phrase": f"{bm['name']} ({bm['handle']})",
                    "explanation": f"CRITICAL HIT: Direct match in Scammer Database! Reported {bm['reports']} times for {bm['category']}."
                })
                detected_types.insert(0, f"Verified Offender: {bm['category']}")
            else:
                total_score += 65
                matched_reasons.insert(0, {
                    "phrase": f"Similarity: {bm['similarity']}% to '{bm['name']}'",
                    "explanation": f"SUSPICIOUS ENTITY: High Levenshtein similarity ({bm['similarity']}%) to reported entity '{bm['name']}' ({bm['handle']})."
                })
                detected_types.insert(0, f"Fuzzy Match: {bm['name']}")

    for rule in RULES:
        matches = re.findall(rule["pattern"], lower_text)
        if matches:
            total_score += rule["score"]
            phrase_found = matches[0] if isinstance(matches[0], str) else "Detected pattern"
            matched_reasons.append({
                "phrase": phrase_found,
                "explanation": rule["explanation"]
            })
            detected_types.append(rule["type"])

    capped_score = min(total_score, 100)
    primary_type = detected_types[0] if detected_types else "none"

    return {
        "score": capped_score,
        "scam_type": primary_type,
        "reasons": matched_reasons
    }

def analyze_progression(messages: list) -> dict:
    """Tracks escalating conversational danger across successive messages."""
    scores = []
    breakdown = []
    for idx, msg in enumerate(messages):
        res = analyze_text_rules(msg)
        scores.append(res["score"])
        breakdown.append({
            "index": idx + 1,
            "snippet": (msg[:50] + "...") if len(msg) > 50 else msg,
            "score": res["score"]
        })

    escalating = False
    if len(scores) >= 2:
        if scores[-1] > scores[0] + 15:
            escalating = True

    return {
        "escalating": escalating,
        "breakdown": breakdown
    }
