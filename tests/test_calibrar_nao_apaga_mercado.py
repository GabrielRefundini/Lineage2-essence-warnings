"""A calibracao de PARTY nao pode apagar a calibracao de MERCADO.

O INCIDENTE QUE ESTE ARQUIVO EXISTE PARA IMPEDIR, medido em campo em
2026-08-30: uma rodada de `calibrar.bat` (`python -m l2scanner.calibrar --auto`)
apagou do `calibration.json` os 13 moldes de glifo, as 3 ancoras do painel, a
grade de negociacao e o `mercado_limiar_de_glifo`. Cada molde de glifo e um
arrasto de mouse mais um rotulo digitado pela mao do usuario; o arquivo e
gitignored, entao nao ha `git checkout` que os traga de volta. O resgate foi
manual (`calibration.RESGATE-13-glifos.json`).

O MECANISMO: `calibrar_automatico` monta uma `Calibracao` DO ZERO, e o
`cal.salvar` final de `main()` grava esse objeto por cima do arquivo inteiro.
Todo campo que a party nao possui vira `null`. O mesmo defeito ja tinha sido
consertado do lado do mercado, como CR-04 (`calibrar_mercado` carrega o arquivo,
muta so o que e seu, e grava). Ficou aberto do lado da party exatamente porque
nao havia teste afirmando a invariante — que e o buraco que este arquivo fecha.

O QUE ESTE ARQUIVO NAO ALCANCA, E PELO MOTIVO VERDADEIRO: o caminho `--tiat`
(`calibrar_tiat`) nao tem caso aqui. Nao e impossibilidade: ele e alcancavel
pelo MESMO idioma do caso 6 (um `JanelaSource` falso) mais dois seams
interativos (`_selecionar_regiao`, chamada duas vezes) e o `_gravar_conferencia`
— tres monkeypatches a mais, e nada alem disso. O que dispensa o caso e outra
coisa: `calibrar_tiat` ja e load-mutate-save comprovado por LEITURA, chamando
`Calibracao.carregar(ARQUIVO_CALIBRACAO)` na primeira linha util da funcao.
O caso seria guarda de regressao, e nao prova de conserto. Quem quiser
acrescentar o caso 7 agora sabe o preco exato.

DISCIPLINA INEGOCIAVEL DESTE ARQUIVO: todo caso monkeypatcha
`l2scanner.calibrar.ARQUIVO_CALIBRACAO` para dentro de `tmp_path`. E a unica
coisa que mantem o `calibration.json` da maquina do usuario fora do alcance
desta suite. Quem remover a linha achando que e ruido reproduz o incidente
dentro do CI, e desta vez sem resgate.
"""

from __future__ import annotations

import json
import sys
from dataclasses import fields

import numpy as np
import pytest

import l2scanner.calibrar
from l2scanner.calibracao import (
    LIMIARES_HP_PADRAO,
    LIMIARES_MP_PADRAO,
    Calibracao,
    LayoutDaParty,
    descrever_geometria_da_tela,
)
from l2scanner.frames import Regiao
from l2scanner.identidade import criar_assinatura

# Os treze nomes que a calibracao de party POSSUI, escritos LITERALMENTE aqui de
# proposito: a afirmacao do teste tem de ser independente da constante do codigo
# de producao. Se as duas listas divergirem, quem denuncia e o caso 4.
NOMES_DA_PARTY = frozenset(
    {
        "party_window",
        "ancora",
        "layout",
        "limiares_hp",
        "limiares_mp",
        "geometria_da_tela",
        "hp_proprio",
        "nome_proprio",
        "nomes",
        "assinaturas",
        "janela",
        "party_window_na_janela",
        "versao",
    }
)

NAO_SAO_DA_PARTY = frozenset(f.name for f in fields(Calibracao)) - NOMES_DA_PARTY


@pytest.fixture(scope="module")
def geo() -> str:
    """A geometria da tela, lida UMA vez.

    O mesmo valor vai para o arquivo semeado e para a calibracao nova: o
    `carregar` nao confere geometria, mas assim o teste nao depende da tela de
    quem o roda.
    """
    return descrever_geometria_da_tela()


