// O DESENHO DO DASHBOARD. Ele EXIBE o que o Python mandou, e não recalcula nada.
//
// REGRA DURA — A STRING QUE VEM DO PYTHON NÃO É REESCRITA AQUI.
// ============================================================
// `formatar_taxa_derivada`, `formatar_centesimos` e `_recencia_em_duas_formas`
// chegam prontos do servidor, em ASCII: `"ha 8 h (31/08 10:00)"`,
// `"sem evidencia - 2 de 5 ofertas distintas"`, `"11,60 XM por milhao de ..."`.
// Este arquivo escreve essas strings COMO RECEBEU.
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
// E A MESMA REGRA VALE PARA ENCURTAR. O rótulo de unidade vem INTEIRO do
// Python, longo, com a marca de derivado no fim. O UI-SPEC proíbe encurtá-lo
// por extenso: quem resolve o comprimento é o CSS (`line-clamp`), que corta na
// TELA sem tocar no texto. Cortar a string aqui seria o mesmo segundo
// formatador com outra roupa.
//
// AS DUAS ÚNICAS COISAS QUE ESTE ARQUIVO COMPÕE SÃO TEMPOS QUE O PYTHON NÃO
// PODE TER DITO: o "há N s" da faixa de servidor mudo — porque o servidor mudo
// é, por definição, o estado em que o Python não respondeu — e nada mais. Todo
// o resto é transporte de string.
//
// NENHUM LITERAL HEXADECIMAL DE COR NESTE ARQUIVO. A paleta mora no
// `dashboard.css`, e quem precisa de cor a pede por `getPropertyValue`. Há
// teste prendendo isso, com controle negativo no CSS.
//
// NENHUMA DECISÃO VISUAL MORA AQUI. O `dashboard.css` desenha cada estado; este
// arquivo só troca o valor de um atributo no `<body>`. Uma condição de tela
// escrita em JavaScript é uma condição que não aparece na folha de estilo, e as
// duas versões da verdade divergem no primeiro ajuste — sem quebrar nada em voz
// alta.

"use strict";

// A mesma string que `dashboard.CAMINHO_DOS_DADOS` guarda do lado do Python. As
// duas só podem divergir de um jeito: silenciosamente.
const CAMINHO_DOS_DADOS = "/dados";

// O NOME DO ESTADO QUE O SERVIDOR PODE MANDAR E QUE ESTE ARQUIVO PRECISA
// RECONHECER — um só, e ele é LIDO, nunca recalculado.
//
// Reconhecer o nome não é recalcular o estado: a conta do piso de evidência
// (`n >= 1` para o menor, `n >= 5` para a mediana) mora no `mercado_analise` e a
// precedência fechada dos cinco estados mora no `dashboard_dados`. Se esta
// página comparasse uma contagem com um piso, passariam a existir duas
// autoridades sobre a mesma pergunta, e elas divergiriam na primeira vez que
// alguém mudasse um dos pisos. Há teste afirmando que nenhuma comparação de
// contagem com piso existe neste arquivo.
const ESTADO_SEM_LEITURA = "sem_leitura";

// Mil milissegundos são um segundo. É aritmética de unidade, e não uma cadência.
const MILISSEGUNDOS_POR_SEGUNDO = 1000;
const SEGUNDOS_POR_MINUTO = 60;

// ESTA CONSTANTE NÃO É O INTERVALO DE POLLING, e a distinção é o ponto inteiro.
//
// O intervalo de polling vem DENTRO do payload (`intervalo_de_polling_ms`), e o
// número mora no `dashboard.py`. Um intervalo escrito em dois lugares não fica
// errado nos dois: fica errado em UM, e a página passa a consultar numa
// frequência que o servidor não conhece. Há teste afirmando que o número do
// servidor não aparece como literal neste arquivo.
//
// O que esta constante governa é outra coisa: a cadência de tentativa enquanto o
// navegador NUNCA falou com o servidor. Nesse instante não há payload, logo não
// há intervalo servido para obedecer, e não tentar de novo deixaria a página
// morta para sempre por causa de uma única resposta perdida. Assim que a
// primeira resposta chega, o número do servidor assume e esta constante nunca
// mais é usada.
const ESPERA_DO_PRIMEIRO_CONTATO_MS = MILISSEGUNDOS_POR_SEGUNDO;

