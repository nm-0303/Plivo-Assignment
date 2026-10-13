"""
Plivo IVR demo: outbound call -> OTP auth -> language menu -> action menu.
 
Call flow (each box is one endpoint that returns Plivo XML):
  /answer          welcome message (once)        -> /otp
  /otp             ask for 4-digit OTP           -> /verify-otp
  /verify-otp      wrong: say so, back to /otp; right: -> /language
  /language        1 English, 2 Spanish           -> /language-choice
  /language-choice invalid: repeat; valid: -> /menu/<lang>
  /menu/<lang>     1 play audio, 2 talk to agent  -> /menu-choice/<lang>
  /menu-choice     1: <Play> then back to menu; 2: <Dial> associate; invalid: repeat
  /dial-status     after the Dial: if it failed, apologise and go back to the menu
No input at any prompt: "We did not receive any input" and the same prompt repeats.
"""
import os
from xml.sax.saxutils import escape
 
import plivo
from dotenv import load_dotenv
from flask import Flask, Response, render_template, request
 
load_dotenv()
 
AUTH_ID = os.getenv("PLIVO_AUTH_ID")
AUTH_TOKEN = os.getenv("PLIVO_AUTH_TOKEN")
PLIVO_NUMBER = os.getenv("PLIVO_NUMBER", "918035454161")
ASSOCIATE_NUMBER = os.getenv("ASSOCIATE_NUMBER", "912264236412")
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")  # your ngrok https URL
OTP = os.getenv("OTP", "1503")  # birthdate DDMM, hardcoded as the assignment asks
AUDIO_URL = os.getenv("AUDIO_URL", "https://s3.amazonaws.com/plivocloud/Trumpet.mp3")
 
app = Flask(__name__)
 
PROMPTS = {
    "en": {
        "lang": "en-US",
        "menu": "Press 1 to hear a short audio message. Press 2 to speak with a live associate.",
        "invalid": "Sorry, that is not a valid option.",
        "connecting": "Connecting you to an associate. Please hold.",
        "after_audio": "Returning to the menu.",
        "no_input": "We did not receive any input.",
        "dial_failed": "Sorry, our associate is not available right now.",
    },
    "es": {
        "lang": "es-ES",
        "menu": "Presione 1 para escuchar un mensaje de audio. Presione 2 para hablar con un asociado.",
        "invalid": "Lo siento, esa no es una opcion valida.",
        "connecting": "Conectando con un asociado. Por favor espere.",
        "after_audio": "Volviendo al menu.",
        "no_input": "No recibimos ninguna entrada.",
        "dial_failed": "Lo siento, nuestro asociado no esta disponible en este momento.",
    },
}
 
 
# ---------- XML helpers ----------
def xml(body):
    return Response(f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>{body}</Response>',
                    mimetype="application/xml")
 
 
def speak(text, language="en-US"):
    return f'<Speak voice="WOMAN" language="{language}">{escape(text)}</Speak>'
 
 
def redirect(path):
    return f'<Redirect method="POST">{BASE_URL}{path}</Redirect>'
 
 
def get_digits(action_path, num_digits, prompt_xml, timeout=10):
    # If the caller enters nothing, Plivo falls through to the next element (we redirect to repeat).
    return (f'<GetDigits action="{BASE_URL}{action_path}" method="POST" numDigits="{num_digits}" '
            f'timeout="{timeout}" retries="1" finishOnKey="#">{prompt_xml}</GetDigits>')
 
 
def digits():
    return (request.values.get("Digits") or "").strip()
 
 
def no_input(path, lang="en"):
    """Caller pressed nothing: say so and repeat the same prompt."""
    p = PROMPTS[lang]
    return speak(p["no_input"], p["lang"]) + redirect(path)
 
 
# ---------- outbound call ----------
def make_call(to_number):
    client = plivo.RestClient(AUTH_ID, AUTH_TOKEN)
    return client.calls.create(
        from_=PLIVO_NUMBER,
        to_=to_number,
        answer_url=f"{BASE_URL}/answer",
        answer_method="POST",
    )
 
 
@app.get("/")
def index():
    return render_template("index.html", result=None)
 
 
