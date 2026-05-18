import re
import streamlit as st
import easyocr
import numpy as np
from PIL import Image

# -----------------------------------------------------------------------------
# Configuration and Data Dictionaries
# All UI strings, outputs, and comments are strictly in English.
# -----------------------------------------------------------------------------

E_ADDITIVES = {
    "102": ("E102: Tartrazine", "Synthetic colorant. May cause allergic reactions."),
    "110": ("E110: Sunset Yellow", "Synthetic colorant linked to allergic reactions."),
    "124": ("E124: Ponceau 4R", "Synthetic colorant, potential allergen."),
    "129": ("E129: Allura Red", "Synthetic colorant, not recommended for children."),
    "132": ("E132: Indigotine", "Colorant that may cause gastric irritation."),
    "133": ("E133: Brilliant Blue", "Synthetic colorant, often avoided by sensitive individuals."),
    "160": ("E160: Carotenes", "Natural colorant. Safe for consumption."),
    "162": ("E162: Beetroot Red", "Natural colorant extracted from beetroot. Safe."),
    "200": ("E200: Sorbic Acid", "Preservative used to prevent mold and yeast growth."),
    "202": ("E202: Potassium Sorbate", "Widely used preservative, generally considered safe."),
    "220": ("E220: Sulfur Dioxide", "Preservative/sulfite. Can trigger asthma attacks in sensitive people."),
    "221": ("E221: Sodium Sulfite", "SULFITE preservative. May cause allergic reactions."),
    "250": ("E250: Sodium Nitrite", "Preservative commonly used in processed meats. Linked to increased cancer risks."),
    "262": ("E262: Sodium Acetate", "Acidity regulator. Excessive amounts may irritate the stomach."),
    "280": ("E280: Propionic Acid", "Preservative primarily used in bakery products."),
    "281": ("E281: Sodium Propionate", "Preservative used in bakery products. Excessive intake may irritate the stomach in sensitive people."),
    "300": ("E300: Ascorbic Acid", "Vitamin C. Safe, though extremely large doses may irritate the stomach."),
    "320": ("E320: Butylated Hydroxyanisole (BHA)", "Antioxidant. Considered a possible human carcinogen; best avoided."),
    "330": ("E330: Citric Acid", "Acidity regulator. Frequent consumption may damage tooth enamel."),
    "407": ("E407: Carrageenan", "Thickener. Associated with intestinal inflammation."),
    "450": ("E450: Diphosphates", "Emulsifier/stabilizer. High intake disrupts calcium-phosphate balance."),
    "471": ("E471: Mono- and Diglycerides", "Common emulsifier derived from fatty acids."),
    "472": ("E472: Fatty Acid Esters", "Emulsifier used to improve texture in baked goods."),
    "510": ("E510: Ammonium Chloride", "Flour treatment agent."),
    "621": ("E621: Monosodium Glutamate (MSG)", "Flavor enhancer. Can trigger headaches and allergic responses."),
    "951": ("E951: Aspartame", "Artificial sweetener. Best limited or avoided."),
    "952": ("E952: Cyclamate", "Artificial sweetener. Banned in some countries due to potential health concerns.")
}

# Hidden chemical names mapped directly to E-codes
HIDDEN_E_CODES = {
    "аскорбинова киселина": "300",
    "ascorbic acid": "300",

    "натриев глутамат": "621",
    "monosodium glutamate": "621",

    "натриев нитрит": "250",
    "sodium nitrite": "250",

    "карагенан": "407",
    "carrageenan": "407",

    "лимонена киселина": "330",
    "citric acid": "330",

    "дифосфат": "450",
    "diphosphate": "450",

    "калиев сорбат": "202",
    "potassium sorbate": "202",

    "натриев пропионат": "281",
    "sodium propionate": "281"
}

KEYWORDS_DATA = {
    "фосфат": ("Phosphates", "May negatively affect kidney function and bone health."),
    "phosphate": ("Phosphates", "May negatively affect kidney function and bone health."),
    "консерван": ("Preservatives", "Often contain synthetic nitrates or sulfites linked to health risks."),
    "preservative": ("Preservatives", "Often contain synthetic nitrates or sulfites linked to health risks."),
    "лактоза": ("Lactose", "May cause severe stomach discomfort and bloating in cases of intolerance."),
    "lactose": ("Lactose", "May cause severe stomach discomfort and bloating in cases of intolerance."),
    "палмово масло": ("Palm Oil", "High in saturated fats, which can negatively impact cardiovascular health."),
    "palm oil": ("Palm Oil", "High in saturated fats, which can negatively impact cardiovascular health."),
    "трансмазнини": ("Trans Fats", "Strongly associated with an increased risk of heart disease."),
    "trans fat": ("Trans Fats", "Strongly associated with an increased risk of heart disease."),
    "царевичен сироп": ("High Fructose Corn Syrup", "Highly processed sweetener linked to obesity.")
}

HEALTHY_ALTERNATIVES = [
    "☑ Instead of processed sausages or cold cuts, choose freshly baked chicken fillet seasoned with natural herbs.",
    "☑ Try homemade lentil stew cooked with fresh carrots, garlic, and spices.",
    "☑ Opt for boiled or poached eggs paired with fresh avocado and crisp, raw vegetables."
]