// ---------------------------------------------------------------------------
// O ESTADO DO MÓDULO
// ---------------------------------------------------------------------------

// O instante da última resposta BEM-SUCEDIDA. É dele que sai o "há N s" da
// faixa de servidor mudo.
let recebidoEm = null;

// O instante em que a página abriu. Ele existe para o caso em que o servidor
// nunca respondeu: sem ele, a faixa teria de dizer "há nada", que não é uma
// informação — e o usuário precisa saber há quanto tempo a tela está sem
// contato, mesmo que o contato nunca tenha existido.
const abertoEm = new Date();

// O intervalo que o servidor mandou na última resposta. `null` enquanto ele
// nunca falou.
let intervaloConhecido = null;

// O último texto escrito em cada elemento, para o pulso de valor mudado saber o
// que mudou. Sem esta memória, o pulso ou dispara sempre (a cada 2 s, virando o
// piscar que o UI-SPEC proíbe) ou nunca.
const textoPintado = new Map();

// ---------------------------------------------------------------------------
// AS PRIMITIVAS DE ESCRITA
// ---------------------------------------------------------------------------

function escrever(id, texto) {
  const alvo = document.getElementById(id);
  if (alvo === null) {
    return;
  }

  // `textContent` e NUNCA marcação. O `nome_exibido` de uma série atravessa o
  // OCR sobre a tela do jogo, e o resto vem de um arquivo que o usuário edita à
  // mão: é conteúdo NÃO CONFIÁVEL terminando dentro desta página. Injetar isso
  // como marcação seria dar ao CSV o direito de escrever HTML na própria página
  // que julga o CSV (T-01-22). Há teste afirmando que a contagem de atribuições
  // a propriedade de marcação interna neste arquivo é zero.
  alvo.textContent = texto;
}

function anotarOTextoCompleto(id, texto) {
  // O texto inteiro no atributo de título, para o que o CSS corta com reticência
  // continuar alcançável. Atributo não é marcação: o navegador não interpreta o
  // valor como HTML.
  const alvo = document.getElementById(id);
  if (alvo !== null) {
    alvo.setAttribute("title", texto);
  }
}

function pulsar(id) {
  const alvo = document.getElementById(id);
  if (alvo === null) {
    return;
  }

  // A DURAÇÃO DO PULSO NÃO ESTÁ AQUI, E ISSO É DE PROPÓSITO. Ela é
  // `200ms` no `dashboard.css`, e repetir o número neste arquivo criaria a
  // mesma classe de defeito que o intervalo de polling: dois lugares, um deles
  // envelhece. Quem apaga o atributo é o próprio fim da animação.
  //
  // Tirar e repor o atributo com um reflow no meio é o que faz uma segunda
  // mudança logo em seguida REINICIAR a animação em vez de ser ignorada.
  alvo.removeAttribute("data-pulso");
  void alvo.offsetWidth;
  alvo.setAttribute("data-pulso", "sim");

  // MOVIMENTO REDUZIDO NÃO PRECISA DE UM SEGUNDO CAMINHO AQUI. O CSS já zera
  // toda animação sob `prefers-reduced-motion: reduce`, e nesse caso o evento de
  // fim nunca chega — o atributo fica posto, sem nada acontecendo na tela, que é
  // exatamente o resultado desejado. Um `if` de preferência neste arquivo seria
  // a segunda autoridade sobre uma decisão que já é do CSS.
}

