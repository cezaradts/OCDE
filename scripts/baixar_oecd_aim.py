import json,re,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data"/"oecd_aim_raw.json"
SITEMAP="https://oecd.ai/sitemaps/incident-monitor-sitemap.xml"
UA="OCDE-AIM-estudo-academico/1.0"

def get(url,timeout=45):
    req=Request(url,headers={"User-Agent":UA})
    with urlopen(req,timeout=timeout) as r:return r.read().decode("utf-8","replace")

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
    if isinstance(v,dict):
        return " ".join(text_value(x) for x in v.values())
    return str(v) if v else ""

def one(url):
    try:
        b=body_from_page(get(url))
        if not b:return None
        country=pick(b,["country","country_name","location","countries"])
        harm=pick(b,["harm_type","harm_types"])
        typ=pick(b,["severity","type","incident_type","classification"])
        date=pick(b,["date","event_date"])
        return {"id":str(b.get("id")),"data":str(date),"pais":text_value(country).strip(),"titulo":str(b.get("title","")).strip(),"tipo":text_value(typ).strip(),"tipos_dano":text_value(harm).strip(),"url":url}
    except Exception as e:
        print(f"ERRO {url}: {e}",file=sys.stderr);return None

def main():
    xml=get(SITEMAP)
    urls=re.findall(r"<loc>([^<]+)</loc>",xml)
    urls=[u for u in urls if re.match(r"https://oecd\.ai/en/incidents/[^/]+$",u)]
    print(f"URLs encontradas: {len(urls)}")
    out=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        fs=[ex.submit(one,u) for u in urls]
        for i,f in enumerate(as_completed(fs),1):
            x=f.result()
            if x:out.append(x)
            if i%250==0:print(f"Processadas: {i}/{len(urls)}")
    out.sort(key=lambda x:(x["data"],x["id"]),reverse=True)
    RAW.parent.mkdir(parents=True,exist_ok=True)
    RAW.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Registros extraídos: {len(out)}")

if __name__=="__main__":main()
