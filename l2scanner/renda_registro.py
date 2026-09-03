"""O arquivo `.renda/<personagem>.csv`: uma linha por amostra, para sempre.

O DIALETO E O DO `.mercado/`, E AS COLUNAS SAO PROPRIAS (CTX-9)
===============================================================
`;` como separador, `csv` da stdlib, cabecalho como CONTRATO que desliga alto,
append por linha com `flush`, e corte de cauda na leitura. O que se copia e a
FORMA; o que nao se copia esta dito em voz alta mais abaixo.

UM ARQUIVO POR PERSONAGEM, SEM ROTACAO POR DATA (C-5)
=====================================================
O `02-CONTEXT.md` supos "um arquivo por personagem por dia, na forma que o
`.mercado/` e o `.loot/` ja usam", e **nenhum dos dois faz isso**: o `.mercado/`
e um arquivo so que cresce sem rotacao (`mercado_registro.py:610`) e o `.loot/`
e uma pasta de marcadores vazios, nem CSV e. Rotacao por data nao existe nesta
arvore. As tres razoes da forma escolhida, na ordem do peso:

1. **UM ESCRITOR POR ARQUIVO.** O usuario roda DUAS INSTANCIAS lado a lado — e
   a razao de o AGEN-07 e o REG-04 existirem. Um arquivo so teria DOIS processos
   apendando, e o dialeto que estamos copiando pressupoe um escritor
   (`mercado_registro.py:607`, "o unico escritor dele"). Duas escritas
   concorrentes em `"a"` no Windows nao tem garantia de atomicidade por chamada,
   e uma linha entrelacada passa no portao do terminador — e a linha parseavel e
   ERRADA que esta fase inteira existe para nao ter.
2. **Rotacao por data e uma forma nova com um modo de falha novo.** Ela
   obrigaria o leitor a decidir o que fazer na virada da meia-noite no meio de
   uma janela movel de dez minutos, e a lacuna artificial que isso cria e
   indistinguivel da lacuna de verdade — que e o unico numero que a CTX-2 manda
   contar a parte.
3. **Sem poda e sem rotacao pela mesma razao do `.loot/`** (`loot.py:11-14`):
   "quanto eu rendia mes passado" e uma pergunta sobre meses.

A COLUNA `personagem` FICA MESMO ASSIM, e nao sao duas verdades: a coluna e o
DADO que o consumidor le, e o nome do arquivo e so o ROTEAMENTO que garante um
escritor. Um arquivo renomeado a mao continua dizendo de quem ele e. Ha teste
afirmando que os dois concordam na escrita.

O QUE FOI COPIADO, E O QUE NAO FOI (C-3)
========================================
COPIADA LITERAL: `conferir_o_terminador`. Ela nao conhece coluna nenhuma —
julga o ultimo byte do arquivo e mais nada — e por isso a copia e do corpo
inteiro, com so o texto da mensagem trocado. Das cinco truncagens medidas byte a
byte na Fase 3 do mercado, DUAS produzem campos todos parseaveis; a contagem de
campos nao pega, a validacao por tipo nao pega, e so o terminador pega, 5 de 5.

NAO COPIADA: `conferir_o_cabecalho`. A do mercado fecha sobre o `COLUNAS`
GLOBAL daquele modulo (`mercado_registro.py:495`) e por isso nao e
parametrizavel. O que atravessa e a FORMA — tres estados, e so tres: ausente,
identico, divergente. A implementacao aqui e propria e recebe as colunas por
parametro, que e precisamente a diferenca.

**NAO COPIADA: A DEDUP, E ELA E O ERRO MAIS CARO QUE ESTE ARQUIVO PODIA
HERDAR.** `mercado_registro.chave_da_observacao` (`:355`) exclui o carimbo de
proposito, para o arquivo do mercado nao crescer uma linha por segundo sobre o
mesmo anuncio. Aqui uma linha por tique **E O PRODUTO**: ela e o denominador da
taxa. Copiar a dedup apagaria toda amostra em que os tres campos nao mudaram —
que a ~1 Hz e a MAIORIA delas, porque a adena so muda quando cai loot. A taxa
sairia calculada sobre um punhado de linhas sobreviventes e ninguem teria como
notar. Ha teste comportamental prendendo isso: gravar duas amostras com `nivel`,
`exp` e `adena` identicos e carimbos diferentes tem de deixar DUAS linhas.

Por isso este modulo **nao tem indice em memoria, nao tem conjunto de
identidades e nao tem funcao de identidade de linha**, e ha portao de arvore de
sintaxe afirmando que nenhum conjunto nasce no construtor.

NADA E IMPORTADO DE `dashboard_dados` (C-2)
===========================================
As seis linhas do corte de cauda e a forma de `ArquivoRecortado` sao COPIADAS.
O import seria mais limpo e custa caro demais: `dashboard_dados` importa
`mercado_console`, que importa `console` -> `rastreador` -> `visao` -> `cv2` —
**350 modulos medidos** (`raiz.py:59-63`) para pegar seis linhas. E de quebra
`dashboard_dados.py:454` chama o parser do mercado pelo nome e o confere contra
o `COLUNAS` GLOBAL daquele modulo, o que refuta a frase "o dashboard acrescenta
uma lista de colunas, nao um parser": ele acrescenta um parser inteiro. Este
modulo nao promete ao workstream `dashboard` nada alem de um arquivo em disco no
mesmo dialeto.

O RELOGIO ENTRA POR PARAMETRO (CTX-10)
======================================
Nao ha `datetime.now()` aqui. O carimbo chega como `float` epoch e vira
`datetime` **uma vez so, na fronteira do disco** — que e onde o dialeto do
registro pede `isoformat()`. A aritmetica da fase inteira e sobre epoch porque a
subtracao de dois epochs e exata; `timedelta.total_seconds()` ja foi medido
devolvendo `69713.696` onde o inteiro dizia `69713`
(`dashboard_dados.py:624-628`).
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .loot import apelido
from .mercado_catalogo import SEPARADOR
from .raiz import RAIZ

if TYPE_CHECKING:  # pragma: no cover - so para o verificador de tipos
    from .renda_leitura import CamposDaRenda

log = logging.getLogger(__name__)

# TUPLA E NAO LISTA, pelo portao `memoria_de_modulo` de
# `tests/test_renda_par.py`, que passou a varrer este arquivo tambem.
__all__ = (
    "ARQUIVO_DO_LEIAME",
    "AUSENCIAS",
    "AmostraLida",
    "ArquivoRecortado",
    "COLUNAS",
    "ContratoDaRendaQuebrado",
    "LeituraAoVivoDaRenda",
    "ORIGEM_INDETERMINADA",
    "PASTA_DA_RENDA",
    "RegistroDaRenda",
    "TEXTO_DO_LEIAME",
    "amostras_ao_vivo",
    "amostras_do_arquivo",
    "arquivo_do_personagem",
    "campos_da_linha",
    "conferir_o_cabecalho",
    "conferir_o_terminador",
    "escrever_leiame",
)


# `.renda/` e mais um diretorio-ponto de estado local e DURAVEL, ao lado de
# `.loot/`, `.agenda/`, `.mercado/` e `.identidades/`, e entra no `.gitignore`
# pela mesma razao que eles. O caminho vem SEMPRE da RAIZ do projeto e NUNCA de
# entrada do usuario — um caminho vindo de fora seria uma travessia de diretorio
# de graca, e nada aqui precisa dessa liberdade (T-02-02).
#
# `RAIZ` e IMPORTADA de `raiz.py` e nunca redefinida: duas definicoes da mesma
# raiz e como elas divergem, e redefini-la aqui a partir de `config` arrastaria
# `cv2` pela cadeia que `raiz.py` existe para cortar.
PASTA_DA_RENDA = RAIZ / ".renda"

ARQUIVO_DO_LEIAME = "LEIAME.txt"

# Ainda nao ha como saber se a adena veio de farm ou de venda, e a CTX-7 decidiu
# que isso se resolve por MARCADOR EXPLICITO e nunca por heuristica. Ate alguem
# saber preencher, a coluna diz `indeterminado` — e isso e honesto. Um balde
# errado com cara de certo e pior que uma celula que admite nao saber (D-02).
ORIGEM_INDETERMINADA = "indeterminado"


# ---------------------------------------------------------------------------
# AS TREZE COLUNAS, NA ORDEM DA TELA
# ---------------------------------------------------------------------------
#
# CADA CAMPO LIDO LEVA TRES COLUNAS JUNTAS: o valor, a GUARDA que o sustentou, e
# o MOTIVO quando ele nao saiu.
#
# A GUARDA VAI GRAVADA PORQUE O LEIT-11 TORNOU ISSO A PERGUNTA MAIS CARA DESTA
# ARVORE. Medido: 3 das 4 leituras erradas de nivel foram aceitas POR
# CONCORDANCIA das duas escalas. Sem a coluna, ninguem consegue perguntar depois
# "as erradas eram as de duas escalas ou as de uma?", e essa e a pergunta que
# decide se o cruzamento fica ou sai. E o mesmo papel de
# `residuo_do_cruzamento` no `.mercado/`, que existe por ser "a unica pista
# independente de leitura errada que esta fase tem"
# (`mercado_registro.py:186-189`).
#
# A GUARDA DO NIVEL E DO EXP E `escalas`; A DA ADENA E `glifos`, E OS NOMES SAO
# DIFERENTES DE PROPOSITO. `ValorDaRenda.escalas` significa "por quantas
# leituras INDEPENDENTES este numero foi sustentado"; a adena e lida por GLIFO e
# nao tem segunda escala com que cruzar, entao um `escalas = 1` ali seria
# indistinguivel do `escalas = 1` do nivel, que significa outra coisa. Afirmar
# guarda inexistente e o defeito que o T-01-43 existe para impedir.
#
# O INVARIANTE DAS TRES COLUNAS POR CAMPO, E ELE E TESTAVEL: para cada campo,
# EXATAMENTE UMA das duas metades esta preenchida — ou (valor E guarda) ou
# (motivo). Nunca as duas, nunca nenhuma.
#
# AS QUATRO AUSENCIAS, E POR QUE SAO AUSENCIAS:
#
# 1. NAO HA COLUNA DE DELTA NEM DE TAXA. Delta e derivacao de DUAS linhas e taxa
#    e derivacao de MUITAS. O D-02 vale inteiro e o precedente e literal: o
#    `.mercado/` recusou a coluna de unitario porque "total e quantidade sao o
#    que a tela AFIRMA; o unitario e o que ela CALCULOU"
#    (`mercado_registro.py:110-114`). A linha grava o que a barra afirmou.
# 2. NAO HA COLUNA DE `level up`. Ela seria derivavel do proprio `nivel` de duas
#    linhas consecutivas, e uma coluna derivada e a mesma objecao do item 1.
# 3. NAO HA COLUNA DE XP ABSOLUTO. Ele e a porcentagem vezes uma constante que
#    muda por nivel e que sera RECALIBRADA (CTX-8). Grava-lo congelaria, em cada
#    linha e para sempre, uma conversao que a ponte de amanha refaz melhor. A
#    barra afirma decimos de milesimo de ponto; a conversao e do leitor.
# 4. NAO HA COLUNA DE GRAVACAO NEM DE FRAME, pelo mesmo criterio do `.mercado/`
#    (D-04): sao artefato de bancada e mentem no uso real.
COLUNAS = (
    "carimbo",
    "personagem",
    "nivel",
    "nivel_escalas",
    "motivo_do_nivel",
    "exp_decimos",
    "exp_escalas",
    "motivo_do_exp",
    "adena",
    "adena_glifos",
    "motivo_da_adena",
    "descontinuidade",
    "origem_do_ganho",
)

# As quatro ausencias, escritas UMA vez, para que o LEIAME e o teste do LEIAME
# derivem da mesma fonte em vez de repetirem a lista a mao. Uma lista escrita a
# mao no teste envelheceria em silencio no dia em que uma quinta nascesse.
AUSENCIAS = (
    "delta ou taxa",
    "level up",
    "XP absoluto",
    "gravacao ou frame",
)


class ContratoDaRendaQuebrado(Exception):
    """O arquivo existe mas nao e mais o arquivo que este modulo escreveu.

    ELA E PROPRIA E NAO HERDADA DE `mercado_registro.ContratoDoArquivoQuebrado`,
    e a razao e de escopo e nao de estilo: herdar acoplaria dois workstreams
    numa hierarquia de excecao, e quem capturasse a do mercado passaria a
    capturar a da renda sem ter pedido. O contrato entre os dois e um arquivo em
    disco, e mais nada.

    A DOUTRINA E A MESMA: arquivo INTEIRO recusado nao e "linha ruim". Linha
    ruim cai sozinha com `warning` e o arquivo carrega. Isto aqui e a feature
    DESLIGANDO ALTO em vez de escrever desalinhado sobre um arquivo que o
    usuario edita a mao e importa no Sheets.
    """


# ---------------------------------------------------------------------------
# O LEIAME, ao lado do CSV
# ---------------------------------------------------------------------------

# SEM ACENTO, como todo texto que este projeto poe na frente do usuario: o
# console do Windows abre em cp1252 e a mesma frase acaba colada num log, numa
# mensagem de erro e num editor qualquer. O arquivo e escrito em UTF-8; a
# escolha aqui e de consistencia, nao de codificacao.
TEXTO_DO_LEIAME = """O QUE E ESTA PASTA
==================
`.renda/` e estado local e duravel deste scanner. Ha UM ARQUIVO CSV POR
PERSONAGEM, com o nome do personagem no nome do arquivo, e uma linha por
amostra da barra de status.

