import json
import re
from typing import List, Any

def _extract_keywords(
    titulo: str,
    descripcion: str,
    palabras: Any,
) -> List[str]:

    pattern = r"[A-Za-zÁÉÍÓÚáéíóúÑñ]+"

    extracted = []

    # Si palabras es string puede ser JSON
    if isinstance(palabras, str):

        try:
            palabras = json.loads(palabras)
        except Exception:
            palabras = [palabras]

    if isinstance(palabras, (list, tuple, set)):
        for p in palabras:
            if isinstance(p, str):
                extracted.extend(re.findall(pattern, p.lower()))

    extracted.extend(re.findall(pattern, titulo.lower()))
    extracted.extend(re.findall(pattern, descripcion.lower()))

    return list(dict.fromkeys(extracted))


if __name__ == "__main__":
    titulo = "Título de ejemplo"
    descripcion = "Descripción de ejemplo"
    palabras = "Palabra 1, Palabra 2, Palabra 3"

    keywords = _extract_keywords(titulo, descripcion, palabras)
    print("Keywords extraídos:", keywords)