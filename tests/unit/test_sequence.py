import requests
import json
import time

api_url = "https://www.globalomnium.com/Direcciones/DameMunicipiosWebs"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch(filter_text):
    try:
        print(f"Enviando solicitud con filtro '{filter_text}'...", end=" ", flush=True)
        response = requests.get(api_url, params={"filtro": filter_text}, headers=headers, timeout=5)
        if response.status_code == 200:
            items = response.json().get("items", [])
            print(f"✅ Recibidos {len(items)} resultados.")
            return items
        else:
            print(f"❌ Error {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    return []

def main():
    sequence = ["va", "Va", "VA", "va"]
    all_results = []

    print("--- Iniciando Secuencia de Pruebas ---")
    for i, step in enumerate(sequence):
        results = fetch(step)
        all_results.append((step, len(results)))
        
        # Espera entre solicitudes
        if i < len(sequence) - 1:
            print("Esperando...")
            time.sleep(2)

    print("\n--- Resumen de la Secuencia ---")
    for step, count in all_results:
        print(f"Filtro '{step}': {count} resultados")

if __name__ == "__main__":
    main()