Nenhum arquivo daqui e versionado, e nao ha desfazer: a renda e desta maquina.

Este LEIAME e escrito UMA VEZ, quando a pasta nasce, e NUNCA e reescrito. Se
voce anotar alguma coisa aqui, a anotacao fica.


POR QUE UM ARQUIVO POR PERSONAGEM
=================================
Porque voce roda duas instancias do jogo lado a lado, e um arquivo so teria dois
programas escrevendo nele ao mesmo tempo. Duas escritas simultaneas podem
entrelacar meia linha de uma com meia linha da outra, e o resultado seria uma
linha que ABRE no Sheets e esta errada — que e a unica coisa que este arquivo
existe para nao ter.

O arquivo NUNCA e podado e NUNCA e rotacionado por data. "Quanto eu rendia mes
passado" e uma pergunta sobre meses.


COMO IMPORTAR NO GOOGLE SHEETS
==============================
1. No Sheets: menu Arquivo > Importar > Enviar o arquivo (File > Import >
   Upload).
2. Escolha o CSV do personagem.
3. No campo de separador, escolha PERSONALIZADO (Custom) e digite ";".

Dois avisos que economizam tempo:

- NAO existe uma opcao pronta de ponto e virgula na lista. Ela oferece apenas
  deteccao automatica, tabulacao, virgula e personalizado.
