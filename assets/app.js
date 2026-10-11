const estado = { dados: [] };
const categorias = {
    A: "A — Saúde de pessoas ou grupos",
    B: "B — Infraestrutura crítica",
    C: "C — Direitos e obrigações legais",
    D: "D — Propriedade, comunidades ou ambiente"
};

let chartTipo = null; 
let chartAno = null; 

async function carregar() {
    try {
        const r = await fetch("data/registros.json", { cache: "no-store" });
        const j = await r.json();
        estado.dados = Array.isArray(j) ? j : (j.registros || []);
    } catch (e) {
        estado.dados = [];
    }
    montarPaises();
    montarAnos(); 
    render();
}

function obterAno(dataStr) {
    if (!dataStr) return "";
    const m = String(dataStr).match(/\d{4}/);
    return m ? m[0] : "";
}

function montarPaises() {
    const s = document.getElementById("pais");
    if(!s) return;
    const ps = [...new Set(estado.dados.map(x => x.pais).filter(Boolean))].sort((a, b) => a.localeCompare(b, "pt-BR"));
    s.innerHTML = '<option value="Todos">Todos os países</option>' + ps.map(p => '<option>' + esc(p) + '</option>').join("");
}

function montarAnos() {
    const s = document.getElementById("ano");
    if (!s) return; 
    const anos = [...new Set(estado.dados.map(x => obterAno(x.data)).filter(Boolean))].sort((a, b) => b.localeCompare(a));
    s.innerHTML = '<option value="Todos">Todos os anos</option>' + anos.map(a => '<option>' + esc(a) + '</option>').join("");
}

function esc(v) {
    return String(v ?? "").replace(/[&<>\"]/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
}

function sim(x, c) {
    return String(x[c] ?? x.categorias?.[c] ?? "").toLowerCase() === "true" || Number(x[c]) === 1;
}

function filtrados() {
    const e = document.getElementById("escopo")?.value || "Mundo",
          c = document.getElementById("categoria")?.value || "Todas",
          p = document.getElementById("pais")?.value || "Todos";
          
    const selectAno = document.getElementById("ano");
    const filtroAno = selectAno ? selectAno.value : "Todos";

    return estado.dados.filter(x => {
        const pais = String(x.pais || "");
        const okEsc = e === "Mundo" || pais === "Brasil" || pais === "Brazil";
        const okPais = p === "Todos" || pais === p;
        const okAno = filtroAno === "Todos" || obterAno(x.data) === filtroAno;
        
        return okEsc && okPais && okAno && (c === "Todas" || sim(x, c));
    });
}

function contar(a, c) {
    return a.filter(x => sim(x, c)).length;
}

function renderizarGraficoTipo(dadosFiltrados) {
    const ctx = document.getElementById('graficoIncidentesTipo');
    if (!ctx) return; 

    const contagem = {};
    dadosFiltrados.forEach(x => {
        const tipo = x.tipo ? String(x.tipo).trim() : "Não especificado";
        contagem[tipo] = (contagem[tipo] || 0) + 1;
    });

    const tiposOrdenados = Object.keys(contagem)
        .sort((a, b) => contagem[b] - contagem[a])
        .slice(0, 10);
        
    const labels = tiposOrdenados.map(t => t.length > 35 ? t.substring(0, 35) + '...' : t);
    const valores = tiposOrdenados.map(t => contagem[t]);

    if (chartTipo) {
        chartTipo.destroy();
    }

    chartTipo = new Chart(ctx, {
        type: 'bar', 
        data: {
            labels: labels,
            datasets: [{
                label: 'Quantidade de Incidentes',
                data: valores,
                backgroundColor: '#1e90ff',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y', 
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false } 
            }
        }
    });
}

function renderizarGraficoAno(dadosFiltrados) {
    const ctx = document.getElementById('graficoIncidentesAno');
    if (!ctx) return;

    const contagem = {};
    dadosFiltrados.forEach(x => {
        const ano = obterAno(x.data);
        if (ano) {
            contagem[ano] = (contagem[ano] || 0) + 1;
        }
    });

    const anos = Object.keys(contagem).sort();
    const totais = anos.map(ano => contagem[ano]);

    if (anos.length === 0) return; 

    if (chartAno) {
        chartAno.destroy();
    }

    chartAno = new Chart(ctx, {
        type: 'line',
        data: {
            labels: anos,
            datasets: [{
                label: 'Incidentes',
                data: totais,
                borderColor: '#1e90ff',
                borderWidth: 2,
                tension: 0.4, 
                pointRadius: 0, 
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function render() {
    const a = filtrados(), t = a.length;
    
    const descEl = document.getElementById("descricao");
    if(descEl) {
        descEl.textContent = (document.getElementById("escopo")?.value === "Mundo" ? "Conjunto mundial" : "Registros identificados no Brasil") + " · " + t + " registro(s) no filtro atual";
    }
    
    const cardsEl = document.getElementById("cards");
    if(cardsEl) {
        cardsEl.innerHTML = '<div class="card"><div class="rotulo">Registros</div><div class="numero">' + t + '</div></div>' + Object.keys(categorias).map(c => '<div class="card"><div class="rotulo">' + esc(categorias[c]) + '</div><div class="numero">' + contar(a, c) + '</div></div>').join("");
    }
    
    const barrasEl = document.getElementById("barras");
    if(barrasEl) {
        const vs = Object.keys(categorias).map(c => ({ c, n: contar(a, c) })), max = Math.max(1, ...vs.map(v => v.n));
        barrasEl.innerHTML = vs.map(v => '<div class="barra-linha"><div>' + esc(categorias[v.c]) + '</div><div class="trilho"><div class="barra" style="width:' + ((v.n / max) * 100) + '%"></div></div><div class="valor">' + v.n + '</div></div>').join("");
    }
    
    const tb = document.getElementById("tabela");
    if(tb) {
        tb.innerHTML = a.slice(0, 200).map(x => '<tr><td>' + esc(x.data) + '</td><td>' + esc(x.pais) + '</td><td>' + esc(x.titulo) + '</td><td>' + esc(x.tipo || "") + '</td>' + Object.keys(categorias).map(c => '<td>' + (sim(x, c) ? "✓" : "—") + '</td>').join("") + '</tr>').join("");
        if (!a.length) {
            tb.innerHTML = '<tr><td colspan="8" class="vazio">Nenhum registro disponível para o filtro atual.</td></tr>';
        }
    }

    renderizarGraficoTipo(a);
    renderizarGraficoAno(a);
}

["escopo", "categoria", "pais"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", render);
});

setTimeout(() => {
    const elAno = document.getElementById("ano");
    if (elAno) elAno.addEventListener("change", render);
}, 100);

const btnLimpar = document.getElementById("limpar");
if(btnLimpar) {
    btnLimpar.addEventListener("click", () => {
        if(document.getElementById("escopo")) document.getElementById("escopo").value = "Mundo";
        if(document.getElementById("categoria")) document.getElementById("categoria").value = "Todas";
        if(document.getElementById("pais")) document.getElementById("pais").value = "Todos";
        if(document.getElementById("ano")) document.getElementById("ano").value = "Todos";
        render();
    });
}

carregar();
