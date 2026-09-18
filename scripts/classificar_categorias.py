import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data"/"oecd_aim_raw.json";OUT=ROOT/"data"/"registros.json";CSV=ROOT/"data"/"registros.csv"

RULES={
"A":[r"physical",r"injur",r"death",r"fatal",r"health",r"medical",r"psychological",r"self.?harm",r"suicide",r"patient",r"mental"],
"B":[r"critical infrastructure",r"industrial control",r"power grid",r"electric grid",r"electricity",r"water supply",r"telecom",r"hospital infrastructure",r"transport infrastructure",r"operational disruption",r"infrastructure"],
"C":[r"human or fundamental rights",r"human rights",r"fundamental rights",r"privacy",r"discrimination",r"discriminat",r"labou?r",r"employment",r"copyright",r"intellectual property",r"consumer rights",r"legal obligation",r"due process"],
"D":[r"economic/property",r"property",r"financial harm",r"economic harm",r"environment",r"environmental",r"community",r"communities",r"pollution",r"water scarcity",r"e-waste"]
}

def hit(text,patterns):return any(re.search(p,text,re.I) for p in patterns)

def classify(x):
    text=" ".join([x.get("titulo",""),x.get("tipos_dano",""),x.get("pais",""),x.get("tipo","")]).lower()
    flags={k:hit(text,v) for k,v in RULES.items()}
    # Human/fundamental rights and economic/property are direct AIM harm labels.
    # Environmental and physical are mapped directly to OECD definitions.
    x.update(flags)
    x["categorias"]="".join(k for k,v in flags.items() if v)
    return x

def main():
    rows=json.loads(RAW.read_text(encoding="utf-8"))
    rows=[classify(x) for x in rows]
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    cols=["id","data","pais","titulo","tipo","tipos_dano","A","B","C","D","categorias","url"]
    with CSV.open("w",encoding="utf-8",newline="") as f:
        f.write(",".join(cols)+"\n")
        for x in rows:
            vals=[]
            for c in cols:
                v=x.get(c,"")
                if isinstance(v,bool):v="1" if v else "0"
                v=str(v).replace('"','""')
                vals.append('"'+v+'"')
            f.write(",".join(vals)+"\n")
    print(f"Classificados: {len(rows)}")

if __name__=="__main__":main()
