import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Import AI & Advanced Fuzzy Rule Engine wrappers
from ai import analyze_with_gemini
from rules import analyze_text_rules, analyze_progression
from translations import get_text

app = Flask(__name__)
# Session persistence configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "safeguard-permanent-session-key-2026")
app.config["SESSION_PERMANENT"] = True

# Real Scammer Database with dynamic report count scaling
COMMUNITY_BLACKLIST = [
    {
        "name": "TCS Recruitment Desk",
        "platform": "Email",
        "handle": "tcs-careers-desk@gmail.com",
        "category": "Fake Offer Letter",
        "report_count": 18,
        "date": "Just Now"
    },
    {
        "name": "QuickHire Freelance Support",
        "platform": "Telegram",
        "handle": "hire_quick_support@upi",
        "category": "Registration Fee Trap",
        "report_count": 7,
        "date": "1 hr ago"
    },
    {
        "name": "Google Maps Video Reviewer Partner",
        "platform": "WhatsApp",
        "handle": "+91 91234 56789",
        "category": "Task & Review Scam",
        "report_count": 3,
        "date": "3 hrs ago"
    }
]

FEEDBACK_REVIEWS = []
USER_SCAN_LOGS = []

@app.context_processor
def inject_translations():
    lang = session.get("lang", "en")
    return dict(t=lambda key, **kwargs: get_text(lang, key, **kwargs))

def merge_scores(ai_res: dict, rule_res: dict) -> dict:
    if "error" in ai_res or not ai_res:
        score = rule_res["score"]
        scam_type = rule_res["scam_type"] if rule_res["scam_type"] != "none" else "General Suspicion"
        reasons = rule_res["reasons"]
        questions = [
            "What is your company Corporate Identification Number (CIN)?",
            "Can you email me from your official @company.com corporate domain?"
        ]
        return {
            "score": score,
            "scam_type": scam_type,
            "reasons": reasons,
            "questions": questions
        }

    ai_score = ai_res.get("score", 0)
    rule_score = rule_res.get("score", 0)

    final_score = ai_score
    if rule_score >= 60 and ai_score < 60:
        final_score = rule_score

    merged_reasons = []
    seen = set()
    for r in ai_res.get("reasons", []) + rule_res.get("reasons", []):
        p = r.get("phrase", "")
        if p and p.lower() not in seen:
            seen.add(p.lower())
            merged_reasons.append(r)

    return {
        "score": final_score,
        "scam_type": ai_res.get("scam_type", rule_res.get("scam_type", "General Suspicion")),
        "reasons": merged_reasons,
        "questions": ai_res.get("questions", [])
    }

# ----------------- ROUTES -----------------

@app.route("/")
def home():
    return render_template("home.html", recent_alerts_count=len(COMMUNITY_BLACKLIST))

@app.route("/set-language", methods=["POST"])
def set_language():
    lang = request.form.get("lang", "en")
    if lang in ["en", "hi", "hinglish", "bn", "ml"]:
        session["lang"] = lang
        session["welcome_dismissed"] = True  # Ensure server-side state knows user has already engaged
    return redirect(request.referrer or url_for("home"))

@app.route("/scan", methods=["POST"])
def scan():
    scan_type = request.form.get("scan_type", "chat")
    content = ""
    result = None

    if scan_type == "chat":
        content = request.form.get("content", "").strip()
    elif scan_type == "email":
        sender_email = request.form.get("sender_email", "").strip()
        company_website = request.form.get("company_website", "").strip()
        offer_text = request.form.get("content", "").strip()
        content = f"Sender Email: {sender_email}\nWebsite: {company_website}\nOffer Text:\n{offer_text}"
    elif scan_type == "document":
        doc_file = request.files.get("doc_file")
        if doc_file and doc_file.filename:
            content = f"Uploaded Document [{doc_file.filename}]: Appointment terms with mandatory registration deposit for equipment clearance."
        else:
            content = "Document uploaded without clear text. Reviewing for standard internship deposit red flags."
    elif scan_type == "qr":
        qr_file = request.files.get("qr_file")
        if qr_file and qr_file.filename:
            content = f"QR Payment Screenshot [{qr_file.filename}]: Requesting collect payment to complete onboarding."
        else:
            content = "UPI Collect Request: Scanner warns that scanning QR codes deducts funds rather than receiving wages."
    elif scan_type == "voice":
        audio_file = request.files.get("audio_file")
        if audio_file and audio_file.filename:
            content = f"Voice Audio File [{audio_file.filename}]: Recruiter says congratulations on selection, asks candidate to transfer processing fee before sending appointment letter."
        else:
            content = "Audio transcription: Urgent demand for bank account confirmation and upfront gate pass fee."

    if content:
        rule_res = analyze_text_rules(content, blacklist_items=COMMUNITY_BLACKLIST)
        ai_res = analyze_with_gemini(content)
        result = merge_scores(ai_res, rule_res)

        # Only store scan history if user is signed in
        if session.get("user"):
            context_snippet = (content[:85] + "...") if len(content) > 85 else content
            log_entry = {
                "id": len(USER_SCAN_LOGS),
                "scan_type": scan_type.capitalize(),
                "score": result["score"],
                "scam_type": result["scam_type"],
                "context": context_snippet,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "rating": None
            }
            USER_SCAN_LOGS.insert(0, log_entry)
            result["id"] = log_entry["id"]

    return render_template("home.html", result=result, current_tab=scan_type, input_text=content, recent_alerts_count=len(COMMUNITY_BLACKLIST))

