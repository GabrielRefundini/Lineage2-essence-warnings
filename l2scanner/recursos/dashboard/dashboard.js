// O DESENHO DO DASHBOARD. Ele EXIBE o que o Python mandou, e não recalcula nada.
//
// REGRA DURA — A STRING QUE VEM DO PYTHON NÃO É REESCRITA AQUI.
// ============================================================
// `formatar_taxa_derivada`, `formatar_centesimos` e `_recencia_em_duas_formas`
// chegam prontos do servidor, em ASCII: `"ha 8 h (31/08 10:00)"`,
// `"sem evidencia - 2 de 5 ofertas distintas"`, `"58,00 XM por 5 milhoes de ..."`.
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
// O EIXO VERTICAL ERA O ÚNICO LUGAR EM QUE A REGRA ACIMA NÃO VALIA COMO ESTAVA
// ESCRITA — E AGORA VALE (2026-09-03).
// ---------------------------------------------------------------------------
// Até esta data `axes[1]` ia configurado como `y: {}`, vazio, e os rótulos do
// eixo (`900 / 1.000 / 1.100`) eram INVENTADOS pela biblioteca, em posições que
// o Python nunca via. Era um segundo formatador de fato — só que dentro do
// pacote vendorizado, onde nenhuma sonda de fonte deste projeto o alcançava. O
// usuário viu o resultado na primeira olhada: `9,10 XM` no destaque e `900` no
// eixo dez centímetros abaixo, duas unidades na mesma tela.
//
// A ROTA ESCOLHIDA: o Python entrega as POSIÇÕES e os TEXTOS, e o navegador só
// escolhe QUAL conjunto cabe na janela visível. É o mesmo desenho que
// `resolucaoPara` já usa no eixo do tempo, sob a frase que já estava escrita
// aqui: "A JANELA é decisão do navegador; a CONTA não é."
//
// AS TRÊS ROTAS RECUSADAS, e por quê:
//
//   1. UM GANCHO DE FORMATAÇÃO NO EIXO. É a resposta de três linhas, e é um
//      SEGUNDO FORMATADOR — o que o DASH-03 proíbe por escrito. Ele não erra no
//      dia em que nasce; erra meses depois, quando alguém mexe num dos dois
//      lados. As sondas de `tests/test_dashboard_js.py` (a tupla de segundo
//      formatador) já o reprovariam, e reprovam de propósito.
//   2. FIXAR A ESCALA VERTICAL NA FAIXA INTEIRA DA SÉRIE — entregar também o
//      mínimo e o máximo e desligar o ajuste automático. Resolveria a escada num
//      passo, mas MATARIA o comportamento de hoje: ao aproximar num período
//      curto, o eixo deixaria de abrir. O usuário não pediu isso e não pode
//      ganhar de brinde.
//   3. UMA ESCADA ÚNICA, FIXA. Ao aproximar muito, sobraria uma marca ou
//      nenhuma — e um eixo sem marca não diz em que unidade está.
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
  // um vão de unidade esperando receber `XM por 5 milhoes de ... (derivado)`
  // separado do número; o payload não entrega os dois separados — ele entrega
  // UMA string pronta, `"58,00 XM por 5 milhoes de ... (derivado)"`, saída de
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

  // A PRIMEIRA SÉRIE DA LISTA, E NÃO "a série tal".
  //
  // O payload traz TODAS as séries que o arquivo conhece, porque filtrar do
  // lado do Python seria o `if` de uma série específica que o DASH-05 recusa —
  // e o teste que prende isto é uma busca LITERAL pelo nome dela no arquivo
  // inteiro, então nem os comentários o escrevem. Quais séries a página
  // instancia é decisão da página — e a decisão desta versão é: a
  // primeira, porque há uma área de gráfico na tela. Instanciar uma segunda é
  // passar `dados.series[1]` para a mesma função, e nenhuma linha de código de
  // gráfico novo.
  //
  // `series` é `[]` nos dois estados de falha fechada, e aí não há série
  // nenhuma para desenhar — o gráfico é apagado junto com o resto.
  if (dados.series.length === 0) {
    escrever("serie-titulo", "");
    apagarOGrafico();
  } else {
    desenharUmaSerie(dados.series[0]);
  }

  pintarAsRotas(dados.calculadora);
}

// ---------------------------------------------------------------------------
// A CALCULADORA DE ROTAS
// ---------------------------------------------------------------------------

// A assinatura da última lista pintada. Ela existe para a lista SÓ ser
// reconstruída quando o conteúdo mudou.
//
// A RAZÃO NÃO É DESEMPENHO. Reconstruir a lista a cada volta de dois segundos
// apagaria a SELEÇÃO DE TEXTO do usuário no meio de uma conferência — e esta é
// justamente uma conta que ele vai conferir com o dedo na tela, comparando o
// número daqui com o da janela do NPC.
//
// A ASSINATURA É A CONCATENAÇÃO DOS TEXTOS QUE O PYTHON JÁ FORMATOU, e não um
// recálculo de coisa nenhuma. Se o Python mandou as mesmas strings, não há nada
// de novo para desenhar.
let assinaturaDasRotas = null;

/**
 * Escreve num vão do molde clonado, por propriedade de TEXTO.
 *
 * POR `data-vao` E NÃO POR `id`: o molde é clonado uma vez por item, e um `id`
 * dentro dele viraria N elementos com o mesmo identificador — `getElementById`
 * devolveria sempre o primeiro, e todas as linhas mostrariam o primeiro item.
 */
function escreverNoVao(raiz, vao, texto) {
  const alvo = raiz.querySelector('[data-vao="' + vao + '"]');
  if (alvo === null) {
    return;
  }
  // `textContent` e NUNCA marcação, pela mesma razão de `escrever`: o nome do
  // item vem de OCR sobre a tela do jogo E de um arquivo que o usuário edita à
  // mão. É conteúdo não confiável terminando dentro desta página.
  alvo.textContent = texto === null || texto === undefined ? "" : texto;
}

/**
 * Uma linha da calculadora, clonada do molde da marcação.
 *
 * NENHUMA MARCAÇÃO É MONTADA EM STRING. O clone do molde não passa por nenhuma
 * das quatro sondas de marcação que a suite já roda, e é por isso que ele é a
 * rota certa — não por ser mais elegante.
 *
 * NENHUMA DECISÃO VISUAL MORA AQUI. A linha recebe dois atributos e o CSS decide
 * o que aparece. Uma condição de tela escrita em JavaScript é uma condição que
 * não aparece na folha de estilo.
 *
 * NENHUMA CONTAGEM É COMPARADA COM UM PISO. O estado de cada linha chega PRONTO
 * do Python; duas autoridades sobre o mesmo piso divergem na primeira vez que
 * alguém mudar uma delas.
 */
