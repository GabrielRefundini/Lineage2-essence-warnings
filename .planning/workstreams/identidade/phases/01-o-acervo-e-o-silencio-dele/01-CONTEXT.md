# Phase 1: O acervo e o silencio dele - Context

**Gathered:** 2026-08-31
**Workstream:** identidade
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 1 area, 5 decisoes, todas aceitas

<domain>
## Phase Boundary

Nasce um acervo duravel de assinaturas visuais que vive FORA do
`calibration.json`, e lido em todo arranque, sobrevive a uma rodada de
`calibrar.bat`, e cujas entradas SEM NOME sao reconhecidas sem virar sujeito
de alerta nenhum.

DENTRO DA FASE: a pasta, o formato, a chave, a leitura no arranque, a
convivencia com `cal.assinaturas`, e o silencio de uma entrada sem nome.

FORA DA FASE: aprender sozinho (Fase 2) e batizar pelo WhatsApp (Fase 3). Esta
fase NAO escreve entrada nenhuma por conta propria — ela le, e prova que uma
entrada posta a mao se comporta certo.

</domain>

<decisions>
## Implementation Decisions

### Area 1: A chave e o formato do acervo

- **A CHAVE E O HASH DO CONTEUDO DA ASSINATURA** (os bytes da mascara). Mesma
  pessoa produz os mesmos pixels, entao produz a mesma chave, sempre. Ela
  atende as tres exigencias que o ROADMAP deixou abertas de uma vez:
  estavel entre reinicios (o conteudo nao muda), independente da POSICAO
  (posicao e lugar, nao pessoa) e independente do NOME (que chega depois e
  pode ser corrigido — BATI-05). Um contador sequencial foi recusado: depende
  da ordem de chegada, e as duas instancias do usuario gerariam numeros
  conflitantes para a mesma pessoa.

- **UM ARQUIVO POR ENTRADA**, no molde do `.loot/`. O `O_CREAT|O_EXCL` resolve
  DURA-03 de graca e nao ha "ler-modificar-escrever" para corromper. Um JSON
  unico com todas seria simples ate as duas instancias gravarem juntas — que
  e a premissa do projeto desde a Fase 1, nao um caso raro.

- **O NOME MORA EM ARQUIVO IRMAO**, `nome_<hash>`, com o nick dentro. Batizar
  e criar um arquivo; corrigir (BATI-05) e trocar o conteudo dele, sem tocar
  na assinatura. Por o nome no NOME do arquivo obrigaria a renomear a cada
  correcao, e o `O_EXCL` deixaria de proteger a assinatura.

- **A PASTA E `.identidades/`**, irma de `.agenda/` e `.loot/`. Ela sobrevive
  ao `calibrar.bat` por NAO ESTAR no arquivo que ele reescreve — a garantia e
  estrutural, nao politica. Dentro do `.agenda/` seria fatal: a poda de 3 dias
  mataria assinaturas, e assinatura e como estatistica de loot, uma pergunta
  sobre meses.

- **O ACERVO NAO E PODADO, e o custo esta medido.** Uma assinatura serializada
  ocupa **562 bytes** (medido no `calibration.json` real do usuario em
  2026-08-31, com 4 assinaturas gravadas). Mil membros diferentes dariam cerca
  de 550 KB. O usuario avaliou e aceitou; nao ha comando de limpeza no v1.

### Claude's Discretion

- Qual funcao de hash, e quantos digitos do hex entram no nome do arquivo.
- Nome exato do modulo e da classe do acervo.
- Se o formato de serializacao reusa o dict de `Assinatura.como_dict` que ja
  existe (campos `nome`, `altura`, `largura`, `bits`) ou nasce proprio.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`l2scanner/identidade.py`** — `Assinatura`, a mascara de texto e a
  correlacao ja existem e ja funcionam. A medicao que decidiu o metodo esta na
  docstring do modulo: recorte justo mais mascara da 1.000 contra 0.454, margem
  0.546. Esta fase NAO mexe no reconhecimento; ela muda de ONDE vem a lista.
- **O formato ja serializado** — `calibration.json` guarda assinaturas com os
  campos `nome`, `altura`, `largura`, `bits`, 562 bytes cada. Reusar em vez de
  inventar um segundo formato para a mesma coisa.
- **`loot.RegistroDeLoot`** — o precedente EXATO de acervo duravel, nunca
  podado, compartilhado por duas instancias, com `O_CREAT|O_EXCL` e tri-estado
  deliberado na falha de disco.
- **`rastreador.py`** — `#linhaN` e `_e_so_uma_posicao` ja implementam o
  silencio de APRE-03. A frase esta no codigo: "estou vendo esta linha e nao
  faco ideia de quem esta nela". Esta fase precisa que esse silencio continue
  valendo para uma entrada do acervo SEM nome.
- **`agenda.RegistroEmDisco`** — o molde da escrita atomica, mas NAO a pasta:
  a poda de 3 dias e o motivo de o acervo ficar fora dela.

### O perigo que da nome ao requisito

`calibrar.py` monta uma `Calibracao` do zero e grava por cima do arquivo
inteiro. WINDOWS #13, confirmado em campo em 2026-08-30: o usuario rodou
`calibrar.bat` e perdeu 13 moldes de glifo e 3 ancoras do mercado.

E `CAMPOS_DA_PARTY` INCLUI `assinaturas` — entao o conserto ja escrito
(`fundir_com_a_calibracao_em_disco`) NAO as protege, e corretamente, porque a
party as possui. Uma assinatura aprendida dentro do `calibration.json` nao
morreria por bug: morreria por desenho. E por isso que a pasta e propria.

### Established Patterns

- **Tempo por parametro**; portao AST sobre `agenda`, `loot`, `presenca`,
  `bosses`, `respawn` — o modulo novo entra na tupla.
- **Portugues SEM acento**; sem travessao em texto de usuario.
- **Docstrings explicam POR QUE, com medida de campo.**

### Integration Points

- `l2scanner/identidade.py` — `Assinatura` e a correlacao
- `l2scanner/rastreador.py` — de onde vem o silencio `#linhaN`
- `l2scanner/calibrar.py` — precisa NAO tocar na pasta nova
- `l2scanner/__main__.py` — a linha de arranque de OPER-01
- `tests/test_presenca.py` — a tupla `MODULOS` do portao AST

</code_context>

<specifics>
## Specific Ideas

- Medido em 2026-08-31 contra a party real do usuario: OCR le 1 nick em 4
  (`Welazkez` certo; `TiTANDER`, `Mostarda`, `PIRULITO` errados, e a passada
  de 3x nao melhora). E por isso que o alvo desta fase e o CADASTRO e nunca a
  leitura — o proprio `identidade.py` ja dizia isso, e agora ha medida de hoje
  alem da docstring.
- O usuario roda DUAS instancias por desenho (Yazalaque e Faerlina), premissa
  do projeto desde a Fase 1. As duas vao ler e, na Fase 2, escrever no acervo.

</specifics>

<deferred>
## Deferred Ideas

- Comando para esquecer uma entrada. O usuario avaliou o crescimento com o
  numero na mao (562 bytes por assinatura) e dispensou no v1.
- OCR PROPOR o nome no batismo (OCRB-01, v2). So faz sentido depois que o
  batismo manual existir, e vale como atalho, nunca como fonte.

</deferred>