function escreverComPulso(id, texto, idDoCartao) {
  const anterior = textoPintado.get(id);
  escrever(id, texto);
  textoPintado.set(id, texto);
  if (anterior !== undefined && anterior !== texto) {
    pulsar(idDoCartao);
  }
}

// ---------------------------------------------------------------------------
// OS AVISOS, E A POSIÇÃO DE CADA UM
// ---------------------------------------------------------------------------

/**
 * Os três avisos que têm lugar próprio na tela, achados por POSIÇÃO.
 *
 * O ACOPLAMENTO ESTÁ AQUI, ESCRITO, PORQUE ELE É REAL.
 * ====================================================
 * `avisos` é uma lista de strings sem rótulo. Achar cada frase pelo TEXTO
 * exigiria copiar as frases do Python para dentro deste arquivo — que é
 * literalmente a segunda cópia que o DASH-03 recusa, e que envelheceria na
 * primeira correção de vírgula do lado de lá. Então a posição é o que sobra.
 *
 * E a posição é DERIVADA, e não adivinhada: a mesma condição que o
 * `dashboard_dados.payload` usa para acrescentar cada bloco viaja no payload
 * como fato estrutural (`fonte.cauda_incompleta`, a chave de estado,
 * `destaque.xm.velho`). Este contador anda pela lista na ordem em que o Python
 * a monta.
 *
 * O CONSERTO CERTO, e por que ele não está aqui: `avisos` deveria ser um objeto
 * com uma chave por lugar da tela, e aí não haveria contador nenhum. Isso é uma
 * mudança no `dashboard_dados.py`, que este plano tem proibido tocar. Fica
 * registrado como pendência declarada, e não como dívida silenciosa — e há
 * teste do lado do Python, sobre payloads REAIS, prendendo a ordem de que estas
 * linhas dependem. Se alguém reordenar os avisos lá, o teste fica vermelho aqui.
 *
 * O ÚLTIMO AVISO NÃO É LIDO POR ESTA FUNÇÃO. Ele é a linha de R$ (indisponível,
 * ou o aviso do câmbio histórico), e as duas frases já nascem na marcação, com o
 * CSS escolhendo qual aparece pelo `data-cambio`. Escrevê-las daqui seria uma
 * terceira cópia de um texto que já está conferido por teste sobre o HTML.
 */
function avisosPorPosicao(dados) {
  const avisos = dados.avisos;
  const achado = { parcial: null, prova: null, velho: null };
  let posicao = 0;

  if (dados.fonte.cauda_incompleta) {
    achado.parcial = avisos[posicao];
    posicao += 1;
  }

  if (dados.estado === ESTADO_SEM_LEITURA) {
    // O bloco do estado vazio tem TRÊS avisos, nesta ordem: título, corpo e a
    // linha de prova. O título e o corpo já estão na marcação — só a linha de
    // prova precisa vir do servidor, porque ela carrega os dois números REAIS
    // do arquivo, e são eles que separam "não há o que mostrar" de "o dashboard
    // não conseguiu abrir o arquivo".
    achado.prova = avisos[posicao + 2];
    posicao += 3;
  }

  if (dados.destaque !== null && dados.destaque.xm.velho) {
    achado.velho = avisos[posicao];
    posicao += 1;
  }

  return achado;
}

// ---------------------------------------------------------------------------
// A PINTURA
// ---------------------------------------------------------------------------