function montarUmaRota(molde, item) {
  const fragmento = molde.content.cloneNode(true);
  const linha = fragmento.querySelector(".rota");

  linha.setAttribute("data-estado", item.estado);
  // A VENCEDORA VIRA ATRIBUTO, e o empate vira cadeia vazia — que é o que faz
  // NENHUMA das duas marcas aparecer, sem precisar de uma terceira regra.
  linha.setAttribute(
    "data-vencedora",
    item.vencedora === null ? "" : item.vencedora
  );
  // O DADO VELHO DA LINHA É DA LINHA, e não do `<body>`. O atributo tem o mesmo
  // NOME do ortogonal da Fase 1 — uma só palavra para o mesmo conceito — mas
  // mora aqui, porque a pergunta "esta leitura está velha?" tem uma resposta por
  // item. O limiar é o mesmo, e ele já foi aplicado no Python.
  linha.setAttribute("data-velho", item.velho ? "sim" : "nao");

  escreverNoVao(fragmento, "item", item.nome_exibido);
  // A FRASE DE FALTA É ESTA, e ela ocupa o lugar do veredito na marcação. Nos
  // quatro estados sem vencedora o Python manda a frase que explica o que
  // faltou; nos outros dois ela vem nula, o vão fica vazio, e o CSS o retira.
  escreverNoVao(fragmento, "aviso", item.aviso);

  // OS DOIS `if` ABAIXO NÃO SÃO CONDIÇÃO DE TELA — são guarda contra ler
  // propriedade de `null`. Nos estados de quebra o Python manda os dois lados
  // NULOS de propósito, e `item.npc.texto` lançaria. Quem decide o que aparece
  // continua sendo o CSS, pelo atributo de estado que a linha acabou de receber.
  if (item.npc !== null) {
    escreverNoVao(fragmento, "npc-valor", item.npc.texto);
    escreverNoVao(fragmento, "npc-pacote", item.npc.pacote_texto);
  }
  if (item.mercado !== null) {
    escreverNoVao(fragmento, "mercado-valor", item.mercado.texto);
  }

  // A MEDIANA É CONTEXTO, e o `n` dela viaja junto em vez de a tela reusar o `n`
  // da linha: os dois pisos podem deixar de ser o mesmo, e aí os dois números
  // discordariam sobre a mesma linha.
  escreverNoVao(fragmento, "mediana", item.mediana.texto);
  escreverNoVao(
    fragmento,
    "mediana-n",
    item.mediana.n === null ? "" : "n=" + item.mediana.n
  );

  if (item.diferenca !== null) {
    escreverNoVao(fragmento, "diferenca-xm", item.diferenca.xm);
    escreverNoVao(fragmento, "diferenca-percentual", item.diferenca.percentual);
    // A PARTE DE R$ NÃO GANHA UM `if`, E A AUSÊNCIA DELE É O PONTO.
    //
    // Quando não há câmbio informado o Python manda este campo NULO, o
    // `escreverNoVao` escreve cadeia vazia, e a regra
    // `body[data-cambio="ausente"]` retira o vão da tela — a MESMA regra, no
    // mesmo agrupamento de seletores, que já retira o cartão de R$ do destaque.
    //
    // Um `if (item.diferenca.reais === null)` aqui seria uma condição de tela
    // escrita em JavaScript: uma condição que NÃO aparece na folha de estilo. As
    // duas versões da verdade divergiriam no primeiro ajuste, sem quebrar nada
    // em voz alta — o cartão sumindo lá em cima e a linha ficando aqui embaixo,
    // sobre o mesmo câmbio que não existe. Há teste desta fase procurando por
    // essa comparação, com controle sobre um trecho de mentira que a contém.
    escreverNoVao(fragmento, "diferenca-reais", item.diferenca.reais);
  }

  // O `n=` é um RÓTULO nosso, e não uma reescrita do valor: o número entra do
  // jeito que veio. Sem contagem, sem rótulo — um `n` sem número ao lado não
  // qualifica nada.
  escreverNoVao(fragmento, "n", item.n === null ? "" : "n=" + item.n);
  escreverNoVao(fragmento, "recencia", item.recencia);

  return fragmento;
}

/**
 * A quarta região inteira.
 *
 * `calculadora` é `null` nos dois estados de falha fechada, e aí não há nada a
 * desenhar — o CSS já retirou o painel da tela junto com os outros três, pela
 * regra de `.painel` que já existia.
 */