def _nova_party(geo: str) -> Calibracao:
    """A calibracao que a rodada VAI produzir — so campos de party."""
    return Calibracao(
        party_window=Regiao(esquerda=100, topo=200, largura=300, altura=400),
        ancora=Regiao(esquerda=0, topo=0, largura=40, altura=28),
        layout=LayoutDaParty(
            icone_x=4,
            icone_y=6,
            icone_tamanho=22,
            barra_x=30,
            barra_largura=120,
            barra_altura=8,
            hp_y=10,
            mp_y=20,
            passo=44,
            max_linhas=8,
        ),
        limiares_hp=LIMIARES_HP_PADRAO,
        limiares_mp=LIMIARES_MP_PADRAO,
        geometria_da_tela=geo,
    )


def _semear(alvo, geo: str) -> dict:
    """Grava a calibracao de PARTIDA em `alvo` e devolve o dict cru gravado.

    Os 27 campos que a party nao possui vao preenchidos com valores
    distinguiveis; os campos de party vao com coordenadas DIFERENTES das que a
    rodada vai gravar, para o caso 3 conseguir ver a diferenca.

    O ARQUIVO SEMEADO TEM DE PASSAR PELO `Calibracao.carregar`, e nao so parecer
    plausivel: um arquivo que o `carregar` recusa faria a fusao cair no ramo de
    erro DEPOIS do conserto, e os casos 1 e 2 continuariam vermelhos com sintoma
    indistinguivel do defeito original. Por isso:
      - moldes/ancoras tem `bytes` em hex de comprimento == altura * largura;
      - a GRADE e semeada primeiro e as quatro colunas sao derivadas DE DENTRO
        dela (`_conferir_uma_coluna` exige dx >= grade.dx e
        dx + largura <= grade.dx + grade.largura);
      - todo `mercado_limiar_*` vive em (0, 1].
    """
    grade = {
        "layout": "negociacao",
        "dx": 10,
        "dy": 60,
        "largura": 800,
        "altura_de_linha": 30,
        "linhas_por_pagina": 12,
    }
    # As quatro colunas, derivadas de DENTRO da grade: [10, 810].
    coluna_do_nome = {"dx": grade["dx"], "largura": 200}
    coluna_da_quantidade = {"dx": grade["dx"] + 210, "largura": 100}
    coluna_do_total = {"dx": grade["dx"] + 330, "largura": 150}
    coluna_do_unitario = {"dx": grade["dx"] + 500, "largura": 120}

    recorte = np.random.RandomState(20260830).randint(
        0, 256, size=(20, 100, 3), dtype=np.uint8
    )
    assinatura_antiga = criar_assinatura("Antigo", recorte)

    velha = Calibracao(
        # --- campos de PARTY, propositalmente diferentes dos novos (caso 3) ---
        party_window=Regiao(esquerda=999, topo=888, largura=77, altura=66),
        ancora=Regiao(esquerda=1, topo=2, largura=3, altura=4),
        layout=LayoutDaParty(
            icone_x=1,
            icone_y=1,
            icone_tamanho=1,
            barra_x=1,
            barra_largura=1,
            barra_altura=1,
            hp_y=1,
            mp_y=2,
            passo=9,
            max_linhas=8,
        ),
        limiares_hp=LIMIARES_HP_PADRAO,
        limiares_mp=LIMIARES_MP_PADRAO,
        geometria_da_tela=geo,
        hp_proprio=Regiao(esquerda=5, topo=6, largura=7, altura=8),
        nome_proprio="Yazalaque",
        nomes=["Antigo"],
        assinaturas=[assinatura_antiga],
        janela="Antigo - XM Essence",
        party_window_na_janela=Regiao(esquerda=11, topo=12, largura=13, altura=14),
        # --- os 27 que a party NAO possui ---
        banner_manutencao=Regiao(esquerda=20, topo=21, largura=22, altura=23),
        tiat_chat=Regiao(esquerda=30, topo=31, largura=32, altura=33),
        tiat_alvo=Regiao(esquerda=40, topo=41, largura=42, altura=43),
        mercado_ancora=Regiao(esquerda=50, topo=51, largura=52, altura=53),
        mercado_molde_da_ancora={
            "altura": 2,
            "largura": 3,
            "bytes": bytes(range(6)).hex(),
        },
        mercado_limiar_da_ancora=0.73,
        mercado_geometria_da_captura={"largura": 1720, "altura": 1392},
        mercado_ancoras=[
            {
                "nome": f"ancora-{i}",
                "dx": 10 * i,
                "dy": 5 * i,
                "altura": 2,
                "largura": 3,
                "bytes": bytes(range(6)).hex(),
            }
            for i in range(3)
        ],
        mercado_grade=grade,
        mercado_templates_de_nome=[
            {
                "nome": "+3 Bota X",
                "altura": 2,
                "largura": 4,
                "bytes": bytes(range(8)).hex(),
            }
        ],
        mercado_templates_de_digito=[
            {
                "glifo": glifo,
                "altura": 3,
                "largura": 4,
                "bytes": bytes(range(12)).hex(),
            }
            for glifo in "0123456789,"
        ]
        + [
            {
                "glifo": palavra,
                "altura": 3,
                "largura": 4,
                "bytes": bytes(range(12)).hex(),
            }
            for palavra in ("XM Coin", "Adena")
        ],
        mercado_limiar_de_template=0.8100,
        mercado_limiar_de_glifo=0.8555,
        mercado_coluna_do_nome=coluna_do_nome,
        mercado_coluna_da_quantidade=coluna_da_quantidade,
        mercado_coluna_do_total=coluna_do_total,
        mercado_coluna_do_unitario=coluna_do_unitario,
        mercado_cabecalho_de_coluna={
            "layout": "negociacao",
            "dy": 40,
            "altura": 4,
            "largura": 6,
            "bytes": bytes(range(24)).hex(),
            "corte_de_brilho": 200,
        },
        mercado_limiar_do_cabecalho=0.9000,
        mercado_sonda_do_fundo={"dx0": 600, "dx1": 700, "folga": 3},
        mercado_limiar_de_dispersao_do_fundo=0.1200,
        mercado_limiar_de_leitura_de_glifo=0.6000,
        mercado_margem_de_leitura_de_glifo=0.0500,
        mercado_corte_de_similaridade=0.9000,
        mercado_piso_de_similaridade=0.7000,
        mercado_tolerancia_do_cruzamento=2.0,
        mercado_minimo_de_linhas_comparadas=3,
    )
    velha.salvar(alvo)

    # O SEMEADOR SE PROVA ANTES DE O TESTE ACUSAR O CODIGO SOB TESTE.
    # Se `carregar` levantar aqui, o problema esta nesta funcao — e nao no
    # `calibrar.py`. Sem esta linha, um semeador invalido produziria, DEPOIS do
    # conserto, exatamente o mesmo vermelho do defeito original.
    Calibracao.carregar(alvo)

    return json.loads(alvo.read_text(encoding="utf-8"))