@app.post("/call")
def call():
    to_number = request.form.get("to", "").strip().lstrip("+")
    if not to_number.isdigit():
        return render_template("index.html", result="Enter the number with country code, digits only, e.g. 919876543210"), 400
    try:
        resp = make_call(to_number)
        result = f"Call started to +{to_number}. Request UUID: {resp.request_uuid}"
    except Exception as e:  # show Plivo's error message on the page instead of crashing
        result = f"Call failed: {e}"
    return render_template("index.html", result=result)
 
 
# ---------- IVR flow ----------
@app.route("/answer", methods=["GET", "POST"])
def answer():
    # Welcome plays once, when the call is answered. Retries go to /otp, which skips it.
    return xml(speak("Welcome to InspireWorks.") + redirect("/otp"))
 
 
@app.route("/otp", methods=["GET", "POST"])
def otp():
    prompt = speak("Please enter your 4 digit O T P.")
    return xml(get_digits("/verify-otp", 4, prompt) + no_input("/otp"))
 
 
@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    entered = digits()
    app.logger.info("OTP entered: %s", entered)
    if not entered:
        return xml(no_input("/otp"))
    if entered == OTP:
        return xml(speak("Thank you. You are verified.") + redirect("/language"))
    return xml(speak("Incorrect O T P. Please try again.") + redirect("/otp"))
 
 
@app.route("/language", methods=["GET", "POST"])
def language():
    prompt = (speak("For English, press 1.", "en-US")
              + speak("Para espanol, presione 2.", "es-ES"))
    return xml(get_digits("/language-choice", 1, prompt) + no_input("/language"))
 
 
@app.route("/language-choice", methods=["GET", "POST"])
def language_choice():
    choice = digits()
    if not choice:
        return xml(no_input("/language"))
    if choice == "1":
        return xml(redirect("/menu/en"))
    if choice == "2":
        return xml(redirect("/menu/es"))
    return xml(speak(PROMPTS["en"]["invalid"]) + redirect("/language"))
 
 
def menu_xml(lang):
    """The Level 2 menu prompt. Reused inline after the audio so the menu always comes back."""
    lang = lang if lang in PROMPTS else "en"
    p = PROMPTS[lang]
    return (get_digits(f"/menu-choice/{lang}", 1, speak(p["menu"], p["lang"]))
            + no_input(f"/menu/{lang}", lang))
 
 
@app.route("/menu/<lang>", methods=["GET", "POST"])
def menu(lang):
    return xml(menu_xml(lang))
 
 
@app.route("/menu-choice/<lang>", methods=["GET", "POST"])
def menu_choice(lang):
    p = PROMPTS.get(lang, PROMPTS["en"])
    choice = digits()
    if not choice:
        return xml(no_input(f"/menu/{lang}", lang if lang in PROMPTS else "en"))
    if choice == "1":
        # Menu XML follows the <Play> directly in the same response (no extra Redirect hop).
        return xml(f"<Play>{escape(AUDIO_URL)}</Play>"
                   + speak(p["after_audio"], p["lang"]) + menu_xml(lang))
    if choice == "2":
        # action URL: when the dial ends (or fails), Plivo asks /dial-status what to do next,
        # so a failed transfer no longer just drops the call.
        return xml(speak(p["connecting"], p["lang"])
                   + f'<Dial callerId="{PLIVO_NUMBER}" timeout="30" '
                     f'action="{BASE_URL}/dial-status/{lang}" method="POST">'
                     f'<Number>{ASSOCIATE_NUMBER}</Number></Dial>')
    return xml(speak(p["invalid"], p["lang"]) + redirect(f"/menu/{lang}"))
 
 
@app.route("/dial-status/<lang>", methods=["GET", "POST"])
def dial_status(lang):
    """Plivo posts here after the <Dial> ends. DialStatus: completed, busy, failed, timeout, no-answer."""
    p = PROMPTS.get(lang, PROMPTS["en"])
    status = request.values.get("DialStatus", "")
    app.logger.info("Dial finished: status=%s hangup_cause=%s", status,
                    request.values.get("DialHangupCause"))
    if status == "completed":
        return xml("<Hangup/>")  # associate answered and the conversation ended normally
    return xml(speak(p["dial_failed"], p["lang"]) + redirect(f"/menu/{lang}"))
 
 
@app.route("/hangup", methods=["GET", "POST"])
def hangup():
    app.logger.info("Call ended: %s", dict(request.values))
    return "OK"
 
 
if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 5000)), debug=True)