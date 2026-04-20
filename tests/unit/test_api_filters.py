import requests

# Lista de filtros para probar la API de localidades
filters = ["a", "e", "i", "o", "u", "va", "val", "valencia", "valència", "alicante", "castellon", "*", "%20", ""]
api_url = "https://www.globalomnium.com/Direcciones/DameMunicipiosWebs"

print(f"{'Filtro':<15} | {'Nº Locales'}")
print("-" * 30)

for f in filters:
    try:
        response = requests.get(api_url, params={"filtro": f}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("items", []))
            print(f"{f:<15} | {count}")
        else:
            print(f"{f:<15} | Error {response.status_code}")
    except Exception as e:
        print(f"{f:<15} | Excepción")
