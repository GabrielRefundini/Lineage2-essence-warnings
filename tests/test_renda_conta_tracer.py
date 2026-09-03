"""A FATIA FINA da Fase 2: de duas amostras a uma taxa por hora, num caminho so.

O QUE ESTE ARQUIVO PROVA
========================
Que as camadas da fase se encaixam **de producao**, e nao em teoria: duas
`LeituraDaRenda` montadas a mao atravessam as regras de par da Fase 1 (chamadas
pelo unico chamador de producao da arvore), viram um `PassoDaRenda` com o delta,
viram uma linha no CSV de `.renda/`, sao relidas pelo leitor tolerante, e saem
como uma `TaxaDaRenda` que se anuncia com `n`, com a janela farmada e com a
unidade dela escrita junto.

E prova o caso que da nome a fase pelo MESMO caminho: o par de campo do level up
— `nivel 66, exp 685_632` -> `nivel 67, exp 80_012` — sai com ganho de EXP
`394_380` decimos de milesimo, que sao os 39,438 pontos percentuais que o
usuario viu na tela. Nunca `-605_620`.

O QUE ELE **NAO** PROVA
=======================
Nada sobre pixel, OCR, calibracao, rede ou o jogo. Ele nao abre frame, nao chama
`ler_os_tres_campos` e nao toca o `calibration.json`. As amostras sao montadas a
mao com carimbos escolhidos, exatamente como `tests/test_renda_par.py:85-93` ja
faz — e e por isso que **uma noite inteira de farm cabe num teste de
milissegundos**.

Ele tambem nao prova a expansao: os casos do level up com o nivel recusado, o
salto do relogio dentro de uma sessao longa, a taxa da sessao inteira ao lado da
taxa da janela movel e a ponte de XP sao dos planos `02-02` e `02-04`. Esta e a
fatia, e ela e de producao.

ESTE ARQUIVO NAO PULA POR NADA
==============================
Um `skip` aqui e falha, e nao configuracao de maquina. Nao ha dependencia
externa, nao ha caminho de disco fora de `tmp_path`, e nao ha relogio: todo
carimbo entra por parametro.
"""

from __future__ import annotations

import csv

import pytest

from l2scanner.loot import apelido
from l2scanner.renda_conta import (
    DESCONTINUIDADE_DA_ANCORA,
    DESCONTINUIDADE_DA_LACUNA,
    DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS,
    GRANDEZA_DA_ADENA,
    GRANDEZA_DO_EXP,
    SEM_DESCONTINUIDADE,
    UNIDADE_DA_JANELA,
    passo_entre,
    taxa_por_hora,
)
from l2scanner.renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    CamposDaRenda,
    LeituraDaRenda,
    ValorDaAdena,
    ValorDaRenda,
)
from l2scanner.renda_registro import (
    COLUNAS,
    ContratoDaRendaQuebrado,
    RegistroDaRenda,
    amostras_ao_vivo,
)

# O fator de salto de exemplo, o mesmo literal que `tests/test_renda_par.py` usa
# e pela mesma razao: aqui ele e ARGUMENTO DE TESTE, e por isso pode ser um
# literal. No fonte ele nao existe — vem do `config.toml` do usuario.
FATOR = 10

# O limiar de lacuna de exemplo. Sessenta segundos a ~1 Hz sao sessenta amostras
# perdidas seguidas, que e cegueira e nao cadencia.
LIMIAR = 60.0

# Os dois pisos de exemplo, e eles sao os defaults da secao `[renda]`.
PISO_DE_AMOSTRAS = 8
PISO_DA_JANELA = 120.0

# Os pisos DESLIGADOS, para os testes que querem ver o numero sair de um par so.
# Eles existem porque a fatia prova o CAMINHO, e o piso e o assunto de outros
# dois testes deste mesmo arquivo — misturar as duas coisas faria um teste que
# nao diz o que quebrou quando quebra.
PISO_DE_AMOSTRAS_DESLIGADO = 1
PISO_DA_JANELA_DESLIGADO = 1.0


