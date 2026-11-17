"""
Routeur d'intention — étape 4/8.

Ce module implémente pour de vrai le garde-fou de périmètre décrit dans la
spécification du projet (non publiée) : "tu réponds UNIQUEMENT à des questions
concernant l'aéroport Agadir Al Massira [...] Si la question sort de
ce périmètre [...], réponds poliment que tu es spécialisé..."

⚠️ LIMITE ASSUMÉE : sans LLM branché (étape 5), on ne peut PAS juger le
sens d'une phrase — seulement la présence de mots-clés. C'est un filtre
imparfait :
- Faux négatif possible : une vraie question sur l'aéroport formulée
  sans aucun des mots-clés listés sera classée à tort "hors-sujet".
- Faux positif possible : une question hors-sujet qui contient par
  hasard un mot-clé ("le bus de mon quartier est en retard") sera
  classée à tort "dans le périmètre".
Ce n'est PAS un défaut de conception à corriger ici — c'est la limite
inhérente au tout premier filtre par mots-clés, en attendant l'étape 5
où le LLM pourra juger l'intention sémantiquement, bien plus fiable.
Cette version sert de filet de sécurité minimal fonctionnel, pas de
solution définitive.
"""

import re
import unicodedata
from enum import Enum
from typing import Optional

FLIGHT_NUMBER_PATTERN = re.compile(r"\b([A-Z]{2,3}\d{2,4})\b")

# Historical in-scope keyword list. Since the router switched to
# "documentary by default" (see classify), it is no longer used to decide the
# intent; it is kept for reference. Overly generic words ("ou", "où",
# "comment", "where", "what", "how", "which", "can i", "is there"...) have been
# removed because they matched almost any question.
IN_SCOPE_KEYWORDS = [
    # Salutations & assistance
    "bonjour", "salut", "bonsoir", "coucou", "hello", "hi", "hey", "salam", "merci", "aide", "help",
    "qui es tu", "qui es-tu", "présente toi", "presente toi", "information", "informations", "info", "infos",
    "question", "guide", "besoin", "quand", "prix", "combien",
    # Français
    "vol", "vols", "avion", "aérien", "aerien", "aéroport", "aeroport", "bagage", "bagages", "valise", "valises", "douane",
    "wifi", "wi-fi", "internet", "parking", "parkings", "stationnement", "restaurant", "restaurants", "café", "cafes",
    "boutique", "boutiques", "shop", "shopping", "porte", "portes", "embarquement", "passeport", "passeports", "visa", "visas",
    "taxi", "taxis", "bus", "navette", "navettes", "terminal", "terminaux",
    "arrivée", "arrivee", "arrivées", "arrivees", "départ", "depart", "départs", "departs", "check-in", "enregistrement",
    "correspondance", "onda", "agadir", "aga", "massira", "al massira", "duty free", "duty-free",
    "cip", "salon", "salons", "vip", "service", "services", "tarif", "tarifs",
    "horaire", "horaires", "contact", "contacts", "fret", "accès", "acces", "marché", "marches", "sécurité", "securite", "pmr", "assistance",
    "documents de voyage", "papier avant de prendre l'avion", "formalités", "formalites", "quitter le maroc",
    # Anglais
    "flight", "flights", "plane", "airplane", "airport", "luggage", "baggage", "bag", "bags", "customs", "gate", "gates", "boarding",
    "passport", "passports", "shuttle", "shuttles", "lounge", "lounges", "fee", "fees", "schedule", "schedules", "security", "car", "rental",
    # Arabe (formes courantes)
    "طيران", "رحلة", "رحلات", "مطار", "حقيبة", "حقائب", "أمتعة", "جمارك", "بوابة", "بوابات", "جواز", "جوازات",
    "تأشيرة", "حافلة", "أكادير", "المسيرة", "صالون", "خدمة", "خدمات", "موقف", "مواقف", "أسعار", "سعر", "مرحبا", "سلام", "شكرا",
]


