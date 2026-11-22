import os
import sys

# Test script for ScamGuard Gemini API Integration
# Run: python test_ai.py

from ai import analyze_with_gemini

test_samples = [
    "Dear candidate, congratulations! You have been selected for Amazon Data Entry intern. Earn 45,000/month. Please pay Rs 999 registration fee via PhonePe to hr@upi to get your offer letter.",
    "Hello sir, I am HR from TechCorp. Can you share your resume for the Software Trainee position?"
]

print("=== ScamGuard Gemini AI Test ===")
api_key = os.environ.get("GEMINI_API_KEY", "")
print(f"API Key configured: {'YES' if api_key else 'NO (running in mock/safety fallback mode)'}")

for idx, text in enumerate(test_samples, 1):
    print(f"\n--- Test Sample {idx} ---")
    print(f"Input: {text}")
    res = analyze_with_gemini(text)
    print(f"Result: {res}")