def leitura(*, nivel: int, exp: int, adena: int, carimbo: float) -> LeituraDaRenda:
    """Uma `LeituraDaRenda` montada a mao. Sem pixel, sem OCR, sem relogio."""
    return LeituraDaRenda(
        personagem="Faerlina", nivel=nivel, exp=exp, adena=adena, carimbo=carimbo
    )


def campos_lidos(amostra: LeituraDaRenda) -> CamposDaRenda:
    """Os tres campos como o leitor de producao os entrega, TODOS aceitos.

    As guardas sao as que a Fase 1 produz de verdade: `escalas` para o nivel e o
    EXP (duas escalas de OCR), `glifos` para a adena (que e lida por glifo e nao
    tem segunda escala). Elas nao sao decoracao — o LEIT-11 mediu que 3 das 4
    leituras erradas de nivel passaram POR CONCORDANCIA das duas escalas, e por
    isso a guarda vai gravada em coluna propria.
    """
    return CamposDaRenda(
        personagem=amostra.personagem,
        nivel=ValorDaRenda(
            campo=CAMPO_DO_NIVEL, valor=amostra.nivel, escalas=2, texto=str(amostra.nivel)
        ),
        exp=ValorDaRenda(
            campo=CAMPO_DO_EXP, valor=amostra.exp, escalas=1, texto=str(amostra.exp)
        ),
        adena=ValorDaAdena(
            campo=CAMPO_DA_ADENA, valor=amostra.adena, glifos=10, texto=str(amostra.adena)
        ),
    )


def passos_da_sequencia(amostras, *, limiar=LIMIAR):
    """A sequencia inteira virando passos, com a ancora na frente.

    E o laco que a Fase 3 vai rodar ao vivo, escrito uma vez: a primeira amostra
    nao tem anterior, logo e ANCORA e nao delta — e e por isso que o REG-02
    ("reiniciar nao inventa nem apaga renda") fecha na CONTA e nao no disco.
    """
    passos = []
    anterior = None
    for atual in amostras:
        passos.append(
            passo_entre(
                anterior,
                atual,
                fator_de_salto=FATOR,
                limiar_de_lacuna_em_segundos=limiar,
            )
        )
        anterior = atual
    return passos


def sequencia_regular(*, n: int, passo_em_segundos: float, comeco: float = 0.0):
    """`n` amostras ordinarias, cadencia fixa, EXP e adena subindo em passo fixo.

    O GANHO POR PASSO E CONSTANTE DE PROPOSITO: e o que faz a taxa da sequencia
    com buraco ser EXATAMENTE a mesma da sequencia sem buraco, em vez de
    aproximadamente a mesma. Um teste de taxa que precisasse de tolerancia
    deixaria de medir a exclusao da lacuna e passaria a medir a tolerancia.
    """
    return [
        leitura(
            nivel=67,
            exp=100_000 + indice * 1_000,
            adena=10_000_000 + indice * 5_000,
            carimbo=comeco + indice * passo_em_segundos,
        )
        for indice in range(n)
    ]


def linhas_de_dado(arquivo) -> list[list[str]]:
    """As linhas do CSV menos o cabecalho, lidas cruas."""
    with arquivo.open("r", encoding="utf-8", newline="") as fonte:
        return list(csv.reader(fonte, delimiter=";"))[1:]


# ---------------------------------------------------------------------------
# O PAR DE CAMPO DO LEVEL UP, e ele e REAL — `tests/test_renda_par.py:99-100`
# ---------------------------------------------------------------------------
#
#   2026-09-01 ~23h50   nivel 66, EXP 68,5632%, adena 10.673.628
#   2026-09-02 ~00h45   nivel 67, EXP  8,0012%, adena 13.160.684
#
# O CARIMBO NAO E O DE CAMPO, E ISSO ESTA DITO EM VOZ ALTA: as duas pontas foram
# lidas com ~55 minutos de diferenca, e com esse intervalo o passo seria
# `lacuna` e o ganho nao seria computado — que e o comportamento CERTO, e esta
# provado no teste da lacuna mais abaixo. O que este par prova sao os VALORES e
# o ganho que sai deles, entao o carimbo do `depois` fica dentro da cadencia.
LEVEL_UP_ANTES = leitura(nivel=66, exp=685_632, adena=10_673_628, carimbo=0.0)
LEVEL_UP_DEPOIS = leitura(nivel=67, exp=80_012, adena=13_160_684, carimbo=30.0)