IN_SCOPE_KEYWORDS.extend([
    # Common English airport-service questions, even when "airport" is omitted.
    "wheelchair", "restroom", "restrooms", "toilet", "toilets", "prayer room", "prayer rooms", "smoking area",
    "play area", "children's area", "currency exchange", "exchange office", "call center",
    "information desk", "check in", "rent a car",
    # Arabic keywords are kept as Unicode so they match actual Arabic queries.
    "مطار", "المطار", "أكادير", "المسيرة", "رحلة", "الرحلات", "طيران", "أمتعة", "الأمتعة",
    "حقائب", "الجمارك", "بوابة", "بوابات", "جواز", "جوازات", "تأشيرة", "حافلة", "الحافلات",
    "سيارة أجرة", "سيارة الأجرة", "سيارات الأجرة", "تاكسي", "طاكسي", "تعريفة", "موقف", "مواقف", "مواقف السيارات", "أركن",
    "الركن", "أسعار", "سعر", "الواي فاي", "الإنترنت", "مطاعم", "المطاعم", "متاجر", "المتاجر",
    "صلاة", "الصلاة", "قاعات الصلاة", "كرسي متحرك", "مراحيض", "الحمامات", "مساعدة طبية", "طبيب",
    "تسجيل الوصول", "الصعود", "المغادرة", "الوصول", "مرحبا", "مرحباً", "أهلا", "السلام عليكم",
    "الوحدة الطبية", "المساعدة الطبية", "طبيب", "الطبيب", "مراحيض", "الحمامات", "دورات المياه",
    "كرسي متحرك", "الكرسي المتحرك", "ذوي الحركة المحدودة", "منطقة ألعاب الأطفال", "ألعاب الأطفال",
    "مركز الاتصال", "مركز النداء", "رقم الهاتف", "أتصل", "الاتصال بالمطار", "معلومات", "حافلات المطار", "المقاهي", "المطاعم", "الصلاة", "قاعات الصلاة",
    "وثائق السفر", "وثائق", "أوراق السفر", "السفر من المغرب", "المطار",
])


class Intent(str, Enum):
    FLIGHT_STATUS = "flight_status"   # numéro de vol détecté -> connecteur AeroDataBox
    DOCUMENTARY = "documentary"        # question dans le périmètre -> RAG vectoriel
    OUT_OF_SCOPE = "out_of_scope"      # hors périmètre -> refus poli (spécification du projet (non publiée))
    GREETING = "greeting"              # salutations courtes -> réponse immédiate, sans RAG


GREETINGS = {
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "bonjour", "bonsoir", "salut", "coucou", "salam", "السلام عليكم", "مرحبا", "أهلا",
}
GREETINGS.update({"السلام عليكم", "مرحبا", "مرحباً", "أهلا"})


def extract_flight_number(text: str) -> Optional[str]:
    match = FLIGHT_NUMBER_PATTERN.search(text.upper())
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
# Arabic prefixes that can be attached to a word. They are never stripped
# blindly: a token matches if its ORIGINAL form or one of its prefix-less
# forms matches a keyword (so "وصول", "بوابة", "لوحة" keep their own form).
ARABIC_PREFIXES = ("وال", "بال", "لل", "ال", "و", "ب", "ل")
_ARABIC_CHAR_MAP = str.maketrans({"ٱ": "ا", "ة": "ه", "ى": "ي", "ـ": None})
_TOKEN_RE = re.compile(r"\w+")


