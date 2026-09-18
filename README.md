# OCDE — Incidentes e Perigos de IA

Painel acadêmico em português para explorar o **OECD.AI AI Incidents and Hazards Monitor (AIM)**, comparar Brasil e mundo e filtrar os registros pelas categorias A, B, C e D.

## Fonte
OECD.AI — AI Incidents and Hazards Monitor: https://oecd.ai/en/incidents

Metodologia: https://oecd.ai/en/incidents-methodology

A OCDE informa que o AIM é um monitor de incidentes e perigos identificados em fontes públicas e que os registros representam apenas um subconjunto dos incidentes e perigos existentes mundialmente. O monitor é dinâmico.

## Dados
O workflow de atualização baixa os registros disponíveis no sitemap do AIM, preserva uma cópia estrutural em `data/oecd_aim_raw.json` e gera `data/registros.json` e `data/registros.csv` com as variáveis derivadas A–D.

## Categorias
A — saúde de pessoas ou grupos  
B — operação de infraestrutura crítica  
C — direitos humanos/fundamentais e obrigações legais, trabalhistas e de propriedade intelectual  
D — propriedade, comunidades ou ambiente

A classificação A–D é uma transformação analítica deste projeto. Um caso pode receber mais de uma categoria.

## Reprodução
1. Execute `python scripts/baixar_oecd_aim.py`.
2. Execute `python scripts/classificar_categorias.py`.
3. Abra o painel ou publique o conteúdo via GitHub Pages.

A extração deve registrar a data de coleta porque o AIM é atualizado continuamente.