# `(1_000_000 - 685_632) + 80_012`, em decimos de milesimo de ponto percentual.
GANHO_DO_LEVEL_UP = 394_380

# O que a subtracao ingenua `80_012 - 685_632` produziria. Ele existe como
# CONSTANTE porque um teste que so afirmasse "o ganho e 394_380" nao diria a
# quem o quebrasse o que ele acabou de reinventar.
GANHO_INGENUO_DO_LEVEL_UP = -605_620


class TestAFatiaDePontaAPontaComOParOrdinario:
    """O caso que roda um milhao de vezes: mesmo nivel, EXP e adena subindo.

    A fatia certa e a mais ORDINARIA de todas, e nao a mais interessante: e ela
    que acontece em 99,99% dos tiques, e um desenho que so funcionasse no level
    up seria um desenho que nao funciona.
    """

    def test_DUAS_AMOSTRAS_ATRAVESSAM_REGRAS_PASSO_DISCO_E_TAXA(self, tmp_path):
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)
        depois = leitura(nivel=67, exp=101_000, adena=10_005_000, carimbo=60.0)

        passos = passos_da_sequencia([antes, depois])
        passo = passos[-1]

        # (1) As regras de par foram chamadas, e o par e coerente.
        assert passo.recusas == (), (
            "um par ordinario — mesmo nivel, EXP e adena subindo — nao pode "
            f"produzir recusa nenhuma. `conferir_o_par` devolveu {passo.recusas}"
        )

        # (2) O passo tem o delta, e ele e positivo.
        assert passo.descontinuidade == SEM_DESCONTINUIDADE
        assert passo.intervalo_em_segundos == 60.0
        assert passo.ganho_de_exp_em_decimos == 1_000
        assert passo.ganho_de_adena == 5_000
        assert passo.gasto_de_adena == 0

        # (3) A amostra virou UMA linha no disco.
        registro = RegistroDaRenda(pasta=tmp_path, personagem=depois.personagem)
        assert registro.registrar(
            campos_lidos(depois),
            carimbo=depois.carimbo,
            descontinuidade=passo.descontinuidade,
        )
        assert len(linhas_de_dado(registro.arquivo)) == 1

        # (4) O leitor tolerante releu o que foi gravado.
        relido = amostras_ao_vivo(registro.arquivo)
        assert len(relido.amostras) == 1
        assert relido.cauda_incompleta is False
        assert relido.amostras[0].exp_decimos == 101_000
        assert relido.amostras[0].adena == 10_005_000

        # (5) E a taxa sai com `n` igual ao numero de PASSOS aceitos.
        taxa = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )
        aceitos = [p for p in passos if p.aceito]
        assert taxa.evidencia.n == len(aceitos) == 1
        assert taxa.por_hora == 60_000  # 1.000 decimos em 60 s = 60.000 por hora
        assert taxa.motivo_da_ausencia is None
        assert taxa.janela_farmada_em_segundos == 60.0

    def test_A_ADENA_QUE_CAI_E_GASTO_E_NAO_RENDA_NEGATIVA(self):
        """CTX-6: queda no contador e GASTO, fora da taxa de ganho."""
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)
        depois = leitura(nivel=67, exp=101_000, adena=9_800_000, carimbo=60.0)

        passo = passos_da_sequencia([antes, depois])[-1]

        assert passo.ganho_de_adena == 0
        assert passo.gasto_de_adena == 200_000
        assert passo.recusas == (), (
            "gastar 200 mil adena de um saldo de dez milhoes nao chega perto do "
            "fator de salto, e recusar aqui seria ruido sobre o evento mais "
            "normal do jogo depois de matar mob: comprar alguma coisa"
        )


