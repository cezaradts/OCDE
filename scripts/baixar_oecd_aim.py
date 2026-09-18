import json
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "oecd_aim_raw.json"

# Endpoint atual do OECD.AI AIM (AI Incidents and Hazards Monitor).
# A página pública atual do AIM usa o mesmo serviço de incidentes.
ENDPOINT = "https://incidents-server.oecdai.org/api/v1/incidents/fetch-incidents"
AIM_BASE_URL = "https://oecd.ai/en/incidents"

UA = "OCDE-AIM-estudo-academico/1.3"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 4
MAX_RESULTS = 100
WINDOW_DAYS = 14
START_DATE = "2020-01-01"


def get_json(url, method="GET", payload=None, timeout=REQUEST_TIMEOUT):
    last = None
    body = None if payload is None else json.dumps(payload).encode("utf-8")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            headers = {
                "User-Agent": UA,
                "Accept": "application/json",
                "Origin": "https://oecd.ai",
                "Referer": "https://oecd.ai/en/incidents",
            }
            if body is not None:
                headers["Content-Type"] = "application/json"

            req = Request(url, data=body, headers=headers, method=method)

            with urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw)

        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < MAX_RETRIES:
                time.sleep(min(2 ** (attempt - 1), 8))

    raise RuntimeError(f"Falha ao consultar o AIM: {last}") from last


def empty_properties():
    return {
        "principles": [],
        "industries": [],
        "harm_types": [],
        "harm_levels": [],
        "harmed_entities": [],
        "business_functions": [],
        "ai_tasks": [],
        "autonomy_levels": [],
        "languages": [],
    }


def fetch_window(from_date, to_date):
    payload = {
        "search_terms": [],
        "and_condition": False,
        "countries": [],
        "from_date": from_date,
        "to_date": to_date,
        "properties_config": empty_properties(),
        "order_by": "date",
        "num_results": MAX_RESULTS,
        "format": "JSON",
    }

    data = get_json(ENDPOINT, method="POST", payload=payload)

    if not isinstance(data, dict):
        raise RuntimeError("Resposta inesperada do endpoint oficial do AIM.")

    incidents = data.get("incidents")
    if not isinstance(incidents, list):
        raise RuntimeError(
            "O endpoint do AIM respondeu sem a lista 'incidents'. "
            f"Chaves recebidas: {sorted(data.keys())}"
        )

    total = data.get("total_results", len(incidents))
    return int(total), incidents


def add_days(iso, days):
    return (date.fromisoformat(iso) + timedelta(days=days)).isoformat()


def incident_url(inc):
    """
    Usa a URL fornecida pelo próprio registro quando disponível.
    Caso o registro não traga URL, usa a rota individual atual do AIM:
    https://oecd.ai/en/incidents/{id}

    Não cria links para caminhos antigos nem usa /en/incidents/ sem ID.
    """
    for key in ("url", "web_url", "link", "source_url"):
        value = inc.get(key)
        if isinstance(value, str) and value.strip():
            value = value.strip()
            if value.startswith("https://oecd.ai/"):
                return value
            if value.startswith("/en/incidents/"):
                return "https://oecd.ai" + value

    incident_id = inc.get("id")
    if incident_id in (None, ""):
        return AIM_BASE_URL

    return f"{AIM_BASE_URL}/{incident_id}"


def transform(inc):
    location = inc.get("location") or {}
    props = inc.get("properties") or {}

    harm = props.get("harm_types") or []
    levels = props.get("harm_levels") or []

    country = (
        location.get("country")
        or location.get("location")
        or ""
    )

    return {
        "id": str(inc.get("id", "")),
        "data": str(inc.get("date", "")),
        "pais": country,
        "titulo": str(inc.get("title", "")).strip(),
        "tipo": " | ".join(str(x) for x in levels),
        "tipos_dano": " | ".join(str(x) for x in harm),
        "url": incident_url(inc),
        "resumo": str(inc.get("summary") or "").strip(),
        "industries": props.get("industries") or [],
        "principles": props.get("principles") or [],
        "harmed_entities": props.get("harmed_entities") or [],
        "business_functions": props.get("business_functions") or [],
        "ai_tasks": props.get("ai_tasks") or [],
        "autonomy_level": props.get("autonomy_level") or "",
        "country_code": location.get("country_code") or "",
    }


def collect_range(start, end, out_by_id):
    """
    Busca um intervalo. Se houver mais de 100 resultados, divide o período
    recursivamente para não truncar dados.
    """
    total, incidents = fetch_window(start, end)

    if total <= MAX_RESULTS:
        for inc in incidents:
            if inc.get("id") is not None:
                out_by_id[str(inc["id"])] = inc
        return 1

    if start == end:
        raise RuntimeError(
            f"O AIM retornou {total} registros em {start}, acima do limite "
            "de 100 e sem paginação disponível."
        )

    start_dt = date.fromisoformat(start)
    end_dt = date.fromisoformat(end)
    midpoint = start_dt + timedelta(days=(end_dt - start_dt).days // 2)
    mid = midpoint.isoformat()

    requests = 1
    requests += collect_range(start, mid, out_by_id)
    requests += collect_range(add_days(mid, 1), end, out_by_id)
    return requests


def main():
    print("Baixando dados pelo endpoint atual do OECD.AI AIM...", flush=True)

    today = date.today().isoformat()
    out_by_id = {}
    cursor = START_DATE
    requests = 0

    while cursor <= today:
        end = min(add_days(cursor, WINDOW_DAYS - 1), today)

        try:
            requests += collect_range(cursor, end, out_by_id)
        except Exception as exc:
            raise RuntimeError(
                f"Falha ao extrair a janela {cursor} a {end}: {exc}"
            ) from exc

        print(
            f"Janela {cursor} a {end}: "
            f"{len(out_by_id)} registros acumulados",
            flush=True,
        )

        cursor = add_days(end, 1)
        time.sleep(0.2)

    out = [transform(inc) for inc in out_by_id.values()]
    out.sort(key=lambda item: (item["data"], item["id"]), reverse=True)

    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Registros extraídos: {len(out)} | requisições: {requests}",
        flush=True,
    )


if __name__ == "__main__":
    main()