def _dirigir(monkeypatch, alvo, argv, party_nova) -> int:
    """Roda o `main()` de verdade, com o disco preso a `tmp_path`."""
    # ESTA LINHA E O QUE MANTEM O calibration.json REAL FORA DO ALCANCE DA
    # SUITE. Ela nao e conveniencia: sem ela, esta suite reproduz o incidente de
    # 2026-08-30 dentro do CI, apagando os moldes de glifo da maquina de quem
    # rodar os testes. NAO REMOVA.
    monkeypatch.setattr(l2scanner.calibrar, "ARQUIVO_CALIBRACAO", alvo)

    # A MIRA DA JANELA, NEUTRALIZADA. Esta linha e o que mantem esta suite
    # independente do `config.toml` DA MAQUINA de quem a roda: no dia em que o
    # usuario preencher `[jogo] personagem`, sem ela estes casos passariam a
    # tentar abrir uma janela de jogo de verdade e quebrariam por um motivo que
    # nao tem nada a ver com o que eles afirmam. Um teste que le a configuracao
    # da maquina de quem o roda nao esta afirmando nada.
    monkeypatch.setattr(
        l2scanner.calibrar, "ler_personagem_do_jogo", lambda *a, **k: None
    )
    # CINTO. Com o curto-circuito de `main()` — que so enumera janelas quando
    # alguem pediu alvo — esta funcao nem chega a ser chamada por aqui. Ela
    # entra justamente por isso: para segurar o dia em que alguem tirar o
    # curto-circuito sem perceber que ele estava prendendo esta suite ao
    # `EnumWindows` da maquina.
    monkeypatch.setattr(
        l2scanner.calibrar, "listar_janelas_do_jogo", lambda *a, **k: []
    )

    pixels = np.zeros((400, 400, 3), dtype=np.uint8)
    monkeypatch.setattr(l2scanner.calibrar, "capturar_tela", lambda: (pixels, 0, 0))
    monkeypatch.setattr(
        l2scanner.calibrar, "calibrar_automatico", lambda *a, **k: party_nova
    )
    monkeypatch.setattr(
        l2scanner.calibrar, "calibrar_selecionando", lambda *a, **k: party_nova
    )
    monkeypatch.setattr(l2scanner.calibrar, "janela_que_contem", lambda *a, **k: None)
    monkeypatch.setattr(
        l2scanner.calibrar, "achar_barra_do_proprio", lambda *a, **k: None
    )
    # `conferir_visualmente` grava PNG na RAIZ do repositorio e nada tem a dizer
    # sobre a invariante desta suite.
    monkeypatch.setattr(
        l2scanner.calibrar, "conferir_visualmente", lambda *a, **k: None
    )
    monkeypatch.setattr(sys, "argv", ["l2scanner.calibrar", *argv])
    return l2scanner.calibrar.main()


