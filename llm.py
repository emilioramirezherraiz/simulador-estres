"""Llamada al LLM (Google Gemini) y lectura de la respuesta."""

import json
import re
import time

from google import genai
from google.genai import types

# Puedes cambiarlo desde los secretos (GEMINI_MODEL) o desde la barra lateral.
# Consulta en Google AI Studio qué modelos tiene disponibles tu nivel gratuito.
DEFAULT_MODEL = "gemini-3.5-flash-lite"


def call_llm(system: str, user: str, api_key: str, model: str = DEFAULT_MODEL,
             max_tokens: int = 8192, temperature: float | None = None,
             retries: int = 3) -> str:
    """Devuelve el texto de la respuesta del modelo.

    Si se supera el límite de peticiones del nivel gratuito (error 429),
    espera y reintenta automáticamente.
    """
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        temperature=temperature,
        response_mime_type="application/json",  # obliga a Gemini a devolver JSON
    )

    for attempt in range(retries):
        try:
            response = client.models.generate_content(model=model, contents=user, config=config)
            break
        except Exception as e:  # noqa: BLE001
                        limited = any(code in str(e) for code in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"))
            if limited and attempt < retries - 1:
                time.sleep(20 * (attempt + 1))
                continue
            raise

    text = response.text
    if not text:
        raise ValueError(
            "El modelo ha devuelto una respuesta vacía "
            "(posible límite de tokens o bloqueo por filtro de seguridad)."
        )
    return text


def parse_json(text: str) -> dict:
    """Extrae el JSON aunque el modelo añada bloques de código o texto alrededor."""
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise
