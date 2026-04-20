import requests
import json
import time
import string
from collections import defaultdict

api_url = "https://www.globalomnium.com/Direcciones/DameMunicipiosWebs"

# Alfabeto extendido para cubrir todas las posibilidades
alphabet = "abcdefghijklmnopqrstuvwxyzáéíóúñABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑ "

def fetch_with_retries(filter_text, retries=3):
    results_set = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for i in range(retries):
        try:
            response = requests.get(api_url, params={"filtro": filter_text}, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                for item in items:
                    # Guardamos una tupla (texto, url) para evitar duplicados
                    results_set.add((item["text"], item["url"]))
                if len(items) > 0:
                    # Si obtuvimos resultados, es probable que hayamos superado la "inestabilidad"
                    # pero seguimos probando hasta el límite de retries para maximizar la recolección
                    pass
        except Exception:
            pass
        time.sleep(0.1)
    return results_set

def main():
    all_localities = {} # Text (Upper) -> URL
    
    print("--- Iniciando Recolección Exhaustiva v2 ---")
    
    # 1. Probar caracteres individuales
    print("Probando caracteres individuales...")
    for char in alphabet:
        res = fetch_with_retries(char)
        for text, url in res:
            all_localities[text.upper()] = url
    
    # 2. Probar combinaciones de 2 letras (Fuerza Bruta Real)
    # Para no tardar horas, probaremos combinaciones que empiecen por letras comunes
    # o simplemente todas si el tiempo lo permite. 54*54 = 2916 peticiones.
    # A 0.1s por petición = ~300 segundos (5 mins). Es viable.
    print("Probando combinaciones de 2 letras (esto puede tardar unos minutos)...")
    
    # Para optimizar, priorizamos combinaciones que empiecen por vocales y letras frecuentes
    # pero el usuario quiere exhaustividad.
    count = 0
    for c1 in alphabet:
        for c2 in alphabet:
            filter_text = c1 + c2
            res = fetch_with_retries(filter_text, retries=1) # Menos retries para las de 2 letras
            if res:
                for text, url in res:
                    all_localities[text.upper()] = url
            
            count += 1
            if count % 100 == 0:
                print(f"Progreso: {count}/{len(alphabet)**2} combinaciones probadas...")

    # Guardado final
    with open("localities_dump.json", "w", encoding="utf-8") as f:
        json.dump(all_localities, f, ensure_ascii=False, indent=4)
    
    print(f"\n--- Proceso Completado ---")
    print(f"Total de localidades únicas recolectadas: {len(all_localities)}")
    
    # Verificar si València está ahora
    found = [k for k in all_localities.keys() if "VALENC" in k]
    if found:
        print(f"✅ ¡Encontrado! Localidades relacionadas con Valencia: {found}")
    else:
        print("❌ València sigue sin aparecer en el volcado.")

if __name__ == "__main__":
    main()