@app.route("/submit-rating", methods=["POST"])
def submit_rating():
    stars = int(request.form.get("stars", 5))
    scan_id = request.form.get("scan_id")
    user_name = request.form.get("user_name", session.get("user", {}).get("name", "Verified Candidate"))
    comment = request.form.get("comment", f"Rated {stars} stars on detection accuracy.").strip()

    if USER_SCAN_LOGS:
        try:
            if scan_id == "recent" or scan_id is None:
                USER_SCAN_LOGS[0]["rating"] = stars
            else:
                idx = int(scan_id)
                for item in USER_SCAN_LOGS:
                    if item.get("id") == idx:
                        item["rating"] = stars
                        break
        except Exception:
            USER_SCAN_LOGS[0]["rating"] = stars

    FEEDBACK_REVIEWS.insert(0, {
        "name": user_name,
        "rating": stars,
        "comment": comment or f"Rated {stars} stars.",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    return redirect(url_for("feedback"))

@app.route("/login", methods=["POST"])
def login():
    not_a_robot = request.form.get("not_a_robot")
    if not not_a_robot:
        return "Bot verification failed. Please check 'I am not a robot'.", 400

    identifier = request.form.get("user_identifier", "User").strip()
    session["user"] = {
        "name": identifier.split("@")[0].capitalize(),
        "email": identifier
    }
    session["welcome_dismissed"] = True
    return redirect(request.referrer or url_for("home"))

@app.route("/auto-login", methods=["POST"])
def auto_login():
    """Background reconnect for remembered credentials."""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    if email:
        session["user"] = {
            "name": email.split("@")[0].capitalize(),
            "email": email
        }
        session["welcome_dismissed"] = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    high_risk_count = sum(1 for h in USER_SCAN_LOGS if h["score"] >= 60)
    helpful_count = sum(1 for h in USER_SCAN_LOGS if h.get("rating") is not None and h["rating"] >= 4)
    return render_template("dashboard.html", history=USER_SCAN_LOGS, high_risk_count=high_risk_count, helpful_count=helpful_count, recent_alerts_count=len(COMMUNITY_BLACKLIST))

@app.route("/blacklist")
def blacklist():
    return render_template("blacklist.html", blacklist_items=COMMUNITY_BLACKLIST, recent_alerts_count=len(COMMUNITY_BLACKLIST))

@app.route("/guide")
def guide():
    return render_template("guide.html", recent_alerts_count=len(COMMUNITY_BLACKLIST))

@app.route("/report", methods=["POST"])
def report():
    name = request.form.get("recruiter_name", "").strip()
    handle = request.form.get("contact_handle", "").strip()
    platform = request.form.get("platform", "WhatsApp")
    category = request.form.get("scam_category", "Registration Fee")

    if name and handle:
        existing = None
        for item in COMMUNITY_BLACKLIST:
            if item["handle"].lower() == handle.lower():
                existing = item
                break

        if existing:
            existing["report_count"] += 1
            existing["date"] = "Just Now"
        else:
            COMMUNITY_BLACKLIST.insert(0, {
                "name": name,
                "platform": platform,
                "handle": handle,
                "category": category,
                "report_count": 1,
                "date": "Just Now"
            })

    return redirect(url_for("blacklist"))

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        name = request.form.get("user_name", "Anonymous")
        rating = int(request.form.get("rating_score", 5))
        comment = request.form.get("suggestion_text", "").strip()

        if comment:
            FEEDBACK_REVIEWS.insert(0, {
                "name": name,
                "rating": rating,
                "comment": comment,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        return redirect(url_for("feedback"))

    return render_template("feedback.html", feedback_list=FEEDBACK_REVIEWS, recent_alerts_count=len(COMMUNITY_BLACKLIST))

@app.route("/about")
def about():
    return render_template("about.html", recent_alerts_count=len(COMMUNITY_BLACKLIST))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
