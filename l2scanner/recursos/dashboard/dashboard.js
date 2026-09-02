// O DESENHO DO DASHBOARD. Ele EXIBE o que o Python mandou, e não recalcula nada.
//
// REGRA DURA — A STRING QUE VEM DO PYTHON NÃO É REESCRITA AQUI.
// ============================================================
// `formatar_taxa_derivada`, `formatar_centesimos` e `_recencia_em_duas_formas`
// chegam prontos do servidor, em ASCII: `"11,60 XM por milhao de adena
// (derivado)"`, `"ha 8 h (31/08 10:00)"`, `"sem evidencia - 2 de 5 ofertas
// distintas"`. Este arquivo escreve essas strings COMO RECEBEU.
//
// Reacentuar `milhao` para `milhão`, ou trocar `ha` por `há`, ou re-arredondar
// o número, seria um SEGUNDO FORMATADOR — exatamente o que o DASH-03 proíbe
// ("mesma fonte, mesma conta, sem um segundo parser"). E o segundo formatador
// não erra no dia em que nasce: ele erra meses depois, quando alguém mexe num
// dos dois lados e ninguém percebe que havia dois.
//
// A DIVERGÊNCIA DE ACENTUAÇÃO ENTRE A MOLDURA E O VALOR É INTENCIONAL. A
// moldura desta página é nossa, é HTML em UTF-8 e leva acento; o valor vem do
// console, que é ASCII por escolha dele. Ver as duas convenções na mesma tela é
// o preço de ter uma fonte só, e é um preço barato.
//
// NENHUM LITERAL HEXADECIMAL DE COR NESTE ARQUIVO. A paleta mora no
// `dashboard.css`, e quem precisa de cor a pede por `getPropertyValue`. Há
// teste prendendo isso, com controle negativo no CSS.

"use strict";

// A mesma string que `dashboard.CAMINHO_DOS_DADOS` guarda do lado do Python. As
// duas só podem divergir de um jeito: silenciosamente.
const CAMINHO_DOS_DADOS = "/dados";

function escrever(id, texto) {
  const alvo = document.getElementById(id);
  if (alvo !== null) {
    alvo.textContent = texto;
  }
}

function pintarODestaque(dados) {
  const xm = dados.destaque.xm;

  // `textContent` e nunca `innerHTML`: o texto vem de um arquivo que o usuário
  // edita à mão no Sheets, e o `nome_exibido` de uma linha atravessa o OCR.
  // Injetar isso como HTML seria dar ao CSV o direito de escrever marcação na
  // própria página que julga o CSV.
  escrever("xm-texto", xm.texto);
  escrever("xm-n", xm.n === null ? "" : "n=" + xm.n);

  // Recência ausente vira cadeia vazia, e NÃO `"—"` nem `"agora"`. Não há
  // carimbo a informar quando não houve leitura, e inventar um rótulo aqui
  // seria a mesma mentira plausível que o Python recusa do outro lado.
  escrever("xm-recencia", xm.recencia === null ? "" : xm.recencia);
}

function buscarOsDados() {
  return fetch(CAMINHO_DOS_DADOS)
    .then(function (resposta) {
      if (!resposta.ok) {
        throw new Error("o servidor local respondeu " + resposta.status);
      }
      return resposta.json();
    })
    .then(pintarODestaque)
    .catch(function (erro) {
      // O TRACER FALHA EM VOZ ALTA, e não em silêncio. O tratamento de verdade
      // — a frase de "sem contato com o servidor local há N s" e a decisão de
      // manter na tela a última resposta recebida — é do plano 01-07, junto com
      // o polling que a torna necessária. Até lá, o console do navegador é onde
      // a falha aparece, e é melhor que uma tela que mente estar carregando.
      console.error("dashboard: falha ao buscar os dados", erro);
    });
}

// Uma busca única no carregamento. O polling de ~2 s é do plano 01-07: ele
// precisa do cache por (tamanho, mtime_ns) no servidor, que ainda não existe, e
// pedir de 2 em 2 segundos uma leitura completa do arquivo antes desse cache
// seria construir a dívida e o juro no mesmo commit.
document.addEventListener("DOMContentLoaded", buscarOsDados);