def _perdidos(antes: dict, depois: dict) -> list[str]:
    return sorted(n for n in NAO_SAO_DA_PARTY if depois.get(n) != antes.get(n))


class TestAPartyNaoApagaOQueNaoEDela:
    def test_auto_preserva_os_27_campos_que_a_party_nao_possui(
        self, monkeypatch, tmp_path, geo
    ):
        """O caso que prende o incidente de 2026-08-30."""
        alvo = tmp_path / "calibration.json"
        antes = _semear(alvo, geo)

        rc = _dirigir(monkeypatch, alvo, ["--auto"], _nova_party(geo))
        assert rc == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        perdidos = _perdidos(antes, depois)
        assert not perdidos, (
            "A calibracao de party APAGOU campos que nao sao dela: "
            + ", ".join(perdidos)
        )

    def test_selecionar_passa_pelo_mesmo_portao(self, monkeypatch, tmp_path, geo):
        """`--selecionar` delega para o mesmo `cal.salvar` — mesmo defeito."""
        alvo = tmp_path / "calibration.json"
        antes = _semear(alvo, geo)

        rc = _dirigir(monkeypatch, alvo, ["--selecionar"], _nova_party(geo))
        assert rc == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        perdidos = _perdidos(antes, depois)
        assert not perdidos, (
            "A calibracao de party por --selecionar APAGOU campos que nao sao "
            "dela: " + ", ".join(perdidos)
        )

    def test_os_13_campos_da_party_recebem_o_valor_NOVO_e_nao_o_do_disco(
        self, monkeypatch, tmp_path, geo
    ):
        """GUARDA DE REGRESSAO — verde nos dois lados, e isso e o esperado.

        Ele nao existe para provar o defeito: o codigo de hoje monta a
        `Calibracao` do zero, entao esses 13 campos JA sao os novos e nao ha o
        que ele denuncie antes do conserto. Ele existe para impedir que o
        CONSERTO vire regressao: um load-mutate-save ingenuo faria `nomes`,
        `assinaturas` e `hp_proprio` VELHOS sobreviverem a uma recalibracao, e
        assinatura estale contra geometria nova e o modo de falha que manda a
        party socorrer a pessoa errada.
        """
        alvo = tmp_path / "calibration.json"
        _semear(alvo, geo)
        nova = _nova_party(geo)

        rc = _dirigir(monkeypatch, alvo, ["--auto"], nova)
        assert rc == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))

        assert depois["party_window"] == nova.party_window.como_dict()
        assert depois["ancora"] == nova.ancora.como_dict()
        assert depois["layout"]["passo"] == nova.layout.passo
        assert depois["geometria_da_tela"] == geo

        # Sem `--nomes`, e sem barra propria achada: o vazio e o valor CORRETO.
        assert depois["nomes"] == []
        assert depois["assinaturas"] == []
        assert depois["hp_proprio"] is None
        assert depois["nome_proprio"] is None
        assert depois["janela"] is None
        assert depois["party_window_na_janela"] is None

    def test_a_lista_de_donos_e_coerente_com_a_dataclass(self):
        """A lista e de DONOS, e nenhum campo de mercado esta dentro dela."""
        da_dataclass = {f.name for f in fields(Calibracao)}

        assert l2scanner.calibrar.CAMPOS_DA_PARTY <= da_dataclass, (
            "CAMPOS_DA_PARTY tem nome que nao existe mais na dataclass: "
            + ", ".join(sorted(l2scanner.calibrar.CAMPOS_DA_PARTY - da_dataclass))
        )
        intrusos = sorted(
            n for n in l2scanner.calibrar.CAMPOS_DA_PARTY if n.startswith("mercado_")
        )
        assert not intrusos, (
            "Campo de mercado classificado como dono da party: " + ", ".join(intrusos)
        )

    def test_arquivo_ilegivel_nao_impede_a_party_de_gravar_e_avisa_ALTO(
        self, monkeypatch, tmp_path, capsys, geo
    ):
        """A rota de recuperacao do usuario: arquivo ruim nao pode travar."""
        alvo = tmp_path / "calibration.json"
        alvo.write_text("{isto nao e JSON", encoding="utf-8")

        rc = _dirigir(monkeypatch, alvo, ["--auto"], _nova_party(geo))
        assert rc == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        assert depois["party_window"]["esquerda"] == 100

        saida = capsys.readouterr().out
        assert "NAO CONSEGUI PRESERVAR" in saida, (
            "Um arquivo ilegivel foi sobrescrito CALADO — o usuario nao ficou "
            "sabendo que a calibracao de mercado e as regioes do Tiat se foram."
        )


