import requests
import json
import time
import string

api_url = "https://www.globalomnium.com/Direcciones/DameMunicipiosWebs"

alphabet = (
    string.ascii_lowercase + 
    string.ascii_uppercase + 
    "áéíóúñÁÉÍÓÚÑ"
)

all_items = {}

def fetch_localities(filter_text):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(api_url, params={"filtro": filter_text}, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("items", [])
    except Exception as e:
        print(f"Error con filtro '{filter_text}': {e}")
    return []

print("--- Iniciando Volcado Exhaustivo de Localidades ---")

# Warm-up
warmup = ["A", "E", "I", "O", "U", "Va", "Val"]
print("Realizando calentamiento de API...")
for w in warmup:
    fetch_localities(w)
    time.sleep(0.2)

# Fuerza bruta caracteres individuales
print("\nProbando caracteres individuales...")
for char in alphabet:
    items = fetch_localities(char)
    if items:
        print(f"Filtro '{char}': +{len(items)} resultados")
        for item in items:
            all_items[item["text"].upper()] = item["url"]
    time.sleep(0.1)

# Combinaciones comunes
print("\nProbando combinaciones comunes de 2 letras...")
common_prefixes = ["va", "Va", "VAL", "Val", "ma", "Ma", "ca", "Ca", "sa", "Sa"]
for pref in common_prefixes:
    items = fetch_localities(pref)
    if items:
        print(f"Filtro '{pref}': +{len(items)} resultados")
        for item in items:
            all_items[item["text"].upper()] = item["url"]
    time.sleep(0.1)

# Guardado
with open("localities_dump.json", "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False, indent=4)

print(f"\n--- Proceso Completado ---")
print(f"Total de localidades únicas: {len(all_items)}")
