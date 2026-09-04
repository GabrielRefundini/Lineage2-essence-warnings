"""O dado do dashboard: le o CSV ao vivo e monta o JSON. UMA fonte, UMA conta.

O QUE ESTE MODULO NAO FAZ, E E ISSO QUE O DEFINE
=================================================
Ele nao tem parser proprio e nao tem formatador proprio. O parser continua sendo
`mercado_registro.observacoes_do_arquivo`; a aritmetica continua sendo
`mercado_analise`; as frases continuam saindo de `mercado_console`. O DASH-03 e
literalmente isto: "mesma fonte, mesma conta, sem um segundo parser".

O que ele acrescenta e SO a leitura AO VIVO — o mercado le o arquivo uma vez, no
arranque; o dashboard le a cada pedido, com o escritor ainda rodando — e a
montagem do dicionario que vira JSON.

ELE E PURO QUANTO DA: sem servidor, sem relogio proprio (o `agora` entra por
parametro), sem escrita. A unica coisa que ele toca no disco e uma leitura em
modo `"r"`, e ha teste de impressao digital prendendo isso.

O INVARIANTE DE LEITURA, ESCRITO POR EXTENSO (DASH-01 / T-01-04)
=================================================================
**Nenhuma funcao deste modulo abre arquivo fora do modo de leitura, e nenhuma
cria pasta.** `RegistroDeObservacoes.carregar` cria o `observacoes.csv` ausente
com cabecalho porque ela e o arranque do ESCRITOR; aqui nao ha escritor nenhum.
Criar o arquivo ou a pasta seria o programa ESCREVENDO num caminho de LEITURA —
o mesmo argumento com que `conferir_o_terminador` recusa truncar a cauda no
disco em vez de "consertar" o arquivo do usuario. Um arquivo que aparece sozinho
porque alguem abriu o dashboard e um efeito colateral que ninguem pediu,
inclusive num diretorio apontado por engano.

DUAS PROVAS PRENDEM ISSO, e nao uma: a impressao digital de tres componentes em
300 leituras (`tests/test_dashboard_leitura.py`) prova o que aconteceu; o
tripwire por leitura de fonte sobre `observacoes_ao_vivo` e sobre
`ArquivoRecortado.open` prova o que o codigo PODE fazer, e pega a regressao no
commit em que ela e escrita.
"""

from __future__ import annotations

import io
import logging
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import dashboard_rotas, mercado_registro
from .mercado_analise import (
    Evidencia,
    ModeloDeMercado,
    mediana_dos_unitarios,
    menor_pedido_visivel,
    recencia_do_preco,
)
from .mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA

# O `_recencia_em_duas_formas` E PRIVADO, E MESMO ASSIM E ELE QUE VEM.
#
# Ele nasceu privado porque so o desenho do console o usava. Agora ha um segundo
# desenho, e a escolha e entre duas coisas ruins: importar um nome com
# underscore, ou escrever a mesma logica de novo aqui. A segunda e pior, e nao
# por pouco — "ha 8 h (31/08 10:00)" reescrito e exatamente o segundo formatador
# que o DASH-03 proibe, e as duas copias divergiriam no primeiro ajuste de
# limiar. O underscore vira, entao, o aviso correto: nao ha promessa de
# estabilidade nesta assinatura, e quem a mudar tem de olhar para os dois
# chamadores.
#
# Promove-lo a nome publico seria mexer em `mercado_console.py`, que a decisao
# do usuario em 2026-09-01 (CTX-2) nao autoriza esta fase a tocar.
from .mercado_console import (
    UNIDADE_DA_TAXA,
    _recencia_em_duas_formas,
    descrever_a_quantidade,
    formatador_do_unitario,
    formatar_centesimos,
    formatar_taxa_derivada,
)

log = logging.getLogger(__name__)

__all__ = [
    "ArquivoRecortado",
    "CALCULADORA_COM_ITENS",
    "CALCULADORA_SEM_ITENS",
    "CALCULADORA_SEM_TAXA",
    "ESTADOS",
    "ESTADOS_DA_CALCULADORA",
    "FRASES_PROIBIDAS",
    "LARGURAS_DE_BALDE",
    "LIMIAR_DE_FRESCOR",
    "LeituraAoVivo",
    "NOTA_DE_LINHA_PARCIAL",
    "PontoDaSerie",
    "ancora_da_meia_noite",
    "baldes",
    "frase_de_piso_da_tipica",
    "frase_de_piso_do_menor",
    "observacoes_ao_vivo",
    "payload",
    "pontos_por_instante",
    "serie_para_o_grafico",
]


# ===========================================================================
# AS FRASES DA TELA — TODAS CONSTANTES NOMEADAS, TODAS DO PYTHON
# ===========================================================================
#
# ELAS SAO COPIA LITERAL DO `## Copywriting Contract` DO `01-UI-SPEC.md`, e
# moram aqui em vez de literais espalhados pelo corpo das funcoes pela mesma
# razao que `UNIDADE_DA_JANELA` mora no topo de `mercado_analise`: uma frase
# escrita duas vezes e uma frase que diverge no primeiro ajuste, e a divergencia
# aparece na tela do usuario e nao no teste.
#
# ELAS LEVAM ACENTO, e as do `mercado_console` nao — isso e INTENCIONAL e esta
# escrito no UI-SPEC. O console e ASCII por escolha dele (o `cmd` do Windows abre
# em cp1252); esta pagina e HTML em UTF-8 e a moldura e nossa. O que NAO pode
# acontecer e o navegador reacentuar a string que veio pronta do console: isso
# seria o SEGUNDO formatador que o DASH-03 proibe.

# A nota da cauda ignorada. Ela viaja no payload quando `cauda_incompleta` for
# verdadeiro, e chega PRONTA ao JS.
#
# E ELA E REDE DE SEGURANCA, E NAO O CAMINHO NORMAL — a medicao esta na
# docstring de `observacoes_ao_vivo`: ZERO leituras parciais em 22.970 tentativas
# durante 200.000 appends concorrentes. Um aviso que aparecesse toda hora viraria
# ruido, e ruido e indistinguivel de defeito.
NOTA_DE_LINHA_PARCIAL = "Última linha ignorada: incompleta (o scanner estava escrevendo)."

# O estado vazio. ELE E A PRIMEIRA TELA QUE O USUARIO VAI VER, e nao um caso de
# borda: medido em 2026-09-01, o `.mercado/observacoes.csv` de campo tem 93
# linhas e ZERO com a sentinela `adena#`. Gastar aqui o mesmo cuidado do estado
# povoado e o que impede a tela de parecer quebrada no dia da estreia.
TITULO_DO_ESTADO_VAZIO = "Nenhuma leitura da Adena ainda"
CORPO_DO_ESTADO_VAZIO = (
    "O painel de Adena nunca foi lido nesta máquina. Para começar: deixe o "
    "vigiar-mercado.bat rodando e abra a aba Adena da World Exchange no "
    "cliente. Cada página lida vira um ponto aqui sozinha, sem recarregar."
)

# A FRASE DE PROVA — a linha que separa "nao ha o que mostrar" de "o dashboard
# nao conseguiu abrir o arquivo". Sem os dois numeros REAIS ao lado, um estado
# vazio e indistinguivel de um defeito, e o usuario vai procurar bug onde nao ha.
#
# AS DUAS CONTAGENS SAO DA MESMA ESPECIE — registros — e e por isso que
# `linhas_completas` nao conta o cabecalho: "93 linhas, 0 da serie" com o
# cabecalho de um lado e observacoes do outro compararia coisas diferentes com a
# mesma palavra. O `01-UI-SPEC.md` ilustra a frase com `93`, que e a contagem de
# LINHAS do arquivo de campo; o payload informa as 92 de DADO.
#
# A PALAVRA `Adena` E COPY TRAVADO no `## Copywriting Contract`, e nao um `if` da
# Adena: a genericidade do DASH-05 mora no contrato de `series`, e nao numa frase
# que o usuario le sobre uma aba especifica. Uma segunda serie instanciada ganha
# a linha dela.
MOLDE_DA_PROVA_DA_LEITURA = "O arquivo foi lido: {linhas} linhas, {da_serie} da série Adena."

# O R$ ausente, dito com PALAVRA. Um cambio chutado — 1,00 "porque e redondo" —
# vira decisao de dinheiro real errada, e o numero errado nao se anuncia.
FRASE_DE_REAIS_INDISPONIVEL = "R$ indisponível — nenhum câmbio informado."

# Com UM valor informado nao existe serie de cambio, e a tela nao pode fingir que
# existe. Aplicar o cambio de hoje a um ponto de tres dias atras SEM AVISAR seria
# um numero certo com significado errado.
AVISO_DO_CAMBIO_HISTORICO = (
    "R$ calculado com o câmbio informado hoje, aplicado a toda a série."
)

# O dado velho. O `{recencia}` vem PRONTO de `_recencia_em_duas_formas` e entra
# sem ser tocado: remontar "ha 3 h (31/08 10:00)" aqui seria o segundo formatador
# de tempo, e as duas copias divergiriam no primeiro ajuste de limiar.
#
# A frase NEGA "agora" de proposito. A proibicao do UI-SPEC e sobre a AFIRMACAO
# de agora colada num numero velho; recusa-la em voz alta e o oposto disso.
MOLDE_DO_DADO_VELHO = (
    "Sem leitura nova: {recencia}. O valor abaixo é dessa leitura, não de agora."
)

# Os dois erros. Cada um diz O QUE FAZER — a anatomia de mensagem da casa, a
# mesma de `conferir_o_cabecalho`: o que aconteceu, o que NAO foi alterado, e o
# passo que religa a feature.
FRASE_DE_ARQUIVO_AUSENTE = (
    "Arquivo de observações não encontrado (.mercado/observacoes.csv). O "
    "--mercado ainda não gravou nada nesta máquina. Rode o vigiar-mercado.bat "
    "uma vez."
)
FRASE_DE_CABECALHO_QUEBRADO = (
    "O cabeçalho de .mercado/observacoes.csv não é o esperado. O dashboard não "
    "vai adivinhar as colunas."
)

# OS ROTULOS DAS DUAS LINHAS. `menor pedido visível` e a palavra do requisito, e
# a razao e honestidade: o scanner ve OFERTAS no quadro, nao transacoes
# concluidas. Ninguem comprou por este valor — alguem PEDIU este valor.
ROTULO_DO_MENOR = "menor pedido visível"
ROTULO_DA_TIPICA = "mediana"

