import json,re,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data"/"oecd_aim_raw.json"
SITEMAP="https://oecd.ai/sitemaps/incident-monitor-sitemap.xml"
UA="OCDE-AIM-estudo-academico/1.1"
REQUEST_TIMEOUT=20
MAX_RETRIES=3
WORKERS=20

def get(url,timeout=REQUEST_TIMEOUT):
    last=None
    for attempt in range(1,MAX_RETRIES+1):
        try:
            req=Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xml"})
            with urlopen(req,timeout=timeout) as r:
                return r.read().decode("utf-8","replace")
        except (HTTPError,URLError,TimeoutError,OSError) as e:
            last=e
            if attempt<MAX_RETRIES:
                time.sleep(min(2**(attempt-1),4))
    raise last

def body_from_page(text):
    m=re.search(r'<script[^>]*id="ng-state"[^>]*>(.+?)</script>',text,re.S)
    if not m:return None
    try: state=json.loads(m.group(1))
    except json.JSONDecodeError:return None
    for v in state.values():
        if not isinstance(v,dict):continue
        b=v.get("b")
        if isinstance(b,dict) and b.get("id") and b.get("title"):return b
    return None

def pick(d,names):
    for n in names:
        v=d.get(n)
        if v not in (None,"",[],{}):return v
    return ""

def text_value(v):
    if isinstance(v,str):return v
    if isinstance(v,list):return " ".join(text_value(x) for x in v)
    if isinstance(v,dict):return " ".join(text_value(x) for x in v.values())
    return str(v) if v else ""

def one(url):
    try:
        b=body_from_page(get(url))
        if not b:return None
        country=pick(b,["country","country_name","location","countries"])
        harm=pick(b,["harm_type","harm_types"])
        typ=pick(b,["severity","type","incident_type","classification"])
        date=pick(b,["date","event_date"])
        return {"id":str(b.get("id")),"data":str(date),
                "pais":text_value(country).strip(),
                "titulo":str(b.get("title","")).strip(),
                "tipo":text_value(typ).strip(),
                "tipos_dano":text_value(harm).strip(),"url":url}
    except Exception as e:
        print(f"ERRO {url}: {e}",file=sys.stderr)
        return None

def main():
    print("Baixando sitemap oficial do OECD AIM...",flush=True)
    xml=get(SITEMAP,timeout=30)
    urls=re.findall(r"<loc>([^<]+)</loc>",xml)
    urls=[u.strip() for u in urls if re.match(r"https://oecd\\.ai/en/incidents/[^/]+$",u.strip())]
    urls=list(dict.fromkeys(urls))
    if not urls: raise RuntimeError("Nenhuma URL de incidente foi encontrada no sitemap.")
    print(f"URLs encontradas: {len(urls)}",flush=True)

    out=[]
    failed=0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures={ex.submit(one,u):u for u in urls}
        for i,f in enumerate(as_completed(futures),1):
            x=f.result()
            if x: out.append(x)
            else: failed+=1
            if i%100==0 or i==len(urls):
                print(f"Processadas: {i}/{len(urls)} | válidas: {len(out)} | falhas: {failed}",flush=True)

    out.sort(key=lambda x:(x["data"],x["id"]),reverse=True)
    RAW.parent.mkdir(parents=True,exist_ok=True)
    RAW.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Registros extraídos: {len(out)}; falhas após tentativas: {failed}",flush=True)

if __name__=="__main__":
    main()
