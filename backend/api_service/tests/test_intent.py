"""Unit tests for the intent router (app/routers/intent.py). No network.

Usage: python tests/test_intent.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.routers.intent import (  # noqa: E402
    IN_SCOPE_KEYWORDS,
    Intent,
    _compile,
    _matches,
    _token_sets,
    classify,
    normalize,
    token_forms,
)


def matches(text: str, keyword: str) -> bool:
    return _matches(_token_sets(text), _compile([keyword]))


def check(label: str, condition: bool) -> None:
    print(("OK   " if condition else "FAIL ") + label)
    if not condition:
        raise SystemExit(1)


print("--- Normalisation ---")
check("French accents removed", normalize("Aéroport À l'Heure") == "aeroport a l'heure")
check("Arabic diacritics removed", normalize("كُرْسِيًّا") == "كرسيا")
check("alif variants unified", normalize("أإآٱ") == "اااا")
check("ta marbuta unified", normalize("بوابة") == "بوابه")

print("--- Arabic prefixes: original form is always kept ---")
for word in ("وصول", "بوابة", "لوحة"):
    norm = normalize(word)
    check(f"{word}: original form kept", norm in token_forms(norm))
check("وصول matches the keyword الوصول", matches("أين قاعة وصول المسافرين؟", "الوصول"))
check("بوابة matches the keyword بوابة", matches("أين بوابة الصعود؟", "بوابة"))
check("لوحة matches the keyword لوحة", matches("أين لوحة الرحلات؟", "لوحة"))
check("بوابة does NOT match an unrelated keyword وابة-like stem", not matches("أين بوابة الصعود؟", "واب"))
check("بالمطار matches مطار", matches("هل يوجد صراف بالمطار؟", "مطار"))
check("للرحلات matches رحلات", matches("لوحة للرحلات", "رحلات"))
check("والمتاجر matches متاجر", matches("المطاعم والمتاجر", "متاجر"))
check("الموقف matches موقف", matches("ما سعة الموقف؟", "موقف"))

print("--- French plurals ---")
check("toilettes matches toilette", matches("Y a-t-il des toilettes ?", "toilette"))
check("vols matches vol", matches("Quels vols partent ?", "vol"))

print("--- Generic words removed ---")
for generic in ("ou", "où", "comment", "where", "what", "how"):
    check(f"'{generic}' not in IN_SCOPE_KEYWORDS", generic not in IN_SCOPE_KEYWORDS)

print("--- classify ---")
cases = [
    ("Bonjour", Intent.GREETING),
    ("مرحبا", Intent.GREETING),
    ("Is flight AT1234 on time?", Intent.FLIGHT_STATUS),
    ("Le vol est-il retardé ce soir ?", Intent.FLIGHT_STATUS),
    ("Which flights are cancelled now?", Intent.FLIGHT_STATUS),
    ("هل ألغيت الرحلة؟", Intent.FLIGHT_STATUS),
    ("Combien de bagages puis-je prendre sur un vol international ?", Intent.DOCUMENTARY),
    ("Where can I find a taxi?", Intent.DOCUMENTARY),
    ("هل يمكنني الاتصال بالإنترنت؟", Intent.DOCUMENTARY),
    ("Donne-moi une recette de couscous", Intent.OUT_OF_SCOPE),
    ("Write a poem about the sea", Intent.OUT_OF_SCOPE),
    ("Is there a film shown in the airport lounge?", Intent.DOCUMENTARY),
    ("Où faire filmer ma valise avec du film plastique ?", Intent.DOCUMENTARY),
    ("Peux-tu me conseiller un bon film ?", Intent.OUT_OF_SCOPE),
    ("Can you recommend a good movie?", Intent.OUT_OF_SCOPE),
]
for text, expected in cases:
    got = classify(text)
    check(f"{text!r} -> {expected.value} (got {got.value})", got == expected)

print("\nTOUS LES TESTS PASSENT.")