# AS DUAS UNIDADES EXIBIDAS. Elas nao sao escolhidas por um `if` sobre a
# sentinela — ver `_e_a_taxa`, que deriva a resposta do UNICO ponto de decisao
# que ja existe (`formatador_do_unitario`).
#
# ATE 2026-09-03 A PRIMEIRA DIZIA `XM por milhão de adena`. A escala passou a
# CINCO milhoes, que e como a coluna do proprio jogo se escreve (`5 mln
# increment`) — ver o bloco de `UNIDADE_DA_TAXA` em `mercado_console.py`.
UNIDADE_EXIBIDA_DA_TAXA = "XM por 5 milhões de adena"
UNIDADE_EXIBIDA_DO_UNITARIO = "centésimos por unidade"

# O valor em R$, com a marca OBRIGATORIA de informado por voce. O UI-SPEC proibe
# por escrito "qualquer valor em R$ sem a marca de informado por você": o cambio
# nao foi lido de lugar nenhum, foi digitado, e quem copiar a linha para o
# WhatsApp precisa que essa procedencia viaje junto.
MOLDE_DO_VALOR_EM_REAIS = (
    "R$ {valor} por 5 milhões de adena (derivado do câmbio informado por você "
    "em {quando})"
)

# AS FRASES PROIBIDAS NA TELA, herdadas do `mercado_console` — onde ja ha teste
# prendendo-as sobre o texto devolvido E sobre o fonte.
#
# As tres sao a mesma mentira: o scanner ve OFERTAS no quadro, e nao transacoes
# concluidas. Ninguem comprou por este valor — alguem PEDIU este valor.
#
# EM MINUSCULA, e comparadas contra `texto.lower()`: a proibicao e sobre a
# expressao, e nao sobre a caixa em que alguem a escreveu.
#
# O `0,00` NAO ESTA NESTA TUPLA, E A RAZAO FOI MEDIDA AQUI. A quarta proibicao do
# UI-SPEC — "`0,00` como espaco reservado enquanto carrega" — parece pertencer a
# esta lista e NAO pertence: comparada por substring, ela reprova
# `"30,00 XM por 5 milhoes de adena (derivado)"`, que e um valor legitimo. Toda taxa
# terminada em zero (`10,00`, `20,00`, `30,00`) cairia junto. A proibicao e sobre
# o NUMERO INTEIRO ser zero, e por isso ela e verificada por TOKEN, com um molde
# de numero, em `tests/test_dashboard_dados.py` (`MOLDE_DE_NUMERO`) — e com um
# controle que exige a sonda acusar um `0,00` de verdade.
FRASES_PROIBIDAS = (
    "preço de venda",
    "preco de venda",
    "vendido por",
    "valor de mercado",
)

# OS CINCO ESTADOS, NA ORDEM DE PRECEDENCIA DO `01-UI-SPEC.md`. A ORDEM E
# FECHADA, e o primeiro que casar manda no destaque e no grafico.
#
# VARIOS PODEM SER VERDADE AO MESMO TEMPO — um arquivo com o cabecalho trocado
# tambem nao tem serie da Adena, e tambem esta abaixo do piso — e e precisamente
# por isso que a ordem precisa estar escrita num lugar so. Espalhada por quatro
# `if` em telas diferentes, ela vira quatro respostas para o mesmo arquivo.
#
# A ORDEM E A DA GRAVIDADE DA IGNORANCIA: primeiro "o arquivo nao e mais este
# arquivo" (nao da para afirmar NADA), depois "nao ha arquivo", depois "ha
# arquivo e nao ha esta serie", depois "ha esta serie e nao ha evidencia
# bastante", e so entao "ha o que mostrar".
ESTADO_ERRO_DE_CONTRATO = "erro_de_contrato"
ESTADO_ARQUIVO_AUSENTE = "arquivo_ausente"
ESTADO_SEM_LEITURA = "sem_leitura"
ESTADO_ABAIXO_DO_PISO = "abaixo_do_piso"
ESTADO_SERIE_PRESENTE = "serie_presente"

ESTADOS = (
    ESTADO_ERRO_DE_CONTRATO,
    ESTADO_ARQUIVO_AUSENTE,
    ESTADO_SEM_LEITURA,
    ESTADO_ABAIXO_DO_PISO,
    ESTADO_SERIE_PRESENTE,
)

# ACIMA DELE A TELA PARA DE AFIRMAR "AGORA" SOBRE O NUMERO — e so isso. O valor
# CONTINUA na tela; o que sai e a afirmacao de que ele vale neste instante.
#
# UMA HORA porque a coleta e de 1 Hz enquanto o `vigiar-mercado.bat` esta aberto:
# uma serie cuja oferta mais nova tem mais de uma hora significa que ninguem
# esteve na aba da Adena nesse tempo, e nao que o mercado ficou parado.
#
# ESCOLHA, NAO MEDICAO, no molde de `N_MINIMO_PARA_MEDIANA`. Ninguem mediu quanto
# tempo uma taxa da Adena leva para envelhecer — nao ha serie em campo para
# medir. Se na pratica a tela calar demais, este numero sobe, e e uma linha.
LIMIAR_DE_FRESCOR = timedelta(hours=1)


# ===========================================================================
# A CALCULADORA DE ROTAS — os tres estados do BLOCO e as frases dele
# ===========================================================================
#
# OS ESTADOS DO BLOCO SAO TRES, E ELES NAO SE MISTURAM COM OS QUATRO DA LINHA.
# O bloco responde "da para calcular alguma coisa?"; a linha responde "o que
# aconteceu com ESTE item". Um vocabulario so para os dois seria um `if` a mais
# em toda tela que os lesse.
CALCULADORA_COM_ITENS = "com_itens"
CALCULADORA_SEM_ITENS = "sem_itens"
CALCULADORA_SEM_TAXA = "sem_taxa"

ESTADOS_DA_CALCULADORA = (
    CALCULADORA_SEM_TAXA,
    CALCULADORA_SEM_ITENS,
    CALCULADORA_COM_ITENS,
)

# NENHUM ITEM CONFIGURADO. A regiao NAO fica um retangulo mudo: um painel vazio
# e indistinguivel de um painel quebrado, e este e o estado em que TODO usuario
# comeca — a secao nasce comentada no `config.toml`.
#
# A frase diz O QUE FAZER, com o nome da secao e os tres campos, na anatomia de
# mensagem da casa (a mesma de `conferir_o_cabecalho`): o que ha, o que falta, e
# o passo que liga a coisa.
FRASE_DE_SEM_ITENS_CONFIGURADOS = (
    "Nenhum item configurado. Para comparar as duas rotas de compra, abra o "
    "config.toml e descomente um bloco [[dashboard.item]] com nome, "
    "preco_npc_adena e quantidade_do_pacote — e reinicie o dashboard."
)

# SEM TAXA DA ADENA NAO HA COMO CONVERTER O PRECO DO NPC. A frase diz qual das
# duas metades falta, e nao "sem dados": o preço do NPC pode estar perfeitamente
# configurado, e o que falta e o outro lado.
#
# ATE 2026-09-03 ELA ERA UMA FRASE FIXA e dizia, por extenso, *"Sem leitura da
# Adena"*. **Ela passou a ser um MOLDE porque a antiga virou falsa no caso
# novo**: com o piso do veredito valendo tambem para a serie da Adena (ver
# `_bloco_da_calculadora`), o bloco pode entrar neste estado com QUATRO ofertas
# lidas — e afirmar que nao ha leitura nenhuma seria uma frase mentindo sobre o
# proprio estado que ela nomeia, que e pior do que nao ter frase.
#
# ELA DIZ AGORA QUANTAS FALTAM, com os dois numeros da `Evidencia` (`n` e
# `piso`) e o `faltam` derivado — o mesmo trio que `frase_de_piso_da_tipica` ja
# usa, e pela mesma razao: quem exibe nao faz conta de cabeca.
#
# **O NOME CONTINUA `FRASE_`, E A TENSAO FICA REGISTRADA.** A convencao desta
# casa e `MOLDE_` para texto com `{campo}` e `FRASE_` para texto fixo, e por ela
# esta constante deveria ter sido renomeada. Ela NAO foi, e a razao e concreta:
# o nome dela esta citado por extenso no comentario da regiao correspondente do
# `index.html`, e este plano nao toca arquivo web nenhum. Renomear aqui deixaria
# um simbolo inexistente citado la — um erro de FATO, que e pior que um prefixo
# fora da convencao, porque o prefixo se desmente no primeiro `.format` do sitio
# de uso e o simbolo fantasma nao se desmente nunca. No dia em que a marcacao
# for mexida por outro motivo, os dois se renomeiam juntos.
FRASE_DE_SEM_TAXA_DA_ADENA = (
    "Ainda não dá para converter o preço do NPC em XM: a série da Adena tem "
    "{n} de {piso} ofertas distintas, faltam {faltam}. Deixe o "
    "vigiar-mercado.bat rodando e abra a aba Adena da World Exchange mais "
    "algumas vezes."
)

# O ITEM QUE NUNCA APARECEU NO CSV. Ele NAO some da tela: sumir seria
# indistinguível de "esqueci de configurar", e o usuário ficaria procurando um
# bloco que já está lá (decisão travada do 02-CONTEXT).
#
# O NOME QUE APARECE É O QUE O USUÁRIO ESCREVEU, e não a chave da série — é o
# texto dele que ele vai procurar no `config.toml` para conferir.
MOLDE_DE_ITEM_NUNCA_VISTO = (
    "O preço de NPC de {item} já está configurado, mas o scanner ainda não viu "
    "esse item no World Exchange. Abra a aba dele no cliente uma vez."
)

# O NOME QUE CASA COM DUAS SÉRIES. O dashboard LISTA e não escolhe: escolher
# daria um número plausível e errado — a mesma disciplina de
# `mercado_analise.margem_de_craft`.
MOLDE_DE_NOME_AMBIGUO = (
    "{item} casa com {quantas} séries ao mesmo tempo: {candidatas}. O dashboard "
    "não vai escolher uma por você — renomeie o item no config.toml para o nome "
    "exato de uma delas."
)

# COMO O NPC REALMENTE VENDE, ao lado do unitário derivado. Sem esta linha, o
# "13,50 por unidade" não tem como ser conferido na janela do NPC, que mostra o
# preço do PACOTE.
#
# AS DUAS METADES SAEM DE FORMATADORES QUE JÁ EXISTEM —
# `descrever_a_quantidade` dos dois lados, uma vez com a chave da Adena (que dá
# "15.000 de adena") e uma vez com a chave da série do item (que dá "1 unidade").
# Nenhum número é montado aqui.
MOLDE_DO_PACOTE_DO_NPC = "{preco} por {quantidade}"

