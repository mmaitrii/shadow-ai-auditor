import streamlit as st
import spacy
import re
import urllib.request
import os

# Download and load the spaCy model robustly without subprocess or pip installer crashes
@st.cache_resource
def load_model():
    model_name = "en_core_web_sm"
    try:
        return spacy.load(model_name)
    except OSError:
        # Fallback: Download direct wheel file into cache if spacy model is absent
        url = "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"
        wheel_path = "en_core_web_sm.whl"
        if not os.path.exists(wheel_path):
            urllib.request.urlretrieve(url, wheel_path)
        os.system(f"python -m pip install {wheel_path}")
        return spacy.load(model_name)

# Safely load NLP model
try:
    nlp = load_model()
except Exception as e:
    st.error(f"Error loading NLP model: {e}")
    nlp = None

st.set_page_config(page_title="Shadow AI Privacy Auditor", layout="centered")

st.title("🛡️ Shadow AI Privacy Auditor")
st.write("Paste your text below before sending it to ChatGPT or Gemini. We will highlight sensitive data and provide a safe version.")

# 1. User Input
user_input = st.text_area("Text to audit:", height=150, placeholder="E.g., Volunteer ID VOL-4821 (Maria) missed her shift; SSN 123-45-6789. The project meeting is scheduled for 3:00 PM.")

# 2. Define Regex Patterns for structured data
patterns = {
    "Email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "Names & Contact Info"),
    "Phone": (r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "Names & Contact Info"),
    "SSN": (r"\b\d{3}-\d{2}-\d{4}\b", "Gov/Financial ID"),
    "Employee/Volunteer ID": (r"\b(?:EMP|VOL)-\d{4,}\b", "Employee/Volunteer Info"),
    "API Key / Password": (r"(?i)(?:password|api_key|bearer)\s*[:=]\s*([a-zA-Z0-9\-_]+)", "Passwords/API Keys"),
    "Confidential Keyword": (r"(?i)\b(strictly confidential|internal only)\b", "Confidential Org Info")
}

if st.button("Audit Text"):
    if not user_input.strip():
        st.warning("Please enter some text to audit.")
    else:
        findings = []
        redacted_text = user_input
        highlighted_text = user_input

        # Step A: Scan with ML Model (spaCy) for Names if available
        if nlp is not None:
            try:
                doc = nlp(user_input)
                for ent in doc.ents:
                    if ent.label_ == "PERSON":
                        findings.append({"text": ent.text, "category": "Names & Contact Info", "reason": "Contains a human name."})
                        redacted_text = redacted_text.replace(ent.text, "[NAME]")
                        highlighted_text = highlighted_text.replace(ent.text, f"<mark style='background-color: #ffcccc; color: red;'><b>{ent.text}</b></mark>")
            except Exception as e:
                st.warning("Model scanning encountered a minor issue; relying on pattern detection.")

        # Step B: Scan with Regex for strict patterns
        for label, (pattern, category) in patterns.items():
            matches = re.finditer(pattern, user_input)
            for match in matches:
                found_text = match.group(0)
                findings.append({"text": found_text, "category": category, "reason": f"Matches format for {label}."})
                redacted_text = redacted_text.replace(found_text, f"[{label.upper()}]")
                highlighted_text = highlighted_text.replace(found_text, f"<mark style='background-color: #ffcccc; color: red;'><b>{found_text}</b></mark>")

        # 3. Display Results
        if not findings:
            st.success("✅ No sensitive information detected. This text looks safe to share!")
            st.info("Safe Text:\n\n" + user_input)
        else:
            st.error("⚠️ Sensitive Information Detected!")
            
            # Show Findings Explanation
            st.subheader("What we found:")
            for item in findings:
                st.write(f"- **{item['text']}** ({item['category']}): {item['reason']}")
            
            # Show Visual Highlight
            st.subheader("Visual Preview:")
            st.markdown(highlighted_text, unsafe_allow_html=True)
            
            # Show Safe Redacted Version
            st.subheader("Safe Version to Copy:")
            st.code(redacted_text, language="text")
            
            st.caption("Notice how safe parts of your text (like standard meeting times) were completely ignored and left intact!")