class TestOParDeCampoDoLevelUpPelaFatiaInteira:
    """O criterio que da nome a fase, pelo MESMO caminho do par ordinario."""

    def test_O_GANHO_DO_LEVEL_UP_SAI_EM_394380_DECIMOS(self, tmp_path):
        passo = passos_da_sequencia([LEVEL_UP_ANTES, LEVEL_UP_DEPOIS])[-1]

        assert passo.ganho_de_exp_em_decimos == GANHO_DO_LEVEL_UP, (
            "o par de campo do level up tem de render "
            f"{GANHO_DO_LEVEL_UP} decimos de milesimo de ponto percentual, que "
            "sao os 39,438 PONTOS PERCENTUAIS que o usuario mediu na tela: "
            "`nivel 66, EXP 68,5632%` -> `nivel 67, EXP 8,0012%`, e "
            f"(100 - 68,5632) + 8,0012 = 39,438. Saiu "
            f"{passo.ganho_de_exp_em_decimos}"
        )

        # As duas pontas atravessam o disco pelo mesmo caminho.
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        for amostra in (LEVEL_UP_ANTES, LEVEL_UP_DEPOIS):
            assert registro.registrar(
                campos_lidos(amostra),
                carimbo=amostra.carimbo,
                descontinuidade=SEM_DESCONTINUIDADE,
            )
        relido = amostras_ao_vivo(registro.arquivo)
        assert [a.nivel for a in relido.amostras] == [66, 67]
        assert [a.exp_decimos for a in relido.amostras] == [685_632, 80_012]

    def test_CONTROLE_O_GANHO_NAO_E_NEGATIVO_NEM_ZERO(self):
        """Sem ele, uma implementacao que devolvesse ZERO passaria no teste de cima.

        A subtracao ingenua `80_012 - 685_632` da `-605_620`, e um numero desses
        gravado vira "a pior hora da noite" no registro de quem acabou de subir
        de nivel. Um `max(0, ...)` em cima dele daria zero — que nao e negativo,
        e continua sendo errado.
        """
        passo = passos_da_sequencia([LEVEL_UP_ANTES, LEVEL_UP_DEPOIS])[-1]

        assert passo.ganho_de_exp_em_decimos != GANHO_INGENUO_DO_LEVEL_UP, (
            "o ganho saiu como a SUBTRACAO INGENUA das duas leituras. Subir de "
            "nivel zera o EXP: a conta e (um nivel inteiro - o EXP de antes) + "
            "o EXP de agora"
        )
        assert passo.ganho_de_exp_em_decimos > 0, (
            "subir de nivel e o melhor que acontece numa farmada, e ele nao "
            "pode entrar na conta como ganho zero nem como prejuizo"
        )
        assert passo.recusas == (), (
            "as tres regras de par se calam neste par de proposito: "
            "`o_exp_andou_para_tras` se abstem quando o nivel mudou, "
            "`o_nivel_andou_para_tras` so olha para baixo, e a adena cresceu "
            "bem abaixo do fator"
        )