# -----------------------------------------------------------------------------
# Core Processing Functions
# -----------------------------------------------------------------------------

@st.cache_resource
def get_ocr_reader():
    # Explicitly configure gpu=False for CPU cloud setup
    return easyocr.Reader(['bg', 'en'], gpu=False)
def preprocess_ocr_text(raw_text):
    text = raw_text.replace("^", "л")
    text = text.replace("а(корбинова", "аскорбинова")
    text = text.replace("кез", "без")
    return text

def has_global_negation(text, keyword_type=""):
    if keyword_type == "preservative":
        negations = ["без изкуствени", "без консерванти", "no preservatives", "free from preservatives"]
        if "без" in text.lower() or "free" in text.lower():
            return True
        for neg in negations:
            if neg in text.lower():
                return True
    return False

def scan_for_e_numbers(text):
    found = {}
    cleaned_text = preprocess_ocr_text(text)
    padded_text = f" {cleaned_text} "
    
    for digits, (name, desc) in E_ADDITIVES.items():
        patterns = [
            f"E{digits}", f"Е{digits}",
            f"E {digits}", f"Е {digits}",
            f"E-{digits}", f"Е-{digits}"
        ]
        for pat in patterns:
            if re.search(re.escape(pat), padded_text, re.IGNORECASE):
                found[digits] = (name, desc)
                break
                    
    for kw, digits in HIDDEN_E_CODES.items():
        if re.search(re.escape(kw), padded_text, re.IGNORECASE):
            name, desc = E_ADDITIVES[digits]
            found[digits] = (name, f"{desc} *(Detected via hidden chemical name)*")
                
    return found

def scan_for_keywords(text):
    found = {}
    cleaned_text = preprocess_ocr_text(text).lower()
    
    for kw, (name, desc) in KEYWORDS_DATA.items():
        if kw in cleaned_text:
            if name == "Preservatives" and has_global_negation(cleaned_text, keyword_type="preservative"):
                continue  
            found[name] = desc
            
    return found

def generate_report_content(text, e_codes, keywords):
    lines = [
        "=== AI FOOD LABEL ANALYZER REPORT ===",
        "",
        "--- EXTRACTED LABEL TEXT ---",
        text,
        "",
        "--- DETECTED HARMFUL INGREDIENTS (E-CODES) ---"
    ]
    
    if e_codes:
        for name, desc in e_codes.values():
            lines.append(f"• {name}: {desc}")
    else:
        lines.append("✅ No dangerous E-numbers detected.")
        
    lines.extend([
        "",
        "--- DETECTED INGREDIENTS (BY KEYWORD) ---"
    ])
    
    if keywords:
        for name, desc in keywords.items():
            lines.append(f"• {name}: {desc}")
    else:
        lines.append("✅ No problematic ingredients detected by keywords.")
        
    lines.extend([
        "",
        "--- HEALTHY ALTERNATIVES TO PROCESSED FOODS ---"
    ])
    lines.extend(HEALTHY_ALTERNATIVES)
    
    return "\n".join(lines)

# -----------------------------------------------------------------------------
# Streamlit Application Layout
# -----------------------------------------------------------------------------

def show_terms_popup():
    @st.dialog("Terms and Conditions")
    def terms_dialog():
        st.markdown(
            """
            <div style="
                max-height: 420px;
                overflow-y: auto;
                padding-right: 10px;
                line-height: 1.55;
            ">
            
            # Disclaimer

            This application is created for educational and demonstration purposes only.

AI Food Label Analyzer uses OCR text recognition and a predefined list of ingredients, E-numbers, chemical names, and keywords. The analysis is generated automatically and may contain mistakes, especially if the photo is unclear, incomplete, blurry, dark, cropped, distorted, or incorrectly recognized by the OCR model.

This application is not a fully certified medical, nutritional, legal, or food safety tool. It is a school project and should be treated as an experimental educational application. The results are informative only and must not be considered professional advice.

The author does not guarantee the accuracy, clarity, completeness, truthfulness, objectivity, reliability, or relevance of any information generated or displayed by this application. The information may be incomplete, outdated, incorrectly interpreted, or technically inaccurate.

This application does not provide medical advice, allergy advice, nutritional advice, legal advice, or official food safety conclusions. It must not be used as a replacement for consultation with a doctor, nutritionist, allergist, pharmacist, food safety expert, lawyer, or any other qualified specialist.

The detected ingredients, warnings, and recommendations do not prove that a product is dangerous, unsafe, illegal, unhealthy, or unsuitable for every person. Some ingredients may be legally allowed and safe in permitted amounts, but may still be important for people with allergies, intolerances, medical conditions, or specific dietary restrictions.

The information provided by this application must not be used as the sole basis for health decisions, allergy-related decisions, dietary restrictions, medical conclusions, product safety conclusions, official complaints, legal claims, reports against manufacturers, or any other formal actions.

The author is not responsible for incorrect use of the application, incorrect interpretation of the results, technical errors, OCR recognition mistakes, incomplete analysis, wrong conclusions, or any direct or indirect consequences caused by decisions made based on the information provided by the application.

Users are fully responsible for verifying all information with the original product label, official product documentation, qualified specialists, and applicable legal or regulatory sources before making any decision.

Always read the original product label carefully before consuming any food. If you have allergies, food intolerances, medical conditions, dietary restrictions, or any doubts about a product, consult a qualified specialist before consuming it or making any decision based on the analysis.

All source code, structure, logic, design decisions, text content, and project materials are the exclusive intellectual property of the author, unless otherwise stated. Any unauthorized copying, modification, storage, publication, distribution, sublicensing, commercial use, reverse engineering, or use of this application or its parts without the author’s explicit permission is strictly prohibited.

Unauthorized use of this project may result in civil, administrative, and/or criminal liability under applicable law, including, where applicable, Article 172a of the Bulgarian Criminal Code concerning unlawful use of copyright-protected works without the consent of the rights holder.

By using this application, you confirm that you have read, understood, and accepted these Terms and Conditions. You also understand that the results are generated automatically, may not be fully accurate, and must be independently verified before being used in any practical, medical, legal, nutritional, or official context.
            </div>
            """,
            unsafe_allow_html=True
        )

        accepted = st.checkbox("I have read and accept the Terms and Conditions.")

        if st.button("Continue", type="primary", disabled=not accepted):
            st.session_state.terms_accepted = True
            st.rerun()

    terms_dialog()