class _JanelaFalsa:
    """Um `JanelaSource` que nao abre janela nenhuma."""

    def __init__(self, *args, **kwargs):
        pass

    def capturar_completo(self):
        return np.zeros((400, 400, 3), dtype=np.uint8)

    def fechar(self):
        pass


class TestOModoSoloContinuaPreservando:
    """GUARDA DE REGRESSAO do caminho `--solo`.

    `--solo` JA preservava antes desta rodada: `calibrar_so_a_propria_barra`
    parte de `Calibracao.carregar(ARQUIVO_CALIBRACAO)`. Este caso nao prova o
    conserto — prova a INVARIANTE, para que `--solo` nao deixe de preservar numa
    refatoracao futura. E exatamente assim que o lado da party ficou aberto
    depois do CR-04: o conserto foi feito de um lado, e nada prendeu o outro.
    """

    def test_solo_preserva_os_27_campos_e_muda_so_o_que_e_dele(
        self, monkeypatch, tmp_path, geo
    ):
        alvo = tmp_path / "calibration.json"
        antes = _semear(alvo, geo)

        # O mesmo motivo de sempre: sem esta linha a suite escreve no
        # calibration.json da maquina de quem roda os testes. NAO REMOVA.
        monkeypatch.setattr(l2scanner.calibrar, "ARQUIVO_CALIBRACAO", alvo)

        titulo = "Yazalaque - XM Essence"
        monkeypatch.setattr(
            l2scanner.calibrar, "listar_janelas_do_jogo", lambda: [titulo]
        )
        monkeypatch.setattr(l2scanner.calibrar, "achar_janela", lambda *a: 4242)
        monkeypatch.setattr(l2scanner.calibrar, "origem_da_janela", lambda *a: (0, 0))
        monkeypatch.setattr(l2scanner.calibrar, "JanelaSource", _JanelaFalsa)
        monkeypatch.setattr(
            l2scanner.calibrar,
            "achar_barra_do_proprio",
            lambda *a, **k: Regiao(esquerda=60, topo=70, largura=80, altura=9),
        )
        # Grava PNG na raiz do repositorio e nada tem a dizer sobre a invariante.
        monkeypatch.setattr(
            l2scanner.calibrar, "_conferencia_do_solo", lambda *a, **k: None
        )
        monkeypatch.setattr(sys, "argv", ["l2scanner.calibrar", "--solo"])

        assert l2scanner.calibrar.main() == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        perdidos = _perdidos(antes, depois)
        assert not perdidos, (
            "O modo --solo APAGOU campos que nao sao dele: " + ", ".join(perdidos)
        )

        # O que o modo solo LEGITIMAMENTE muda:
        assert depois["janela"] == titulo
        assert depois["nome_proprio"] == "Yazalaque"
        assert depois["hp_proprio"] == {
            "esquerda": 60,
            "topo": 70,
            "largura": 80,
            "altura": 9,
        }
        # E o que ele promete por escrito ao usuario no `.bat`: a party window
        # da calibracao anterior sobrevive.
        assert depois["party_window"] == antes["party_window"]