# O INSTANTE EM QUE O PROGRAMA LEU O ARQUIVO — e NUNCA o instante em que o
# usuário informou o preço.
#
# AS DUAS COISAS TÊM NOMES PARECIDOS E SÃO FATOS DIFERENTES, e trocar uma pela
# outra é mentir com a forma de um número: o preço pode estar no `config.toml`
# há meses, e a leitura ser de dois minutos atrás. A escolha da palavra é o
# requisito aqui, e não redação — o plano 02-03 traz a razão inteira com a
# alternativa recusada.
#
# POR QUE ELE EXISTE: esta fase cria um modo de falha que a Fase 1 não tinha. A
# configuração é lida UMA vez, no arranque. Quem corrigir um preço no
# `config.toml` e recarregar o navegador vê o número VELHO, sem nenhum sinal de
# que o processo não releu o arquivo. Com o instante da leitura na tela, a
# pergunta "o dashboard que está rodando já conhece a minha correção?" tem
# resposta.
#
# O `{recencia}` VEM PRONTO de `_recencia_em_duas_formas` — a relativa e a
# absoluta juntas. Remontar "há 8 h (31/08 10:00)" aqui seria o segundo
# formatador de tempo, e o navegador não tem o direito de compor uma segunda
# forma de tempo.
MOLDE_DA_LEITURA_DA_CONFIGURACAO = (
    "Preços de NPC lidos do config.toml {recencia}. Corrigiu o arquivo? "
    "Reinicie o dashboard."
)

# A DIFERENÇA EM PORCENTAGEM, com UMA casa decimal.
#
# ESTE É O PRIMEIRO FORMATADOR DE PORCENTAGEM DA CAMADA DE EXIBIÇÃO, e não um
# segundo: não havia nenhum. O único lugar do projeto que imprime porcentagem é
# `mercado_analise.frase_da_tendencia`, que a monta inline com `:+.1f%` para o
# console — e ele é console (ASCII, com sinal) enquanto este é página (acento,
# sem sinal, com vírgula decimal). O que os dois compartilham é a PRECISÃO: uma
# casa. Duas casas afirmariam sobre um número que repousa em UMA oferta uma
# precisão que ele não tem.
#
# O ARREDONDAMENTO ACONTECE SÓ AQUI, sobre a `Fraction` exata, e a vírgula é
# montada por divisão inteira — nunca por `float`, pelo mesmo motivo que
# `formatar_centesimos` usa `divmod`.
MOLDE_DA_DIFERENCA_PERCENTUAL = "{valor}%"


@dataclass(frozen=True)
class ArquivoRecortado:
    """Um objeto com FORMA de `Path`, que entrega texto ja cortado.

    POR QUE ELE EXISTE
    ==================
    `observacoes_do_arquivo` recebe um `Path` e le o arquivo ela mesma
    (`mercado_registro.py:552-556`). O dashboard precisa do MESMO corpo — os
    mesmos dois portoes, as mesmas duas redes por linha — mas sobre um texto que
    ele ja cortou na ultima quebra de linha. Este adaptador e o encaixe: ele diz
    "sim, eu sou um arquivo", devolve o texto recortado no `open()`, e devolve o
    caminho REAL no `__str__`.

    AS QUATRO ROTAS, E POR QUE TRES FORAM RECUSADAS
    ===============================================
    A pesquisa desta fase listou tres saidas para reusar o corpo do parser sobre
    um texto ja cortado, e recomendou a (a). Nenhuma das tres serve:

    (a) EXTRAIR `observacoes_do_texto` DE `mercado_registro.py`, deixando
        `observacoes_do_arquivo` como uma casca que le e delega. E a mais limpa
        das quatro, e seria a escolha obvia — mas ela MEXE em
        `mercado_registro.py`, e a decisao do usuario em 2026-09-01 (CTX-2)
        nomeia `mercado_catalogo.py` como o UNICO arquivo do workstream
        `mercado` que esta fase pode tocar. Recusada por escopo, e nao por
        merito: quando o workstream `mercado` abrir de novo, esta rota deve
        substituir este adaptador.

    (b) ESCREVER O TEXTO CORTADO NUM ARQUIVO TEMPORARIO e passar o caminho dele.
        Recusada porque quebra a mensagem de erro: `conferir_o_cabecalho`
        imprime o caminho que recebeu, e o usuario leria "restaure a primeira
        linha de C:\\Users\\...\\AppData\\Local\\Temp\\tmp8f2a.csv" — um arquivo
        que nao existe mais quando ele for procurar. A instrucao da mensagem so
        vale se ela nomear o arquivo que da para abrir. Ha teste prendendo isso.

    (c) UM SEGUNDO LACO DE `csv.reader` AQUI. Recusada porque e, literalmente, o
        segundo parser que a docstring de `observacoes_do_arquivo` existe para
        nao ter: das cinco truncagens medidas byte a byte na Fase 3, DUAS
        produzem seis campos todos parseaveis, com `80` virando `8`. Duas
        implementacoes de leitura sao duas chances de uma delas nao ter o portao
        do terminador.

    (d) ESTE ADAPTADOR — a escolhida. Zero arquivo do mercado tocado, UM parser,
        os dois portoes continuam sendo chamados, e a mensagem continua nomeando
        `.mercado/observacoes.csv`.

    O PRECO, DITO EM VOZ ALTA: e um acoplamento de FORMA. Este objeto implementa
    `open`, `__str__` e `__fspath__` porque e o que `observacoes_do_arquivo` usa
    hoje; se ela passar a chamar `.stat()` ou `.exists()`, este adaptador quebra
    com `AttributeError`. O antidoto e o teste de equivalencia do tracer, que
    compara o resultado desta rota com a chamada direta do parser sobre o mesmo
    arquivo — se o corpo do parser mudar de forma, o teste cai antes do usuario.
    """

    caminho_real: Path
    texto: str

    def open(self, *args: Any, **kwargs: Any) -> io.StringIO:
        """O texto ja cortado, como se viesse do disco.

        Os argumentos sao ACEITOS E IGNORADOS de proposito: quem chama passa
        `("r", encoding="utf-8", newline="")`, e o texto ja esta decodificado e
        sem traducao de quebra de linha. Recusar os argumentos obrigaria o
        chamador a saber que nao e um `Path` de verdade, que e exatamente o que
        este objeto existe para esconder.
        """
        return io.StringIO(self.texto, newline="")

    def __str__(self) -> str:
        return str(self.caminho_real)

    def __fspath__(self) -> str:
        return str(self.caminho_real)


@dataclass(frozen=True)
class LeituraAoVivo:
    """O que uma leitura ao vivo devolve: o dado E o que houve com o arquivo.

    OS DOIS SINAIS VIAJAM COLADOS no dado, e nao ao lado dele, pela mesma razao
    que a `Evidencia` viaja dentro de cada resultado do `mercado_analise`: quem
    desenha nao pode ser obrigado a LEMBRAR de perguntar se a cauda estava
    cortada. `arquivo_ausente` e `cauda_incompleta` sao fatos sobre a procedencia
    do numero, e o rodape da tela existe para mostra-los.
    """

    observacoes: list = field(default_factory=list)
    cauda_incompleta: bool = False
    arquivo_ausente: bool = False

    # QUANTAS LINHAS DE DADO O TRECHO COMPLETO TINHA — sem o cabecalho, e
    # contando tambem as que o parser descartou.
    #
    # ELA E A PROVA DE QUE A LEITURA ACONTECEU, e e isso que a torna necessaria:
    # no estado vazio a tela precisa dizer "o arquivo foi lido: N linhas, 0 da
    # serie Adena". Sem esse numero, "0 da serie Adena" e indistinguivel de "o
    # dashboard nao conseguiu abrir o arquivo" — que e exatamente o erro que o
    # estado vazio desenhado existe para nao cometer.
    #
    # ELA CONTA REGISTROS, E NAO LINHAS DO ARQUIVO. A frase que ela alimenta poe
    # duas contagens lado a lado ("N linhas, M da serie"), e as duas tem de ser
    # da mesma especie: incluir o cabecalho de um lado e contar observacoes do
    # outro seria comparar coisas diferentes com a mesma palavra.
    #
    # E ELA CONTA A LINHA RUIM TAMBEM. A linha esta no arquivo; quem quiser saber
    # quantas sobreviveram ao parser tem `len(observacoes)` ao lado, e o log
    # NOMEIA cada uma que caiu.
    linhas_completas: int = 0