- Abrir o arquivo com duplo clique no Drive NAO oferece esse dialogo. So o
  caminho pelo menu Arquivo > Importar deixa escolher o separador.

O separador e ponto e virgula porque a exibicao do jogo usa padrao brasileiro,
com virgula decimal. Um CSV separado por virgula colapsaria a planilha inteira
numa coluna so.


AS TREZE COLUNAS
================
Cada campo lido leva TRES colunas juntas: o valor, a guarda que o sustentou, e o
motivo quando ele nao saiu. Para cada campo, exatamente uma das duas metades
esta preenchida — ou o valor e a guarda, ou o motivo. Nunca as duas, nunca
nenhuma.

  carimbo           a hora local em que a amostra foi lida, sem fuso.
  personagem        de quem e a tela. E o mesmo nome que da nome ao arquivo.

  nivel             o nivel lido, inteiro nu.
  nivel_escalas     por quantas leituras INDEPENDENTES o nivel foi sustentado.
                    1 quer dizer que a segunda escala se absteve, e a guarda
                    contra digito trocado ficou mais fraca NAQUELA linha.
  motivo_do_nivel   por que o nivel nao saiu, quando nao saiu.

  exp_decimos       o EXP em DECIMOS DE MILESIMO de ponto percentual. 80012 no
                    arquivo e 8,0012% na tela. Nao ha virgula decimal em
                    coluna nenhuma, e o nome da coluna carrega a unidade.
  exp_escalas       o mesmo que nivel_escalas, para o EXP.
  motivo_do_exp     por que o EXP nao saiu, quando nao saiu.

  adena             a adena em unidades, inteiro nu.
  adena_glifos      quantos simbolos a peneira entregou ao leitor de glifo.
                    E a guarda que a adena REALMENTE tem: ela e lida por glifo
                    e nao por duas escalas, entao ela nao tem "escalas" e dizer
                    que tem seria afirmar uma guarda que nao existe.
                    13.160.684 sao dez glifos: oito digitos e duas virgulas.
  motivo_da_adena   por que a adena nao saiu, quando nao saiu.

  descontinuidade   preenchida quando aquele passo NAO entra na conta da taxa:
                    `ancora` (primeira amostra, nao ha anterior),
                    `lacuna` (o scanner ficou cego tempo demais),
                    `relogio-andou-para-tras` (a hora da maquina pulou).
  origem_do_ganho   se a adena veio de farm ou de venda. Hoje sai sempre
                    `indeterminado`, e isso e de proposito: ninguem sabe
                    preencher ainda, e adivinhar seria pior que admitir.


AS RECUSAS TAMBEM ESTAO AQUI, E ISSO E DE PROPOSITO
===================================================
Uma amostra em que o nivel nao leu vira linha do mesmo jeito, com o motivo na
coluna. Um arquivo que so tivesse sucessos nao permitiria responder "por que a
taxa desta hora tem n=12 se o scanner rodou quarenta minutos". A taxa de recusa
e dado, e nao ruido.


AS QUATRO COISAS QUE VOCE VAI PROCURAR E NAO VAI ACHAR
======================================================
- Nao ha coluna de delta ou taxa. Elas sao derivadas de duas linhas e de muitas
  linhas; a linha grava o que a barra AFIRMOU, e a conta e de quem le.
- Nao ha coluna de level up. Ela e derivavel do proprio `nivel` de duas linhas
  consecutivas.
- Nao ha coluna de XP absoluto. Ele e a porcentagem vezes uma constante que
  muda por nivel e por personagem, e que ainda vai ser remedida. Grava-la
  congelaria para sempre, em cada linha, uma conversao que amanha sai melhor.
- Nao ha coluna de gravacao ou frame. Sao artefato de bancada: no farm ao vivo
  nao existe "frame 78", e uma coluna que so tem conteudo quando se roda a
  suite e uma coluna que mente no uso real.