class TestAAncoraEOSaltoDoRelogio:
    """Os dois estados em que o passo existe e o delta nao."""

    def test_UMA_AMOSTRA_SEM_ANTERIOR_E_ANCORA_E_NAO_TEM_DELTA(self):
        sozinha = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)

        passo = passo_entre(
            None,
            sozinha,
            fator_de_salto=FATOR,
            limiar_de_lacuna_em_segundos=LIMIAR,
        )

        assert passo.descontinuidade == DESCONTINUIDADE_DA_ANCORA
        assert passo.intervalo_em_segundos is None
        assert passo.ganho_de_exp_em_decimos is None
        assert passo.ganho_de_adena is None
        assert passo.aceito is False

    def test_CONTROLE_UM_PAR_NORMAL_TRAZ_A_DESCONTINUIDADE_VAZIA(self):
        """Sem ele, uma implementacao que marcasse TUDO como ancora passaria."""
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)
        depois = leitura(nivel=67, exp=101_000, adena=10_005_000, carimbo=30.0)

        passo = passos_da_sequencia([antes, depois])[-1]

        assert passo.descontinuidade == SEM_DESCONTINUIDADE
        assert passo.aceito is True

    def test_O_CARIMBO_QUE_ANDA_PARA_TRAS_E_DESCONTINUIDADE_NOMEADA(self):
        """CTX-10: o PC e dual boot e o Windows volta ~3h adiantado do Linux."""
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=1_000.0)
        depois = leitura(nivel=67, exp=101_000, adena=10_005_000, carimbo=970.0)

        passo = passos_da_sequencia([antes, depois])[-1]

        assert passo.descontinuidade == DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS
        assert passo.aceito is False

    def test_CONTROLE_O_INTERVALO_NEGATIVO_NAO_FOI_ABSORVIDO(self):
        """O sinal e o DADO, e um `abs()` ou um `max(0, ...)` o apagariam.

        Duas afirmacoes, e as duas sao necessarias: o intervalo guardado
        continua NEGATIVO (nada o absorveu), e o passo nao entra no denominador
        da taxa. Sem a segunda, um intervalo negativo somado a janela farmada a
        ENCOLHERIA, e a taxa por hora sairia inflada exatamente quando o relogio
        pulou.
        """
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=1_000.0)
        depois = leitura(nivel=67, exp=101_000, adena=10_005_000, carimbo=970.0)

        passos = passos_da_sequencia([antes, depois])

        assert passos[-1].intervalo_em_segundos == -30.0, (
            "o intervalo tem de sair NEGATIVO e ficar negativo: `abs()` e "
            "`max(0, delta)` fazem o mesmo estrago com nomes diferentes"
        )

        taxa = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )
        assert taxa.evidencia.n == 0
        assert taxa.janela_farmada_em_segundos == 0.0
        assert taxa.por_hora is None


class TestAIdaEVoltaPeloDisco:
    """O arquivo em `.renda/`, sempre em `tmp_path` e nunca na pasta real."""

    def test_O_PERSONAGEM_DA_COLUNA_E_O_MESMO_DO_NOME_DO_ARQUIVO(self, tmp_path):
        """A coluna e o DADO; o nome do arquivo e o ROTEAMENTO. E eles concordam."""
        amostra = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)

        registro = RegistroDaRenda(pasta=tmp_path, personagem=amostra.personagem)
        registro.registrar(
            campos_lidos(amostra),
            carimbo=amostra.carimbo,
            descontinuidade=SEM_DESCONTINUIDADE,
        )

        relido = amostras_ao_vivo(registro.arquivo)

        assert registro.arquivo.name == "faerlina.csv"
        assert registro.arquivo.stem == apelido(relido.amostras[0].personagem)

    def test_UM_NOME_HOSTIL_NAO_ESCAPA_DA_PASTA(self, tmp_path):
        """T-02-02: o nome vem do titulo da janela do jogo e vira caminho.

        `apelido()` reduz por lista de PERMISSAO (`a-z0-9`), e nao por lista de
        proibicao — nao ha caractere de travessia que sobreviva a isso.
        """
        hostil = "../../Windows/System32"

        registro = RegistroDaRenda(pasta=tmp_path, personagem=hostil)

        assert registro.arquivo.parent == tmp_path
        assert ".." not in registro.arquivo.name

    def test_DUAS_AMOSTRAS_IDENTICAS_DEIXAM_DUAS_LINHAS(self, tmp_path):
        """O portao comportamental da C-3: a dedup do mercado NAO atravessou.

        `mercado_registro.chave_da_observacao` exclui o carimbo de proposito,
        para o arquivo do mercado nao crescer uma linha por segundo sobre o
        mesmo anuncio. Aqui uma linha por tique E O PRODUTO — ela e o
        denominador da taxa —, e a ~1 Hz a maioria das amostras tem os tres
        campos identicos a anterior, porque a adena so muda quando cai loot.
        Uma dedup copiada por engano faria uma linha so, e a taxa da noite
        sairia calculada sobre um punhado de sobreviventes.
        """
        primeira = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)
        segunda = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=30.0)

        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        for amostra in (primeira, segunda):
            registro.registrar(
                campos_lidos(amostra),
                carimbo=amostra.carimbo,
                descontinuidade=SEM_DESCONTINUIDADE,
            )

        linhas = linhas_de_dado(registro.arquivo)
        assert len(linhas) == 2, (
            "duas amostras com `nivel`, `exp` e `adena` IDENTICOS e carimbos "
            "diferentes sao DUAS medicoes e tem de virar DUAS linhas. Uma linha "
            "so quer dizer que a dedup do mercado foi copiada, e ela apagaria a "
            f"maioria das amostras de uma noite de farm. Achei {len(linhas)}"
        )
        assert len({tuple(linha) for linha in linhas}) == 2

    def test_O_CABECALHO_E_AS_TREZE_COLUNAS(self, tmp_path):
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        with registro.arquivo.open("r", encoding="utf-8", newline="") as fonte:
            cabecalho = next(csv.reader(fonte, delimiter=";"))
        assert tuple(cabecalho) == COLUNAS
        assert len(COLUNAS) == 13


