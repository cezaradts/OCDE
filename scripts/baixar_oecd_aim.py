import json
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "oecd_aim_raw.json"
ENDPOINT = "https://incidents-server.oecdai.org/api/v1/incidents/fetch-incidents"
UA = "OCDE-AIM-estudo-academico/1.2"
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
            }
            if body is not None:
                headers["Content-Type"] = "application/json"
            req = Request(url, data=body, headers=headers, method=method)
            with urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            last = e
            if attempt < MAX_RETRIES:
                time.sleep(min(2 ** (attempt - 1), 8))
    raise last


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
    if not isinstance(data, dict) or not isinstance(data.get("incidents"), list):
        raise RuntimeError("Resposta inesperada do endpoint oficial do AIM.")
    total = data.get("total_results", len(data["incidents"]))
    return total, data["incidents"]


def add_days(iso, days):
    return (date.fromisoformat(iso) + timedelta(days=days)).isoformat()


def transform(inc):
    location = inc.get("location") or {}
    props = inc.get("properties") or {}
    harm = props.get("harm_types") or []
    levels = props.get("harm_levels") or []
    country = location.get("country") or location.get("location") or ""
    return {
        "id": str(inc.get("id", "")),
        "data": str(inc.get("date", "")),
        "pais": country,
        "titulo": str(inc.get("title", "")).strip(),
        "tipo": " | ".join(str(x) for x in levels),
        "tipos_dano": " | ".join(str(x) for x in harm),
        "url": f"https://oecd.ai/en/incidents/{inc.get('id', '')}",
        "resumo": str(inc.get("summary") or "").strip(),
        "industries": props.get("industries") or [],
        "principles": props.get("principles") or [],
        "harmed_entities": props.get("harmed_entities") or [],
        "business_functions": props.get("business_functions") or [],
        "ai_tasks": props.get("ai_tasks") or [],
        "autonomy_level": props.get("autonomy_level") or "",
        "country_code": location.get("country_code") or "",
    }


def main():
    print("Baixando dados pelo endpoint JSON oficial do OECD AIM...", flush=True)
    today = date.today().isoformat()
    out_by_id = {}
    cursor = START_DATE
    requests = 0

    while cursor <= today:
        end = min(add_days(cursor, WINDOW_DAYS - 1), today)
        total, incidents = fetch_window(cursor, end)
        requests += 1
        print(f"Janela {cursor} a {end}: {total} registros", flush=True)

        if total > MAX_RESULTS:
            # The API caps each response at 100 and does not support offset.
            # Split the date window until every response is complete.
            if cursor == end:
                raise RuntimeError(
                    f"O AIM retornou {total} registros em um único dia; "
                    "não há paginação por offset disponível."
                )
            midpoint = add_days(cursor, (date.fromisoformat(end) - date.fromisoformat(cursor)).days // 2)
            for sub_from, sub_to in ((cursor, midpoint), (add_days(midpoint, 1), end)):
                sub_total, sub_incidents = fetch_window(sub_from, sub_to)
                requests += 1
                if sub_total > MAX_RESULTS:
                    # Re-run the same logic with a one-day recursive splitter.
                    stack = [(sub_from, sub_to, sub_total, sub_incidents)]
                    while stack:
                        sf, st, stotal, sins = stack.pop()
                        if stotal <= MAX_RESULTS:
                            for inc in sins:
                                if inc.get("id"):
                                    out_by_id[str(inc["id"])] = inc
                            continue
                        if sf == st:
                            raise RuntimeError(f"AIM retornou {stotal} registros em {sf}.")
                        mid = add_days(sf, (date.fromisoformat(st) - date.fromisoformat(sf)).days // 2)
                        for a, b in ((sf, mid), (add_days(mid, 1), st)):
                            t, ins = fetch_window(a, b)
                            requests += 1
                            stack.append((a, b, t, ins))
                else:
                    for inc in sub_incidents:
                        if inc.get("id"):
                            out_by_id[str(inc["id"])] = inc
        else:
            for inc in incidents:
                if inc.get("id"):
                    out_by_id[str(inc["id"])] = inc

        cursor = add_days(end, 1)
        time.sleep(0.2)

    out = [transform(inc) for inc in out_by_id.values()]
    out.sort(key=lambda x: (x["data"], x["id"]), reverse=True)
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(f"Registros extraídos: {len(out)} | requisições: {requests}", flush=True)


if __name__ == "__main__":
    main()