def observacoes_ao_vivo(arquivo: Path) -> LeituraAoVivo:
    """As observacoes do CSV ATE A ULTIMA LINHA COMPLETA, com o arquivo em uso.

    ESTA FUNCAO DECIDE O CONTRARIO DO QUE A FASE 3 DECIDIU, E A FASE 3 ESTAVA
    CERTA — PARA ELA
    ==================================================================
    `conferir_o_terminador` RECUSA O ARQUIVO INTEIRO quando ele nao termina em
    quebra de linha, e a docstring dela explica por que: la o leitor e o ARRANQUE
    DO ESCRITOR, que vai APENDAR em seguida. Uma cauda ambigua naquele contexto
    vira chave de dedup errada e depois preco errado gravado como bom, para
    sempre. Desligar alto e a resposta certa.

    Aqui o contexto e outro e o oposto e a resposta certa. Este processo NUNCA
    escreve neste arquivo, e o escritor legitimo esta rodando AGORA, no outro
    processo. Recusar o arquivo inteiro por causa de uma cauda de meio segundo
    apagaria o grafico da tela a cada vez que o `--mercado` estivesse no meio de
    um `write` — e o usuario veria o dashboard "quebrar" sozinho, sem causa
    visivel.

    O CORTE ACONTECE ANTES DO PORTAO, E POR ISSO O PORTAO CONTINUA EXISTINDO. O
    texto entregue ao parser termina em quebra de linha POR CONSTRUCAO, entao
    `conferir_o_terminador` e chamada e passa; `conferir_o_cabecalho` e chamada e
    continua desligando alto se o arquivo nao for mais o arquivo deste programa.
    Nenhum dos dois portoes foi afrouxado — o primeiro passou a julgar um texto
    de que a ambiguidade ja foi retirada.

    A FREQUENCIA DO CASO ESTA MEDIDA, E O ROADMAP A SUPERESTIMOU
    ============================================================
    A premissa era "leituras parciais vao acontecer o tempo todo". Ela e FALSA
    para o escritor que este projeto tem. `csv.writer.writerow` seguido de
    `flush` e UMA unica chamada de escrita, e o escritor abre, escreve, da flush
    e fecha por linha. Medido: em **22.970** leituras de cauda durante 200.000
    appends concorrentes, **ZERO** leituras sem terminador e zero erros de
    abertura. Com uma linha de 256 KB, tambem zero.

    E O ZERO E RESULTADO, E NAO CEGUEIRA DA SONDA: um controle positivo que
    escrevia a linha em DUAS chamadas com pausa no meio (`os.write` do texto,
    pausa, `os.write` do terminador) acusou **3.252 de 4.079**. A sonda enxerga
    o defeito quando ele existe; ela nao o viu porque ele nao acontece.

    O QUE ISSO MUDA: esta degradacao e REDE DE SEGURANCA, e nao o caminho
    normal. Ela existe para o arquivo editado a mao no Sheets e salvo sem quebra
    final, e para a queda de energia — nao para a corrida com o escritor, que
    medimos e nao existe. Escrever "o normal e a cauda estar cortada" no fonte
    seria carregar para as proximas fases uma premissa que a medicao ja derrubou.

    ELA NAO CAPTURA `ContratoDoArquivoQuebrado`. O portao do cabecalho continua
    desligando alto, e quem decide o que MOSTRAR nessa hora e a camada de
    payload — engolir a excecao aqui esconderia de todos os chamadores um
    arquivo que deixou de ser este arquivo.
    """
    try:
        with arquivo.open("r", encoding="utf-8", newline="") as fonte:
            bruto = fonte.read()
    except FileNotFoundError:
        # A `.mercado/` nasce vazia, e "ainda nao gravaram nada" e uma resposta
        # legitima — nao um erro. O molde e o de `observacoes_do_arquivo`, que
        # tambem devolve vazio em vez de levantar.
        return LeituraAoVivo(arquivo_ausente=True)

    if not bruto:
        # Zero bytes: nao ha byte do usuario para julgar, e tambem nao ha cauda.
        return LeituraAoVivo()

    corte = bruto.rfind("\n")
    if corte < 0:
        # NENHUMA quebra de linha no arquivo inteiro. Nao ha uma unica linha
        # completa, entao nao ha o que ler — e a cauda e o arquivo todo.
        return LeituraAoVivo(cauda_incompleta=True)

    completo = bruto[: corte + 1]
    cauda = bruto[corte + 1 :]

    return LeituraAoVivo(
        observacoes=mercado_registro.observacoes_do_arquivo(
            ArquivoRecortado(caminho_real=arquivo, texto=completo)
        ),
        # As linhas de DADO do trecho completo: tudo menos o cabecalho, e sem
        # contar as linhas em branco que o parser tambem pula. O `max` protege o
        # unico caso em que o arquivo tem cabecalho e mais nada — subtrair daria
        # `-1`, e uma contagem negativa na frase de prova seria pior que nenhuma.
        linhas_completas=max(
            0, len([linha for linha in completo.splitlines() if linha.strip()]) - 1
        ),
        # `bool(cauda)` e nao `bool(cauda.strip())`: qualquer byte depois do
        # ultimo terminador e uma linha que o programa nao consegue afirmar,
        # inclusive um punhado de espacos. O rodape prefere dizer "ignorei uma
        # cauda" de graca a esconder uma de verdade.
        cauda_incompleta=bool(cauda),
    )


# ===========================================================================
# A AGREGACAO: UM PONTO E UM INSTANTE, E O BALDE NUNCA INVENTA VALOR
# ===========================================================================


@dataclass(frozen=True)
class PontoDaSerie:
    """UM instante de leitura: o menor, a tipica, e a evidencia de cada um.

    A `Evidencia` VIAJA DENTRO DO PONTO, e nao num campo paralelo — o molde e o
    de `mercado_analise:226-254`, e a razao escrita la vale aqui inteira:
    estatistica sem `n` e adivinhacao com cara de numero, e um `n` que quem
    desenha pode esquecer de pedir e um `n` que uma hora nao vai ser exibido.

    SAO DUAS EVIDENCIAS E NAO UMA porque os pisos sao diferentes e o motivo da
    ausencia tambem: o menor pedido e um FATO OBSERVADO (piso 1 — aquele anuncio
    existiu), e a mediana e uma INFERENCIA (piso 5 — com menos de cinco, duas
    leituras aberrantes movem o miolo). Um campo so obrigaria quem desenha a
    adivinhar de qual dos dois numeros aquele `n` estava falando.

    `frozen` porque ninguem reescreve um ponto depois de calcula-lo: o arquivo e
    a verdade e este objeto e uma conta sobre ele.
    """

    instante: datetime
    menor: Fraction | None
    menor_evidencia: Evidencia
    tipica: Fraction | None
    tipica_evidencia: Evidencia
    n: int


def pontos_por_instante(observacoes: Sequence) -> list[PontoDaSerie]:
    """UM PONTO = UM INSTANTE DE LEITURA (`primeira_vez`). Literalmente.

    A DECISAO, A RECOMENDACAO CONTRARIA, E QUEM DECIDIU
    ===================================================
    Esta funcao aplica `menor_pedido_visivel` e `mediana_dos_unitarios` — as
    MESMAS contas do console — ao SUBCONJUNTO de um unico instante. Ela nao e a
    conta que o console faz: o console chama as duas sobre `observacoes_de(chave)`,
    que e a serie INTEIRA.

    A pesquisa desta fase mediu o custo dessa diferenca sobre o dado real: **92
    observacoes com apenas 13 valores distintos de `primeira_vez`**, e a maior
    serie com **15 observacoes em 2 instantes**. Com `N_MINIMO_PARA_MEDIANA`
    valendo 5, agrupar por instante deixa a linha da mediana **AUSENTE na maior
    parte do grafico**. A docstring de `mercado_analise` ja avisava por extenso
    que "nao existe serie temporal de preco neste CSV — existe uma sequencia de
    anuncios diferentes, e o `n` conta anuncios, nao instantes", e e essa frase
    que esta agregacao paga.

    A PESQUISA, POR ISSO, RECOMENDOU A OUTRA LEITURA: o acumulado ATE o instante,
    que bate literalmente com o console ("os numeros batem para o mesmo
    instante", DASH-03) e quase sempre tem mediana.

    **O USUARIO, CONFRONTADO COM ESSA MEDICAO EXATA EM 2026-09-01, MANTEVE A
    LEITURA LITERAL (CTX-1) e recusou o acumulado.** A recusa esta registrada no
    `01-CONTEXT.md` e no bloco `RESOLVIDO` da `Open Question 1` do
    `01-RESEARCH.md`, que termina com "nao reintroduzir (b)".

    CONSEQUENCIA, E ELA E O CAMINHO NORMAL DESTA TELA
    =================================================
    A linha da mediana falta na maior parte do grafico, e onde ela falta o que
    aparece e a **frase de piso vinda do Python** — nunca um numero. Isso NAO e
    um defeito do grafico nem um estado de erro: e a ausencia de evidencia sendo
    dita com palavra em vez de preenchida com zero, que e a disciplina que este
    projeto inteiro segue. Quem vier depois e achar que "esta faltando dado" tem
    de ler este paragrafo antes de "consertar".

    A ORDEM DE SAIDA E POR INSTANTE, e nao a do arquivo. O `ModeloDeMercado`
    preserva de proposito a ordem do CSV — para nao esconder de quem depura o que
    o arquivo diz — mas um eixo do tempo desordenado desenharia a serie indo e
    voltando. Ordenar e responsabilidade desta camada.
    """
    por_instante: dict[datetime, list] = {}
    for observacao in observacoes:
        por_instante.setdefault(observacao.primeira_vez, []).append(observacao)

    pontos: list[PontoDaSerie] = []
    for instante in sorted(por_instante):
        do_instante = por_instante[instante]
        menor = menor_pedido_visivel(do_instante)
        tipica = mediana_dos_unitarios(do_instante)
        pontos.append(
            PontoDaSerie(
                instante=instante,
                menor=menor.unitario,
                menor_evidencia=menor.evidencia,
                tipica=tipica.unitario,
                tipica_evidencia=tipica.evidencia,
                # O `n` do ponto e o das ofertas COMPARAVEIS, e por isso ele sai
                # da evidencia em vez de `len(do_instante)`: uma linha de
                # quantidade nao positiva nao entra em conta nenhuma, e conta-la
                # como evidencia seria inflar a evidencia.
                n=menor.evidencia.n,
            )
        )
    return pontos


# AS TRES LARGURAS DE BALDE, E POR QUE TRES.
#
# O usuario disse a pergunta dele em voz alta, e ela tem duas resolucoes:
# "mostrar em horarios do dia" e "dar zoom-out em dias atras". Uma largura de
# CINCO MINUTOS serve a primeira (dentro de uma sessao de farm, cada releitura do
# painel e um ponto), uma de UM DIA serve a segunda, e UMA HORA e a intermediaria
# sem a qual o salto entre as duas engole a forma da curva de um dia inteiro.
#
# ESCOLHA, NAO MEDICAO — no molde de `N_MINIMO_PARA_MEDIANA`. Ninguem mediu qual
# resolucao o usuario mais usa, porque ainda nao ha uso: a serie da Adena tem
# zero linhas em campo. Se na pratica uma delas nunca for tocada, ela sai daqui,
# e e uma linha.
LARGURAS_DE_BALDE = {
    "cinco_minutos": timedelta(minutes=5),
    "uma_hora": timedelta(hours=1),
    "um_dia": timedelta(days=1),
}


def ancora_da_meia_noite(instante: datetime) -> datetime:
    """A meia-noite LOCAL do dia deste instante. A origem dos baldes.

    MEDIDO, E E POR ISSO QUE ESTA FUNCAO EXISTE: com a ancora posta num instante
    arbitrario — a primeira observacao, por exemplo, as `2026-08-31 15:00` — os
    baldes de `timedelta(days=1)` comecam as **15:00**. Duas leituras do mesmo
    dia civil, uma as 09:00 e outra as 22:00, caem em baldes DIFERENTES, e "dias
    atras" deixa de querer dizer o que um humano acha que quer dizer.

    O erro nao aparece como excecao nem como numero absurdo: aparece como uma
    curva que "parece deslocada", que e a familia de defeito mais cara de achar.
    Ha teste com CONTROLE prendendo os dois lados — a ancora certa junta o dia, a
    ancora de 15:00 o parte.

    HORA LOCAL INGENUA, sem fuso, como todo carimbo deste projeto: o CSV grava
    `agora.isoformat()` sem `tzinfo`, e introduzir fuso aqui criaria duas
    convencoes de tempo na mesma tela.
    """
    return instante.replace(hour=0, minute=0, second=0, microsecond=0)