class TestOLeitorTolerante:
    """O corte de cauda, e o portao que continua existindo depois dele."""

    def test_UMA_CAUDA_PARCIAL_NAO_LEVANTA_E_E_SINALIZADA(self, tmp_path):
        amostra = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)
        registro = RegistroDaRenda(pasta=tmp_path, personagem="Faerlina")
        registro.registrar(
            campos_lidos(amostra),
            carimbo=amostra.carimbo,
            descontinuidade=SEM_DESCONTINUIDADE,
        )

        # Meia linha, como uma escrita interrompida deixaria.
        with registro.arquivo.open("a", encoding="utf-8", newline="") as destino:
            destino.write("2026-09-02T00:00:30;Faerlina;67;2;;101")

        relido = amostras_ao_vivo(registro.arquivo)

        assert len(relido.amostras) == 1
        assert relido.linhas_completas == 1
        assert relido.cauda_incompleta is True

    def test_CONTROLE_UM_ARQUIVO_SEM_NENHUMA_QUEBRA_DE_LINHA_LEVANTA(
        self, tmp_path
    ):
        """Sem uma unica linha completa nao ha nem cabecalho: nao e este arquivo.

        A DIVERGENCIA COM O `dashboard_dados` E DELIBERADA e esta escrita no
        fonte: la quem le e um painel de so-leitura, que tem de degradar para
        nao ficar mudo; aqui o mesmo arquivo e do ESCRITOR, e apendar num
        arquivo cujo estado o programa nao consegue afirmar produziria a linha
        parseavel e ERRADA que a fase existe para nao ter.
        """
        alvo = tmp_path / "faerlina.csv"
        alvo.write_text("lixo sem quebra de linha nenhuma", encoding="utf-8")

        with pytest.raises(ContratoDaRendaQuebrado):
            amostras_ao_vivo(alvo)

    def test_UM_ARQUIVO_AUSENTE_DEVOLVE_VAZIO_SEM_LEVANTAR(self, tmp_path):
        relido = amostras_ao_vivo(tmp_path / "nunca-existiu.csv")
        assert relido.arquivo_ausente is True
        assert relido.amostras == ()