SE O REGISTRO DESLIGAR
======================
Ele desliga alto, com uma mensagem no log que diz o que fazer. Os dois motivos
possiveis sao o arquivo nao terminar em quebra de linha e a primeira linha nao
ser mais o cabecalho que este programa escreve. Nos dois casos NENHUM byte seu e
alterado: abra o arquivo, conserte a linha apontada, salve com quebra de linha
no fim, e o proximo arranque religa.

Enquanto isso, todo o resto do scanner continua igual: morte, saida e
ressurreicao seguem sendo detectadas e entregues.
"""


def escrever_leiame(pasta: Path) -> bool:
    """Poe o LEIAME ao lado dos CSVs, e SO SE ELE NAO EXISTIR.

    Devolve `True` quando escreveu e `False` quando ja havia um. A regra e
    ESCREVER SO SE AUSENTE, nunca sobrescrever, e a razao e o dono do arquivo:
    ele e um texto para humano, na pasta do humano, e o usuario pode anotar
    coisas ali. Um programa que o reescrevesse a cada arranque apagaria a
    anotacao calado — a mesma familia de erro que o cabecalho-contrato existe
    para impedir do outro lado do modulo.
    """
    alvo = pasta / ARQUIVO_DO_LEIAME
    if alvo.exists():
        return False
    alvo.write_text(TEXTO_DO_LEIAME, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# OS DOIS PORTOES DE CONTRATO, FORA DA CLASSE
# ---------------------------------------------------------------------------
#
# As duas conferencias sao sobre o ARQUIVO e nao sobre o REGISTRO, entao moram
# no modulo e a classe as CHAMA. E o que permite `amostras_do_arquivo`
# atravessar o mesmo portao sem uma segunda implementacao dele no projeto —
# e duas implementacoes do mesmo portao seriam duas chances de divergir.


def conferir_o_terminador(bruto: str, arquivo: Path) -> None:
    """Sem quebra de linha no fim, o arquivo INTEIRO e recusado.

    O CORPO E COPIADO LITERAL DE `mercado_registro.conferir_o_terminador`
    (`:410-477`), com o texto da mensagem trocado e mais nada. A copia e literal
    porque a funcao **nao conhece coluna nenhuma**: ela julga o ultimo byte do
    arquivo, e esse julgamento e o mesmo em qualquer CSV escrito com
    `csv.writer.writerow` seguido de `flush`.

    A CONTAGEM DE CAMPOS NAO SERVE PARA ISTO, E ESTA MEDIDO no outro modulo:
    sobre uma linha completa cortada byte a byte a partir do fim, os cinco
    cortes deixam o arquivo sem quebra de linha final — mas DOIS deles produzem
    campos todos parseaveis, com `80` virando `8` e `48` virando `4`. Essa linha
    passaria pela contagem e viraria dado. `'8'` e um inteiro perfeitamente
    valido, entao a validacao por tipo tambem nao a pega. So o terminador pega,
    5 de 5.

    A BICONDICIONAL QUE SUSTENTA O CRITERIO TAMBEM FOI MEDIDA:
    `csv.writer.writerow` emite UMA unica chamada de escrita contendo a linha E
    o terminador, logo **um registro esta completo se e somente se o arquivo
    termina em quebra de linha**.

    AS DUAS OUTRAS SAIDAS FORAM CONSIDERADAS E RECUSADAS la, e valem aqui pelas
    mesmas razoes: truncar a cauda seria o programa apagando bytes do usuario
    num caminho de LEITURA, e completar a cauda com uma quebra de linha
    PROMOVERIA a linha possivelmente truncada a dado permanente.

    CUSTO ACEITO, E ELE E REAL: uma queda de energia de verdade desliga o
    registro daquele personagem ate intervencao manual. Aceitavel porque a
    mensagem diz exatamente o que fazer para religar, e porque a alternativa e
    renda errada gravada como boa.
    """
    if bruto.endswith("\n"):
        return

    cauda = bruto[bruto.rfind("\n") + 1 :]
    mensagem = (
        "REGISTRO DE RENDA DESLIGADO — o arquivo %s NAO TERMINA EM QUEBRA DE "
        "LINHA, e por isso NADA foi lido dele. Duas hipoteses, e o criterio "
        "nao consegue distinguir uma da outra: ou a ultima gravacao foi "
        "INTERROMPIDA (queda de energia, ou disco cheio no meio da escrita), "
        "ou o arquivo foi EDITADO A MAO e salvo sem a quebra de linha final. A "
        "cauda crua e %r, e ela esta INTACTA no disco: nenhum byte foi "
        "removido, reparado ou reescrito. O QUE FAZER: abra o arquivo, olhe a "
        "ultima linha, complete-a ou apague-a, e salve COM quebra de linha no "
        "fim — isso religa o registro no proximo arranque. Enquanto isso, os "
        "alertas de party (morte, saida e ressurreicao) seguem sendo "
        "detectados e entregues."
    )
    log.error(mensagem, arquivo, cauda)
    raise ContratoDaRendaQuebrado(mensagem % (arquivo, cauda))


def conferir_o_cabecalho(
    linhas: list[list[str]], arquivo: Path, colunas: tuple[str, ...]
) -> None:
    """A primeira linha e o cabecalho que este programa escreve? Tres estados.

    ELA NAO E COPIA, E A DIFERENCA E O TERCEIRO PARAMETRO. A do mercado fecha
    sobre o `COLUNAS` global daquele modulo (`mercado_registro.py:495`) e por
    isso nao e parametrizavel — copia-la para ca traria junto o `COLUNAS`
    errado, ou obrigaria a uma segunda copia por conjunto de colunas. O que
    atravessa e a FORMA: tres estados, e so tres. Arquivo AUSENTE cria com
    cabecalho (tratado em `carregar`); primeiro registro IDENTICO as colunas
    depois de `strip` segue; DIVERGENTE, ou ausente num arquivo nao-vazio,
    levanta.

    A INVERSAO EM RELACAO AO CATALOGO TEM MOTIVO, e e o mesmo do mercado: la o
    cabecalho e CONVENIENCIA para o olho humano; aqui ele e a IDENTIDADE do
    arquivo. Migrar sozinho um arquivo que o usuario edita a mao e importa no
    Sheets e exatamente como se corrompe dado calado — o append passaria a
    escrever valores nas colunas erradas e ninguem veria, porque o arquivo
    continuaria abrindo.
    """
    encontrado = tuple(campo.strip() for campo in linhas[0]) if linhas else ()
    if encontrado == colunas:
        return

    mensagem = (
        "REGISTRO DE RENDA DESLIGADO — o cabecalho de %s nao e o que este "
        "programa escreve, e por isso NADA foi lido dele. Esperava %r e "
        "encontrei %r. NENHUM byte foi alterado: migrar sozinho um arquivo que "
        "voce edita a mao e importa no Sheets e como se corrompe dado calado, "
        "porque o append passaria a escrever valores nas colunas erradas e o "
        "arquivo continuaria abrindo. O QUE FAZER: restaure a primeira linha "
        "para o cabecalho esperado, ou renomeie o arquivo para o programa "
        "criar um novo — qualquer um dos dois religa o registro no proximo "
        "arranque. Enquanto isso, os alertas de party (morte, saida e "
        "ressurreicao) seguem sendo detectados e entregues."
    )
    log.error(mensagem, arquivo, colunas, encontrado)
    raise ContratoDaRendaQuebrado(mensagem % (arquivo, colunas, encontrado))


# ---------------------------------------------------------------------------
# A METADE PURA: dos tres campos lidos as treze celulas
# ---------------------------------------------------------------------------


def arquivo_do_personagem(pasta: Path, personagem: str) -> Path:
    """`.renda/faerlina.csv` a partir de `Faerlina`.

    O NOME PASSA POR `apelido()`, QUE E UMA LISTA DE PERMISSAO (T-02-02). O
    nome do personagem vem do titulo da janela do jogo e vira caminho em disco;
    `re.sub(r"[^a-z0-9]+", "-", ...)` reduz `..\\..\\Windows\\System32` a
    `-windows-system32`, e nao ha caractere de travessia que sobreviva a uma
    lista de PERMISSAO. E ela e IMPORTADA de `loot` e nao recopiada — medido:
    `import l2scanner.loot` traz 97 modulos, sem `cv2` e sem `numpy`, e uma
    TERCEIRA copia do mesmo regex e exatamente o que a docstring de
    `agenda.apelido_do_evento` argumenta contra pelo nome.
    """
    return pasta / f"{apelido(personagem)}.csv"


def _celulas_do_campo(lido: Any) -> tuple[str, str, str]:
    """As TRES celulas de um campo: valor, guarda, motivo. Exatamente uma metade.

    A DISTINCAO E POR ATRIBUTO E NAO POR `isinstance`, e a razao esta na
    docstring do modulo: importar `renda_leitura` no topo custaria 334 modulos
    com `cv2` e `numpy`. O import de tipos mora sob `TYPE_CHECKING`, e em tempo
    de execucao a pergunta e "este objeto tem `motivo`?" — que e verdade para
    `RecusaDaRenda` e falsa para os dois tipos de valor.

    `escalas` E `glifos` SAO NOMES DIFERENTES DE PROPOSITO, e por isso a funcao
    aceita os dois: `ValorDaRenda` carrega `escalas` e `ValorDaAdena` carrega
    `glifos`, e uniformizar os dois obrigaria a adena a afirmar uma guarda que
    ela nao tem.
    """
    motivo = getattr(lido, "motivo", None)
    if motivo is not None:
        return ("", "", str(motivo))

    guarda = getattr(lido, "escalas", None)
    if guarda is None:
        guarda = getattr(lido, "glifos", None)
    return (str(int(lido.valor)), "" if guarda is None else str(int(guarda)), "")


def campos_da_linha(
    campos: CamposDaRenda,
    *,
    carimbo: float,
    descontinuidade: str,
    origem_do_ganho: str,
) -> tuple[str, ...]:
    """As treze celulas da linha, na ordem de `COLUNAS`.

    O CARIMBO ENTRA POR PARAMETRO (CTX-10): este modulo nunca chama o relogio do
    sistema e nunca constroi um `Relogio`. Quem chama passa o `float` epoch que
    a `LeituraDaRenda` ja carrega.

    A UNICA CONVERSAO DE EPOCH PARA `datetime` DA FASE INTEIRA ACONTECE AQUI, e
    ela e de saida: o dialeto do registro escreve `isoformat()`, e a aritmetica
    da conta e sobre epoch porque a subtracao de dois epochs e exata. Um
    `datetime` ingenuo em hora local e o que `Relogio.agora` ja produz
    (`relogio.py:163`), entao o `.isoformat()` sai sem fuso — o formato que o
    resto do projeto usa.

    ELA RECEBE `CamposDaRenda` E NUNCA O RESULTADO DE `ler_a_renda` (Pitfall 3).
    `ler_a_renda` devolve a PRIMEIRA recusa em `ORDEM_DOS_CAMPOS`, e `nivel` e o
    primeiro dessa ordem: uma amostra com EXP e adena perfeitos sumiria por
    causa do campo mais fragil dos tres. AS RECUSAS TAMBEM SAO GRAVADAS (CTX-9),
    e e por isso que o tipo que atravessa e o que carrega os tres campos
    separados, cada um valor OU recusa.
    """
    nivel, nivel_guarda, nivel_motivo = _celulas_do_campo(campos.nivel)
    exp, exp_guarda, exp_motivo = _celulas_do_campo(campos.exp)
    adena, adena_guarda, adena_motivo = _celulas_do_campo(campos.adena)
    return (
        datetime.fromtimestamp(carimbo).isoformat(),
        campos.personagem,
        nivel,
        nivel_guarda,
        nivel_motivo,
        exp,
        exp_guarda,
        exp_motivo,
        adena,
        adena_guarda,
        adena_motivo,
        descontinuidade,
        origem_do_ganho,
    )


@dataclass(frozen=True)
class AmostraLida:
    """Uma linha do CSV, de volta ao programa e TIPADA.

    Os tres valores voltam como `int | None` e os tres motivos como `str`: a
    ausencia de valor e a presenca de motivo sao o mesmo fato visto dos dois
    lados, e o invariante das tres colunas por campo e o que garante isso.

    ELA E ENTRADA NAO CONFIAVEL, e a docstring diz isso porque o usuario edita o
    arquivo a mao e o importa no Sheets. Nada aqui e usado sem passar pelos dois
    portoes de contrato e pelas redes por linha.
    """

    carimbo: datetime
    personagem: str
    nivel: int | None
    nivel_escalas: int | None
    motivo_do_nivel: str
    exp_decimos: int | None
    exp_escalas: int | None
    motivo_do_exp: str
    adena: int | None
    adena_glifos: int | None
    motivo_da_adena: str
    descontinuidade: str
    origem_do_ganho: str


def _inteiro_ou_nada(celula: str) -> int | None:
    """A celula vazia vira `None`; a preenchida LEVANTA se nao for inteiro.

    Os dois comportamentos sao de proposito: vazio e um estado LEGITIMO (o campo
    recusou, e o motivo esta na coluna ao lado), e lixo numa celula que deveria
    ter numero e uma linha ruim — que cai sozinha, com `warning`, sem condenar o
    arquivo (a doutrina do D-14).
    """
    if celula == "":
        return None
    return int(celula)


# ---------------------------------------------------------------------------
# A LEITURA: um parser so, e o corte de cauda antes do portao
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArquivoRecortado:
    """Um objeto com FORMA de `Path`, que entrega texto ja cortado.

    COPIADO NA FORMA de `dashboard_dados.ArquivoRecortado` (`:271-345`), e nao
    importado: aquele modulo importa `mercado_console` -> `console` ->
    `rastreador` -> `visao` -> `cv2`, e sao 350 modulos medidos para pegar um
    adaptador de tres metodos.

    POR QUE ELE EXISTE: `amostras_do_arquivo` recebe um `Path` e le o arquivo
    ela mesma. O leitor tolerante precisa do MESMO corpo — os mesmos dois
    portoes, as mesmas redes por linha — mas sobre um texto que ele ja cortou na
    ultima quebra de linha. Este adaptador e o encaixe: ele diz "sim, eu sou um
    arquivo", devolve o texto recortado no `open()`, e devolve o caminho REAL no
    `__str__`, para que a mensagem de erro continue nomeando o arquivo que o
    usuario consegue abrir.

    A ALTERNATIVA RECUSADA E UM SEGUNDO LACO DE `csv.reader` AQUI, e ela e
    recusada pela mesma razao de sempre: duas implementacoes de leitura sao duas
    chances de uma delas nao ter o portao do terminador.

    O PRECO, DITO EM VOZ ALTA: e um acoplamento de FORMA. Este objeto implementa
    `open`, `__str__` e `__fspath__` porque e o que `amostras_do_arquivo` usa
    hoje; se ela passar a chamar `.stat()` ou `.exists()`, este adaptador quebra
    com `AttributeError`. O antidoto e o teste de ida e volta do tracer.
    """

    caminho_real: Path
    texto: str

    def open(self, *args: Any, **kwargs: Any) -> io.StringIO:
        """O texto ja cortado, como se viesse do disco. Argumentos ignorados."""
        return io.StringIO(self.texto, newline="")

    def __str__(self) -> str:
        return str(self.caminho_real)

    def __fspath__(self) -> str:
        return str(self.caminho_real)


def amostras_do_arquivo(arquivo: Any) -> list[AmostraLida]:
    """As linhas do CSV, TIPADAS, pelo MESMO portao que `carregar` atravessa.

    ELA NAO E UM PARSER NOVO, E ISSO E O CRITERIO. Ha uma verdade so sobre o que
    o arquivo e, e o leitor tolerante a alcanca pelo adaptador acima em vez de
    escrever a sua.

    ELA NUNCA ESCREVE E NUNCA CRIA A PASTA. `carregar` cria o arquivo ausente
    com cabecalho porque ela e o arranque do ESCRITOR; esta e leitura pura.
    Arquivo ausente devolve lista vazia sem levantar: a `.renda/` nasce vazia e
    quem le tem de dizer "sem evidencia", nao explodir.

    O QUE LEVANTA E O QUE CAI SOZINHO: o terminador e o cabecalho sao o arquivo
    INTEIRO recusado (`ContratoDaRendaQuebrado`, registro desligado alto); uma
    linha ruim cai sozinha com `warning` que NOMEIA o numero dela, e as demais
    carregam.
    """
    try:
        with arquivo.open("r", encoding="utf-8", newline="") as fonte:
            bruto = fonte.read()
    except FileNotFoundError:
        return []

    if not bruto:
        return []

    conferir_o_terminador(bruto, arquivo)
    linhas = list(csv.reader(io.StringIO(bruto, newline=""), delimiter=SEPARADOR))
    conferir_o_cabecalho(linhas, arquivo, COLUNAS)

    lidas: list[AmostraLida] = []
    for numero, campos in enumerate(linhas[1:], start=2):
        if not campos:
            continue
        if len(campos) != len(COLUNAS):
            log.warning(
                "A linha %d de %s tem %d campos e nao %d: ela cai sozinha e o "
                "resto do arquivo carrega.",
                numero,
                arquivo,
                len(campos),
                len(COLUNAS),
            )
            continue
        try:
            lidas.append(
                AmostraLida(
                    carimbo=datetime.fromisoformat(campos[0]),
                    personagem=campos[1],
                    nivel=_inteiro_ou_nada(campos[2]),
                    nivel_escalas=_inteiro_ou_nada(campos[3]),
                    motivo_do_nivel=campos[4],
                    exp_decimos=_inteiro_ou_nada(campos[5]),
                    exp_escalas=_inteiro_ou_nada(campos[6]),
                    motivo_do_exp=campos[7],
                    adena=_inteiro_ou_nada(campos[8]),
                    adena_glifos=_inteiro_ou_nada(campos[9]),
                    motivo_da_adena=campos[10],
                    descontinuidade=campos[11],
                    origem_do_ganho=campos[12],
                )
            )
        except ValueError as erro:
            log.warning(
                "A linha %d de %s nao virou amostra (%s): ela cai sozinha e o "
                "resto do arquivo carrega.",
                numero,
                arquivo,
                erro,
            )
    return lidas


@dataclass(frozen=True)
class LeituraAoVivoDaRenda:
    """O que o leitor tolerante achou, com a cauda declarada em vez de escondida."""

    amostras: tuple[AmostraLida, ...] = ()
    linhas_completas: int = 0
    cauda_incompleta: bool = False
    arquivo_ausente: bool = False


def amostras_ao_vivo(arquivo: Path) -> LeituraAoVivoDaRenda:
    """Le um arquivo que o escritor pode estar apendando AGORA.

    O CORTE ACONTECE ANTES DO PORTAO, E POR ISSO O PORTAO CONTINUA EXISTINDO. O
    texto entregue ao parser termina em quebra de linha POR CONSTRUCAO, entao
    `conferir_o_terminador` e chamada e passa; `conferir_o_cabecalho` e chamada
    e continua desligando alto se o arquivo nao for mais o arquivo deste
    programa. Nenhum dos dois portoes foi afrouxado — o primeiro passou a julgar
    um texto de que a ambiguidade ja foi retirada.

    A FREQUENCIA DO CASO ESTA MEDIDA NO OUTRO MODULO, E ELA E BAIXA: em 22.970
    leituras de cauda durante 200.000 appends concorrentes, ZERO leituras sem
    terminador. E o zero e resultado e nao cegueira da sonda — um controle
    positivo que escrevia a linha em DUAS chamadas acusou 3.252 de 4.079. Esta
    degradacao e REDE DE SEGURANCA, e nao o caminho normal.

    UM ARQUIVO NAO VAZIO SEM NENHUMA QUEBRA DE LINHA LEVANTA, e aqui esta a
    DIVERGENCIA deliberada com `dashboard_dados.observacoes_ao_vivo`, que devolve
    "cauda incompleta" e segue. La quem le e um painel de so-leitura, que tem de
    degradar para nao ficar mudo. Aqui o mesmo arquivo e do ESCRITOR, e um
    arquivo sem uma unica linha completa nao tem nem cabecalho: ele nao e o
    arquivo que este programa escreve, e apendar nele produziria exatamente a
    linha parseavel e errada que a fase existe para nao ter.
    """
    try:
        with arquivo.open("r", encoding="utf-8", newline="") as fonte:
            bruto = fonte.read()
    except FileNotFoundError:
        return LeituraAoVivoDaRenda(arquivo_ausente=True)

    if not bruto:
        # Zero bytes: nao ha byte do usuario para julgar, e tambem nao ha cauda.
        return LeituraAoVivoDaRenda()

    corte = bruto.rfind("\n")
    if corte < 0:
        mensagem = (
            "REGISTRO DE RENDA DESLIGADO — o arquivo %s nao tem UMA UNICA "
            "quebra de linha, entao nao ha nem cabecalho nem uma linha "
            "completa nele, e NADA foi lido. NENHUM byte foi alterado. O QUE "
            "FAZER: abra o arquivo e veja o que ha ali; se for lixo, apague o "
            "arquivo e o proximo arranque cria um novo com o cabecalho certo. "
            "Enquanto isso, os alertas de party (morte, saida e ressurreicao) "
            "seguem sendo detectados e entregues."
        )
        log.error(mensagem, arquivo)
        raise ContratoDaRendaQuebrado(mensagem % (arquivo,))

    completo = bruto[: corte + 1]
    cauda = bruto[corte + 1 :]

    return LeituraAoVivoDaRenda(
        amostras=tuple(
            amostras_do_arquivo(
                ArquivoRecortado(caminho_real=arquivo, texto=completo)
            )
        ),
        # As linhas de DADO do trecho completo: tudo menos o cabecalho, e sem
        # contar as linhas em branco. O caso do arquivo so com cabecalho daria
        # `-1` numa subtracao nua, e uma contagem negativa numa frase de prova
        # seria pior que nenhuma — por isso a subtracao acontece so quando ha o
        # que subtrair, e nao dentro de um `max` que absorveria o sinal.
        linhas_completas=_linhas_de_dado(completo),
        # `bool(cauda)` e nao `bool(cauda.strip())`: qualquer byte depois do
        # ultimo terminador e uma linha que o programa nao consegue afirmar,
        # inclusive um punhado de espacos.
        cauda_incompleta=bool(cauda),
    )


def _linhas_de_dado(completo: str) -> int:
    """Quantas linhas de DADO ha no trecho completo. Nunca negativo, sem `max`."""
    escritas = len([linha for linha in completo.splitlines() if linha.strip()])
    if escritas <= 0:
        return 0
    return escritas - 1


# ---------------------------------------------------------------------------
# A METADE DE DISCO: o arquivo que cresce por append
# ---------------------------------------------------------------------------


class RegistroDaRenda:
    """O arquivo `.renda/<personagem>.csv`, e o UNICO escritor dele.

    SEM INDICE E SEM DEDUP, E ISSO E O CONTRARIO DO IRMAO DO MERCADO. La o
    indice de chaves existe para que rever a mesma pagina nao acrescente linha;
    aqui uma linha por tique E O PRODUTO, porque ela e o denominador da taxa.
    Ha portao de arvore de sintaxe afirmando que nenhum conjunto nasce neste
    construtor, e teste comportamental afirmando que duas amostras identicas
    deixam DUAS linhas.

    A PASTA CHEGA NO CONSTRUTOR e nao e derivada aqui dentro, pelo mesmo motivo
    escrito em `mercado_catalogo.py:426-430`: e o que permite ao teste apontar
    para `tmp_path` sem nunca tocar a `.renda/` real, que e dado acumulado e sem
    desfazer. Producao passa `PASTA_DA_RENDA`.

    O CONSTRUTOR NAO SE DEFENDE, e isso e deliberado: `mkdir` pode levantar e
    `carregar` pode levantar `ContratoDaRendaQuebrado` ou `OSError`. Quem
    envolve tudo num `try` e a montagem, pelo trilho de `montar_gravador` — que
    existe precisamente porque um construtor que faz `mkdir` e `open` fora de
    qualquer `try` derrubava o scanner inteiro.
    """

    def __init__(self, pasta: Path, personagem: str) -> None:
        # CLASSE COMUM E NAO `dataclass`, e a razao e o portao: o criterio de
        # aceitacao varre o `__init__` deste modulo procurando `ast.Set` e
        # `ast.SetComp` — o sinal de alerta de que a dedup do mercado
        # atravessou. Um `dataclass` nao teria `__init__` no fonte e o portao
        # varreria o vazio, passando por construcao em vez de por medicao.
        self.pasta = pasta
        self.personagem = personagem
        self.ligado = True
        self.pasta.mkdir(parents=True, exist_ok=True)
        # Logo DEPOIS do `mkdir` e ANTES de qualquer leitura: o texto que
        # explica o arquivo nasce junto com a pasta que o guarda, e nunca
        # depois. Ele nao toca o CSV — e um arquivo ao lado, nao uma linha
        # dentro.
        escrever_leiame(self.pasta)
        self.carregar()

    @property
    def arquivo(self) -> Path:
        return arquivo_do_personagem(self.pasta, self.personagem)

    # -- leitura ------------------------------------------------------------

    def carregar(self) -> list[AmostraLida]:
        """Le o arquivo e atravessa os dois portoes. Ausente -> cria cabecalho.

        ELA DEVOLVE AS AMOSTRAS EM VEZ DE MONTAR UM INDICE, e a diferenca com o
        irmao do mercado e a ausencia da dedup: nao ha nada a indexar porque
        nada e deduplicado.

        `newline=""` TAMBEM NA LEITURA e nao so na escrita: sem ele a traducao
        universal de quebras de linha alteraria um campo que contenha `\\r`.

        `OSError` NAO E CAPTURADO AQUI: o erro sobe para a montagem desligar a
        feature, em vez de degradar calado para "arquivo vazio" — que faria a
        taxa da sessao ser calculada sobre nada.
        """
        try:
            with self.arquivo.open("r", encoding="utf-8", newline="") as fonte:
                bruto = fonte.read()
        except FileNotFoundError:
            # Primeira execucao numa maquina limpa e estado LEGITIMO, nao erro.
            # Nada a preservar, entao o cabecalho nasce aqui.
            self._criar_com_cabecalho()
            return []

        if not bruto:
            # O UNICO caso que NAO passa pelo portao de contrato, e a razao e
            # que nao ha dado a preservar: zero bytes nao tem byte do usuario
            # para ser destruido. O que aconteceu ali foi uma CRIACAO
            # interrompida, nao uma escrita perdida.
            log.warning(
                "O arquivo de renda %s tem ZERO BYTES: a criacao dele foi "
                "interrompida. Escrevi o cabecalho e segui — nao havia dado "
                "nenhum ali para preservar.",
                self.arquivo,
            )
            self._criar_com_cabecalho()
            return []

        return amostras_do_arquivo(self.arquivo)

    def _criar_com_cabecalho(self) -> None:
        """Escreve o cabecalho num arquivo AUSENTE. Unica escrita do arranque.

        O modo e `"w"` e ele so alcanca arquivo que nao existe (ou de zero
        bytes) — nao ha byte do usuario para destruir.
        """
        with self.arquivo.open("w", encoding="utf-8", newline="") as destino:
            csv.writer(destino, delimiter=SEPARADOR).writerow(COLUNAS)

    # -- escrita ------------------------------------------------------------

    def registrar(
        self,
        campos: CamposDaRenda,
        *,
        carimbo: float,
        descontinuidade: str,
        origem_do_ganho: str = ORIGEM_INDETERMINADA,
    ) -> bool:
        """Uma amostra vira UMA linha. Sempre. Devolve se a linha foi escrita.

        NUNCA LEVANTA PARA FORA. A doutrina da casa e degradar a FEATURE e nunca
        o PRODUTO: uma excecao aqui derrubaria o scanner por causa de disco
        cheio, levando os alertas de morte da party junto (T-02-06).

        NAO HA CONFERENCIA DE DUPLICATA ANTES DE ESCREVER, e essa e a linha mais
        importante desta docstring. Duas amostras com os tres campos identicos e
        carimbos diferentes sao DUAS medicoes, e as duas entram: elas sao o
        denominador da taxa. A dedup do mercado, copiada para ca, apagaria a
        maioria das linhas de uma noite de farm.

        AS TRES DECISOES DE ESCRITA SAO AS DO IRMAO, com os numeros que as
        mediram:

        - **`flush()` sem `os.fsync()`.** `flush` sozinho custa 0,0037 ms e
          `flush+fsync` custa 1,5990 ms — 432x mais caro —, e `writerow`+`flush`
          e UMA `write()` so, entao Ctrl+C, excecao ou `taskkill` nao produzem
          linha truncada.
        - **Abrir e FECHAR por linha** (0,1295 ms, ruido num tique de 1 Hz).
          Medido: com a alca JA ABERTA, marcar o arquivo como somente-leitura
          NAO impede a escrita — o `PermissionError` so nasce no `open`. E de
          quebra nunca segura uma alca sobre o arquivo que o usuario quer abrir
          no Sheets.
        - **`newline=""`** porque sem ele o modulo `csv` escreve `\\r\\r\\n` no
          Windows.

        `except OSError` E SO, e nao `except Exception`: os quatro modos desta
        maquina sao `PermissionError`, `FileNotFoundError` e `FileExistsError`,
        todas subclasses de `OSError`. `except Exception` esconderia um
        `AttributeError` de refactor como se fosse disco cheio.
        """
        if not self.ligado:
            return False

        celulas = campos_da_linha(
            campos,
            carimbo=carimbo,
            descontinuidade=descontinuidade,
            origem_do_ganho=origem_do_ganho,
        )

        # O `try` envolve a ABERTURA, a ESCRITA e o `flush` — os tres, porque os
        # erros nascem em pontos diferentes: o `PermissionError` de arquivo
        # somente-leitura nasce no `open`, e o `ENOSPC` de disco cheio nasce no
        # `flush`.
        try:
            with self.arquivo.open("a", encoding="utf-8", newline="") as destino:
                csv.writer(destino, delimiter=SEPARADOR).writerow(celulas)
                destino.flush()
        except OSError as erro:
            # DEFINITIVO PARA A SESSAO, e nao ha nova tentativa: um retry por
            # tique a 1 Hz encheria o log com o mesmo erro e daria ao usuario a
            # impressao de que ainda esta gravando. Quem religa e o proximo
            # arranque, depois de o usuario consertar o arquivo ou a pasta.
            self.ligado = False
            log.error(
                "REGISTRO DE RENDA DESLIGADO — nao consegui escrever a amostra "
                "em %s: %s. O registro de renda PAROU nesta sessao e nao vai "
                "tentar de novo; quem religa e o proximo arranque, depois de "
                "voce consertar o arquivo ou a pasta.",
                self.arquivo,
                erro,
            )
            log.error(
                "Todo o resto do scanner continua igual: morte, saida e "
                "ressurreicao seguem sendo detectadas e entregues."
            )
            return False

        return True
