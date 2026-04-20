import requests
import json

api_url = "https://www.globalomnium.com/Direcciones/DameMunicipiosWebs"
filter_text = "va"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def make_request():
    try:
        response = requests.get(api_url, params={"filtro": filter_text}, headers=headers, timeout=3)
        if response.status_code == 200:
            return response.json().get("items", [])
    except Exception as e:
        return f"Error: {e}"
    return []

print(f"--- Probando doble solicitud para filtro '{filter_text}' ---")

# Primera solicitud
res1 = make_request()
count1 = len(res1) if isinstance(res1, list) else "Error"
print(f"Solicitud 1: {count1} resultados")

# Segunda solicitud inmediata
res2 = make_request()
count2 = len(res2) if isinstance(res2, list) else "Error"
print(f"Solicitud 2: {count2} resultados")

if isinstance(count1, int) and isinstance(count2, int):
    if count2 > count1:
        print("\n✅ ¡Hipótesis confirmada! La segunda solicitud devolvió más resultados.")
    elif count2 < count1:
        print("\n❌ La segunda solicitud devolvió menos resultados.")
    else:
        print("\n➖ Ambas solicitudes devolvieron la misma cantidad de resultados.")
else:
    print("\n❌ No se pudieron comparar los resultados debido a errores.")

if isinstance(res2, list) and len(res2) > 0:
    print("\nDetalle de la segunda respuesta:")
    for item in res2:
        print(f"- {item['text']}: {item['url']}")