def normalize(text: str) -> str:
    """Casefold, remove accents and Arabic diacritics, unify alif / ta marbuta."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    # Removing combining marks drops French accents, Arabic short vowels and
    # the hamza/madda carried by alif (أ إ آ -> ا).
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", stripped).translate(_ARABIC_CHAR_MAP)


def _is_arabic(token: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in token)


def token_forms(token: str) -> set[str]:
    """Original token plus its plausible base forms (the original is always kept)."""
    forms = {token}
    if _is_arabic(token):
        for prefix in ARABIC_PREFIXES:
            if token.startswith(prefix) and len(token) - len(prefix) >= 2:
                forms.add(token[len(prefix):])
    elif len(token) > 3 and token[-1] in "sx":
        forms.add(token[:-1])  # French/English plural
    return forms


def _keyword_forms(keyword: str) -> tuple:
    """A keyword phrase as a sequence of accepted forms, one set per token."""
    out = []
    for tok in _TOKEN_RE.findall(normalize(keyword)):
        forms = {tok}
        if _is_arabic(tok) and tok.startswith("ال") and len(tok) > 4:
            forms.add(tok[2:])
        elif not _is_arabic(tok) and len(tok) > 3 and tok[-1] in "sx":
            forms.add(tok[:-1])
        out.append(frozenset(forms))
    return tuple(out)


def _compile(keywords) -> list:
    return [k for k in {_keyword_forms(w) for w in keywords} if k]


def _matches(token_sets: list, compiled) -> bool:
    for phrase in compiled:
        n = len(phrase)
        for i in range(len(token_sets) - n + 1):
            if all(token_sets[i + j] & phrase[j] for j in range(n)):
                return True
    return False


def _token_sets(text: str) -> list:
    return [token_forms(t) for t in _TOKEN_RE.findall(normalize(text))]


# ---------------------------------------------------------------------------
# Rule vocabularies
# ---------------------------------------------------------------------------
# Live flight questions without a flight number: a flight noun AND a live-state
# marker (delay, cancellation, landing, status, gate assignment, "now").
FLIGHT_NOUNS = [
    "vol", "avion", "flight", "plane", "aircraft",
    "رحلة", "رحلات", "طائرة", "طيارة",
]
LIVE_FLIGHT_MARKERS = [
    # fr
    "retard", "retardé", "retardés", "retardée", "annulé", "annulés", "annulée", "annulation",
    "atterrit", "atterrir", "atterrissage", "à l'heure", "statut", "attribuée", "attribué",
    "maintenant", "actuellement", "en ce moment",
    # en
    "delay", "delayed", "delays", "cancelled", "canceled", "cancellation", "land", "lands", "landing",
    "landed", "on time", "status", "assigned", "now", "currently",
    # ar
    "تأخر", "تأخرت", "متأخر", "متأخرة", "تأخير", "ألغيت", "ملغاة", "إلغاء", "تهبط", "هبوط",
    "في موعدها", "حالة", "الآن", "حاليا",
]
# Explicit off-topic domains. Used only when the message has no airport anchor.
OFF_TOPIC_TERMS = [
    # cooking
    "recette", "recipe", "وصفة", "طريقة تحضير",
    # sport
    "football", "coupe du monde", "champions league", "world cup", "كرة القدم", "كأس العالم", "مباراة",
    # creative writing, translation, jokes, entertainment
    "poème", "poem", "قصيدة", "traduis", "traduire", "translate", "ترجم", "blague", "joke", "نكتة",
    # "film" alone is ambiguous ("film plastique" = luggage wrapping): only
    # entertainment phrasings are listed (changed after the held-out run).
    "regarder un film", "un bon film", "watch a movie", "good movie", "مشاهدة فيلم",
    "chanson", "song", "أغنية",
    # programming and homework
    "programmation", "programming", "python", "javascript", "برمجة", "devoirs", "homework",
    "lettre de motivation", "cover letter",
    # politics, finance
    "élection", "election", "انتخابات", "bitcoin", "crypto", "bourse", "stock market", "البورصة",
]
# Words that tie a message to the airport even if an off-topic term appears.
AIRPORT_ANCHORS = [
    "aéroport", "aérogare", "airport", "terminal", "مطار", "المحطة", "vol", "flight", "avion", "plane",
    "رحلة", "طائرة", "massira", "المسيرة", "onda", "aga",
]

_FLIGHT_NOUNS = _compile(FLIGHT_NOUNS)
_LIVE_MARKERS = _compile(LIVE_FLIGHT_MARKERS)
_OFF_TOPIC = _compile(OFF_TOPIC_TERMS)
_ANCHORS = _compile(AIRPORT_ANCHORS)
_GREETINGS = {normalize(g).strip(" .,!?…؛؟،") for g in GREETINGS}


def is_live_flight_question(text: str) -> bool:
    sets = _token_sets(text)
    return _matches(sets, _FLIGHT_NOUNS) and _matches(sets, _LIVE_MARKERS)


def classify(text: str) -> Intent:
    """Classify a message. Order of priority:
    1. flight number -> FLIGHT_STATUS;
    2. short greeting -> GREETING;
    3. flight noun + live-state marker -> FLIGHT_STATUS (no number needed);
    4. explicit off-topic domain and no airport anchor -> OUT_OF_SCOPE;
    5. otherwise DOCUMENTARY (default). /chat then applies a retrieval-distance
       threshold before any LLM call, so undocumented or off-topic questions get
       the "no information" reply instead of a generated answer.
    """
    if extract_flight_number(text):
        return Intent.FLIGHT_STATUS

    normalized = re.sub(r"\s+", " ", normalize(text)).strip(" \t\r\n.,!?…؛؟،")
    if normalized in _GREETINGS:
        return Intent.GREETING

    sets = _token_sets(text)
    if _matches(sets, _FLIGHT_NOUNS) and _matches(sets, _LIVE_MARKERS):
        return Intent.FLIGHT_STATUS

    if _matches(sets, _OFF_TOPIC) and not _matches(sets, _ANCHORS):
        return Intent.OUT_OF_SCOPE

    return Intent.DOCUMENTARY


OUT_OF_SCOPE_REPLIES = {
    "fr": "Je suis spécialisé sur l'aéroport Agadir Al Massira (vols, services, formalités de voyage). Peux-tu reformuler ta question dans ce cadre ?",
    "ar": "أنا متخصص فقط في مطار أكادير المسيرة (الرحلات، الخدمات، إجراءات السفر). هل يمكنك إعادة صياغة سؤالك في هذا الإطار؟",
    "en": "I'm specialized in the Agadir Al Massira airport (flights, services, travel formalities). Could you rephrase your question within that scope?",
}
OUT_OF_SCOPE_REPLIES["ar"] = "أنا متخصص في مطار أكادير المسيرة (الرحلات والخدمات وإجراءات السفر). أعد صياغة سؤالك بما يتعلق بهذا المطار من فضلك."


def out_of_scope_reply(lang: str) -> str:
    return OUT_OF_SCOPE_REPLIES.get(lang, OUT_OF_SCOPE_REPLIES["fr"])