function pintarAsRotas(calculadora) {
  const lista = document.getElementById("rotas-lista");
  if (lista === null) {
    return;
  }

  if (calculadora === null || calculadora === undefined) {
    escrever("rotas-aviso", "");
    escrever("rotas-lidos-em", "");
    lista.textContent = "";
    assinaturaDasRotas = null;
    return;
  }

  // A frase de bloco e o instante da leitura vêm PRONTOS do Python. O CSS
  // esconde cada um quando está vazio — decidir se a linha aparece continua
  // sendo do CSS.
  escrever("rotas-aviso", calculadora.aviso === null ? "" : calculadora.aviso);
  escrever(
    "rotas-lidos-em",
    calculadora.itens_lidos_em === null ? "" : calculadora.itens_lidos_em
  );

  const assinatura = JSON.stringify(calculadora.itens);
  if (assinatura === assinaturaDasRotas) {
    return;
  }
  assinaturaDasRotas = assinatura;

  const molde = document.getElementById("molde-da-rota");
  if (molde === null) {
    return;
  }

  // `textContent = ""` esvazia a lista sem tocar em nenhuma propriedade de
  // marcação.
  lista.textContent = "";
  calculadora.itens.forEach(function (item) {
    lista.appendChild(montarUmaRota(molde, item));
  });
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

// ===========================================================================
// O COMPONENTE DE SÉRIE — GENÉRICO POR CONSTRUÇÃO (DASH-05)
// ===========================================================================
//
// A PALAVRA QUE NOMEIA A SÉRIE DE HOJE NÃO APARECE NESTE ARQUIVO NEM NO CSS, e
// isso é estrutural em vez de uma intenção: esta função recebe UM elemento da
// lista `series` do payload e mais nada. Ela não sabe qual série está
// desenhando, e é por isso que a segunda instância não pede código novo.
//
// Há teste afirmando as duas metades da mesma coisa: que a palavra não está no
// JS nem no CSS, E que ela ESTÁ no que o Python serve. Sem a segunda metade, o
// teste ficaria verde num projeto onde a palavra simplesmente não existe em
// lugar nenhum — provando a genericidade pelo motivo errado.
//
// O CONTRATO DE PROPRIEDADES, E AS DUAS DIVERGÊNCIAS DECLARADAS
// ==============================================================
// O `01-UI-SPEC.md` escreve o contrato como
// `{ titulo, unidade, pontos[], formatador, rotulo_principal, rotulo_tipico }`.
// O que este arquivo consome é `{ titulo, unidade, pontos, baldes,
// rotulo_principal, rotulo_tipico }`, e as duas diferenças têm razão:
//
//   - `formatador` NÃO CHEGA como propriedade porque ele já foi APLICADO. O
//     ponto de decisão único (`formatador_do_unitario`) roda no Python, e o que
//     atravessa a fronteira HTTP é o resultado dele: `menor_texto` e
//     `tipica_texto`, prontos. Receber a função aqui exigiria reimplementá-la em
//     JavaScript, que é exatamente o segundo formatador que o DASH-03 recusa.
//   - `baldes` chega A MAIS porque o UI-SPEC pede que o zoom largo agregue por
//     mediana inferior, e essa conta não pode acontecer aqui: ela é ordenação de
//     fração exata, e no navegador viraria ordenação de ponto flutuante. O
//     Python manda as três larguras já agregadas; a janela do zoom é decisão do
//     navegador, a CONTA não é.
//
// Há teste afirmando que o conjunto de propriedades lidas nesta região é
// EXATAMENTE esse, e nenhuma a mais.
//
// <<< COMPONENTE-DE-SERIE

// As três larguras que o payload traz, e o alcance visível até o qual cada uma
// serve.
//
// ATÉ 2026-09-03 HAVIA UMA QUARTA ENTRADA AQUI: `{ nome: null, ate:
// SEGUNDOS_POR_DIA }`, a série CRUA — um ponto por instante de leitura
// (CTX-1), usada sempre que a janela visível cabia num dia. ELA FOI RETIRADA
// PORQUE O PRÓPRIO USUÁRIO MEDIU O DEFEITO NA TELA REAL: subir e descer de
// andar faz o painel ser relido várias vezes em poucos minutos, e a série crua
// desenhava cada releitura como se fosse outra oferta — o mínimo balançando
// para cima e para baixo entre pontos vizinhos, sem que o mercado tivesse
// mudado. `cinco_minutos` já existia (as três larguras chegam prontas do
// Python) e já resolve isso: dentro do balde, o valor exibido é o `median_low`
// das releituras daquela janela, e CTX-1 continua valendo — cada elemento do
// balde é um ponto que existiu, só que agora o zoom mais fechado também
// agrega em vez de desenhar cada instante cru.
//
// ESTES LIMITES CONTINUAM SENDO ESCOLHA, E NÃO MEDIÇÃO — só o de baixo (a
// série crua) tinha virado medição, e a medição reprovou ele. Se um dia
// `cinco_minutos` também ficar denso demais, o número muda aqui — e nada mais
// no arquivo precisa saber.
const SEGUNDOS_POR_HORA = 3600;
const SEGUNDOS_POR_DIA = 24 * SEGUNDOS_POR_HORA;
const RESOLUCOES = [
  { nome: "cinco_minutos", ate: SEGUNDOS_POR_DIA * 7 },
  { nome: "uma_hora", ate: SEGUNDOS_POR_DIA * 60 },
  { nome: "um_dia", ate: Infinity },
];

// AS TRÊS EXCEÇÕES DECLARADAS DA ESCALA DE ESPAÇAMENTO, do `dashboard.css`:
// espessura de linha do gráfico é parâmetro da BIBLIOTECA e não CSS de layout,
// e por isso ela mora aqui e não lá. Sólido de dois contra tracejado de um e
// meio.
//
// E O TRAÇO NÃO É REDUNDÂNCIA DA COR. Sólido contra tracejado sobrevive a
// daltonismo, a monitor mal calibrado e ao `Gamma=1.16` do cliente; cor sozinha
// não sobreviveria a nenhum dos três. A legenda da marcação usa exatamente as
// mesmas duas formas, para que a amostra ao lado do rótulo seja a mesma coisa
// que a linha no gráfico.
const LARGURA_DA_LINHA_PRINCIPAL = 2;
const LARGURA_DA_LINHA_TIPICA = 1.5;
const TRACEJADO_DA_LINHA_TIPICA = [6, 4];
const LARGURA_DA_GRADE = 1;

// O quanto uma parada da roda aproxima ou afasta. Escolha, e não medição.
const PASSO_DO_ZOOM = 1.25;

// O botão do meio, na numeração do evento do navegador.
const BOTAO_DO_MEIO = 1;

// Quantas marcas do eixo vertical ainda cabem antes de os rótulos se
// atropelarem. ESCOLHA, E NÃO MEDIÇÃO, na mesma voz do bloco de `RESOLUCOES`
// logo acima: oito rótulos em uma coluna deixam respiro com a escala
// tipográfica de hoje, e se um dia ficar apertado o número muda aqui e nada
// mais no arquivo precisa saber.
const MAXIMO_DE_MARCAS_VISIVEIS = 8;

// O último conjunto de textos entregue ao gráfico. A dica sob o cursor lê daqui.
let textosDoGrafico = { instantes: [], principal: [], tipica: [] };

// AS ESCADAS DO EIXO VERTICAL, como o Python as entregou, da mais fina para a
// mais grossa — e a fatia delas que está na tela agora.
//
// ELES SÃO ESTADO DE MÓDULO PELA MESMA RAZÃO QUE `textosDoGrafico` É: a
// instância do gráfico é REAPROVEITADA entre voltas, e o objeto de opções que a
// criou fica preso à primeira série. Uma escada capturada lá dentro envelheceria
// na segunda volta e o eixo passaria a rotular a série antiga.
let escadasDoEixo = [];
let marcasDesenhadas = [];

let grafico = null;
let serieDesenhada = null;
let resolucaoAtual = null;
let alcanceTotal = null;
let trocandoDeResolucao = false;

/**
 * A paleta, PEDIDA AO CSS por nome de token.
 *
 * A biblioteca desenha em canvas, e canvas não herda CSS: a cor tem de ser
 * ENTREGUE a ela em configuração. Entregar um hexadecimal escrito aqui criaria
 * a segunda paleta do projeto, e ela divergiria da primeira no dia em que o tema
 * mudasse — sem quebrar nada em voz alta.
 *
 * Uma cor sem nome de token é uma cor que o gráfico não consegue pedir, e foi
 * exatamente por isso que a cor da linha da mediana ganhou token próprio no CSS
 * em vez de continuar sendo um literal solto.
 */
function paletaDoTema() {
  const raiz = getComputedStyle(document.documentElement);
  return {
    principal: raiz.getPropertyValue("--cor-ouro").trim(),
    tipica: raiz.getPropertyValue("--cor-serie-tipica").trim(),
    grade: raiz.getPropertyValue("--cor-grade").trim(),

    // ERA `--cor-texto-fraco` (6,12:1 sobre a placa). O usuário mediu o eixo
    // como pouco legível na tela real (2026-09-03), e `--cor-texto` é o mesmo
    // par já cobrado em `TestOContrasteFoiRecalculado` a 13,16:1 — sem token
    // novo, sem recontar contraste.
    rotulo: raiz.getPropertyValue("--cor-texto").trim(),
  };
}

/**
 * A fonte dos rótulos do gráfico, LIDA de um elemento que o CSS já dimensionou.
 *
 * Mesma razão da paleta, e a mesma armadilha: o canvas não herda a folha de
 * estilo, então a fonte precisa ser entregue como string. Escrever aqui o
 * tamanho e a família seria a segunda escala tipográfica do projeto.
 *
 * A linha de prova do estado vazio é o modelo porque ela já é exatamente o papel
 * que os rótulos do eixo têm: tamanho de rótulo, na fonte numérica. Ler dela é
 * pegar a decisão que o CSS já tomou, em vez de repeti-la.
 */
function fonteDosRotulos() {
  const modelo = document.getElementById("serie-vazio-prova");
  if (modelo === null) {
    return null;
  }
  const estilo = getComputedStyle(modelo);
  return estilo.fontSize + " " + estilo.fontFamily;
}

/**
 * O carimbo do Python virando o número que o eixo do tempo entende.
 *
 * `Date.parse` de um carimbo SEM FUSO é lido como hora LOCAL, e é isso que se
 * quer: o CSV grava `agora.isoformat()` sem fuso, e o projeto inteiro usa hora
 * local ingênua. Introduzir fuso aqui criaria duas convenções de tempo na mesma
 * tela.
 */
function emSegundos(carimbo) {
  return Date.parse(carimbo) / MILISSEGUNDOS_POR_SEGUNDO;
}

function conjuntoCru(serie) {
  const pontos = serie.pontos;
  return {
    dados: [
      pontos.map(function (ponto) {
        return emSegundos(ponto.instante);
      }),
      pontos.map(function (ponto) {
        return ponto.menor_pixel;
      }),

      // A MEDIANA AUSENTE VIRA VÃO NA LINHA, E NUNCA ZERO. O payload manda
      // `null` — nunca `0.0` — e a razão é a mesma do lado de lá: zero é uma
      // POSIÇÃO no eixo, e desenhar a ausência ali afirmaria que a taxa
      // desabou. Abaixo do piso de evidência a linha simplesmente não existe
      // naquele instante, e o texto da dica traz a frase de falta do Python.
      pontos.map(function (ponto) {
        return ponto.tipica_pixel;
      }),
    ],
    textos: {
      instantes: pontos.map(function (ponto) {
        // O `n=` é rótulo, e não reescrita: a contagem entra do jeito que veio.
        return ponto.instante + "  n=" + ponto.n;
      }),
      principal: pontos.map(function (ponto) {
        return ponto.menor_texto;
      }),
      tipica: pontos.map(function (ponto) {
        return ponto.tipica_texto;
      }),
    },
  };
}

/**
 * Um dos três conjuntos de balde, com as duas linhas ALINHADAS no mesmo eixo.
 *
 * O Python agrega cada linha separadamente, e por isso os instantes das duas não
 * coincidem: um balde pode ter menor e não ter mediana. A biblioteca exige um
 * eixo horizontal só, então as duas listas são reunidas pela união dos
 * instantes, com vão onde a linha não tem valor.
 *
 * REUNIR NÃO É AGREGAR. Nenhum valor novo nasce aqui: cada número continua sendo
 * o que o Python calculou com mediana inferior sobre fração exata, e o vão
 * continua sendo vão. A regra do D-02 — um número exibido tem de ter existido —
 * atravessa esta função intacta.
 *
 * A ORDENAÇÃO É SOBRE O CARIMBO EM TEXTO, e é correta por construção: todos os
 * carimbos vêm do mesmo `isoformat()`, com o mesmo comprimento e os campos do
 * mais significativo para o menos, então a ordem alfabética É a ordem
 * cronológica.
 */
function conjuntoDeBalde(serie, nome) {
  const balde = serie.baldes[nome];
  const porInstante = new Map();

  function guardar(lista, ondePoeOPixel, ondePoeOTexto) {
    lista.forEach(function (item) {
      let achado = porInstante.get(item.instante);
      if (achado === undefined) {
        achado = { principal: null, tipica: null, textoPrincipal: "", textoTipica: "" };
        porInstante.set(item.instante, achado);
      }
      achado[ondePoeOPixel] = item.pixel;
      achado[ondePoeOTexto] = item.texto;
    });
  }

  guardar(balde.principal, "principal", "textoPrincipal");
  guardar(balde.tipica, "tipica", "textoTipica");

  const instantes = Array.from(porInstante.keys()).sort();
  const reunidos = instantes.map(function (instante) {
    return porInstante.get(instante);
  });

  return {
    dados: [
      instantes.map(emSegundos),
      reunidos.map(function (item) {
        return item.principal;
      }),
      reunidos.map(function (item) {
        return item.tipica;
      }),
    ],
    textos: {
      // SEM `n` NO BALDE, e isso é honestidade e não esquecimento: `n` é a
      // contagem de ofertas de UM instante, e um balde é vários instantes.
      // Somar as contagens produziria um número que não qualifica o valor
      // exibido — o valor exibido é o de um instante só, escolhido por mediana
      // inferior entre os do balde.
      instantes: instantes,
      principal: reunidos.map(function (item) {
        return item.textoPrincipal;
      }),
      tipica: reunidos.map(function (item) {
        return item.textoTipica;
      }),
    },
  };
}

function resolucaoPara(alcanceVisivel) {
  for (let i = 0; i < RESOLUCOES.length; i += 1) {
    if (alcanceVisivel <= RESOLUCOES[i].ate) {
      return RESOLUCOES[i].nome;
    }
  }
  return RESOLUCOES[RESOLUCOES.length - 1].nome;
}

function conjuntoNaResolucao(serie, nome) {
  return nome === null ? conjuntoCru(serie) : conjuntoDeBalde(serie, nome);
}

/**
 * As marcas do eixo vertical para a janela visível: FILTRA e ESCOLHE, e é tudo.
 *
 * O MESMO MOLDE DE `resolucaoPara`, E PELA MESMA RAZÃO. As escadas chegam do
 * Python da mais fina para a mais grossa, e esta função fica com a PRIMEIRA cujo
 * número de marcas dentro da janela ainda cabe na coluna. Filtrar por faixa é
 * SELEÇÃO, não formatação: nenhum dígito é composto aqui, e o texto de cada
 * marca é o que o Python escreveu.
 *
 * SEM ESCADA NENHUMA, LISTA VAZIA. A biblioteca então desenha o eixo sem marca,
 * que é honesto; inventar uma marca seria inventar uma unidade.
 */
function marcasVisiveis(minimoDaJanela, maximoDaJanela) {
  for (let posicao = 0; posicao < escadasDoEixo.length; posicao += 1) {
    const naJanela = escadasDoEixo[posicao].marcas.filter(function (marca) {
      return marca.pixel >= minimoDaJanela && marca.pixel <= maximoDaJanela;
    });
    if (naJanela.length <= MAXIMO_DE_MARCAS_VISIVEIS) {
      return naJanela;
    }
  }
  return [];
}

/**
 * A dica sob o cursor, montada a partir das STRINGS do ponto.
 *
 * A REGRA, QUE É A MESMA DA FRONTEIRA DO `float`: o número no payload é o PIXEL,
 * e a string é a VERDADE. O `float` existe porque o canvas só aceita número de
 * JS, e o erro dele foi medido — pior caso `7,76e-11` na escala de cinco
 * milhões (era `1,9e-11` enquanto a escala era o milhão; o número subiu junto
 * com a escala, e o erro RELATIVO caiu). Ele serve para posicionar uma linha;
 * ele NÃO serve para ser lido. O que o usuário lê é a string que o Python
 * formatou, e é por isso que cada ponto viaja com as duas coisas.
 */
function textoSobOCursor(qualLista) {
  return function (instancia, valor, indiceDaSerie, indiceDoPonto) {
    if (indiceDoPonto === null || indiceDoPonto === undefined) {
      return "";
    }
    const texto = qualLista()[indiceDoPonto];
    return texto === null || texto === undefined ? "" : texto;
  };
}

function opcoesDoGrafico(serie, area) {
  const paleta = paletaDoTema();
  const fonte = fonteDosRotulos();
  const eixo = {
    stroke: paleta.rotulo,
    grid: { stroke: paleta.grade, width: LARGURA_DA_GRADE },
    ticks: { stroke: paleta.grade, width: LARGURA_DA_GRADE },
  };
  if (fonte !== null) {
    eixo.font = fonte;
    eixo.labelFont = fonte;
  }

  return {
    width: area.clientWidth,
    height: area.clientHeight,
    scales: { x: { time: true }, y: {} },

    // TODA MUDANÇA DE JANELA PASSA POR AQUI, venha ela da roda, do arrasto de
    // deslocamento, do zoom por seleção nativo, do clique duplo que a biblioteca
    // já usa para restaurar, ou do botão. Um gancho só, em vez de uma chamada
    // repetida em cada manipulador: caminhos que se esquecem de avisar são
    // exatamente como a resolução do desenho passa a discordar da janela visível.
    hooks: {
      setScale: [
        function (instancia, chave) {
          if (chave === "x") {
            ajustarAResolucao();
          }
        },
      ],

      // A DICA SOB O CURSOR reage aqui, e não a um `mousemove` próprio: este
      // gancho já traz o `idx` do ponto mais perto resolvido pela biblioteca
      // (roda, arrasto, teclado, toque — os mesmos caminhos que mudam a janela
      // acima), então não há um segundo cálculo de "qual ponto é este" a
      // divergir do que a legenda nativa já mostra.
      setCursor: [
        function (instancia) {
          atualizarADica(instancia);
        },
      ],
    },
    axes: [
      Object.assign({}, eixo),

      // O RÓTULO DO EIXO VERTICAL É A UNIDADE QUE VEIO DO PYTHON, inteira. Ela
      // muda com a série — a taxa e o unitário comum têm unidades diferentes —,
      // e é justamente por isso que ela é propriedade do objeto e não uma
      // constante deste arquivo.
      //
      // E AGORA AS MARCAS E OS TEXTOS DELAS TAMBÉM VÊM DE LÁ. O navegador só
      // escolhe QUAL escada cabe na janela; ele não compõe um dígito.
      //
      // A ORDEM DAS DUAS CHAMADAS É GARANTIDA PELA BIBLIOTECA, E FOI LIDA E NÃO
      // SUPOSTA: na passagem de eixos do pacote vendorizado (`vendor/uPlot.iife.
      // min.js`, v1.6.32) as duas saem na MESMA expressão, `_splits` primeiro e
      // `_values` logo em seguida, recebendo exatamente aquelas posições. É isso
      // que autoriza `values` a ler o que `splits` acabou de guardar em vez de
      // recalcular a seleção — recalcular seria a segunda oportunidade de os
      // dois discordarem.
      Object.assign({}, eixo, {
        label: serie.unidade,
        splits: function (instancia, indice, minimoDaEscala, maximoDaEscala) {
          marcasDesenhadas = marcasVisiveis(minimoDaEscala, maximoDaEscala);
          return marcasDesenhadas.map(function (marca) {
            return marca.pixel;
          });
        },
        values: function () {
          return marcasDesenhadas.map(function (marca) {
            return marca.texto;
          });
        },
      }),
    ],
    series: [
      {
        value: textoSobOCursor(function () {
          return textosDoGrafico.instantes;
        }),
      },
      {
        label: serie.rotulo_principal,
        stroke: paleta.principal,
        width: LARGURA_DA_LINHA_PRINCIPAL,

        // Vão é VÃO. Sem esta linha a biblioteca ligaria os dois lados de uma
        // ausência com uma reta, desenhando uma variação que ninguém observou.
        spanGaps: false,
        value: textoSobOCursor(function () {
          return textosDoGrafico.principal;
        }),
      },
      {
        label: serie.rotulo_tipico,
        stroke: paleta.tipica,
        width: LARGURA_DA_LINHA_TIPICA,
        dash: TRACEJADO_DA_LINHA_TIPICA,
        spanGaps: false,
        value: textoSobOCursor(function () {
          return textosDoGrafico.tipica;
        }),
      },
    ],
  };
}

/**
 * Troca a resolução do desenho quando a janela visível muda de ordem de
 * grandeza. A JANELA é decisão do navegador; a CONTA não é.
 *
 * A trava existe porque entregar dados novos faz a biblioteca reavaliar as
 * escalas, o que chama de volta o gancho que chamou esta função. Sem ela, a
 * primeira rodada da roda entraria em recursão.
 */
function ajustarAResolucao() {
  if (grafico === null || serieDesenhada === null || trocandoDeResolucao) {
    return;
  }
  const desejada = resolucaoPara(grafico.scales.x.max - grafico.scales.x.min);
  if (desejada === resolucaoAtual) {
    return;
  }
  trocandoDeResolucao = true;
  resolucaoAtual = desejada;
  const conjunto = conjuntoNaResolucao(serieDesenhada, desejada);
  textosDoGrafico = conjunto.textos;
  grafico.setData(conjunto.dados, false);
  trocandoDeResolucao = false;
}

// ===========================================================================
// O ZOOM POR RODA E O ARRASTO DE DESLOCAMENTO — CÓDIGO NOSSO, E EIS A MEDIÇÃO
// ===========================================================================
//
// A REFUTAÇÃO, COM O NÚMERO, PORQUE ELA CONTRARIA O QUE O UI-SPEC AFIRMAVA.
// ------------------------------------------------------------------------
// O `01-UI-SPEC.md` escreveu, sobre o gráfico: *"Zoom do gráfico: Roda do mouse
// e arrasto, pela biblioteca"*, e justificou com *"Toda biblioteca dessa classe
// faz isso com config"*.
//
// **Medido, e falso para a biblioteca que usamos.** A varredura sobre o arquivo
// minificado das três candidatas contou os nomes de evento que cada uma
// registra:
//
//     escolhida  -> click, dblclick, mousedown, mouseenter, mouseleave,
//                   mousemove, mouseup, resize, scroll ....... ZERO `wheel`
//     segunda    -> click, dblclick, mousedown, mousemove, mouseout,
//                   mouseover, mouseup, resize, touchstart ... ZERO `wheel`
//     terceira   -> ................................. 2x `wheel`, 2x `deltaY`
//
// E a documentação oficial da escolhida confirma o mecanismo, textualmente:
// **"No built-in drag scrolling/panning"**, e o zoom por roda *"can be added
// externally via the plugin/hooks API"*, com dois demos oficiais. O zoom por
// SELEÇÃO retangular, esse sim, é nativo — e por isso não é reescrito aqui.
//
// ESTAS LINHAS SÃO CONSEQUÊNCIA DESSA MEDIÇÃO, E NÃO CAPRICHO. A alternativa
// óbvia — a terceira candidata, a única que trazia o evento pronto — foi
// recusada por outros três motivos, e nenhum deles é o `wheel`: veredito de
// legitimidade suspeito por ser nova demais, quase quatro vezes o tamanho
// vendorizado, e o risco não medido de ela ser feita para grade temporal
// REGULAR enquanto a nossa série é esparsa e irregular. Trinta linhas nossas
// custam menos que qualquer um dos três.
//
// A COLISÃO DE GESTOS, DITA POR EXTENSO. O arrasto com o botão principal já é o
// zoom por seleção NATIVO, e ele não se reescreve — então o deslocamento não
// pode morar no mesmo gesto. Ele mora no arrasto com a tecla de maiúsculas
// pressionada, e no arrasto com o botão do meio. O clique duplo, que a
// biblioteca já usa para restaurar o alcance, continua valendo, e o botão da
// tela faz a mesma coisa com o nome escrito.

function ligarOZoomEODeslocamento(instancia) {
  const sobreposicao = instancia.over;

  sobreposicao.addEventListener(
    "wheel",
    function (evento) {
      // O NAVEGADOR PODE IGNORAR ESTA CHAMADA SEM AVISAR. Um ouvinte de roda
      // registrado sem a opção abaixo é tratado como passivo em vários
      // contextos, e aí o pedido de não rolar a página é descartado em
      // silêncio: o gráfico aproximaria E a página desceria junto.
      evento.preventDefault();

      const caixa = sobreposicao.getBoundingClientRect();
      const alvo = instancia.posToVal(evento.clientX - caixa.left, "x");
      const minimo = instancia.scales.x.min;
      const maximo = instancia.scales.x.max;

      // O ZOOM É EM TORNO DO CURSOR, e não do centro: o instante que está
      // debaixo do ponteiro continua debaixo do ponteiro depois da parada da
      // roda. Zoom centrado no meio obriga a pessoa a corrigir a posição a cada
      // passo, e é a diferença entre navegar e caçar.
      const fator = evento.deltaY < 0 ? 1 / PASSO_DO_ZOOM : PASSO_DO_ZOOM;
      instancia.setScale("x", {
        min: alvo - (alvo - minimo) * fator,
        max: alvo + (maximo - alvo) * fator,
      });
    },
    { passive: false }
  );

  sobreposicao.addEventListener("mousedown", function (evento) {
    const querDeslocar = evento.shiftKey || evento.button === BOTAO_DO_MEIO;
    if (!querDeslocar) {
      // Arrasto simples é o zoom por seleção nativo. Sair daqui é o que o
      // preserva.
      return;
    }
    evento.preventDefault();

    const partiuDe = evento.clientX;
    const minimoInicial = instancia.scales.x.min;
    const maximoInicial = instancia.scales.x.max;
    const larguraEmValor = maximoInicial - minimoInicial;
    const larguraEmPixel = sobreposicao.clientWidth;
    if (larguraEmPixel === 0) {
      return;
    }

    function arrastar(movimento) {
      const andou = ((movimento.clientX - partiuDe) / larguraEmPixel) * larguraEmValor;
      instancia.setScale("x", {
        min: minimoInicial - andou,
        max: maximoInicial - andou,
      });
    }

    // OS OUVINTES DE MOVIMENTO FICAM NO DOCUMENTO, e não na sobreposição: quem
    // arrasta rápido tira o ponteiro do gráfico no meio do gesto, e um ouvinte
    // preso ao elemento perderia o resto do arrasto e o `mouseup` — deixando a
    // janela grudada no ponteiro para sempre.
    function soltar() {
      document.removeEventListener("mousemove", arrastar);
      document.removeEventListener("mouseup", soltar);
    }

    document.addEventListener("mousemove", arrastar);
    document.addEventListener("mouseup", soltar);
  });
}

/**
 * A DICA SOB O CURSOR: mínimo e mediana do instante apontado, perto do
 * ponteiro. Chamada uma vez por instância, no mesmo lugar que já liga o zoom.
 *
 * `mouseleave` É NECESSÁRIO ALÉM DO `setCursor`: a biblioteca zera o `idx` ao
 * sair, mas o navegador entrega os dois eventos em ordens que não são a mesma
 * em todo motor — sem este ouvinte próprio, a dica ficaria presa na tela em
 * alguns navegadores até o próximo movimento do mouse sobre o gráfico.
 */
function ligarADica(instancia) {
  instancia.over.addEventListener("mouseleave", function () {
    const dica = document.getElementById("serie-dica");
    if (dica !== null) {
      dica.hidden = true;
    }
  });
}

/**
 * Escreve e posiciona a dica para o ponto sob o cursor de agora.
 *
 * A POSIÇÃO USA `getBoundingClientRect`, A MESMA TÉCNICA DO ARRASTO ACIMA — e
 * não `instancia.over` como pai direto da dica: destruir o gráfico
 * (`apagarOGrafico`, no caminho em que a série fica sem ponto nenhum) apagaria
 * a dica junto, e nenhum código a recriaria depois. A dica mora na marcação,
 * sempre; só a posição dela é calculada aqui.
 *
 * O TEXTO É SEMPRE A STRING QUE `textosDoGrafico` JÁ GUARDA — a mesma fonte da
 * legenda nativa (`textoSobOCursor`), nunca um número recalculado (DASH-03).
 */
function atualizarADica(instancia) {
  const dica = document.getElementById("serie-dica");
  const area = document.getElementById("serie-area");
  if (dica === null || area === null) {
    return;
  }

  const indice = instancia.cursor.idx;
  if (indice === null || indice === undefined) {
    dica.hidden = true;
    return;
  }

  const caixaDaArea = area.getBoundingClientRect();
  const caixaDaSobreposicao = instancia.over.getBoundingClientRect();

  escrever("serie-dica-tempo", textosDoGrafico.instantes[indice] || "");
  escrever("serie-dica-principal", textosDoGrafico.principal[indice] || "");
  escrever("serie-dica-tipica", textosDoGrafico.tipica[indice] || "");

  dica.hidden = false;
  dica.style.left =
    caixaDaSobreposicao.left - caixaDaArea.left + instancia.cursor.left + "px";
  dica.style.top =
    caixaDaSobreposicao.top - caixaDaArea.top + instancia.cursor.top + "px";
}

function apagarOGrafico() {
  if (grafico !== null) {
    grafico.destroy();
    grafico = null;
  }
  serieDesenhada = null;
  resolucaoAtual = null;
  alcanceTotal = null;

  // A dica sobrevive à destruição do gráfico (ela mora na marcação, não em
  // `instancia.over`) — sem esconder aqui, ela ficaria presa na tela por cima
  // da placa de estado vazio, mostrando o último ponto de um gráfico que já
  // não existe.
  const dica = document.getElementById("serie-dica");
  if (dica !== null) {
    dica.hidden = true;
  }
}

/**
 * Desenha UMA série. A instância de hoje é apenas a primeira chamada.
 *
 * O ESTADO VAZIO NÃO É DESENHADO AQUI, E ISSO É DE PROPÓSITO. Os eixos, a grade,
 * a placa central e a legenda já estão no CSS e na marcação, governados pelo
 * atributo de estado — gráfico vazio mudo está proibido, e a proibição foi
 * cumprida do lado que desenha. Instanciar a biblioteca sem ponto nenhum aqui
 * produziria um quadro em branco POR CIMA da placa, que é o oposto do combinado.
 */
function desenharUmaSerie(serie) {
  // O título vem do nome exibido, que atravessa o OCR e oscila. Texto, nunca
  // marcação; e o texto completo no atributo de título, porque o CSS corta a
  // linha com reticência e quem precisa do nome inteiro tem de alcançá-lo.
  escrever("serie-titulo", serie.titulo);
  anotarOTextoCompleto("serie-titulo", serie.titulo);

  const area = document.getElementById("serie-grafico");
  if (area === null) {
    return;
  }

  if (serie.pontos.length === 0) {
    apagarOGrafico();
    return;
  }

  const biblioteca = window[NOME_GLOBAL_DA_BIBLIOTECA];
  if (biblioteca === undefined) {
    // Os números do destaque continuam na tela: a falta da biblioteca de
    // gráfico não pode derrubar a metade da página que não depende dela.
    console.error("dashboard: a biblioteca de grafico nao carregou");
    return;
  }

  // O ALCANCE TOTAL SAI SEMPRE DA SÉRIE CRUA, mesmo quando o desenho está num
  // balde: ele é o período inteiro que existe, e é isso que o botão restaura.
  const cru = conjuntoCru(serie);
  const eixoDoTempo = cru.dados[0];
  alcanceTotal = {
    min: eixoDoTempo[0],
    max: eixoDoTempo[eixoDoTempo.length - 1],
  };

  // NA MESMA LINHA EM QUE `serieDesenhada` É ATUALIZADA, e essa vizinhança é a
  // razão: a instância do gráfico é reaproveitada entre voltas, e o eixo lê a
  // escada por esta variável justamente para não ficar preso à série que criou
  // as opções.
  serieDesenhada = serie;
  escadasDoEixo = serie.escadas_do_eixo;

  if (grafico === null) {
    // A PRIMEIRA PINTURA PASSA PELA MESMA ESCOLHA DE RESOLUÇÃO QUE O ZOOM
    // USA — nunca crua por padrão. Não dá para deixar `ajustarAResolucao`
    // decidir sozinha aqui: o gancho `setScale` da biblioteca já dispara
    // DURANTE `new biblioteca(...)`, antes desta atribuição terminar, e a
    // trava de `grafico === null` faria aquele primeiro disparo sair sem
    // fazer nada — foi assim que a série crua virava o padrão silencioso até
    // o usuário mexer no zoom uma vez.
    resolucaoAtual = resolucaoPara(alcanceTotal.max - alcanceTotal.min);
    const inicial = conjuntoNaResolucao(serie, resolucaoAtual);
    textosDoGrafico = inicial.textos;
    grafico = new biblioteca(opcoesDoGrafico(serie, area), inicial.dados, area);
    ligarOZoomEODeslocamento(grafico);
    ligarADica(grafico);
    return;
  }

  // A INSTÂNCIA É REAPROVEITADA, e esta é a linha que mais importa do laço.
  // Recriar o gráfico a cada volta jogaria fora, de dois em dois segundos, o
  // zoom que o usuário acabou de dar — um defeito que não aparece em teste
  // nenhum e aparece na primeira vez que alguém tenta olhar uma tarde
  // específica. `false` no segundo argumento é o que preserva a escala.
  const conjunto = conjuntoNaResolucao(serie, resolucaoAtual);
  textosDoGrafico = conjunto.textos;
  grafico.setData(conjunto.dados, false);
}

/**
 * Devolve o período inteiro. Sem este botão o usuário fica preso no zoom.
 */
function verTodoOPeriodo() {
  if (grafico === null || alcanceTotal === null) {
    return;
  }
  if (alcanceTotal.max <= alcanceTotal.min) {
    // Um ponto só não tem período para restaurar, e pedir à biblioteca uma
    // escala de largura zero é pedir uma divisão por zero.
    return;
  }
  grafico.setScale("x", { min: alcanceTotal.min, max: alcanceTotal.max });
}

// >>> COMPONENTE-DE-SERIE

// ===========================================================================
// O ENVIO DO CÂMBIO, SEM RECARREGAR
// ===========================================================================
//
// INTERCEPTAR O ENVIO É OBRIGATÓRIO, E NÃO UMA MELHORIA.
// -------------------------------------------------------
// A diretiva de segurança servida em toda resposta traz `form-action 'none'`, e
// o formulário da marcação NÃO TEM DESTINO — as duas coisas de propósito. Se
// este arquivo não impedisse o comportamento padrão, a tecla de confirmação
// dispararia um envio nativo que o NAVEGADOR BLOQUEIA, e o usuário não veria
// nada além de um erro no console: o botão simplesmente não faria nada.
//
// E essa é a FALHA FECHADA CERTA, e é por isso que a marcação foi escrita assim:
// se este arquivo morrer, o formulário não envia — em vez de recarregar a página
// para lugar nenhum, ou de vazar o câmbio para fora da máquina. Mas o
// interceptador é a metade que faz o caminho normal existir, e sem ele só
// sobraria a falha.
//
// A VALIDAÇÃO NÃO MORA AQUI, E ISSO TAMBÉM É DE PROPÓSITO.
// ---------------------------------------------------------
// As únicas conveniências do lado do navegador são o comprimento máximo e o tipo
// de teclado, e as duas moram na marcação. O JULGAMENTO do que é um câmbio
// válido é inteiro do servidor, no portão de duas camadas — e escrever aqui um
// "é número positivo?" seria um SEGUNDO validador, com a mesma doença do segundo
// formatador: duas opiniões sobre a mesma pergunta, divergindo em silêncio.
//
// A falha fechada de verdade está do lado de lá: um envio feito por fora desta
// página é recusado exatamente igual, e há teste em Python provando isso. O que
// este arquivo faz com uma recusa é uma coisa só — EXIBIR a frase que veio.

// As mesmas strings que o `dashboard.py` guarda do outro lado. As duas só podem
// divergir de um jeito: silenciosamente.
const CAMINHO_DO_CAMBIO = "/cambio";
const CAMPO_DO_POST = "cambio";

function enviarOCambio() {
  const campo = document.getElementById("campo-cambio");
  const botao = document.getElementById("botao-salvar");
  if (campo === null || botao === null) {
    return;
  }

  // O BOTÃO TROCA DE RÓTULO POR ATRIBUTO, e não por texto escrito daqui: os
  // dois rótulos moram na marcação e o CSS escolhe qual aparece. Assim a cópia
  // continua conferível por teste sobre o HTML, e este arquivo não vira o lugar
  // onde texto de interface se esconde. E ele NÃO vira indicador giratório.
  botao.setAttribute("data-salvando", "sim");
  botao.disabled = true;
  escrever("cambio-erro", "");

  const pedido = {};
  pedido[CAMPO_DO_POST] = campo.value;

  // UMA CONSULTA RELATIVA DO PRÓPRIO DOCUMENTO JÁ MANDA A ORIGEM SOZINHA, e é
  // disso que o portão de origem do servidor precisa. Não há nada a configurar —
  // mas mexer no modo ou na origem à mão quebraria o envio com uma recusa, e o
  // sintoma seria "o botão salvar não faz nada".
  return fetch(CAMINHO_DO_CAMBIO, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pedido),
  })
    .then(function (resposta) {
      return resposta.json().then(function (conteudo) {
        return { ok: resposta.ok, conteudo: conteudo };
      });
    })
    .then(function (resultado) {
      if (!resultado.ok) {
        // A FRASE VEM PRONTA DO SERVIDOR, e cada causa tem a sua: o texto
        // digitado, o histórico ilegível, a origem recusada, o corpo grande
        // demais, a gravação que falhou. Colapsar as cinco numa mensagem só
        // descreveria para o usuário um problema que não é o dele.
        //
        // E O CAMPO NÃO É LIMPO. O valor digitado permanece, para ninguém ter de
        // redigitar o que acabou de escrever — não há nenhuma atribuição de
        // valor vazio ao campo em caminho nenhum deste arquivo.
        if (typeof resultado.conteudo.erro === "string") {
          escrever("cambio-erro", resultado.conteudo.erro);
        } else {
          marcarOServidorComoMudo();
        }
        return null;
      }

      // A confirmação sai PRONTA do Python, com o carimbo dentro. Remontá-la
      // aqui seria o segundo formatador de dinheiro e de data na mesma linha.
      escrever("cambio-carimbo", resultado.conteudo.mensagem);

      // E O R$ APARECE SEM RECARREGAR: uma volta imediata repinta a tela com o
      // payload novo. Sem esta linha o usuário clicaria em salvar e não veria
      // nada acontecer até o próximo ciclo.
      //
      // Ela NÃO agenda nada: quem agenda é o laço, e chamar a volta completa
      // aqui criaria uma segunda corrente de temporizadores rodando em paralelo
      // com a primeira, dobrando a frequência de consulta a cada salvamento.
      return buscarOsDados();
    })
    .catch(function (erro) {
      // O servidor local não respondeu — e a frase para isso já existe, na
      // faixa do topo, com o tempo desde o último contato. Escrever aqui uma
      // segunda frase de "não consegui falar" seria uma cópia nova de um texto
      // que a página já tem.
      console.error("dashboard: falha ao salvar o cambio", erro);
      marcarOServidorComoMudo();
    })
    .then(function () {
      botao.setAttribute("data-salvando", "nao");
      botao.disabled = false;
    });
}