class TestATaxaComLacunaESemLacuna:
    """CTX-2: o tempo cego SAI do denominador, e e contado a parte."""

    def test_UM_BURACO_DE_VINTE_MINUTOS_NAO_MUDA_A_TAXA_POR_HORA(self):
        """A afirmacao mais forte deste arquivo, e ela e de IGUALDADE EXATA.

        Vinte e uma amostras a cada 30 s cobrem dez minutos. A mesma sequencia
        com as onze ultimas deslocadas em vinte minutos tem o MESMO ganho por
        segundo farmado — e por isso a taxa por hora e identica, e nao parecida.
        Se o tempo cego entrasse no denominador, a segunda sairia cerca de tres
        vezes menor, e o usuario leria isso como "o farm piorou".
        """
        sem_buraco = sequencia_regular(n=21, passo_em_segundos=30.0)

        com_buraco = list(sem_buraco[:10])
        for amostra in sem_buraco[10:]:
            com_buraco.append(
                leitura(
                    nivel=amostra.nivel,
                    exp=amostra.exp,
                    adena=amostra.adena,
                    carimbo=amostra.carimbo + 1_200.0,
                )
            )

        taxa_limpa = taxa_por_hora(
            passos_da_sequencia(sem_buraco),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )
        passos_furados = passos_da_sequencia(com_buraco)
        taxa_furada = taxa_por_hora(
            passos_furados,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa_limpa.por_hora == taxa_furada.por_hora, (
            "o tempo cego entrou no denominador: a taxa com buraco saiu "
            f"{taxa_furada.por_hora} contra {taxa_limpa.por_hora} sem buraco. O "
            "denominador e a soma dos intervalos entre amostras consecutivas "
            "ACEITAS, e nao o relogio de parede (CTX-2)"
        )
        assert taxa_limpa.lacunas_excluidas == 0
        assert taxa_furada.lacunas_excluidas == 1
        assert taxa_furada.segundos_em_lacuna == 1_230.0
        assert taxa_furada.evidencia.n == 19
        assert taxa_furada.janela_farmada_em_segundos == 570.0
        assert (
            sum(
                1
                for p in passos_furados
                if p.descontinuidade == DESCONTINUIDADE_DA_LACUNA
            )
            == 1
        )

    def test_A_ADENA_ATRAVESSA_A_MESMA_CONTA(self):
        """A taxa nao e do EXP: ela e de uma GRANDEZA que chega por parametro."""
        taxa = taxa_por_hora(
            passos_da_sequencia(sequencia_regular(n=21, passo_em_segundos=30.0)),
            grandeza=GRANDEZA_DA_ADENA,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )
        # 20 passos x 5.000 adena em 600 s = 100.000 adena em 10 min = 600.000/h
        assert taxa.por_hora == 600_000


class TestOsDoisPisos:
    """Abaixo de qualquer um dos dois, a resposta e o MOTIVO e nunca um numero."""

    def test_QUARENTA_SEGUNDOS_DE_SESSAO_NAO_VIRAM_TAXA_HORARIA(self):
        curta = sequencia_regular(n=41, passo_em_segundos=1.0)

        taxa = taxa_por_hora(
            passos_da_sequencia(curta),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.por_hora is None, (
            "quarenta segundos de sessao nao sao uma taxa por hora, e o "
            "criterio 1 do roadmap manda anuncia-los como ruido"
        )
        assert taxa.motivo_da_ausencia
        assert "janela_minima_para_taxa_segundos" in taxa.motivo_da_ausencia, (
            "o motivo tem de nomear QUAL dos dois pisos faltou. Aqui faltou o de "
            "TEMPO: sao 40 passos aceitos, bem acima do piso de amostras, e 40 "
            f"segundos de janela farmada. Saiu: {taxa.motivo_da_ausencia!r}"
        )
        assert taxa.evidencia.n == 40
        assert taxa.evidencia.suficiente is True

    def test_CONTROLE_A_MESMA_SEQUENCIA_ESTENDIDA_ACIMA_DO_PISO_DA_NUMERO(self):
        """Sem ele, um `taxa_por_hora` que devolvesse sempre `None` passaria."""
        longa = sequencia_regular(n=121, passo_em_segundos=1.0)

        taxa = taxa_por_hora(
            passos_da_sequencia(longa),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.motivo_da_ausencia is None
        assert taxa.por_hora == 3_600_000  # 1.000 decimos por segundo
        assert taxa.janela_farmada_em_segundos == 120.0

    def test_POUCAS_AMOSTRAS_NOMEIAM_O_OUTRO_PISO(self):
        """Os dois pisos sao DOIS porque sao dois fatos, e cada um se nomeia.

        Tres passos de sessenta segundos dao 180 s de janela — acima do piso de
        TEMPO — e so tres amostras. Um motivo generico deixaria o usuario sem
        saber se ele precisa esperar mais tempo ou capturar mais rapido.
        """
        rala = sequencia_regular(n=4, passo_em_segundos=60.0)

        taxa = taxa_por_hora(
            passos_da_sequencia(rala),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.por_hora is None
        assert "amostras_minimas_para_taxa" in taxa.motivo_da_ausencia
        assert taxa.evidencia.n == 3
        assert taxa.evidencia.faltam == 5
        assert taxa.janela_farmada_em_segundos == 180.0


class TestATaxaNuncaEUmNumeroNu:
    """REND-06: `n`, janela, unidade, lacunas e recencia viajam com o valor."""

    def test_A_UNIDADE_DA_JANELA_VIAJA_ESCRITA_E_E_MINUTOS_FARMADOS(self):
        taxa = taxa_por_hora(
            passos_da_sequencia(sequencia_regular(n=21, passo_em_segundos=30.0)),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.unidade_da_janela == UNIDADE_DA_JANELA == "minutos farmados"
        assert taxa.janela_farmada_em_segundos == 600.0, (
            "`minutos farmados` e `minutos de relogio` sao numeros DIFERENTES, e "
            "a diferenca entre os dois e a medicao inteira da CTX-2: medido em "
            "campo, a media de 8h45 deu 226 mil adena/h e a janela curta deu "
            "466 mil/h, e a diferenca inteira e tempo parado. Sem a unidade "
            "escrita ao lado do numero, quem le supoe o relogio de parede"
        )

    def test_A_RECENCIA_VIAJA_SEPARADA_DO_VALOR(self):
        amostras = sequencia_regular(n=21, passo_em_segundos=30.0)

        taxa = taxa_por_hora(
            passos_da_sequencia(amostras),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.ate == amostras[-1].carimbo
        assert taxa.evidencia.piso == PISO_DE_AMOSTRAS
        assert taxa.evidencia.n == 20


class TestNenhumLimiarTemValorDeFabrica:
    """Um limiar por omissao e a definicao de constante magica.

    O molde e `test_O_FATOR_NAO_TEM_VALOR_DE_FABRICA`
    (`tests/test_renda_par.py:337-343`), e a razao e a mesma: os cinco numeros
    moram no `config.toml` do usuario e os defaults deles moram na CASCA. Um
    default aqui dentro seria um numero escolhido por este fonte fingindo ter
    sido escolhido pelo usuario.
    """

    def test_passo_entre_EXIGE_OS_DOIS_LIMIARES(self):
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)
        depois = leitura(nivel=67, exp=101_000, adena=10_005_000, carimbo=30.0)

        with pytest.raises(TypeError):
            passo_entre(antes, depois)

        with pytest.raises(TypeError):
            passo_entre(antes, depois, fator_de_salto=FATOR)

        with pytest.raises(TypeError):
            passo_entre(antes, depois, limiar_de_lacuna_em_segundos=LIMIAR)

    def test_taxa_por_hora_EXIGE_OS_DOIS_PISOS(self):
        passos = passos_da_sequencia(
            sequencia_regular(n=21, passo_em_segundos=30.0)
        )

        with pytest.raises(TypeError):
            taxa_por_hora(passos, grandeza=GRANDEZA_DO_EXP)

        with pytest.raises(TypeError):
            taxa_por_hora(
                passos,
                grandeza=GRANDEZA_DO_EXP,
                piso_de_amostras=PISO_DE_AMOSTRAS,
            )

        with pytest.raises(TypeError):
            taxa_por_hora(
                passos,
                grandeza=GRANDEZA_DO_EXP,
                piso_da_janela_em_segundos=PISO_DA_JANELA,
            )