def baldes(
    pontos: Sequence[tuple[datetime, Fraction]],
    largura: timedelta,
    ancora: datetime,
) -> list[tuple[datetime, Fraction]]:
    """Um valor por balde, e o valor do balde EXISTIU na tela (D-02).

    Recebe pares `(instante, valor)` — e nao `PontoDaSerie` — porque um ponto tem
    DOIS valores (o menor e a tipica) e cada um vira uma linha propria no
    grafico. Passar o ponto inteiro obrigaria esta funcao a escolher qual das
    duas linhas ela esta agregando, e essa escolha e de quem monta a serie.

    O INDICE E INTEIRO EXATO: `(t - ancora) // largura` opera sobre os
    microssegundos inteiros do `timedelta`. `total_seconds()` devolveria `float`
    — medido, **69713.696** contra **69713** inteiro — e `float` e como um
    centavo aparece do nada. Um indice de balde nao tem parte fracionaria nenhuma
    a preservar, entao o `float` aqui so poderia piorar.

    O VALOR DE CADA BALDE E `statistics.median_low`, E A ALTERNATIVA ESTA
    REFUTADA COM O NUMERO: `statistics.median` sobre quatro `Fraction` devolveu
    **13/42**, um valor que **nao esta na lista** — a media dos dois do meio,
    meio centavo inventado, exatamente o que o D-02 recusou quando decidiu nao
    guardar o unitario arredondado. `median_low` devolve sempre um ELEMENTO da
    lista, e cada elemento ja e um unitario que esteve na tela; a composicao
    portanto preserva a disciplina. Ha um `assert in` por balde prendendo isso, e
    ele e a forma executavel do D-02: `median`, `mean` e `median_high` continuam
    devolvendo um numero plausivel e do tamanho certo, e so o `assert in` os pega.

    A ORDEM DE SAIDA E CRONOLOGICA porque `dict` preserva ordem de INSERCAO, e a
    de insercao e a da lista de entrada — que nao e garantidamente ordenada.
    """
    por_balde: dict[int, list[Fraction]] = {}
    for instante, valor in pontos:
        por_balde.setdefault((instante - ancora) // largura, []).append(valor)

    return sorted(
        (ancora + indice * largura, statistics.median_low(valores))
        for indice, valores in por_balde.items()
    )


# ===========================================================================
# AS DUAS FRASES DE PISO — ESPELHO DAS DUAS LINHAS DO CONSOLE
# ===========================================================================
#
# SAO DUAS, E NAO UMA COM UM SINALIZADOR, pela razao que `formatar_taxa_derivada`
# ja escreveu neste projeto: "um default e uma chamada que alguem esquece de
# passar; duas funcoes com nomes diferentes sao duas coisas que ninguem confunde
# por omissao". O console tem duas redacoes — o menor sem `faltam`, a mediana com
# — e espelhar UMA das duas em ambos os lugares faria a tela discordar do
# terminal para um dos dois numeros.
#
# ELAS NAO SAO REUSO POR CHAMADA, E O `01-01-SUMMARY` PEDIU QUE ISSO FICASSE DITO:
# `_linha_do_menor` e `_linha_da_mediana` entregam a frase ja dentro de uma linha
# formatada para o terminal (recuo de quatro espacos, rotulo colado), e essa
# metade nao serve ao HTML. O que da para prender e a IGUALDADE POR SUBSTRING, e
# ha um teste por frase fazendo exatamente isso contra a linha do console — se
# alguem mexer num dos dois lados, os dois testes caem juntos.


def frase_de_piso_do_menor(evidencia: Evidencia) -> str:
    """O que FALTA para haver menor pedido visivel. Nunca um numero.

    Espelha `mercado_console._linha_do_menor:549-553` — SEM `faltam`, porque o
    piso do menor e 1 e "faltam 1" nao acrescenta nada a "0 de 1".
    """
    return (
        f"sem evidencia - {evidencia.n} de {evidencia.piso} ofertas distintas"
    )


def frase_de_piso_da_tipica(evidencia: Evidencia) -> str:
    """O que FALTA para haver mediana. Nunca um numero.

    Espelha `mercado_console._linha_da_mediana:588-593` — COM `faltam`, que e
    campo derivado da `Evidencia` justamente para quem exibe nao ter de fazer a
    conta de cabeca.
    """
    return (
        f"sem evidencia - {evidencia.n} de {evidencia.piso} ofertas distintas, "
        f"faltam {evidencia.faltam}"
    )


# ===========================================================================
# A SERIE PARA O GRAFICO — GENERICA POR CONSTRUCAO (DASH-05)
# ===========================================================================


def _e_a_taxa(chave_da_serie: str) -> bool:
    """Esta serie se fala em XM por 5 milhoes? A resposta vem do UNICO ponto.

    ELA NAO REPETE O `if` DA SENTINELA. `formatador_do_unitario` ja e o unico
    ponto de decisao entre a taxa da Adena e o unitario comum, e a docstring dele
    explica o que quatro `if` espalhados fariam: no dia em que um divergisse, a
    tela imprimiria `0,00 por unidade` para a Adena com toda a confianca do
    mundo. Aqui a unidade EXIBIDA e a ESCALA do grafico sao derivadas da
    identidade da funcao devolvida — se o criterio mudar la, muda aqui junto, sem
    ninguem precisar lembrar.
    """
    return formatador_do_unitario(chave_da_serie) is formatar_taxa_derivada


def _escala_do_grafico(chave_da_serie: str) -> int:
    """O multiplicador que leva o unitario a unidade EXIBIDA daquela serie.

    Sem ele, a taxa da Adena entraria no eixo como `0,00116` — inexibivel e
    indistinguivel de zero num grafico, que e o mesmo defeito que
    `formatar_taxa_derivada` existe para nao ter no texto.
    """
    return UNIDADE_DA_TAXA if _e_a_taxa(chave_da_serie) else 1


def _pixel(chave_da_serie: str, valor: Fraction | None) -> float | None:
    """A FRONTEIRA DO `float`, e ela existe UMA vez — aqui.

    O `float` NO JSON E O PIXEL; A `string` NO JSON E A VERDADE. JSON nao tem
    `Fraction`, e o canvas so aceita numero de JS: em algum ponto a fracao exata
    tem de virar ponto flutuante. Este e o ponto, e ele carrega a string pronta ao
    lado em todo lugar onde aparece — o texto do tooltip e o da legenda saem da
    STRING, e nunca de um `toFixed()` no navegador (isso seria o segundo
    formatador que o DASH-03 proibe).

    O ERRO DESSA CONVERSAO ESTA MEDIDO, e por isso ela e aceitavel: sobre a taxa
    da Adena em centesimos por 5 milhoes, o pior caso medido foi **7,76e-11** —
    em `Fraction(1, 3) x 5x10⁶`, que da `1666666.6666666667`. Os valores reais
    do CSV (`11600/10.000.000` e `30000/15.000.000`) converteram com erro
    **ZERO** — medido de novo na escala nova, e nao herdado da anterior. Um erro
    de 7,76e-11 centesimo nao move um pixel; um erro na string moveria a decisao
    de compra.

    ESTE NUMERO SUBIU, E SUBIR ERA O ESPERADO: ate 2026-09-03 a escala era um
    milhao e o pior caso medido era **1,9e-11**, em `Fraction(1, 3) x 10⁶` =
    `333333.3333333333`. Multiplicar por cinco leva o valor a uma faixa onde o
    `float` de dupla precisao tem menos bits de fracao disponiveis, entao o erro
    ABSOLUTO cresce junto — quase pelo mesmo fator (medido: 1,94e-11 -> 7,76e-11,
    exatamente x4). O erro RELATIVO nao piorou: medido, ele CAIU de 5,82e-17
    para 4,66e-17, os dois abaixo do epsilon da maquina (2,22e-16). As duas
    medicoes sairam de chamadas a codigo de producao, e nao de uma conta refeita
    por fora.

    AUSENCIA VIRA `None`, E NUNCA `0.0`. Zero e um lugar no eixo — uma taxa de
    zero — e desenhar a ausencia la seria afirmar que a taxa despencou.
    """
    if valor is None:
        return None
    return float(valor * _escala_do_grafico(chave_da_serie))


# O TETO DE MARCAS DE UMA ESCADA. ELE E ESCOLHA, E NAO MEDICAO — e dizer isso e
# mais honesto do que deixar o leitor supor que houve um experimento.
#
# O QUE ELE COMPRA: o tamanho do payload. Cada marca custa um `float` e uma
# string curta, e sem teto a escada mais fina de uma faixa larga teria dezenas de
# milhares delas.
#
# O QUE ELE CUSTA: o quanto da para APROXIMAR antes de o eixo comecar a perder
# marca. As escadas nascem da faixa INTEIRA da serie; quem aproxima alem do que a
# escada mais fina cobre ve menos marcas, e no limite nenhuma. Duzentos e o ponto
# em que a faixa medida do CSV de hoje ainda entrega passo 5 — cinco centesimos
# de resolucao — sem o payload sentir.
MAXIMO_DE_MARCAS_POR_ESCADA = 200


def _passos_bonitos(largura_da_faixa: Fraction) -> list[int]:
    """Um, dois e cinco vezes potencia de dez, enquanto o passo couber na faixa.

    SAO OS PASSOS QUE UM HUMANO LE SEM PENSAR — `56,00 / 57,00 / 58,00`, e nunca
    `56,37 / 57,74`. A regra e a mesma que qualquer eixo de grafico usa, e esta
    escrita aqui como REGRA para nao virar uma tabela de casos que envelhece.

    O corte e `passo > largura`: um passo maior que a faixa inteira nao pode ter
    duas marcas dentro dela. Isso NAO dispensa o filtro de duas marcas la em
    cima — um passo que cabe na largura ainda pode cair desalinhado e render uma
    marca so (faixa `[5550, 6000]`, passo 450: so `5850`).
    """
    passos: list[int] = []
    expoente = 0
    while True:
        for base in (1, 2, 5):
            passo = base * 10**expoente
            if passo > largura_da_faixa:
                return passos
            passos.append(passo)
        expoente += 1


def _escadas_do_eixo(minimo: Fraction, maximo: Fraction) -> list[dict]:
    """As marcas do eixo vertical, JA COM O TEXTO, da mais fina para a mais grossa.

    AS DUAS ENTRADAS JA VEM NA ESCALA EXIBIDA — a mesma que `_escala_do_grafico`
    aplica —, e nao no unitario cru. Escalar aqui dentro seria a segunda
    aplicacao da escala, que e o defeito que `tests/test_escala_de_exibicao.py`
    existe para pegar.

    A REGRA, e nao a implementacao dela: para cada passo bonito que cabe na
    faixa, as marcas sao os MULTIPLOS dele entre o teto do minimo e o piso do
    maximo. Uma escada entra se tiver de DUAS a `MAXIMO_DE_MARCAS_POR_ESCADA`
    marcas, e a lista sai da mais fina para a mais grossa — porque quem escolhe e
    o navegador, e o que ele quer e a primeira que cabe na janela.

    A ESCADA SEM PASSO. Se NENHUMA entrar — faixa degenerada, um ponto so, ou
    faixa mais estreita que a menor marca —, sai UMA escada com UMA marca no
    valor arredondado do MEIO da faixa, e o campo `passo` dela e zero. Zero e o
    que diz "esta marca nao veio de uma regua"; um eixo sem marca nenhuma seria
    um eixo que nao diz em que unidade esta.

    O TEXTO SAI DE `formatar_centesimos`, A MESMA FUNCAO JA EXISTENTE, e a razao
    de ela servir e que a marca e INTEIRA em centesimos por construcao (multiplo
    de um passo inteiro). Nenhum segundo formatador nasce aqui — nem neste modulo
    nem, muito menos, no navegador.

    O PIXEL DE CADA MARCA E `float` DE UM INTEIRO, E ISTO NAO E UMA SEGUNDA
    FRONTEIRA DO `float` NO SENTIDO DO `_pixel`. Aquela converte uma FRACAO e por
    isso carrega erro medido; esta converte um inteiro, e inteiro ate dois
    elevado a 53 atravessa sem perder um bit. Quem prende essa distincao — em vez
    de so afirma-la — e `test_o_pixel_de_toda_marca_e_INTEIRO`.
    """
    escadas: list[dict] = []
    for passo in _passos_bonitos(maximo - minimo):
        # Teto do minimo e piso do maximo, em aritmetica de `Fraction`: nenhuma
        # marca cai fora da faixa por arredondamento.
        primeiro = -((-minimo) // passo)
        ultimo = maximo // passo
        quantidade = int(ultimo - primeiro) + 1
        if quantidade < 2 or quantidade > MAXIMO_DE_MARCAS_POR_ESCADA:
            continue
        escadas.append(
            {
                "passo": passo,
                "marcas": [
                    {
                        "pixel": float(multiplo * passo),
                        "texto": formatar_centesimos(multiplo * passo),
                    }
                    for multiplo in range(int(primeiro), int(ultimo) + 1)
                ],
            }
        )

    if not escadas:
        unica = round((minimo + maximo) / 2)
        escadas.append(
            {
                "passo": 0,
                "marcas": [
                    {"pixel": float(unica), "texto": formatar_centesimos(unica)}
                ],
            }
        )
    return escadas


def serie_para_o_grafico(
    chave_da_serie: str, observacoes: Sequence, agora: datetime
) -> dict:
    """UMA serie, no contrato de props do `01-UI-SPEC.md`. Sem nada de Adena.

    A PALAVRA `adena` NAO APARECE NESTE CORPO, e isso e o DASH-05 sendo
    estrutural em vez de uma intencao: a chave entra por parametro, o titulo sai
    de `ModeloDeMercado.nome_exibido_de`, a unidade e a escala saem de
    `formatador_do_unitario` (o unico ponto de decisao), e o formatador do numero
    tambem. Instanciar uma segunda serie e chamar esta funcao de novo.

    OS PONTOS SAO POR INSTANTE (CTX-1), E OS BALDES SAO A AGREGACAO DO ZOOM. As
    tres larguras vem juntas no payload porque o zoom acontece no navegador —
    filtrar e trocar de resolucao sem uma nova viagem ao servidor e o que o
    CONTEXT chamou de "o arquivo inteiro e carregado", e com 93 linhas hoje isso
    custa nada.

    O QUE NAO ESTA AQUI: a cor. Ela e do CHAMADOR — a instancia da Adena usa
    `--cor-ouro`, e a paleta e do tema e nao do componente. Um campo de cor neste
    dicionario seria a segunda paleta que o `dashboard.js` ja tem teste para nao
    ter.
    """
    pontos = pontos_por_instante(observacoes)
    formatador = formatador_do_unitario(chave_da_serie)

    def _texto(valor: Fraction | None, evidencia: Evidencia, do_menor: bool) -> str:
        if valor is not None:
            return formatador(valor)
        return (
            frase_de_piso_do_menor(evidencia)
            if do_menor
            else frase_de_piso_da_tipica(evidencia)
        )

    def _balde_exibido(pares) -> list[dict]:
        return [
            {
                "instante": inicio.isoformat(),
                "texto": formatador(valor),
                "pixel": _pixel(chave_da_serie, valor),
            }
            for inicio, valor in pares
        ]

    # A ancora sai do PRIMEIRO ponto, e nao de `agora`: o eixo pertence ao dado,
    # e nao ao instante em que alguem abriu a pagina. Com `agora` como ancora, a
    # mesma serie cairia em baldes diferentes a cada recarregamento.
    ancora = ancora_da_meia_noite(pontos[0].instante) if pontos else agora

    # A FAIXA DO EIXO SAI DOS PONTOS, E OS BALDES NAO ENTRAM NA CONTA. Todo balde
    # e uma MEDIANA de um subconjunto dos pontos, e por isso vive dentro da faixa
    # deles: incluir os baldes nao moveria o minimo nem o maximo, so o custo.
    #
    # A ESCALA E APLICADA AQUI E NAO DENTRO DE `_escadas_do_eixo`, e a
    # multiplicacao fica em `Fraction` ate a marca ser um inteiro. Passar por
    # `_pixel` primeiro levaria a faixa para `float` antes da conta da escada, e
    # ai a marca deixaria de ser exata — que e justamente o que autoriza a
    # conversao barata la dentro.
    escala = _escala_do_grafico(chave_da_serie)
    valores_na_escala = [
        valor * escala
        for ponto in pontos
        for valor in (ponto.menor, ponto.tipica)
        if valor is not None
    ]
    escadas = (
        _escadas_do_eixo(min(valores_na_escala), max(valores_na_escala))
        if valores_na_escala
        else []
    )

    return {
        "chave": chave_da_serie,
        "titulo": ModeloDeMercado.de_observacoes(observacoes).nome_exibido_de(
            chave_da_serie
        ),
        "unidade": (
            UNIDADE_EXIBIDA_DA_TAXA
            if _e_a_taxa(chave_da_serie)
            else UNIDADE_EXIBIDA_DO_UNITARIO
        ),
        "rotulo_principal": ROTULO_DO_MENOR,
        "rotulo_tipico": ROTULO_DA_TIPICA,
        "escadas_do_eixo": escadas,
        "pontos": [
            {
                "instante": ponto.instante.isoformat(),
                "menor_texto": _texto(ponto.menor, ponto.menor_evidencia, True),
                "tipica_texto": _texto(ponto.tipica, ponto.tipica_evidencia, False),
                "menor_pixel": _pixel(chave_da_serie, ponto.menor),
                "tipica_pixel": _pixel(chave_da_serie, ponto.tipica),
                "n": ponto.n,
            }
            for ponto in pontos
        ],
        "baldes": {
            nome: {
                "principal": _balde_exibido(
                    baldes(
                        [
                            (ponto.instante, ponto.menor)
                            for ponto in pontos
                            if ponto.menor is not None
                        ],
                        largura,
                        ancora,
                    )
                ),
                "tipica": _balde_exibido(
                    baldes(
                        [
                            (ponto.instante, ponto.tipica)
                            for ponto in pontos
                            if ponto.tipica is not None
                        ],
                        largura,
                        ancora,
                    )
                ),
            }
            for nome, largura in LARGURAS_DE_BALDE.items()
        },
    }


# ===========================================================================
# O PAYLOAD — A PRECEDENCIA FECHADA
# ===========================================================================


def _fonte(arquivo: Path, leitura: LeituraAoVivo | None = None) -> dict:
    """A procedencia do numero, que viaja no payload e nao no folclore."""
    return {
        "arquivo": str(arquivo),
        "cauda_incompleta": leitura.cauda_incompleta if leitura else False,
        "arquivo_ausente": leitura.arquivo_ausente if leitura else False,
        "linhas_completas": leitura.linhas_completas if leitura else 0,
        # Afirmado no payload porque e a promessa central do DASH-01, e o rodape
        # a exibe. Ha impressao digital e tripwire prendendo que ela e verdade.
        "somente_leitura": True,
    }


def _falha_fechada(estado: str, arquivo: Path, agora: datetime, avisos: list) -> dict:
    """Sem destaque, sem grafico, so a mensagem. NUNCA adivinhar coluna.

    Os dois primeiros estados da ordem sao os dois em que nao ha o que afirmar:
    o arquivo deixou de ser este arquivo, ou nao existe. Devolver um destaque
    "provisorio" aqui daria ao usuario um numero cuja procedencia o proprio
    programa acabou de recusar.
    """
    return {
        "estado": estado,
        "gerado_em": agora.isoformat(),
        "fonte": _fonte(arquivo),
        "avisos": avisos,
        "destaque": None,
        "series": [],
        # A CALCULADORA CAI JUNTO, e pela MESMA razao que o destaque e a serie:
        # quando o programa acabou de dizer que nao entende o arquivo, ele nao
        # pode oferecer um veredito sobre dinheiro tirado dele. A rota do NPC
        # ate existiria (o preco esta no `config.toml`, que continua legivel),
        # mas ela sozinha nao e comparacao nenhuma — e uma coluna solta com cara
        # de resposta.
        "calculadora": None,
    }


def _valor_em_reais(taxa: Fraction, cambio) -> str:
    """A taxa em R$ por 5 milhoes de adena, com a marca de informado por voce.

    A CONTA, ESCRITA POR EXTENSO, no molde de `formatar_taxa_derivada`:

        taxa = Fraction(11600, 10_000_000) centesimos de XM POR ADENA
          -> x 5.000.000 = 5.800 centesimos de XM por 5 milhoes
          -> x R$ 0,50 por XM = 2.900 CENTAVOS de R$ por 5 milhoes
          -> 2.900 centavos = R$ 29,00 por 5 milhoes

    ATE 2026-09-03 ESTA CONTA MULTIPLICAVA POR 1.000.000 e terminava em `R$ 5,80
    por milhao`. A escala de exibicao passou a cinco milhoes junto com a do
    texto em XM — as duas saem da MESMA `UNIDADE_DA_TAXA`, e essa e a razao de
    nenhuma linha de codigo desta funcao ter mudado na troca.

    A MULTIPLICACAO POR `UNIDADE_DA_TAXA` E POR `reais_por_xm` NA MESMA LINHA NAO
    E ECONOMIA DE CODIGO: centesimos-de-XM vezes reais-por-XM da centavos-de-R$
    diretamente, porque as duas escalas de centesimo se cancelam. Dividir por 100
    no meio e multiplicar por 100 no fim introduziria dois arredondamentos onde
    zero bastam.

    `Fraction(cambio.reais_por_xm)` E EXATO: `Fraction` aceita `Decimal` sem
    passar por `float`. Converter para `float` aqui reintroduziria erro
    exatamente onde o portao de duas camadas do `01-03` acabou de garantir um
    decimal simples — e sobre dinheiro real.

    O ARREDONDAMENTO ACONTECE SO NA ULTIMA LINHA, sobre a fracao exata.
    """
    centavos = round(taxa * UNIDADE_DA_TAXA * Fraction(cambio.reais_por_xm))
    return MOLDE_DO_VALOR_EM_REAIS.format(
        valor=formatar_centesimos(centavos),
        quando=cambio.informado_em.strftime("%d/%m %H:%M"),
    )


def _percentual_em_texto(fracao: Fraction) -> str:
    """Uma `Fraction` de um -> `12,3`. O arredondamento acontece SO aqui.

    A DIVISAO E INTEIRA E A VIRGULA E MONTADA A MAO, e nao `f"{float(x):.1f}"`,
    pelo mesmo motivo que `formatar_centesimos` usa `divmod`: converter para
    `float` no ultimo passo reintroduziria erro de representacao exatamente onde
    a fase inteira gastou `Fraction` para nao ter nenhum. `round` sobre a fracao
    exata e depois aritmetica de inteiro nao perde um bit.
    """
    decimos = round(fracao * 1000)
    inteiro, resto = divmod(decimos, 10)
    return f"{inteiro},{resto}"


def _lado_da_rota(custo, chave: str) -> dict:
    """Um lado da comparacao no payload, com o texto JA formatado.

    O FORMATADOR E `formatador_do_unitario(chave)` NOS DOIS LADOS, e isso e o
    ponto: as duas rotas terminam na MESMA unidade (centesimos de XM por
    unidade), entao elas TEM de sair do mesmo formatador. Escolher um formatador
    diferente por lado faria duas colunas em unidades diferentes ficarem lado a
    lado com a mesma cara — e `formatador_do_unitario` e justamente o UNICO ponto
    de decisao entre as duas irmas, criado para que quatro `if` espalhados nao
    divergissem.
    """
    return {"texto": formatador_do_unitario(chave)(custo.unitario)}


def _bloco_da_calculadora(
    itens: Sequence,
    modelo: ModeloDeMercado,
    menor_da_adena,
    agora: datetime,
    itens_lidos_em: datetime | None,
) -> dict:
    """A quarta regiao do payload: as duas rotas de cada item configurado.

    **A TAXA E O `unitario` DO MESMO `MenorPedidoVisivel` QUE O DESTAQUE EXIBE**,
    e nunca uma segunda chamada de `menor_pedido_visivel` sobre a serie da Adena.
    A razao nao e economia: duas leituras da mesma serie DENTRO DO MESMO PAYLOAD
    poderiam divergir no dia em que alguem mudasse uma delas, e a pagina passaria
    a mostrar dois valores para a mesma adena — um no destaque, outro dentro do
    veredito — sem que nada quebrasse em voz alta. Uma autoridade so sobre a
    taxa.

    **A PERGUNTA QUE O PLANO 02-01 DEIXOU ESCRITA AQUI FOI RESPONDIDA: SIM, O
    VEREDITO HERDA A EVIDENCIA DA TAXA.**
    ==========================================================================
    O criterio de "sem taxa" era `menor.unitario is None` — ou seja o piso do
    MENOR, que vale UM. Ele guardava so um dos dois lados da comparacao. Mas a
    rota do NPC e `preco_em_adena x taxa`, e a taxa sai de `menor_pedido_visivel`
    sobre a serie da Adena: **uma taxa apoiada numa unica oferta vira o veredito
    com a mesma facilidade com que um preco de item apoiado numa unica oferta
    vira**. Exigir cinco de um lado enquanto se aceita um do outro e uma regra
    que ninguem consegue justificar depois.

    O QUE SE DECIDIU: os dois lados da comparacao respondem ao MESMO piso,
    `dashboard_rotas.N_MINIMO_PARA_O_VEREDITO`. A `Evidencia` da taxa e
    construida aqui com esse piso, sobre o `n` que o `payload` ja tem em maos —
    e nao com uma segunda leitura da serie da Adena.

    A ALTERNATIVA RECUSADA, E POR QUE ELA ERA DEFENSAVEL: deixar a taxa no piso
    do menor tinha um argumento de pe — o menor da Adena e um FATO OBSERVADO
    sobre a serie mais densa do arquivo. **Medido em 2026-09-03: `adena#` tem
    n=50 contra n=8 do item mais visto.** O argumento e verdadeiro hoje e **nao
    e uma regra**: ele descreve o arquivo DESTA SEMANA, e nao o de uma maquina
    em que alguem abriu a aba da Adena uma vez.

    O QUE A DECISAO CUSTA HOJE: **nada**. Com n=50 contra um piso de 5, nenhum
    comportamento visivel muda nesta arvore. Ela existe para a maquina em que a
    aba da Adena foi aberta uma vez — que e precisamente a maquina em que
    ninguem estaria olhando para a tela desconfiando do numero.

    E E POR ISSO QUE ELA ESTA SENDO ESCRITA AGORA: com n=50 o assunto nunca mais
    seria revisitado, e a assimetria sobreviveria calada.

    A ORDEM DE PRECEDENCIA DO BLOCO E `ESTADOS_DA_CALCULADORA`: sem taxa vence
    sem itens, porque sem taxa nao ha conta possivel nem que houvesse cem itens —
    e mandar o usuario configurar itens nesse momento seria mandar ele fazer
    trabalho que nao vai produzir nada.

    **NADA DAQUI ENTRA NA LISTA `avisos` DO PAYLOAD.** A ordem daquela lista virou
    contrato no `01-07`: o `dashboard.js` acha tres frases por POSICAO, e quatro
    testes prendem isso sobre payloads reais. As frases desta fase viajam DENTRO
    deste bloco, cada uma no campo `aviso` do seu dono.
    """
    taxa = menor_da_adena.unitario

    # A EVIDENCIA DA TAXA, COM O PISO DO VEREDITO — ver a decisao na docstring.
    # O `n` vem do MESMO `MenorPedidoVisivel` que o destaque exibe; so o piso e
    # outro, e `piso` e um campo da `Evidencia` justamente para isto.
    evidencia_da_taxa = Evidencia(
        n=menor_da_adena.evidencia.n,
        piso=dashboard_rotas.N_MINIMO_PARA_O_VEREDITO,
    )

    if taxa is None or not evidencia_da_taxa.suficiente:
        return {
            "estado": CALCULADORA_SEM_TAXA,
            "aviso": FRASE_DE_SEM_TAXA_DA_ADENA.format(
                n=evidencia_da_taxa.n,
                piso=evidencia_da_taxa.piso,
                faltam=evidencia_da_taxa.faltam,
            ),
            "itens_lidos_em": None,
            "itens": [],
        }

    # O INSTANTE DA LEITURA E DE NIVEL DE BLOCO, e nao de linha. A configuracao
    # inteira foi lida UMA vez, no arranque; repeti-lo dentro de cada item
    # imprimiria a mesma frase N vezes e criaria a impressao falsa de que cada
    # item foi lido num instante proprio.
    #
    # Ele so aparece quando ha item configurado: sem item nenhum, "li o arquivo
    # ha 3 min" nao qualifica coisa nenhuma.
    lidos_em = (
        None
        if itens_lidos_em is None
        else MOLDE_DA_LEITURA_DA_CONFIGURACAO.format(
            recencia=_recencia_em_duas_formas(itens_lidos_em, agora)
        )
    )

    if not itens:
        return {
            "estado": CALCULADORA_SEM_ITENS,
            "aviso": FRASE_DE_SEM_ITENS_CONFIGURADOS,
            "itens_lidos_em": None,
            "itens": [],
        }

    vereditos = dashboard_rotas.vereditos_das_rotas(itens, modelo, taxa, agora)
    return {
        "estado": CALCULADORA_COM_ITENS,
        "aviso": None,
        "itens_lidos_em": lidos_em,
        "itens": [_linha_da_rota(veredito, agora) for veredito in vereditos],
    }


def _linha_da_rota(veredito, agora: datetime) -> dict:
    """UM item no payload. Todo texto ja formatado; o navegador so escreve.

    OS DOIS ESTADOS DE QUEBRA SAIEM COM `npc` E `mercado` NULOS E UM `aviso`
    PROPRIO. Um `null` mudo obrigaria quem desenha a adivinhar entre "nunca vi
    este item" e "o nome esta ambiguo", e as duas coisas se escrevem diferente na
    tela — a mesma objecao que faz `MargemDeCraft` carregar um `motivo`.
    """
    if veredito.estado == dashboard_rotas.ROTA_NOME_AMBIGUO:
        aviso = MOLDE_DE_NOME_AMBIGUO.format(
            item=veredito.item,
            quantas=len(veredito.candidatas),
            candidatas=", ".join(veredito.candidatas),
        )
    elif veredito.estado == dashboard_rotas.ROTA_NUNCA_VISTA:
        aviso = MOLDE_DE_ITEM_NUNCA_VISTO.format(item=veredito.item)
    else:
        aviso = None

    if veredito.npc is None or veredito.mercado is None:
        return {
            "estado": veredito.estado,
            "item": veredito.item,
            "nome_exibido": veredito.nome_exibido,
            "npc": None,
            "mercado": None,
            "vencedora": None,
            "diferenca": None,
            "n": None,
            "recencia": None,
            "velho": False,
            "aviso": aviso,
        }

    chave = veredito.chave
    npc = _lado_da_rota(veredito.npc, chave)
    # COMO O NPC REALMENTE VENDE, ao lado do unitario derivado. As duas metades
    # saem de `descrever_a_quantidade`, uma com a chave da Adena e outra com a
    # chave da serie do item — e por isso as palavras nunca discordam do que a
    # linha esta contando.
    npc["pacote_texto"] = MOLDE_DO_PACOTE_DO_NPC.format(
        preco=descrever_a_quantidade(
            CHAVE_DA_SERIE_DA_ADENA, veredito.npc.preco_em_adena
        ),
        quantidade=descrever_a_quantidade(chave, veredito.npc.quantidade),
    )

    # O DADO VELHO USA O MESMO `LIMIAR_DE_FRESCOR` DO DESTAQUE, e nao um limiar
    # proprio: dois limiares sobre a mesma pergunta divergiriam na primeira vez
    # que alguem mudasse um deles, e a tela mostraria o destaque frio ao lado do
    # veredito quente, sobre a MESMA leitura.
    velho = veredito.idade is not None and veredito.idade > LIMIAR_DE_FRESCOR

    diferenca = {
        "xm": formatador_do_unitario(chave)(veredito.diferenca_por_unidade),
        "percentual": (
            None
            if veredito.diferenca_percentual is None
            else MOLDE_DA_DIFERENCA_PERCENTUAL.format(
                valor=_percentual_em_texto(veredito.diferenca_percentual)
            )
        ),
    }

    return {
        "estado": veredito.estado,
        "item": veredito.item,
        "nome_exibido": veredito.nome_exibido,
        "npc": npc,
        "mercado": _lado_da_rota(veredito.mercado, chave),
        "vencedora": veredito.vencedora,
        "diferenca": diferenca,
        # TODO NUMERO VIAJA COM `n` E RECENCIA AO LADO — a mesma disciplina do
        # destaque, pela mesma razao: estatistica sem `n` e adivinhacao com cara
        # de numero.
        "n": veredito.evidencia.n,
        "recencia": (
            None
            if veredito.recencia is None
            else _recencia_em_duas_formas(veredito.recencia, agora)
        ),
        "velho": velho,
        "aviso": aviso,
    }


def payload(
    pasta_do_mercado: Path,
    agora: datetime,
    cambio=None,
    itens: Sequence = (),
    itens_lidos_em: datetime | None = None,
) -> dict:
    """O dicionario que vira o JSON de `GET /dados`, com a ordem FECHADA.

    A PRECEDENCIA E A DE `ESTADOS`, e o primeiro que casar manda. Varios podem
    ser verdade ao mesmo tempo — um arquivo de cabecalho trocado tambem nao tem
    serie da Adena — e ha teste de EMPATE prendendo qual dos dois vence.

    O `agora` ENTRA POR PARAMETRO, e nao sai de `datetime.now()` aqui: e o que
    torna a recencia afirmavel por teste sem congelar o relogio do processo. A
    casa ja faz isso em `mercado_console`, que recebe `agora` em toda funcao de
    desenho.

    `itens` E `itens_lidos_em` ENTRAM POR PARAMETRO COM DEFAULT, e a assinatura
    antiga continua valendo — exatamente como aconteceu quando o `cambio` entrou.
    Quem le o `config.toml` e o ARRANQUE do servidor, uma vez; este modulo
    continua sem tocar em TOML e sem saber o que e um `[[dashboard.item]]`: ele
    consome objetos com tres atributos, pelo mesmo contrato por FORMA com que
    consome o cambio.

    **`itens_lidos_em` E O INSTANTE DA LEITURA DO ARQUIVO, E NUNCA O INSTANTE EM
    QUE O USUARIO INFORMOU O PRECO.** As duas coisas tem nomes parecidos e sao
    fatos diferentes: o numero pode estar no `config.toml` ha meses e a leitura
    ser de dois minutos atras. Ver `MOLDE_DA_LEITURA_DA_CONFIGURACAO`.

    O `cambio` TAMBEM ENTRA POR PARAMETRO, e nao por import de `dashboard_cambio`.
    E o que mantem este modulo puro e testavel sem disco: a conta de R$ e uma
    multiplicacao, e nao precisa que um JSON exista para ser exercitada. O
    contrato e por FORMA — dois atributos, `reais_por_xm` e `informado_em` — e uma
    dependencia nos dois sentidos entre dado e persistencia seria um ciclo que
    nenhum dos dois lados pediu.

    O DESTAQUE E A CONTA DO CONSOLE, E O GRAFICO E A CONTA POR INSTANTE, E ISSO E
    DE PROPOSITO. O destaque chama `menor_pedido_visivel` sobre a serie INTEIRA,
    que e literalmente o que `_linha_do_menor` faz — e o DASH-03 exige que os dois
    numeros batam. O grafico agrupa por instante porque um ponto e um instante
    (CTX-1). Sao perguntas diferentes: "quanto vale agora" e "como isso variou".

    O TEXTO NUNCA E MONTADO AQUI. Ele sai de `formatador_do_unitario(chave)`, que
    e o UNICO ponto de decisao entre a taxa da Adena e o unitario comum. Um
    `f-string` local, ou um `round` a mao, imprimiria `0,00` para a Adena com toda
    a confianca do mundo — o modo de falha mais convincente que o
    `mercado_console` tem, e ele esta documentado la.

    `series` E SEMPRE UMA LISTA, MESMO COM UM ELEMENTO SO, e essa e a forma do
    DASH-05. Uma segunda serie e um ELEMENTO a mais — nao uma chave nova, nao um
    campo `adena`, nao um `if`. E ela traz TODAS as series que o arquivo conhece,
    e nao so a da Adena: quais delas a pagina instancia e decisao da pagina, e
    filtrar aqui seria justamente o `if` da Adena que o requisito recusa.
    """
    arquivo = pasta_do_mercado / mercado_registro.ARQUIVO_DE_OBSERVACOES

    # (1) ERRO DE CONTRATO — vence tudo. `observacoes_ao_vivo` continua
    #     desligando alto; quem decide o que MOSTRAR nessa hora e esta camada.
    try:
        leitura = observacoes_ao_vivo(arquivo)
    except mercado_registro.ContratoDoArquivoQuebrado as erro:
        # A mensagem da excecao viaja junto da frase curta: a curta diz o que
        # houve, e a longa e a que nomeia o arquivo REAL e diz como consertar.
        return _falha_fechada(
            ESTADO_ERRO_DE_CONTRATO,
            arquivo,
            agora,
            [FRASE_DE_CABECALHO_QUEBRADO, str(erro)],
        )

    # (2) ARQUIVO AUSENTE.
    if leitura.arquivo_ausente:
        return _falha_fechada(
            ESTADO_ARQUIVO_AUSENTE, arquivo, agora, [FRASE_DE_ARQUIVO_AUSENTE]
        )

    modelo = ModeloDeMercado.de_observacoes(leitura.observacoes)
    da_adena = modelo.observacoes_de(CHAVE_DA_SERIE_DA_ADENA)

    menor = menor_pedido_visivel(da_adena)
    tipica = mediana_dos_unitarios(da_adena)
    quando = recencia_do_preco(da_adena)

    # (3) SEM LEITURA DA ADENA / (4) ABAIXO DO PISO / (5) SERIE PRESENTE.
    if not menor.evidencia.suficiente:
        estado = ESTADO_SEM_LEITURA
    elif not tipica.evidencia.suficiente:
        estado = ESTADO_ABAIXO_DO_PISO
    else:
        estado = ESTADO_SERIE_PRESENTE

    # O DADO VELHO E ORTOGONAL: ele NAO toma a precedencia. O numero continua na
    # tela; o que sai e a afirmacao de "agora".
    velho = quando is not None and (agora - quando) > LIMIAR_DE_FRESCOR
    recencia = _recencia_em_duas_formas(quando, agora) if quando is not None else None

    avisos: list[str] = []
    if leitura.cauda_incompleta:
        avisos.append(NOTA_DE_LINHA_PARCIAL)
    if estado == ESTADO_SEM_LEITURA:
        avisos.append(TITULO_DO_ESTADO_VAZIO)
        avisos.append(CORPO_DO_ESTADO_VAZIO)
        avisos.append(
            MOLDE_DA_PROVA_DA_LEITURA.format(
                linhas=leitura.linhas_completas, da_serie=menor.evidencia.n
            )
        )
    if velho:
        avisos.append(MOLDE_DO_DADO_VELHO.format(recencia=recencia))
    if cambio is None:
        avisos.append(FRASE_DE_REAIS_INDISPONIVEL)
    else:
        avisos.append(AVISO_DO_CAMBIO_HISTORICO)

    # O SUB-OBJETO DE R$ SO EXISTE QUANDO HA CAMBIO INFORMADO. Ele nao fica
    # cinza, nao fica zerado, nao vem com um valor de exemplo: ele SOME, e a
    # frase de indisponivel toma o lugar dele nos avisos. Um cambio chutado vira
    # decisao de dinheiro real errada, e por isso a ausencia se escreve com
    # palavra e nunca com zero.
    reais = None
    if cambio is not None and menor.unitario is not None:
        reais = {
            "texto": _valor_em_reais(menor.unitario, cambio),
            "n": menor.evidencia.n,
            "recencia": recencia,
            "velho": velho,
            # DERIVADO, e dito no dado e no texto. Sem a marca, alguem copia a
            # linha para o WhatsApp e o numero derivado vira "o que o scanner
            # leu" — que e falso duas vezes: o scanner nao le R$, e nao leu este.
            "derivado": True,
            "informado_em": cambio.informado_em.isoformat(),
        }

    return {
        "estado": estado,
        "gerado_em": agora.isoformat(),
        "fonte": _fonte(arquivo, leitura),
        "avisos": avisos,
        "destaque": {
            "xm": {
                "texto": (
                    formatador_do_unitario(CHAVE_DA_SERIE_DA_ADENA)(menor.unitario)
                    if menor.unitario is not None
                    else frase_de_piso_do_menor(menor.evidencia)
                ),
                # TODO NUMERO VIAJA COM `n` E RECENCIA AO LADO. Estatistica sem
                # `n` e adivinhacao com cara de numero, e uma recencia que quem
                # desenha precisa pedir a parte e uma recencia que uma hora nao
                # vai ser exibida.
                "n": menor.evidencia.n,
                "recencia": recencia,
                "velho": velho,
                "derivado": True,
            },
            "reais": reais,
        },
        "series": [
            serie_para_o_grafico(chave, modelo.observacoes_de(chave), agora)
            for chave in modelo.series()
        ],
        # A QUARTA REGIAO. Ela e um BLOCO PROPRIO e nao mais uma entrada em
        # `avisos`: a ordem daquela lista virou contrato no `01-07`, com quatro
        # testes sobre payloads reais prendendo-a, e o `dashboard.js` acha tres
        # frases por POSICAO. Acrescentar la seria empurrar a linha de R$ para
        # fora do lugar em que o navegador a procura.
        "calculadora": _bloco_da_calculadora(
            itens, modelo, menor, agora, itens_lidos_em
        ),
    }