function ligarOFormularioDoCambio() {
  const formulario = document.getElementById("form-cambio");
  if (formulario === null) {
    return;
  }
  formulario.addEventListener("submit", function (evento) {
    evento.preventDefault();
    enviarOCambio();
  });
}

// ===========================================================================
// A PARTIDA
// ===========================================================================

// A BIBLIOTECA DE GRÁFICO É CARREGADA POR ESTE ARQUIVO, E ISSO É UMA COSTURA
// ENTRE PLANOS QUE FICA DECLARADA.
// ==========================================================================
// O `index.html` carrega a FOLHA DE ESTILO da biblioteca e o `dashboard.css`
// retematiza o que ela desenha — mas a marcação nunca ganhou a linha que carrega
// o CÓDIGO dela. Sem essa linha o objeto global não existe, e o gráfico não
// poderia ser instanciado de jeito nenhum.
//
// O conserto mais simples é uma linha de `<script src>` no `index.html`, ao lado
// da que já carrega este arquivo — e o teste de marcação da fase aceita vários
// scripts, desde que todos carreguem por arquivo. Esse conserto NÃO foi feito
// aqui porque o `index.html` está fora do alcance declarado deste plano; fica
// registrado como pendência nomeada, e não como surpresa.
//
// A CARGA POR CÓDIGO É LEGÍTIMA, E NÃO UM DESVIO DA CSP: `script-src 'self'`
// proíbe a forma EMBUTIDA e a origem de fora, e não a criação de um elemento com
// origem própria. O caminho é uma constante deste arquivo — nunca um valor vindo
// do payload —, então nada que atravesse a fronteira HTTP escolhe o que executa.
const ARQUIVO_DA_BIBLIOTECA = "vendor/uPlot.iife.min.js";
const NOME_GLOBAL_DA_BIBLIOTECA = "uPlot";

