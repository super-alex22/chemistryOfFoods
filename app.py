import re
import streamlit as st
import easyocr
import numpy as np
import time
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
    "301": ("E301: Sodium Ascorbate", "Antioxidant. Generally considered safe, but still an added food additive."),
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

    "калиев сорбат": "202",
    "potassium sorbate": "202",

    "натриев пропионат": "281",
    "sodium propionate": "281",
    "нитритна сол": "250",
    "нитрит": "250",
    "nitrite": "250",

    "дифосфат": "450",
    "дифосфати": "450",
    "diphosphate": "450",
    "diphosphates": "450",

    "аскорбат": "301",
    "натриев аскорбат": "301",
    "sodium ascorbate": "301",
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
    "царевичен сироп": ("High Fructose Corn Syrup", "Highly processed sweetener linked to obesity."),
        # Allergens and important food components
    "глутен": ("Gluten", "Common allergen. Important for people with gluten intolerance or celiac disease."),
    "gluten": ("Gluten", "Common allergen. Important for people with gluten intolerance or celiac disease."),
    "пшеница": ("Wheat", "Contains gluten and may be unsafe for people with wheat allergy or gluten intolerance."),
    "пшенично": ("Wheat", "Contains gluten and may be unsafe for people with wheat allergy or gluten intolerance."),
    "wheat": ("Wheat", "Contains gluten and may be unsafe for people with wheat allergy or gluten intolerance."),
    "whole grain flour": ("Wheat / Gluten", "May contain gluten and should be checked by people with gluten intolerance."),
    "refined flour": ("Wheat / Gluten", "May contain gluten and should be checked by people with gluten intolerance."),

    "соя": ("Soy", "Common allergen. Important for people with soy allergy or intolerance."),
    "соев": ("Soy", "Common allergen. Important for people with soy allergy or intolerance."),
    "соев лецитин": ("Soy Lecithin", "Soy-derived ingredient. Important for people with soy allergy."),
    "soy": ("Soy", "Common allergen. Important for people with soy allergy or intolerance."),
    "soy lecithin": ("Soy Lecithin", "Soy-derived ingredient. Important for people with soy allergy."),

    "мляко": ("Milk", "Common allergen. May be unsuitable for people with milk allergy or lactose intolerance."),
    "milk": ("Milk", "Common allergen. May be unsuitable for people with milk allergy or lactose intolerance."),
    "сухо мляко": ("Milk Powder", "Milk-derived ingredient. Important for people with milk allergy or lactose intolerance."),
    "milk powder": ("Milk Powder", "Milk-derived ingredient. Important for people with milk allergy or lactose intolerance."),
    "суроватка": ("Whey", "Milk-derived ingredient. May be unsuitable for people with milk allergy."),
    "whey": ("Whey", "Milk-derived ingredient. May be unsuitable for people with milk allergy."),

    "яйца": ("Eggs", "Common allergen. Important for people with egg allergy."),
    "яйчен": ("Eggs", "Common allergen. Important for people with egg allergy."),
    "egg": ("Eggs", "Common allergen. Important for people with egg allergy."),
    "eggs": ("Eggs", "Common allergen. Important for people with egg allergy."),

    "ядки": ("Nuts", "Common allergen. May cause serious allergic reactions in sensitive people."),
    "nuts": ("Nuts", "Common allergen. May cause serious allergic reactions in sensitive people."),
    "фъстъци": ("Peanuts", "Common allergen. May cause serious allergic reactions in sensitive people."),
    "peanuts": ("Peanuts", "Common allergen. May cause serious allergic reactions in sensitive people."),
    "бадеми": ("Almonds", "Tree nut allergen. Important for people with nut allergy."),
    "almonds": ("Almonds", "Tree nut allergen. Important for people with nut allergy."),
    "лешници": ("Hazelnuts", "Tree nut allergen. Important for people with nut allergy."),
    "hazelnuts": ("Hazelnuts", "Tree nut allergen. Important for people with nut allergy."),

    "сусам": ("Sesame", "Common allergen. Important for people with sesame allergy."),
    "sesame": ("Sesame", "Common allergen. Important for people with sesame allergy."),

    "горчица": ("Mustard", "Common allergen. Important for people with mustard allergy."),
    "mustard": ("Mustard", "Common allergen. Important for people with mustard allergy."),

    "риба": ("Fish", "Common allergen. Important for people with fish allergy."),
    "fish": ("Fish", "Common allergen. Important for people with fish allergy."),
    "ракообразни": ("Crustaceans", "Common allergen. Important for people with seafood allergy."),
    "crustaceans": ("Crustaceans", "Common allergen. Important for people with seafood allergy."),

    "сулфити": ("Sulfites", "May trigger allergic reactions or asthma symptoms in sensitive people."),
    "sulfites": ("Sulfites", "May trigger allergic reactions or asthma symptoms in sensitive people."),
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
    return easyocr.Reader(
        ['bg', 'en'],
        gpu=False,
        model_storage_directory="easyocr_models",
        download_enabled=False
    )