function pintarUmCartao(prefixo, valor) {
  // O TEXTO INTEIRO VAI PARA O NÚMERO, e o vão da unidade fica vazio.
  //
  // ISTO É UMA COSTURA ENTRE PLANOS, E ELA ESTÁ DECLARADA. A marcação reservou
  // um vão de unidade esperando receber `XM por milhao de ... (derivado)`
  // separado do número; o payload não entrega os dois separados — ele entrega
  // UMA string pronta, `"11,60 XM por milhao de ... (derivado)"`, saída de
  // `formatar_taxa_derivada`. Partir essa string aqui, num espaço ou numa
  // vírgula, seria o segundo formatador: o navegador passaria a ter uma opinião
  // sobre onde termina o número e começa a unidade, e essa opinião erraria no
  // dia em que o formatador do Python mudasse. Então o vão fica vazio, e a
  // string vai inteira para onde ela cabe.
  escreverComPulso(prefixo + "-texto", valor.texto, "cartao-" + prefixo);

  // `n` e recência COLADOS no número, sempre. Estatística sem `n` é adivinhação
  // com cara de número — a disciplina do console de mercado, aplicada à tela.
  // O `n=` é um RÓTULO nosso, e não uma reescrita do valor: o número entra do
  // jeito que veio.
  escrever(prefixo + "-n", "n=" + valor.n);

  // Recência ausente vira cadeia vazia, e NÃO `"—"` nem `"agora"`. Não há
  // carimbo a informar quando não houve leitura, e inventar um rótulo aqui seria
  // a mesma mentira plausível que o Python recusa do outro lado.
  escrever(prefixo + "-recencia", valor.recencia === null ? "" : valor.recencia);
}

function pintar(dados) {
  const corpo = document.body;
  const destaque = dados.destaque;

  // A PRECEDÊNCIA JÁ FOI DECIDIDA PELO SERVIDOR, e esta linha é uma ATRIBUIÇÃO e
  // não uma tradução: os nomes de `data-estado` são exatamente os nomes de
  // `dashboard_dados.ESTADOS`. Um vocabulário só dos dois lados, porque dois
  // vocabulários divergem em silêncio.
  //
  // Recalcular a precedência aqui seria o começo de duas verdades sobre o mesmo
  // fato — e a segunda verdade sempre é a que ninguém está olhando.
  corpo.setAttribute("data-estado", dados.estado);

  // O servidor respondeu, logo ele não está mudo. A faixa sai da tela sozinha.
  corpo.setAttribute("data-servidor", "ok");

  // OS ORTOGONAIS SÃO LIDOS DA FORMA DO PAYLOAD, e não de um nome de estado: o
  // cartão de R$ existe quando o sub-objeto de R$ existe, e a ausência dele é
  // `null` — nunca um zero, nunca um valor de exemplo.
  corpo.setAttribute(
    "data-cambio",
    destaque !== null && destaque.reais !== null ? "informado" : "ausente"
  );
  corpo.setAttribute(
    "data-velho",
    destaque !== null && destaque.xm.velho ? "sim" : "nao"
  );

  // A FALHA FECHADA SE RECONHECE PELA FORMA, e não pelo nome do estado: quando
  // não há o que afirmar, o payload manda `destaque` nulo e `series` vazia. Aí
  // TODOS os avisos são a mensagem, e o CSS já retirou as três regiões da tela.
  // Perguntar pela forma em vez de pelo nome é o que faz um sexto estado de
  // falha fechada, se um dia existir, cair aqui sozinho.
  if (destaque === null) {
    escrever("faixa-erro", dados.avisos.join(" "));
  } else {
    escrever("faixa-erro", "");
  }

  const posicoes = avisosPorPosicao(dados);
  escrever("nota-linha-parcial", posicoes.parcial === null ? "" : posicoes.parcial);
  escrever("serie-vazio-prova", posicoes.prova === null ? "" : posicoes.prova);
  escrever("aviso-dado-velho", posicoes.velho === null ? "" : posicoes.velho);

  if (destaque !== null) {
    pintarUmCartao("xm", destaque.xm);
    if (destaque.reais !== null) {
      pintarUmCartao("reais", destaque.reais);
    }
    escrever("fonte-n", "n=" + destaque.xm.n);
    escrever(
      "fonte-recencia",
      destaque.xm.recencia === null ? "" : destaque.xm.recencia
    );
  }

  // A PROCEDÊNCIA VIAJA NO PAYLOAD, e não no folclore de quem desenha.
  escrever("fonte-arquivo", dados.fonte.arquivo);
  anotarOTextoCompleto("fonte-arquivo", dados.fonte.arquivo);
}

