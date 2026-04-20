import requests
import json
import time
import string

api_url = "https://www.globalomnium.com/Direcciones/DameMunicipiosWebs"

# Alfabeto extendido: mayúsculas, minúsculas y caracteres especiales españoles
alphabet = (
    string.ascii_lowercase + 
    string.ascii_uppercase + 
    "áéíóúñÁÉÍÓÚÑ"
)

all_items = {}

def fetch_localities(filter_text):
    try:
        # Usamos un User-Agent real para evitar bloqueos
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

# 1. "Calentamiento" (Warm-up)
# Probamos algunas mayúsculas comunes para intentar "activar" la API según lo observado por el usuario
warmup = ["A", "E", "I", "O", "U", "Va", "Val"]
print("Realizando calentamiento de API...")
for w in warmup:
    fetch_localities(w)
    time.sleep(0.2)

# 2. Fuerza Bruta de caracteres individuales (Case Sensitive)
print("\nProbando caracteres individuales (Mayúsculas y Minúsculas)...")
for char in alphabet:
    items = fetch_localities(char)
    if items:
        print(f"Filtro '{char}': +{len(items)} resultados")
        for item in items:
            # Guardamos usando el nombre en mayúsculas como llave para evitar duplicados
            all_items[item["text"].upper()] = item["url"]
    time.sleep(0.1) # Pequeña pausa para no saturar el servidor

# 3. Probando combinaciones comunes de 2 letras (opcional pero recomendado según el feedback)
# Probamos combinaciones de Vocales + Consonantes comunes para intentar capturar más
print("\nProbando combinaciones comunes de 2 letras...")
common_prefixes = ["va", "Va", "VAL", "Val", "ma", "Ma", "ca", "Ca", "sa", "Sa"]
for pref in common_prefixes:
    items = fetch_localities(pref)
    if items:
        print(f"Filtro '{pref}': +{len(items)} resultados")
        for item in items:
            all_items[item["text"].upper()] = item["url"]
    time.sleep(0.1)

# Guardado final
with open("localities_dump.json", "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False, indent=4)

print(f"\n--- Proceso Completado ---")
print(f"Total de localidades únicas recolectadas: {len(all_items)}")
print("Resultados guardados en localities_dump.json")
