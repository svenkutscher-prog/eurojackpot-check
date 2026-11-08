"""Liest die aktuellen Eurojackpot-Gewinnzahlen von eurojackpot.de
und trägt sie in ziehungen.json ein. Nur Python-Standardbibliothek."""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

URLS = [
    "https://www.eurojackpot.de/brand/homepage/",
    "https://www.eurojackpot.de/gewinnauskunft/",
]
DATEI = Path(__file__).resolve().parent.parent / "ziehungen.json"
MUSTER = re.compile(
    r"(Dienstag|Freitag),?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s+"
    r"((?:\d{1,2}\s+){5})Eurozahlen\s+(\d{1,2})\s+(\d{1,2})",
    re.IGNORECASE,
)


def seite_laden(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (eurojackpot-check)",
        "Accept-Language": "de-DE,de;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def als_text(roh, scripts_entfernen):
    if scripts_entfernen:
        roh = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", roh, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", roh)
    return re.sub(r"\s+", " ", html.unescape(text))


def finden(text):
    for m in MUSTER.finditer(text):
        tag, monat, jahr = int(m[2]), int(m[3]), int(m[4])
        n = [int(x) for x in m[5].split()]
        e = [int(m[6]), int(m[7])]
        if (len(set(n)) == 5 and all(1 <= x <= 50 for x in n)
                and len(set(e)) == 2 and all(1 <= x <= 12 for x in e)):
            return {"date": f"{jahr:04d}-{monat:02d}-{tag:02d}", "n": sorted(n), "e": sorted(e)}
    return None


def main():
    ziehung = None
    for url in URLS:
        try:
            roh = seite_laden(url)
        except Exception as fehler:
            print(f"Konnte {url} nicht laden: {fehler}")
            continue
        for ohne_scripts in (True, False):
            ziehung = finden(als_text(roh, ohne_scripts))
            if ziehung:
                break
        if ziehung:
            print(f"Gefunden auf {url}: {ziehung}")
            break
        print(f"Keine Gewinnzahlen erkannt auf {url}. Textauszug:")
        print(als_text(roh, True)[:1500])

    if not ziehung:
        print("FEHLER: Gewinnzahlen nicht gefunden – evtl. wurde die Seite umgebaut.")
        sys.exit(1)

    daten = json.loads(DATEI.read_text(encoding="utf-8")) if DATEI.exists() else {"draws": []}
    draws = [d for d in daten.get("draws", []) if d.get("date") != ziehung["date"]]
    vorher = next((d for d in daten.get("draws", []) if d.get("date") == ziehung["date"]), None)
    if vorher == ziehung:
        print("Ziehung ist schon eingetragen.")
        return
    draws.append(ziehung)
    draws.sort(key=lambda d: d["date"], reverse=True)
    daten["draws"] = draws[:200]
    DATEI.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ziehungen.json aktualisiert.")


if __name__ == "__main__":
    main()