function carregarABiblioteca(depois) {
  if (window[NOME_GLOBAL_DA_BIBLIOTECA] !== undefined) {
    depois();
    return;
  }
  const elemento = document.createElement("script");
  elemento.src = ARQUIVO_DA_BIBLIOTECA;

  // NOS DOIS CASOS A PÁGINA SEGUE. Se a biblioteca não carregar, o destaque, a
  // procedência e o campo do câmbio continuam funcionando — perder o gráfico não
  // pode custar a metade da tela que responde "quanto vale agora".
  elemento.addEventListener("load", depois);
  elemento.addEventListener("error", function () {
    console.error("dashboard: nao consegui carregar " + ARQUIVO_DA_BIBLIOTECA);
    depois();
  });
  document.head.appendChild(elemento);
}

function comecar() {
  const botao = document.getElementById("ver-todo-o-periodo");
  if (botao !== null) {
    botao.addEventListener("click", verTodoOPeriodo);
  }

  ligarOFormularioDoCambio();

  window.addEventListener("resize", function () {
    const area = document.getElementById("serie-grafico");
    if (grafico !== null && area !== null) {
      grafico.setSize({ width: area.clientWidth, height: area.clientHeight });
    }
  });

  carregarABiblioteca(darUmaVolta);
}

document.addEventListener("DOMContentLoaded", comecar);