// ---------------------------------------------------------------------------
// O SERVIDOR MUDO
// ---------------------------------------------------------------------------

/**
 * O tempo decorrido, na forma curta que o contrato de cópia trava (`12 s`).
 *
 * É O ÚNICO NÚMERO QUE ESTE ARQUIVO COMPÕE, e ele só existe porque o Python não
 * pode tê-lo dito: o estado de servidor mudo é, por definição, aquele em que o
 * servidor não respondeu. A frase inteira em volta dele mora na marcação, com
 * um vão para este pedaço.
 */
function tempoDesde(instante) {
  const segundos = Math.floor((Date.now() - instante.getTime()) / MILISSEGUNDOS_POR_SEGUNDO);
  if (segundos < SEGUNDOS_POR_MINUTO) {
    return segundos + " s";
  }
  return Math.floor(segundos / SEGUNDOS_POR_MINUTO) + " min";
}

function marcarOServidorComoMudo() {
  // OS VALORES FICAM NA TELA. Limpar o destaque porque uma consulta falhou seria
  // trocar um dado velho honesto por nenhum dado — e o usuário está olhando para
  // isto ao lado do jogo, onde o último valor conhecido ainda vale alguma coisa.
  // O que a faixa retira é a afirmação de que o que está na tela é de agora.
  document.body.setAttribute("data-servidor", "mudo");
  escrever("servidor-mudo-ha", tempoDesde(recebidoEm === null ? abertoEm : recebidoEm));
}

// ---------------------------------------------------------------------------
// O POLLING
// ---------------------------------------------------------------------------

function buscarOsDados() {
  return fetch(CAMINHO_DOS_DADOS)
    .then(function (resposta) {
      if (!resposta.ok) {
        throw new Error("o servidor local respondeu " + resposta.status);
      }
      return resposta.json();
    })
    .then(function (dados) {
      recebidoEm = new Date();

      // O INTERVALO VEM DE DENTRO DA RESPOSTA. Se o servidor mudar a cadência,
      // o navegador acompanha sozinho, sem ninguém editar este arquivo.
      intervaloConhecido = dados.intervalo_de_polling_ms;
      pintar(dados);
    })
    .catch(function (erro) {
      console.error("dashboard: falha ao buscar os dados", erro);
      marcarOServidorComoMudo();
    });
}

function agendarAProximaBusca() {
  const espera =
    intervaloConhecido === null ? ESPERA_DO_PRIMEIRO_CONTATO_MS : intervaloConhecido;
  window.setTimeout(darUmaVolta, espera);
}

/**
 * Uma volta do laço: busca, pinta, e só ENTÃO agenda a próxima.
 *
 * AGENDAR DEPOIS DE ASSENTAR, E NÃO EM PARALELO. Um `setInterval` continuaria
 * disparando com o servidor morto, empilhando consultas que ninguém vai atender
 * (T-01-26). Aqui, uma volta só começa quando a anterior terminou — de bem ou de
 * mal —, então o pior caso é uma consulta pendurada, e nunca uma fila delas.
 *
 * E O POLLING NÃO É CARREGAMENTO. Não há indicador giratório em lugar nenhum
 * deste arquivo, e o estado de primeira pintura NUNCA é reposto: ele nasce na
 * marcação, com o rótulo de leitura em curso no lugar do número, e a primeira
 * resposta o substitui para sempre. Girar um indicador a cada dois segundos ao
 * lado do jogo é ruído, e voltar ao rótulo de carregamento a cada volta seria
 * pior: a tela piscaria entre "tenho um número" e "estou lendo" indefinidamente.
 */
function darUmaVolta() {
  return buscarOsDados().then(agendarAProximaBusca);
}

document.addEventListener("DOMContentLoaded", darUmaVolta);