def main():
    st.set_page_config(page_title="AI Food Label Analyzer", layout="centered")

    st.markdown(
        """
        <style>
        div[data-testid="stModal"] {
            backdrop-filter: blur(6px);
            background-color: rgba(0, 0, 0, 0.35);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if "terms_accepted" not in st.session_state:
        st.session_state.terms_accepted = False

    st.title("🍏 AI Food Label Analyzer")
    st.write("Extract text from food labels using EasyOCR and immediately detect hidden harmful ingredients, additives, and allergens.")
    st.markdown("---")

    if not st.session_state.terms_accepted:
        show_terms_popup()
        st.stop()

    with st.spinner("⏳ Pre-loading AI models into memory (First load takes 1-2 minutes)..."):
        reader = get_ocr_reader()
        
    tab_file, tab_cam = st.tabs(["📂 Upload File", "📷 Take Photo"])
    raw_image = None
    
    with tab_file:
        file_buffer = st.file_uploader("Upload a label image (JPG, PNG):", type=["jpg", "jpeg", "png"])
        if file_buffer:
            raw_image = Image.open(file_buffer)
            st.image(raw_image, caption="Uploaded Label Image", width="stretch")
            
    with tab_cam:
        cam_buffer = st.camera_input("Take a clear picture of the ingredient list:")
        if cam_buffer:
            raw_image = Image.open(cam_buffer)
            st.image(raw_image, caption="Captured Label Image", width="stretch")
            
    if raw_image and st.button("🔍 Analyze Label", type="primary"):
        
        with st.status("Processing label data...", expanded=True) as status:
            
            st.write("📷 Loading image data into memory...")
            img_array = np.array(raw_image.convert("RGB"))
            
            st.write("⏳ Extracting raw text via EasyOCR neural network...")
            # Reader is already safely loaded upfront, making this step fast and stable
            text_segments = reader.readtext(img_array, detail=0)
            full_extracted_text = " ".join(text_segments)
            
            st.write("⚙️ Preprocessing and filtering OCR noise...")
            
            st.write("🔬 Scanning for direct E-codes and hidden chemical names...")
            detected_e = scan_for_e_numbers(full_extracted_text)
            
            st.write("⚠️ Cross-referencing hazardous additives and allergen keywords...")
            detected_kw = scan_for_keywords(full_extracted_text)
            
            status.update(label="Analysis Complete!", state="complete", expanded=False)
            
        st.subheader("📜 Extracted Text from Label:")
        st.info(full_extracted_text if full_extracted_text.strip() else "No readable text detected.")
        
        st.subheader("⚠️ Detected Harmful Ingredients (E-codes):")
        if detected_e:
            for _, (name, desc) in detected_e.items():
                st.error(f"**{name}**\n\n{desc}")
        else:
            st.success("✅ No dangerous E-numbers detected.")
            
        st.subheader("⚠️ Detected Ingredients (by Keyword):")
        if detected_kw:
            for kw_name, kw_desc in detected_kw.items():
                st.warning(f"**{kw_name}** — {kw_desc}")
        else:
            st.success("✅ No problematic ingredients detected by keywords.")
            
        st.subheader("💡 Alternatives to Processed Foods:")
        for alt_text in HEALTHY_ALTERNATIVES:
            st.markdown(alt_text)
            
        st.markdown("---")
        
        report_data = generate_report_content(full_extracted_text, detected_e, detected_kw)
        st.download_button(
            label="📥 Download Report as .txt",
            data=report_data.encode("utf-8"),
            file_name="food_label_report.txt",
            mime="text/plain"
        )

if __name__ == "__main__":
    main()
