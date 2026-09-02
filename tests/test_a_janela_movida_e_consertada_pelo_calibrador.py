"""Uma janela movida se conserta com uma RODADA, e nao com um COMMIT.

E o criterio 4 do roadmap na sua metade executavel. A frase que ele pede --
*"sem editar uma linha de codigo"* -- e testavel de verdade: calcula-se um
resumo criptografico de todo `l2scanner/*.py` antes do ato 1 e depois do ato 3,
e afirma-se que sao IDENTICOS. Isso vale mais que a frase porque nao depende de
ninguem se lembrar de conferir.

A IDA E VOLTA INTEIRA, SEM O JOGO ABERTO, em tres atos:

  ato 1  uma calibracao cuja `barra_esquerda` aponta para a REGIAO PRETA da
         montagem -- aquela que o `01-01` deixou preta de proposito porque
         nenhuma gravacao existente contem o nivel. A leitura de tiro unico
         devolve RECUSA DE CAMPO VAZIO, nomeada.
  ato 2  o calibrador roda com a selecao dublada devolvendo o retangulo CERTO,
         gravando numa calibracao dentro do `tmp_path`.
  ato 3  a MESMA leitura, contra o MESMO frame, com a calibracao nova -- e
         agora ela devolve o EXP. Afirma-se o INTEIRO, e nao apenas "nao
         recusou".

POR QUE A REGIAO PRETA E NAO UM RETANGULO FORA DO FRAME: as duas produzem
recusas por motivos DIFERENTES (`campo-vazio` contra `recorte-fora-do-frame`),
e o que se simula aqui e uma janela MOVIDA, e nao uma calibracao impossivel.
Um retangulo fora do frame nunca chega ao OCR; um retangulo dentro do frame e
no lugar errado chega, e e esse o caso do usuario.

O QUE O QUARTO CASO ACHOU, E ELE NAO FOI PINTADO DE VERDE
=========================================================
O plano mandava deslocar o retangulo por poucos pixels, de modo a CORTAR UM
DIGITO em vez de sair do campo, e REGISTRAR o que a leitura devolve -- com a
expectativa de recusa, e com a instrucao explicita de que um numero seria um
ACHADO e nao um teste a forcar.

**Ela devolve um numero, e ele esta errado.** Medido nesta arvore, sobre
`montagem_da_janela.png`, com o retangulo do EXP `0,1368 520x24` e piso 160,
deslocando a borda ESQUERDA para dentro (a verdade de campo e `8,0012%`, ou
`80012`):

    deslocamento   resultado                            escalas
    ------------   ----------------------------------   -------
    ate +82        80012  (`8.0012%`)  CERTO                 1-2
        +83        recusa por discordancia entre escalas       -
        +84        30012  (`3.0012%`)  ERRADO                  1
        +85        10012  (`1.0012%`)  ERRADO                  1
        +86        10012  (`1.0012%`)  ERRADO                  2
        +87 e alem recusa por gramatica                        -

**Ha uma janela de TRES PIXELS (84 a 86) em que a leitura FABRICA um EXP
gramaticalmente perfeito e errado.** E o `+86` e o pior dos tres: **as DUAS
escalas concordam no numero errado**, entao o cruzamento nao pega -- e o
cruzamento e a unica guarda que resta depois da gramatica.

ISSO CONTRADIZ, PARCIALMENTE, UMA AFIRMACAO DO `01-01`. A docstring de
`_cruzar_as_escalas` diz que a regra da abstencao *"continua CORRETA E
OBRIGATORIA para o EXP e para o nivel"* e que ela FALHOU so na adena, porque a
adena tem um sosia gramatical adjacente. Medido aqui: o EXP tem o mesmo modo de
falha, so que por RECORTE em vez de por campo vizinho -- cortar o primeiro
digito transforma `8` em `3` e depois em `1`, e o que sobra passa na gramatica
inteira. O sosia nao precisa estar ao lado; basta o corte fabricar um.

**A guarda que existe para isso e a de RECORTE, e nao a de leitura**: o
retangulo vem do calibrador, o calibrador desenha a imagem de conferencia, e o
olho do usuario e quem ve que o `8` esta cortado. Este arquivo registra a
medicao para que ninguem conclua, do teste do ato 3, que "deslocamento pequeno
sempre recusa". **Ele NAO recusa numa janela de 3 px, e essa janela e
exatamente onde uma janela levemente movida cai.**

O QUE ESTE CASO COBRE E O QUE NAO COBRE: ele cobre UM campo (o EXP), UMA
fixtura, UM piso e deslocamento SO da borda esquerda. Ele nao mede a borda
direita, nem o deslocamento vertical, nem os outros dois campos. Uma conclusao
geral a partir dele seria a mesma sorte que o M-N ja custou a esta fase.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.calibrar_renda as cr
from l2scanner import ocr
from l2scanner.frames import Regiao
from l2scanner.renda_leitura import (
    MOTIVO_DO_CAMPO_VAZIO,
    RecusaDaRenda,
    ValorDaRenda,
    exp_da_barra,
    recortar,
)

RAIZ = Path(__file__).resolve().parent.parent
FIXTURAS = RAIZ / "tests" / "fixtures" / "renda"
MONTAGEM = FIXTURAS / "montagem_da_janela.png"
CALIBRACAO_DE_FIXTURE = FIXTURAS / "calibracao_de_fixture.json"

TEM_OCR = ocr.disponivel()
MOTIVO_SEM_OCR = ocr.motivo_indisponivel()
ocr._resetar_cache()

RAZAO_DO_SKIP = (
    "Este Python nao tem as bindings de OCR do Windows"
    f" ({MOTIVO_SEM_OCR.splitlines()[0] if MOTIVO_SEM_OCR else 'motivo desconhecido'})."
    " O ambiente de producao tem, e o global tem pytest: rode com os dois,"
    ' PYTHONPATH=".;<repo>/.venv/Lib/site-packages" python -m pytest'
    " tests/test_a_janela_movida_e_consertada_pelo_calibrador.py"
)

precisa_de_ocr = pytest.mark.skipif(not TEM_OCR, reason=RAZAO_DO_SKIP)

# A VERDADE DE CAMPO desta fixtura, lida a olho no monitor e escrita em
# `tests/fixtures/renda/LEIA-ME.md`: o EXP da Faerlina e `8,0012%`.
EXP_DA_FAERLINA = 80012

# O retangulo CERTO do EXP nesta montagem, e a REGIAO PRETA que faz as vezes de
# janela movida. Os dois sao DADO DE TESTE e saem da fixtura de calibracao --
# nao sao constantes de producao, e o portao do criterio 4 varre
# `l2scanner/*.py` e nunca `tests/`.
PERSONAGEM = "Faerlina"


def _resumo_de_l2scanner() -> str:
    """Um resumo criptografico de TODO `l2scanner/*.py`, em ordem estavel.

    E a forma executavel de "sem editar uma linha de codigo". Ordenar os
    caminhos importa: sem a ordem, o resumo mudaria conforme o sistema de
    arquivos devolvesse os nomes, e o caso viraria intermitente.
    """
    digestor = hashlib.sha256()
    for caminho in sorted((RAIZ / "l2scanner").glob("*.py")):
        digestor.update(caminho.name.encode("utf-8"))
        digestor.update(caminho.read_bytes())
    return digestor.hexdigest()


def _calibracao_apontando_para_o_preto(tmp_path: Path) -> Path:
    """A calibracao do ato 1: o EXP apontado para a regiao preta da montagem."""
    dados = json.loads(CALIBRACAO_DE_FIXTURE.read_text(encoding="utf-8"))
    entrada = dados["renda_por_personagem"][PERSONAGEM]
    entrada["barra_esquerda"]["regiao"] = dict(entrada["nivel"]["regiao"])
    alvo = tmp_path / "calibration.json"
    alvo.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    return alvo


def _regiao_do_exp(caminho: Path) -> Regiao:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    bloco = dados["renda_por_personagem"][PERSONAGEM]["barra_esquerda"]
    return Regiao.de_dict(bloco["regiao"])


def _piso_do_exp(caminho: Path) -> int:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return int(
        dados["renda_por_personagem"][PERSONAGEM]["barra_esquerda"]["piso_de_brilho"]
    )


def _ler_o_exp(frame, caminho: Path):
    """A leitura de tiro unico, com a calibracao que estiver naquele arquivo."""
    recorte = recortar(frame, _regiao_do_exp(caminho), campo="exp")
    if isinstance(recorte, RecusaDaRenda):
        return recorte
    return exp_da_barra(recorte, piso_de_brilho=_piso_do_exp(caminho))


def _rodar_o_calibrador(monkeypatch, alvo: Path, frame, retangulo) -> int:
    """O ato 2: o calibrador, com a selecao dublada e o disco preso ao tmp_path.

    A varredura de OCR e dublada para fora porque o ato 2 e sobre GRAVAR O
    RETANGULO. O piso ja esta no arquivo e nao muda -- e assim o ato 3 mede a
    diferenca que o retangulo fez, e nao a soma de duas mudancas.
    """
    monkeypatch.setattr(cr, "ARQUIVO_CALIBRACAO", alvo)
    monkeypatch.setattr(
        cr,
        "_selecionar_regiao",
        lambda _pixels, titulo, *_a, **_k: (
            retangulo if titulo == cr.ROTULO_DA_REGIAO["barra_esquerda"] else None
        ),
    )
    monkeypatch.setattr(cr, "_gravar_conferencia", lambda _tela: None)
    monkeypatch.setattr(cr, "_varrer_as_regioes_de_ocr", lambda *_a, **_k: {})
    monkeypatch.setattr(
        cr, "_resolver_a_fonte", lambda _args, _cal: (frame, PERSONAGEM, None, None)
    )
    return cr.main(["--imagem", "irrelevante.png", "--personagem", PERSONAGEM])


@pytest.fixture()
def frame():
    imagem = cv2.imread(str(MONTAGEM))
    assert imagem is not None, f"a fixtura {MONTAGEM} nao abriu"
    return imagem


class TestAIdaEVoltaEmTresAtos:
    @precisa_de_ocr
    def test_UM_RETANGULO_ERRADO_RECUSA_O_CALIBRADOR_CONSERTA_E_A_LEITURA_PASSA(
        self, monkeypatch, tmp_path, frame
    ):
        resumo_antes = _resumo_de_l2scanner()

        # --- ATO 1: o retangulo errado, apontado para a regiao preta ---------
        alvo = _calibracao_apontando_para_o_preto(tmp_path)
        antes = _ler_o_exp(frame, alvo)
        assert isinstance(antes, RecusaDaRenda), (
            f"a leitura com o retangulo ERRADO devolveu {antes!r} em vez de "
            f"recusar. O ato 3 nao provaria nada: nao havia o que consertar."
        )
        assert antes.motivo == MOTIVO_DO_CAMPO_VAZIO, (
            "a recusa veio por outro motivo. A regiao preta simula uma janela "
            "MOVIDA (retangulo valido, lugar errado), e nao uma calibracao "
            "impossivel -- se o motivo mudou, a fixtura mudou."
        )

        # --- ATO 2: o calibrador grava o retangulo certo ----------------------
        certo = json.loads(CALIBRACAO_DE_FIXTURE.read_text(encoding="utf-8"))[
            "renda_por_personagem"
        ][PERSONAGEM]["barra_esquerda"]["regiao"]
        rc = _rodar_o_calibrador(
            monkeypatch,
            alvo,
            frame,
            (
                certo["esquerda"],
                certo["topo"],
                certo["largura"],
                certo["altura"],
            ),
        )
        assert rc == 0
        assert _regiao_do_exp(alvo) == Regiao.de_dict(certo)

        # --- ATO 3: a MESMA leitura, o MESMO frame, a calibracao nova ---------
        depois = _ler_o_exp(frame, alvo)
        assert isinstance(depois, ValorDaRenda), (
            f"depois do conserto a leitura ainda recusa: {depois!r}"
        )
        assert depois.valor == EXP_DA_FAERLINA, (
            f"a leitura devolveu {depois.valor} e a tela dizia "
            f"{EXP_DA_FAERLINA} (`8,0012%`). Afirmar o INTEIRO e nao apenas 'nao "
            f"recusou' e o que separa 'consertou' de 'parou de reclamar'."
        )

        # --- O RESUMO: a forma executavel de "sem editar uma linha" -----------
        assert _resumo_de_l2scanner() == resumo_antes, (
            "`l2scanner/*.py` mudou entre a recusa e o conserto. O criterio 4 "
            "existe justamente para que uma janela movida NAO custe um commit."
        )

    def test_A_REGIAO_PRETA_DA_MONTAGEM_CONTINUA_PRETA(self, frame):
        """A fixtura do ato 1, conferida sem OCR nenhum.

        Se a montagem deixar de ter regiao preta, o ato 1 para de simular uma
        janela movida e o caso inteiro passa a medir outra coisa -- e este caso
        e quem denuncia isso, em vez de o ato 1 ficar vermelho por um motivo
        que ninguem liga a fixtura.
        """
        dados = json.loads(CALIBRACAO_DE_FIXTURE.read_text(encoding="utf-8"))
        preta = Regiao.de_dict(
            dados["renda_por_personagem"][PERSONAGEM]["nivel"]["regiao"]
        )
        recorte = recortar(frame, preta, campo="nivel")
        assert not isinstance(recorte, RecusaDaRenda)
        assert int(np.max(recorte)) == 0, (
            "a regiao que o `01-01` deixou preta de proposito deixou de ser "
            "preta; o ato 1 nao simula mais uma janela movida"
        )

    def test_O_RESUMO_DE_l2scanner_E_ESTAVEL_ENTRE_DUAS_CHAMADAS(self):
        """Sem isto, o caso acima poderia passar por o resumo ser aleatorio."""
        assert _resumo_de_l2scanner() == _resumo_de_l2scanner()

    def test_CONTROLE_O_RESUMO_MUDA_QUANDO_UM_ARQUIVO_MUDA(self, tmp_path):
        """O controle positivo do resumo. Um resumo que nunca muda nao prova

        que nada mudou -- prova que ele nao olha.
        """
        pasta = tmp_path / "pacote"
        pasta.mkdir()
        (pasta / "a.py").write_text("X = 1\n", encoding="utf-8")

        def resumir() -> str:
            digestor = hashlib.sha256()
            for caminho in sorted(pasta.glob("*.py")):
                digestor.update(caminho.name.encode("utf-8"))
                digestor.update(caminho.read_bytes())
            return digestor.hexdigest()

        primeiro = resumir()
        (pasta / "a.py").write_text("X = 2\n", encoding="utf-8")
        assert resumir() != primeiro


class TestOQuartoCasoEUmaMEDICAOENaoUmaEXPECTATIVA:
    """O deslocamento que corta um digito. Ver a docstring do modulo.

    A expectativa do plano era RECUSA. A medicao devolveu NUMERO ERRADO numa
    janela de tres pixels, e os casos abaixo afirmam a MEDICAO. Pintar de verde
    a forca -- afrouxando para "recusa ou numero" -- apagaria justamente o
    achado.
    """

    # (deslocamento da borda esquerda, valor esperado ou None para recusa)
    MEDIDO = (
        (80, EXP_DA_FAERLINA),
        (82, EXP_DA_FAERLINA),
        (83, None),
        (84, 30012),
        (85, 10012),
        (86, 10012),
        (87, None),
        (90, None),
    )

    def _ler_deslocado(self, frame, deslocamento: int):
        base = json.loads(CALIBRACAO_DE_FIXTURE.read_text(encoding="utf-8"))[
            "renda_por_personagem"
        ][PERSONAGEM]["barra_esquerda"]
        certo = Regiao.de_dict(base["regiao"])
        recorte = recortar(
            frame,
            Regiao(
                esquerda=certo.esquerda + deslocamento,
                topo=certo.topo,
                largura=certo.largura - deslocamento,
                altura=certo.altura,
            ),
            campo="exp",
        )
        return exp_da_barra(recorte, piso_de_brilho=int(base["piso_de_brilho"]))

    @precisa_de_ocr
    @pytest.mark.parametrize("deslocamento,esperado", MEDIDO)
    def test_O_QUE_A_LEITURA_DEVOLVE_EM_CADA_DESLOCAMENTO(
        self, frame, deslocamento, esperado
    ):
        leitura = self._ler_deslocado(frame, deslocamento)
        if esperado is None:
            assert isinstance(leitura, RecusaDaRenda), (
                f"+{deslocamento}px: esperava recusa e veio {leitura!r}. A "
                f"tabela deste arquivo e uma MEDICAO -- se ela mudou, remeca e "
                f"reescreva a tabela, nao afrouxe a afirmacao."
            )
        else:
            assert isinstance(leitura, ValorDaRenda), (
                f"+{deslocamento}px: esperava o numero {esperado} e veio "
                f"{leitura!r}"
            )
            assert leitura.valor == esperado

    @precisa_de_ocr
    def test_HA_UMA_JANELA_DE_TRES_PIXELS_QUE_FABRICA_UM_EXP_ERRADO(self, frame):
        """O achado, afirmado como achado.

        Este caso NAO e uma promessa de que o comportamento e bom -- ele e a
        anotacao de que o comportamento e RUIM, presa por teste para que a
        proxima pessoa que mexer no recorte ou no cruzamento veja que existe
        uma janela onde a leitura mente.
        """
        fabricados = {
            deslocamento: leitura.valor
            for deslocamento in (84, 85, 86)
            for leitura in [self._ler_deslocado(frame, deslocamento)]
            if isinstance(leitura, ValorDaRenda)
        }
        assert fabricados == {84: 30012, 85: 10012, 86: 10012}, fabricados
        assert EXP_DA_FAERLINA not in fabricados.values(), (
            "os tres deslocamentos devolveram o numero CERTO; o achado sumiu e "
            "a docstring deste modulo precisa ser reescrita"
        )

    @precisa_de_ocr
    def test_E_NUM_DELES_AS_DUAS_ESCALAS_CONCORDAM_NO_NUMERO_ERRADO(self, frame):
        """O pior dos tres, e o que contradiz parcialmente o `01-01`.

        A docstring de `_cruzar_as_escalas` afirma que a regra da abstencao
        "continua CORRETA E OBRIGATORIA para o EXP" e que ela falhou so na
        adena, por causa do sosia gramatical adjacente. Medido aqui: em
        `+86px` as DUAS escalas leem `1,0012%` onde a tela diz `8,0012%`. O
        cruzamento nao pega, porque nao ha nada para cruzar -- as duas erram
        igual. O sosia nao precisa estar ao lado; o corte fabrica um.
        """
        leitura = self._ler_deslocado(frame, 86)
        assert isinstance(leitura, ValorDaRenda)
        assert leitura.escalas == 2, (
            "esperava as DUAS escalas concordando no numero errado; veio "
            f"escalas={leitura.escalas}"
        )
        assert leitura.valor != EXP_DA_FAERLINA
