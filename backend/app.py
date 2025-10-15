# backend/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps, ImageEnhance
import numpy as np
import pytesseract
import easyocr
from googletrans import Translator
import io

app = Flask(__name__)
CORS(app)

# Initialize EasyOCR reader for Nepali (Devanagari)
reader = easyocr.Reader(['ne'], gpu=False)  # set gpu=True if you have GPU
translator = Translator()

# ----------------------------
# Helpers: script counts & preprocessing
# ----------------------------
def count_devanagari_chars(text: str) -> int:
    return sum(1 for ch in text if '\u0900' <= ch <= '\u097F')

def count_sinhala_chars(text: str) -> int:
    return sum(1 for ch in text if '\u0D80' <= ch <= '\u0DFF')

def preprocess_image(pil_img: Image.Image, upscale_width=1600):
    """
    Basic preprocessing: convert to RGB, optionally upscale, convert to grayscale,
    enhance contrast. Returns PIL Image.
    """
    # Convert to RGB (handles PDFs / CMYK)
    img = pil_img.convert("RGB")

    # Upscale if small for better OCR
    w, h = img.size
    if w < upscale_width:
        scale = upscale_width / float(w)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)

    # Convert to grayscale and enhance contrast
    gray = ImageOps.grayscale(img)
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(1.3)  # tweak factor if needed

    # Optional binarization could be added later
    return gray

# ----------------------------
# Decide best OCR output
# ----------------------------
def run_hybrid_ocr(pil_img: Image.Image):
    """
    Runs EasyOCR (Nepali) and Tesseract (Sinhala & Nepali) and picks best output
    based on script character counts.
    Returns: (best_text, detected_language, engine_used, debug_outputs)
    """
    debug = {}

    # Preprocess (grayscale & resize)
    proc = preprocess_image(pil_img)

    # Convert for EasyOCR (numpy array, RGB required by EasyOCR)
    easy_img = np.array(pil_img.convert("RGB"))

    # 1) EasyOCR (Nepali / Devanagari)
    try:
        easy_result_list = reader.readtext(easy_img, detail=0, paragraph=True)
        easy_text = " ".join([t for t in easy_result_list if isinstance(t, str)])
    except Exception as e:
        easy_text = ""
        debug['easy_error'] = str(e)

    debug['easy_text'] = easy_text
    easy_dev_count = count_devanagari_chars(easy_text)
    easy_sin_count = count_sinhala_chars(easy_text)
    debug['easy_dev_count'] = easy_dev_count
    debug['easy_sin_count'] = easy_sin_count

    # 2) Tesseract Sinhala
    try:
        tesseract_sin_text = pytesseract.image_to_string(proc, lang='sin')
    except Exception as e:
        tesseract_sin_text = ""
        debug['tess_sin_error'] = str(e)

    debug['tess_sin_text'] = tesseract_sin_text
    tess_sin_dev_count = count_devanagari_chars(tesseract_sin_text)
    tess_sin_count = count_sinhala_chars(tesseract_sin_text)
    debug['tess_sin_dev_count'] = tess_sin_dev_count
    debug['tess_sin_count'] = tess_sin_count

    # 3) Tesseract Nepali (fallback)
    try:
        tesseract_nep_text = pytesseract.image_to_string(proc, lang='nep')
    except Exception as e:
        tesseract_nep_text = ""
        debug['tess_nep_error'] = str(e)

    debug['tess_nep_text'] = tesseract_nep_text
    tess_nep_dev_count = count_devanagari_chars(tesseract_nep_text)
    tess_nep_sin_count = count_sinhala_chars(tesseract_nep_text)
    debug['tess_nep_dev_count'] = tess_nep_dev_count
    debug['tess_nep_sin_count'] = tess_nep_sin_count

    # Scoring: prefer outputs with more script-specific chars
    candidates = [
        {"text": easy_text, "engine": "easyocr", "dev_count": easy_dev_count, "sin_count": easy_sin_count},
        {"text": tesseract_nep_text, "engine": "tesseract-nep", "dev_count": tess_nep_dev_count, "sin_count": tess_nep_sin_count},
        {"text": tesseract_sin_text, "engine": "tesseract-sin", "dev_count": tess_sin_dev_count, "sin_count": tess_sin_count},
    ]

    # For each candidate compute a score:
    # score_dev = number of Devanagari chars, score_sin = number of Sinhala chars
    # final_score = max(score_dev, score_sin) but also penalize if both zeros.
    for c in candidates:
        c['dev_score'] = c['dev_count']
        c['sin_score'] = c['sin_count']
        # primary_score: prefer strong script presence
        c['primary_score'] = max(c['dev_score'], c['sin_score'])
        # length fallback score
        c['length'] = len(c['text'].strip())

    # Pick candidate with highest primary_score; if tie or zero, pick largest length
    candidates_sorted = sorted(candidates, key=lambda x: (x['primary_score'], x['length']), reverse=True)
    best = candidates_sorted[0]

    # If best primary score is zero (no script chars detected), but length small, try fallback selection:
    if best['primary_score'] == 0:
        # choose candidate with max length
        best = max(candidates, key=lambda x: x['length'])

    chosen_text = best['text'].strip()
    engine_used = best['engine']

    # Determine detected language by script counts in chosen_text
    if count_devanagari_chars(chosen_text) > count_sinhala_chars(chosen_text):
        detected_lang = 'ne'
    elif count_sinhala_chars(chosen_text) > count_devanagari_chars(chosen_text):
        detected_lang = 'si'
    else:
        detected_lang = 'unknown'

    debug['candidates'] = candidates_sorted
    debug['chosen'] = {"engine": engine_used, "detected_lang": detected_lang, "length": len(chosen_text)}

    return chosen_text, detected_lang, engine_used, debug

# ----------------------------
# OCR extraction endpoint
# ----------------------------
@app.route("/extract", methods=["POST"])
def extract_text():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        # Load image via PIL
        img_stream = io.BytesIO(file.read())
        image = Image.open(img_stream)

        # Run hybrid OCR & selection
        text, detected_lang, engine_used, debug = run_hybrid_ocr(image)

        return jsonify({
            "text": text,
            "language": detected_lang,
            "engine": engine_used,
            "debug": debug  # include debug for development; remove in production
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------
# Translation endpoint (unchanged)
# ----------------------------
@app.route("/translate", methods=["POST"])
def translate_text():
    try:
        data = request.get_json()
        text = data.get("text", "")
        if not text:
            return jsonify({"error": "No text to translate"}), 400

        src_lang = 'auto'
        # if script detection returns a specific language, we can use it
        if any('\u0900' <= ch <= '\u097F' for ch in text):
            src_lang = 'ne'
        elif any('\u0D80' <= ch <= '\u0DFF' for ch in text):
            src_lang = 'si'

        translated = translator.translate(text, src=src_lang, dest="en")
        return jsonify({"translated": translated.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