def preprocess_image_for_ocr(image):
    image = image.convert("RGB")

    width, height = image.size
    image = image.resize((width * 2, height * 2))

    import PIL.ImageOps as ImageOps
    import PIL.ImageEnhance as ImageEnhance
    import PIL.ImageFilter as ImageFilter

    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(1.8)
    image = ImageEnhance.Sharpness(image).enhance(2.0)
    image = image.filter(ImageFilter.SHARPEN)

    return image
def preprocess_ocr_text(raw_text):
    text = raw_text.lower()

    replacements = {
        "^": "л",
        "а(корбинова": "аскорбинова",
        "кез": "без",

        # Common Bulgarian OCR mistakes from food labels
        "хранмтелни": "хранителни",
        "стойности": "стойности",
        "нерпйна": "енергийна",
        "отсвинскомесо": "от свинско месо",
        "свинсюо": "свинско",
        "месо": "месо",

        # Nitrite / sodium nitrite
        "нитритна": "нитритна",
        "нитpитна": "нитритна",
        "нuтритна": "нитритна",
        "нитритна сол": "нитритна сол",
        "матриев": "натриев",
        "maтриев": "натриев",
        "maтpиев": "натриев",
        "маtриев": "натриев",
        "натpиев": "натриев",
        "натриев #ифи": "натриев нитрит",
        "натриев ифи": "натриев нитрит",
        "натриев нити": "натриев нитрит",
        "натриев нитри": "натриев нитрит",

        # Diphosphates
        "дюфосфати": "дифосфати",
        "дюфосфат": "дифосфат",
        "диюфосфати": "дифосфати",
        "дuфосфати": "дифосфати",
        "дlфосфати": "дифосфати",

        # Ascorbate
        "асюорбат": "аскорбат",
        "асюор6ат": "аскорбат",
        "асюорбат": "аскорбат",
        "аchoорбат": "аскорбат",
        "аcюорбат": "аскорбат",
        "aскорбат": "аскорбат",

        # Gluten / lactose
        "лутен": "глутен",
        "глyтен": "глутен",
        "глутен": "глутен",
        "лктоза": "лактоза",
        "илктоза": "лактоза",
        "и лктоза": "и лактоза",
        "без лутен": "без глутен",
        "бе [лутен": "без глутен",
        "бе глутен": "без глутен",

        # Preservative
        "консервант": "консервант",
        "юонсервант": "консервант",
        "ноисервант": "консервант",
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    return text

def has_global_negation(text, keyword_type=""):
    lower = text.lower()

    if keyword_type == "preservative":
        negations = ["без изкуствени", "без консерванти", "no preservatives", "free from preservatives"]
        return any(neg in lower for neg in negations)

    if keyword_type == "gluten":
        negations = ["без глутен", "no gluten", "gluten free", "gluten-free"]
        return any(neg in lower for neg in negations)

    if keyword_type == "lactose":
        negations = ["без лактоза", "no lactose", "lactose free", "lactose-free"]
        return any(neg in lower for neg in negations)

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

            if name in ["Gluten", "Wheat", "Wheat / Gluten"] and has_global_negation(cleaned_text, keyword_type="gluten"):
                continue

            if name == "Lactose" and has_global_negation(cleaned_text, keyword_type="lactose"):
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
        # --- Initialize multi-step session states ---
        if "terms_step" not in st.session_state:
            st.session_state.terms_step = 1
        if "timer_done" not in st.session_state:
            st.session_state.timer_done = False

        # --- STEP 1: The Massive Disclaimer Document ---
        if st.session_state.terms_step == 1:
            st.markdown(
                """
                <div style="
                    max-height: 380px;
                    overflow-y: auto;
                    padding-right: 10px;
                    line-height: 1.55;
                ">
                <h2>Disclaimer</h2>
                <p>This application, including its source code, user interface, internal logic, text content, structure, design decisions, databases, ingredient lists, keyword lists, reports, and all related project materials, is created for educational and demonstration purposes only.</p>
                <p>AI Food Label Analyzer is not a certified, approved, official, medical, nutritional, allergy-related, legal, regulatory, or food safety tool. It is an experimental school project. It must not be treated as a professional system, official source, medical device, diagnostic tool, legal instrument, food safety authority, or certified product evaluation service.</p>
                <p>The application uses OCR text recognition and a predefined list of ingredients, E-numbers, chemical names, and keywords. The analysis is generated automatically and may contain errors, omissions, distortions, false positives, false negatives, incomplete results, outdated information, or incorrect interpretations. Such errors may be caused by blurry photos, unclear labels, poor lighting, cropped images, damaged packaging, unusual fonts, OCR limitations, spelling differences, language differences, technical limitations, or limitations of the predefined database.</p>
                <p>The author does not guarantee, under any circumstances, the accuracy, completeness, clarity, truthfulness, objectivity, reliability, legality, relevance, timeliness, medical correctness, nutritional correctness, or practical usefulness of any information generated, displayed, stored, downloaded, or suggested by this application.</p>
                <p>The information provided by this application is strictly informational and educational. It must not be used as the sole or primary basis for medical decisions, allergy-related decisions, dietary restrictions, food consumption decisions, health conclusions, product safety conclusions, official complaints, legal claims, reports against manufacturers, disputes with sellers, insurance claims, regulatory submissions, or any other formal, legal, medical, commercial, or administrative action.</p>
                <p>This application does not provide medical advice, allergy advice, nutritional advice, legal advice, consumer protection advice, product safety certification, or official interpretation of food labels. Users must consult a qualified doctor, allergist, nutritionist, pharmacist, food safety specialist, lawyer, or other competent professional before making any decision that may affect health, safety, legal rights, financial interests, or official actions.</p>
                <p>The detected ingredients, warnings, descriptions, and recommendations do not prove that any product is dangerous, unsafe, illegal, unhealthy, misleading, defective, incorrectly labeled, unsuitable for consumption, or harmful to any specific person. Some ingredients may be legally permitted and safe in regulated amounts, while still being relevant for people with allergies, intolerances, medical conditions, dietary restrictions, or personal preferences.</p>
                <p>The author accepts no responsibility or liability for any direct, indirect, accidental, incidental, consequential, material, immaterial, medical, nutritional, legal, financial, emotional, reputational, academic, or other damage resulting from the use, misuse, inability to use, interpretation, misinterpretation, copying, modification, distribution, storage, or reliance on this application or any information produced by it.</p>
                <p>The user is fully and exclusively responsible for verifying all information with the original product label, official product documentation, manufacturer information, qualified specialists, and applicable legal or regulatory sources before making any decision. If there is any doubt, the information generated by this application must be considered unreliable until independently verified.</p>
                <h2>AGE RESTRICTION</h2>
                <p>This application is strictly prohibited for use by persons under the age of 18.</p>
                <p>By accessing or using this application, the user confirms that they are at least 18 years old and have full legal capacity to accept these Terms and Conditions.</p>
                <p>Any access, use, copying, modification, distribution, storage, publication, or interaction with this application by a person under the age of 18 is strictly unauthorized and prohibited.</p>
                <p>The author accepts no responsibility or liability for any use of this application by minors or by persons who are not legally allowed to accept these Terms and Conditions.</p>
                <p>If you are under 18 years of age, you must immediately stop using this application.</p>
                <h2>LEGAL CAPACITY, SUPERVISION, AND RESTRICTED USE</h2>
                <p>This application is not intended for use by persons who do not have the legal capacity, mental capacity, or practical ability to fully read, understand, accept, and comply with these Terms and Conditions.</p>
                <p>Persons who are legally incapacitated, partially incapacitated, under guardianship, under legal supervision, or otherwise unable to fully understand the nature, purpose, limitations, risks, and consequences of using this application are strictly prohibited from using it without the direct permission, control, and supervision of a legally responsible adult, guardian, caregiver, teacher, or other authorized responsible person.</p>
                <p>Persons whose medical, psychological, cognitive, emotional, or other condition may affect their ability to understand the information provided by this application, evaluate its limitations, verify the results, or make safe and responsible decisions based on it, must not use this application without appropriate supervision and support.</p>
                <p>The author does not verify and is not responsible for verifying the user’s age, identity, legal capacity, mental capacity, medical condition, psychological condition, guardianship status, permissions, intentions, or ability to understand these Terms and Conditions.</p>
                <p>Any use of this application by a person who lacks the required legal capacity, mental capacity, understanding, permission, or supervision is strictly unauthorized and is performed entirely at the risk and responsibility of the user and, where applicable, their parent, guardian, caregiver, supervisor, teacher, or other legally responsible person.</p>
                <p>The author accepts no responsibility or liability for any consequences, damage, misunderstanding, misuse, wrong conclusions, unsafe decisions, emotional distress, health-related decisions, legal actions, or other results caused by the use of this application by persons who are not legally or practically able to use it responsibly and independently.</p>
                <p>If you do not fully understand these Terms and Conditions, if you are not legally allowed to accept them, or if you require supervision to use digital tools safely and responsibly, you must immediately stop using this application unless you are under appropriate supervision by a legally responsible person.</p>
                <h2>FALSE INFORMATION AND MISREPRESENTATION</h2>
                <p>The user confirms that any information, statements, files, images, materials, or claims provided during the use of this application must be lawful, truthful, accurate, and not misleading.</p>
                <p>Providing false, misleading, fabricated, manipulated, unlawful, or intentionally incorrect information, including false statements about age, identity, permissions, ownership, authorship, intended use, or legal rights, is strictly prohibited.</p>
                <p>Any attempt to misrepresent facts, submit manipulated materials, bypass restrictions, falsely claim permission, falsely claim ownership, or use this application for misleading, unlawful, harmful, abusive, or fraudulent purposes may result in civil, administrative, and/or criminal liability under applicable law.</p>
                <p>The author accepts no responsibility or liability for any false, misleading, unlawful, manipulated, or unauthorized information, material, statement, file, image, claim, or action submitted or performed by any user.</p>
                <p>The user is fully and exclusively responsible for the truthfulness, legality, accuracy, and consequences of any information, material, statement, claim, file, image, or action connected with their use of this application.</p>
                <h2>PRIVACY AND USER-PROVIDED MATERIALS</h2>
                <p>Users are responsible for ensuring that any uploaded image, file, or material does not contain personal data, confidential information, private documents, faces, addresses, phone numbers, payment details, medical information, or any other sensitive information.</p>
                <p>The author is not responsible for any personal, confidential, private, sensitive, or third-party information uploaded, displayed, processed, stored, copied, or shared by the user through this application.</p>
                <p>Users must not upload materials that they do not have the right to use, process, or share.</p>
                <p>Any uploaded material is provided entirely at the user’s own risk and responsibility.</p>
                <h2>PROHIBITED CONTENT AND ILLEGAL MATERIALS</h2>
                <p>The use of this application for uploading, processing, storing, displaying, distributing, sharing, generating, modifying, or transmitting adult content, pornographic content, sexually explicit content, obscene material, exploitative material, violent sexual material, illegal material, or any content involving minors in a sexual or exploitative context is strictly prohibited.</p>
                <p>Users must not upload or process any image, file, text, or material that is unlawful, abusive, harmful, threatening, defamatory, discriminatory, exploitative, pornographic, sexually explicit, violent, invasive of privacy, or otherwise inappropriate for an educational school project.</p>
                <p>Any attempt to use this application for adult content, pornographic content, sexually explicit material, exploitation, harassment, abuse, illegal distribution, or any other unlawful purpose is strictly unauthorized and may result in civil, administrative, and/or criminal liability under applicable law.</p>
                <p>The author accepts no responsibility or liability for any prohibited, illegal, harmful, adult, pornographic, sexually explicit, exploitative, abusive, or unauthorized content uploaded, submitted, processed, stored, distributed, or shared by any user.</p>
                <p>Where required or permitted by applicable law, any suspected illegal content, unlawful activity, exploitation, abuse, or serious misuse of this application may be reported to the relevant local authorities, law enforcement bodies, hosting providers, platform administrators, school administration, or other competent organizations.</p>
                <p>If you intend to upload, process, distribute, or use any adult, pornographic, sexually explicit, illegal, exploitative, harmful, or unauthorized material, you must immediately stop using this application.</p>
                <h2>INTELLECTUAL PROPERTY</h2>
                <p>All intellectual property rights related to this application belong exclusively to the author, unless otherwise stated. This includes, but is not limited to, the source code, logic, structure, databases, text content, visual presentation, project concept, reports, documentation, and educational materials.</p>
                <p>Any unauthorized copying, reproduction, modification, storage, publication, distribution, sublicensing, resale, commercial use, public demonstration, reverse engineering, extraction, adaptation, translation, redistribution, uploading, sharing, or use of this application or any part of it without the author’s explicit prior permission is strictly prohibited.</p>
                <p>Any unauthorized use, distribution, copying, modification, storage, publication, or exploitation of this project may result in civil, administrative, and/or criminal liability under applicable law, including copyright and intellectual property legislation of the Republic of Bulgaria, the European Union, and other applicable jurisdictions.</p>
                <h2>FINAL ACCEPTANCE</h2>
                <p>By continuing to use this application, you confirm that you have read, understood, and accepted these Terms and Conditions.</p>
                <p>You also confirm that you understand that the application may be inaccurate, incomplete, unclear, non-objective, outdated, misleading, or technically wrong, and that you agree not to use its results as official, medical, legal, allergy-related, nutritional, regulatory, commercial, administrative, or product safety evidence.</p>
                <p>You confirm that you are at least 18 years old, have full legal and mental capacity to accept these Terms and Conditions, and are not prohibited from using this application.</p>
                <p>Any violation of these Terms and Conditions, including unauthorized use by minors, false statements, misrepresentation, unlawful copying, unauthorized distribution, prohibited content, illegal material, adult content, pornographic content, sexually explicit material, or misuse of the application, may result in legal consequences under applicable civil, administrative, and/or criminal law.</p>
                <p>If you do not fully accept these Terms and Conditions, you must immediately stop using this application.</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            accepted = st.checkbox(
                "I confirm that I am at least 18 years old, have full legal and mental capacity to accept these Terms and Conditions, and have read, understood, and fully accepted all liability limitations, intellectual property restrictions, age restrictions, supervision requirements, privacy warnings, prohibited content rules, and possible legal consequences for unauthorized use, false information, illegal content, adult content, or misuse of this application."
            )

            if st.button("Next Step ➡️", type="primary", disabled=not accepted):
                st.session_state.terms_step = 2
                st.rerun()

        # --- STEP 2: The Final Warning Box with Countdown ---
        # --- STEP 2: The Final Warning Box with Countdown ---
        elif st.session_state.terms_step == 2:
            st.write("### 🚨 Critical Verification Check")
            
            # Custom container styling: Updated with criminal liability warning
            warning_box_html = """
            <div style="
                background-color: #FFEBEE; 
                border: 2px solid #C62828; 
                padding: 18px; 
                border-radius: 6px; 
                color: #B71C1C; 
                font-family: sans-serif;
                font-size: 14px;
                line-height: 1.5;
                margin-top: 10px;
                margin-bottom: 20px;
            ">
                <strong>ATTENTION REQUIRED:</strong><br>
                By clicking the button below, you officially declare that you have 
                <strong>fully read, completely understood, and irrevocably accepted</strong> 
                the provided Disclaimer. You acknowledge the technical errors of OCR 
                and confirm you hold total legal and mental capacity.<br><br>
                <strong>CRIMINAL LIABILITY NOTICE:</strong> Providing false statements, 
                manipulated images, or misrepresenting your age/legal capacity to bypass 
                system restrictions is strictly prohibited. Under applicable laws (including 
                the Criminal Code of the Republic of Bulgaria), intentionally submitting false 
                declarations or engaging in fraudulent misrepresentation may lead to severe civil, 
                administrative, and/or <strong>criminal prosecution</strong>.
            </div>
            """
            st.markdown(warning_box_html, unsafe_allow_html=True)

            timer_placeholder = st.empty()

            # Execute the 10-second wait loop if not completed yet
            if not st.session_state.timer_done:
                for seconds_left in range(10, 0, -1):
                    timer_placeholder.markdown(
                        f"<p style='color: #757575; font-style: italic;'>"
                        f"⏳ <em>Please read the text. The system is verifying your choice. "
                        f"The button unlocks in <strong>{seconds_left}</strong> seconds...</em></p>", 
                        unsafe_allow_html=True
                    )
                    time.sleep(1)
                st.session_state.timer_done = True
                st.rerun()

            # Clear placeholder and render navigation buttons in columns
            timer_placeholder.empty()

            col_back, col_continue = st.columns()
            
            with col_back:
                if st.button("⬅️ Back", use_container_width=True):
                    st.session_state.terms_step = 1
                    st.session_state.timer_done = False # Reset timer so it ticks again if they come back
                    st.rerun()
                    
            with col_continue:
                if st.button("Continue", type="primary", key="final_continue_btn", use_container_width=True):
                    st.session_state.terms_accepted = True
                    del st.session_state.terms_step
                    del st.session_state.timer_done
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

            st.write("📷 Loading and improving image data...")
            processed_image = preprocess_image_for_ocr(raw_image)
            img_array = np.array(processed_image)

            st.write("⏳ Loading OCR model...")
            reader = get_ocr_reader()

            st.write("⏳ Extracting raw text via EasyOCR neural network...")
            text_segments = reader.readtext(
                img_array,
                detail=0,
                paragraph=True,
                decoder="beamsearch",
                contrast_ths=0.05,
                adjust_contrast=0.7,
                text_threshold=0.5,
                low_text=0.3
            )
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
