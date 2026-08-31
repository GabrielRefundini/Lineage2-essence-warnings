"""O batismo: o scanner PERGUNTA quem e, e o usuario RESPONDE do celular.

A DESCOBERTA QUE DEFINE ESTA FASE, DITA EM VOZ ALTA

O acervo real do usuario tem AGORA duas entradas anonimas (`15caecfa...`, 161
pixels de texto; `f19e3c92...`, 79 pixels), aprendidas em campo pela Fase 2 em
31/08/2026. E o caminho do APRENDIZADO nunca vai perguntar sobre elas:

1. no arranque, `carregar_identidades` funde calibradas e acervo, e as duas
   entram em `cal.assinaturas`;
2. no proximo `extrair`, a linha de cada uma casa ~1.000 contra ela mesma;
3. `Casamento.nome` de uma entrada anonima e a string VAZIA, e nao `None`;
4. `sessao._candidatas_para_aprender` exige `linha.nome is None`;
5. elas nunca sao candidatas, o `Aprendiz` nunca as ve, e nenhum `Aprendizado`
   nasce.

Um gatilho preso apenas ao evento "gravei uma assinatura nova" faria a feature
funcionar perfeitamente na suite e NAO PERGUNTAR NADA no unico acervo real que
existe. Por isso ha DOIS gatilhos — o aprendizado e a varredura de arranque — e
UM marcador so (`perguntado_<chave>`, `O_CREAT|O_EXCL`). D-04 diz "uma pergunta
por assinatura", por ASSINATURA e nao por evento de aprendizado.

`TestOGatilhoDoAprendizadoNaoAlcancaOQueJaEstaNoDisco` e a prova de que a
varredura nao e redundancia. Sem ela, as duas pessoas ficam "Membro N" para
sempre.

OS IDIOMAS SAO COPIADOS, E NAO IMPORTADOS

As fixtures vem de `tests/test_acervo.py` e os falsos de despacho e leitura de
`tests/test_janela_sob_demanda.py`, copiados pela razao que aquele arquivo ja
escreve: importar entre arquivos de teste cria dependencia entre eles, e o que
esta em jogo aqui e a COSTURA, que e onde os erros deste projeto moram.

Todo caso roda dentro de `tmp_path`, com o jogo fechado e sem rede.
"""

from __future__ import annotations

import ast
import json
import os
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.acervo import (
    PREFIXO_ASSINATURA,
    PREFIXO_NOME,
    AcervoDeIdentidades,
    carregar_identidades,
    chave_da_assinatura,
)
from l2scanner.agenda import RegistroEmDisco
from l2scanner.aprendiz import AjustesDoAprendiz, Aprendiz
from l2scanner.batismo import (
    DIGITOS_DO_APELIDO,
    Pendente,
    apelido_da_chave,
    montar_pergunta,
    pendentes_do_acervo,
    responder_batismo,
)
from l2scanner.calibracao import Calibracao
from l2scanner.comandos import (
    COMANDOS_DE_MEMBRO,
    _AJUDA,
    Comando,
    Membro,
    interpretar_dinamico,
)
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import Assinatura, criar_assinatura
from l2scanner.notificador import Categoria
from l2scanner.rastreador import Rastreador
from l2scanner.sessao import Sessao
from l2scanner.visao import _recorte_do_nome, extrair

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "identidade"

# A linha da party window que fica DESCONHECIDA nos casos do aprendizado: as
# outras tres sao semeadas no acervo. A segunda, e nao a primeira, para que o
# rotulo esperado ("Membro 2") nao possa coincidir por acidente com um
# "Membro 1" vindo de um indice zerado.
LINHA_DA_FATIA = 1

# O telefone de DONO, o mesmo que o resto da suite usa.
DONO = "+5544997077000"
# O de MEMBRO nao pode colidir com o de dono nos 8 digitos finais, que sao os
# unicos comparados.
TELEFONE_DE_MEMBRO = "+5544912345678"
MEMBROS = (Membro(nick="Korzis", telefone=TELEFONE_DE_MEMBRO),)


# ---------------------------------------------------------------------------
# Fixtures e falsos, copiados dos dois arquivos que ja os tem
# ---------------------------------------------------------------------------


@pytest.fixture
def calibracao() -> Calibracao:
    """A calibracao da fixture SEM as assinaturas que ela ja traz.

    O acervo tem de ser a unica fonte de identidade nestes testes: com as
    quatro assinaturas calibradas na mesa, um casamento correto nao provaria
    que a entrada em disco foi lida.
    """
    cal = Calibracao.carregar(FIXTURES / "calibracao.json")
    cal.assinaturas = []
    return cal


@pytest.fixture
def pixels() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture da party nao pode ser lida"
    return px


def assinatura_da_linha(px: np.ndarray, cal: Calibracao, indice: int) -> Assinatura:
    """A assinatura ANONIMA do nome que esta naquela linha do frame real."""
    recorte = _recorte_do_nome(px, cal, indice)
    assert recorte is not None
    return criar_assinatura("", recorte)


def semear(pasta: Path, assinatura: Assinatura, nome: str | None = None) -> str:
    """Escreve uma entrada A MAO, como um humano faria, e devolve a chave."""
    pasta.mkdir(parents=True, exist_ok=True)
    chave = chave_da_assinatura(assinatura)
    corpo = assinatura.como_dict()
    corpo.pop("nome", None)
    (pasta / f"{PREFIXO_ASSINATURA}{chave}.json").write_text(
        json.dumps(corpo), encoding="utf-8"
    )
    if nome is not None:
        (pasta / f"{PREFIXO_NOME}{chave}").write_text(nome, encoding="utf-8")
    return chave


def observar_frame(px: np.ndarray, cal: Calibracao):
    return extrair(Frame(pixels=px, indice=0, saude=SaudeDoFrame.OK), cal)


def retrato_da_pasta(pasta: Path) -> dict[str, bytes]:
    """Todo arquivo da pasta com o conteudo, para comparar antes e depois."""
    if not pasta.exists():
        return {}
    return {c.name: c.read_bytes() for c in sorted(pasta.iterdir())}


class DespachanteQueGrava:
    """Grava `(texto, categoria, conversa_alvo)` em vez de mandar para a rede.

    Truthy de proposito: `atender_comandos` e `Sessao._despachar` testam
    `if not despachante` e `if self.despachante`.
    """

    def __init__(self) -> None:
        self.despachos: list[tuple[str, object, str | None]] = []

    def despachar(self, texto, categoria=None, conversa_alvo=None) -> None:
        self.despachos.append((texto, categoria, conversa_alvo))

    @property
    def alvos(self) -> list:
        return [conversa for _, _, conversa in self.despachos]

    @property
    def textos(self) -> list:
        return [texto for texto, _, _ in self.despachos]

    @property
    def perguntas(self) -> list:
        """So os despachos que sao a PERGUNTA do batismo.

        Filtrado pela sintaxe que a pergunta ensina, e nao pela contagem total:
        um caso que contasse todos os despachos quebraria no dia em que a
        sessao passasse a falar de outra coisa no mesmo tick, e estaria
        medindo a coisa errada.
        """
        return [texto for texto, _, _ in self.despachos if "/batizar" in texto]


class LeitorDeUmaMensagem:
    """Um `LeitorDeComandos` falso que devolve UMA mensagem crua.

    A mensagem e CRUA (dict, como a API do Chatwoot devolve) de proposito: as
    travas de `comandos_novos` — tipo, nota privada, id repetido, vocabulario e
    autorizacao — tem de rodar de verdade.
    """

    ativo = True

    def __init__(
        self,
        texto: str,
        *,
        telefone: str = DONO,
        conversa="1",
        identificador: int = 7777,
    ) -> None:
        self.telefones = [DONO]
        self.membros = list(MEMBROS)
        self._mensagem = {
            "id": identificador,
            "content": texto,
            "message_type": 0,
            "private": False,
            "sender": {"name": "Ze do Zap", "phone_number": telefone},
            "conversation_id": conversa,
        }

    def ler(self, _monotonico):
        return [self._mensagem]


def responder_pelo_whatsapp(
    texto: str,
    tmp_path,
    *,
    acervo=None,
    assinaturas_vivas=None,
    rastreador=None,
    telefone: str = DONO,
    conversa="1",
    identificador: int = 7777,
    registro=None,
) -> DespachanteQueGrava:
    """Roda `atender_comandos` como o LACO roda, e devolve o que saiu.

    Adaptado do helper `perguntar` de `tests/test_janela_sob_demanda.py` para
    passar `acervo=` e `assinaturas_vivas=`, que sao os parametros novos desta
    fase. `agora` e `datetime` e `monotonico` e float: os dois relogios de
    `atender_comandos` nao sao intercambiaveis.
    """
    from datetime import datetime

    from l2scanner.__main__ import atender_comandos

    despachante = DespachanteQueGrava()
    atender_comandos(
        LeitorDeUmaMensagem(
            texto,
            telefone=telefone,
            conversa=conversa,
            identificador=identificador,
        ),
        registro if registro is not None else RegistroEmDisco(tmp_path / "agenda"),
        [],
        despachante,
        datetime(2026, 8, 31, 20, 30),
        time.monotonic(),
        rastreador,
        acervo=acervo,
        assinaturas_vivas=assinaturas_vivas,
    )
    return despachante


class SilencioParado:
    def ativo(self):
        return False

    def atualizar(self, agora):
        return None


def montar_sessao(
    tmp_path,
    calibracao,
    *,
    acervo,
    despachante=None,
    leituras_para_aprender: int = 3,
    identidades=None,
    rastreador=None,
) -> Sessao:
    """Uma `Sessao` de verdade, com o aprendiz e o acervo ligados."""
    return Sessao(
        cal=calibracao,
        rastreador=rastreador
        or Rastreador(
            nomes=list(calibracao.nomes),
            assinaturas_configuradas=(
                identidades.configuradas if identidades is not None else False
            ),
        ),
        eventos_agendados=[],
        registro=RegistroEmDisco(tmp_path / "agenda"),
        silencio=SilencioParado(),
        despachante=despachante,
        aprendiz=Aprendiz(
            acervo, AjustesDoAprendiz(leituras_para_aprender=leituras_para_aprender)
        ),
        acervo=acervo,
    )


def semear_tres_das_quatro(pasta: Path, px, cal) -> list[str]:
    """Semeia todas as linhas MENOS `LINHA_DA_FATIA`, que fica desconhecida.

    Semear as quatro faria o caso do aprendizado passar sem que NENHUMA
    escrita acontecesse.
    """
    return [
        semear(pasta, assinatura_da_linha(px, cal, indice))
        for indice in range(4)
        if indice != LINHA_DA_FATIA
    ]


def carregar_na_calibracao(cal, pasta: Path):
    identidades = carregar_identidades([], AcervoDeIdentidades(pasta))
    cal.assinaturas = identidades.assinaturas
    return identidades


# ---------------------------------------------------------------------------
# A GUARDA CONTRA PROVA VAZIA, PRIMEIRO
# ---------------------------------------------------------------------------


class TestAGuardaContraProvaVazia:
    """Antes de qualquer coisa: a entrada anonima E reconhecida, e CALA.

    Sem esta afirmacao inicial, "depois do batismo o nome apareceu" passaria
    igualzinho num cenario onde a assinatura nunca casou com nada — e o caso
    estaria provando que o acervo nao funciona, com cara de estar provando que
    o batismo funciona.
    """

    def test_a_entrada_anonima_e_reconhecida_com_nome_VAZIO(
        self, tmp_path, pixels, calibracao
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        carregar_na_calibracao(calibracao, tmp_path)

        linha = observar_frame(pixels, calibracao).linhas[LINHA_DA_FATIA]

        assert linha.confianca_do_nome > 0.9, (
            "ela FOI reconhecida — sem isso o resto do arquivo nao prova nada"
        )
        assert linha.nome == "", (
            "uma entrada anonima tem nome VAZIO, e nao None: e exatamente por "
            "isso que o gatilho do aprendizado nunca a alcanca"
        )

    def test_o_rotulo_exibido_e_Membro_N(self, tmp_path, pixels, calibracao):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        obs = observar_frame(pixels, calibracao)
        rastreador = Rastreador(
            nomes=list(calibracao.nomes),
            assinaturas_configuradas=identidades.configuradas,
        )
        for i in range(15):
            rastreador.observar(obs, -100 + i)

        identidade = rastreador._identidade_por_linha[LINHA_DA_FATIA]
        assert identidade == f"#linha{LINHA_DA_FATIA}"
        assert (
            rastreador._nome_exibido(identidade) == f"Membro {LINHA_DA_FATIA + 1}"
        )


# ---------------------------------------------------------------------------
# A DESCOBERTA: o gatilho do aprendizado nao alcanca o que ja esta no disco
# ---------------------------------------------------------------------------


class TestOGatilhoDoAprendizadoNaoAlcancaOQueJaEstaNoDisco:
    """A prova de que a varredura de arranque NAO e redundancia.

    Este e o caso mais importante do arquivo. Ele afirma o que o acervo real do
    usuario faria hoje: as duas entradas ja gravadas entram na lista viva, sao
    reconhecidas com nome VAZIO, e o `Aprendiz` nunca as ve.

    Quem as alcanca e a varredura de arranque (Tarefa 3), que e a dona do
    marcador. Esta classe prova apenas que ela e NECESSARIA.
    """

    def test_cinquenta_ticks_com_tudo_ja_no_acervo_nao_aprendem_NADA(
        self, tmp_path, pixels, calibracao
    ):
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        assert len(identidades.assinaturas) == 4, "premissa: as quatro no acervo"
        assert identidades.sem_nome == 4, "premissa: as quatro sem nome"

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )

        for indice in range(50):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            assert resultado.aprendizados == [], (
                f"tick {indice}: uma entrada ja gravada virou candidata de "
                "novo. Se isso acontecer, o acervo incha com uma entrada nova "
                "a cada N ticks para a MESMA pessoa (APRE-04)"
            )

        assert despachante.perguntas == [], (
            "o gatilho do APRENDIZADO nao pode perguntar por elas: elas nunca "
            "produzem Aprendizado. Quem pergunta e a varredura de arranque"
        )

    def test_e_o_disco_continua_intacto_depois_dos_cinquenta_ticks(
        self, tmp_path, pixels, calibracao
    ):
        """Nenhuma entrada nova, e nenhum marcador queimado pelo caminho."""
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        antes = retrato_da_pasta(tmp_path)

        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=DespachanteQueGrava(),
            identidades=identidades,
        )
        for indice in range(50):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        assert retrato_da_pasta(tmp_path) == antes


# ---------------------------------------------------------------------------
# O GATILHO DO APRENDIZADO: pergunta UMA vez, citando a linha
# ---------------------------------------------------------------------------


class TestOAprendizadoPergunta:
    def test_a_enesima_leitura_grava_UMA_entrada_e_manda_UMA_pergunta(
        self, tmp_path, pixels, calibracao
    ):
        conhecidas = semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        assert len(conhecidas) == 3, "premissa: tres conhecidas, uma nao"

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )

        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        assert len(aprendidas) == 1, (
            f"uma linha desconhecida, uma entrada. Saiu: {aprendidas}"
        )
        assert len(despachante.perguntas) == 1, (
            f"uma entrada nova, uma pergunta. Saiu: {despachante.perguntas}"
        )

    def test_a_pergunta_cita_o_apelido_e_a_linha_em_BASE_1(
        self, tmp_path, pixels, calibracao
    ):
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        pergunta = despachante.perguntas[0]
        apelido = apelido_da_chave(aprendidas[0].chave)
        assert apelido in pergunta, (
            f"a pergunta nao cita o apelido {apelido!r} da chave gravada; sem "
            f"ele nao ha o que responder.\n{pergunta}"
        )
        assert f"linha {LINHA_DA_FATIA + 1}" in pergunta, (
            "a posicao e citada em BASE 1, como o usuario a ve na tela "
            f"(criterio 1 do ROADMAP).\n{pergunta}"
        )
        assert "/batizar" in pergunta, "a pergunta ensina a sintaxe da resposta"

    def test_a_pergunta_sai_com_Categoria_SEMPRE(
        self, tmp_path, pixels, calibracao
    ):
        """O marcador de D-04 e de MAO UNICA.

        `Categoria.NORMAL` e CORTADA no transporte durante o silencio de
        TvT/Prime, e a mensagem cortada nem entra no outbox — a pergunta seria
        queimada e nunca enviada, sistematicamente, justamente durante o evento
        em que a party mais muda de gente.
        """
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        for indice in range(10):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        categorias = {
            categoria
            for texto, categoria, _ in despachante.despachos
            if "/batizar" in texto
        }
        assert categorias == {Categoria.SEMPRE}, (
            "a pergunta tem de atravessar o silencio: uma pergunta silenciada "
            f"e uma pergunta perdida PARA SEMPRE. Saiu: {categorias}"
        )


class TestAPerguntaNaoSeRepete:
    def test_mais_vinte_ticks_identicos_nao_perguntam_de_novo(
        self, tmp_path, pixels, calibracao
    ):
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        for indice in range(10):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
        depois_da_primeira = len(despachante.perguntas)
        assert depois_da_primeira == 1, "premissa: uma pergunta ja saiu"

        for indice in range(10, 30):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        assert len(despachante.perguntas) == depois_da_primeira, (
            "a pergunta repetiu num tick seguinte. O usuario ja reclamou de "
            "spam neste projeto uma vez"
        )

    def test_uma_sessao_NOVA_sobre_a_MESMA_pasta_tambem_nao_pergunta(
        self, tmp_path, pixels, calibracao
    ):
        """O marcador esta em DISCO, e nao em memoria.

        Sem isso, reiniciar o scanner refaria todas as perguntas ja feitas — e
        o usuario reinicia o scanner o tempo todo.
        """
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        primeira = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=primeira,
            identidades=identidades,
        )
        for indice in range(10):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
        assert len(primeira.perguntas) == 1, "premissa: a primeira perguntou"

        # O reinicio: calibracao recarregada do disco, sessao nova, acervo novo
        # sobre a MESMA pasta.
        cal2 = Calibracao.carregar(FIXTURES / "calibracao.json")
        cal2.assinaturas = []
        identidades2 = carregar_na_calibracao(cal2, tmp_path)
        segunda = DespachanteQueGrava()
        sessao2 = montar_sessao(
            tmp_path,
            cal2,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=segunda,
            identidades=identidades2,
        )
        for indice in range(10):
            sessao2.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        assert segunda.perguntas == [], (
            "depois de reiniciar, a pergunta saiu de novo: o marcador nao "
            "esta em disco"
        )


class TestSemDespachanteNadaEMarcado:
    """D-05 estendido: nao queimar o marcador quando nao ha para onde mandar.

    Quem roda sem `.env` e sem `--dry-run` — o caminho que `montar_despachante`
    documenta como "o scanner continua util no console" — simplesmente ainda
    nao perguntou, e vai perguntar no dia em que configurar a entrega. Queimar
    o marcador aqui deixaria a pessoa como "Membro N" ate alguem apagar um
    arquivo a mao.
    """

    def test_sem_despachante_o_marcador_nao_aparece_na_pasta(
        self, tmp_path, pixels, calibracao
    ):
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=None,
            identidades=identidades,
        )
        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        assert len(aprendidas) == 1, "premissa: a entrada foi gravada mesmo assim"
        marcadores = [
            c.name for c in tmp_path.iterdir() if c.name.startswith("perguntado_")
        ]
        assert marcadores == [], (
            "a pergunta foi QUEIMADA sem sair: o marcador e para sempre, e a "
            f"pessoa ficaria Membro N ate alguem apagar um arquivo. {marcadores}"
        )


# ---------------------------------------------------------------------------
# O COMANDO: existe, e ele e de DONO
# ---------------------------------------------------------------------------


class TestOComandoEDeDono:
    def test_o_comando_existe_no_enum(self):
        assert hasattr(Comando, "BATIZAR")

    def test_o_tripwire_da_ajuda_segue_verde(self):
        assert set(_AJUDA) == set(Comando)

    def test_o_comando_tem_linha_na_ajuda(self):
        linha = _AJUDA[Comando.BATIZAR]
        assert linha.sintaxe.startswith("/batizar")
        assert "apelido" in linha.descricao.lower(), (
            "a descricao precisa dizer de onde vem o apelido: e a unica coisa "
            "nao obvia do comando"
        )

    def test_o_batismo_NAO_e_comando_de_membro(self):
        """Decisao 2 do ROADMAP, ja travada.

        Um nome errado e corrupcao duravel e dificil de notar num acervo que
        nunca e podado e nao tem comando de esquecer — a mesma familia de
        `/corrigir` e `/pegou`. E `COMANDOS_DE_MEMBRO` e LISTA DE INCLUSAO
        justamente para que um comando destrutivo novo NASCA fora do alcance.
        """
        assert Comando.BATIZAR not in COMANDOS_DE_MEMBRO


class TestOCaminhoRealDeLeituraEntregaOComando:
    @pytest.mark.parametrize(
        "texto",
        [
            "/batizar 15caec Mostarda",
            "/batizar-15caec Mostarda",
            ".batizar 15caec Mostarda",
            "/nomear 15caec Mostarda",
        ],
    )
    def test_as_quatro_formas_escritas(self, texto):
        assert interpretar_dinamico(texto, frozenset()) == (
            Comando.BATIZAR,
            "15caec Mostarda",
        ), texto

    def test_a_palavra_sozinha_nao_vira_consulta_de_nick(self):
        """O `return None` dos ramos NAO e redundancia.

        Sem ele o fluxo cai no ramo de consulta logo abaixo, onde
        `_NICK_VALIDO` casa as palavras "batizar" e "nomear", e um personagem
        homonimo transformaria o comando numa consulta dele.
        """
        conhecidos = frozenset({"batizar", "nomear"})
        assert interpretar_dinamico("/batizar", conhecidos) is None
        assert interpretar_dinamico("/nomear", conhecidos) is None


# ---------------------------------------------------------------------------
# A RESPOSTA BATIZA A ASSINATURA CERTA
# ---------------------------------------------------------------------------


class TestARespostaBatizaAAssinaturaCerta:
    def test_o_arquivo_de_nome_nasce_com_o_nick_exato(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        apelido = apelido_da_chave(chave)

        responder_pelo_whatsapp(
            f"/batizar {apelido} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        alvo = tmp_path / f"{PREFIXO_NOME}{chave}"
        assert alvo.exists(), "o irmao nome_<chave> nao foi criado"
        assert alvo.read_text(encoding="utf-8") == "Mostarda"

    def test_a_assinatura_NAO_e_tocada_e_por_isso_a_chave_nao_muda(
        self, tmp_path, pixels, calibracao
    ):
        """D-06, afirmado byte a byte."""
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        arquivo = tmp_path / f"{PREFIXO_ASSINATURA}{chave}.json"
        antes = arquivo.read_bytes()

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        assert arquivo.read_bytes() == antes, (
            "batizar tocou a assinatura. Se ela muda, a chave muda, e o pino "
            "de D-01 deixa de apontar para lugar nenhum"
        )
        assert AcervoDeIdentidades(tmp_path).chaves() == [chave]

    def test_a_resposta_confirma_no_privado_E_no_grupo(
        self, tmp_path, pixels, calibracao
    ):
        """A PERGUNTA foi publica, entao a resposta fecha o circuito no grupo.

        Uma resposta so no privado deixaria a pergunta pendurada no grupo para
        sempre, e o proximo party-mate que tentasse responder cairia no
        `continue` da autorizacao, sem resposta nenhuma.
        """
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )

        despachante = responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
        )

        assert despachante.alvos == ["1", None], (
            f"a confirmacao tinha que ir para a origem E para o grupo; "
            f"os destinos foram {despachante.alvos}"
        )
        assert "Mostarda" in despachante.textos[0]
        assert "Mostarda" in despachante.textos[1]

    def test_sem_acervo_o_ramo_recusa_e_NAO_ecoa_no_grupo(self, tmp_path):
        """O laco que nao tem acervo responde, e responde so a quem digitou."""
        despachante = responder_pelo_whatsapp(
            "/batizar 15caec Mostarda", tmp_path, acervo=None
        )

        assert despachante.alvos == ["1"]
        assert "identidades" in despachante.textos[0].lower()


class TestONomePassaAValerSemReiniciar:
    """D-08, nas TRES metades. A leitura ingenua e uma linha, e ela nao basta."""

    def _cenario(self, tmp_path, pixels, calibracao):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        rastreador = Rastreador(
            nomes=list(calibracao.nomes),
            assinaturas_configuradas=identidades.configuradas,
        )
        return chave, rastreador

    def test_a_lista_viva_ganha_o_nome(self, tmp_path, pixels, calibracao):
        chave, rastreador = self._cenario(tmp_path, pixels, calibracao)
        antes = [
            a.nome for a in calibracao.assinaturas if chave_da_assinatura(a) == chave
        ]
        assert antes == [""], "premissa: a assinatura viva esta anonima"

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        depois = [
            a.nome for a in calibracao.assinaturas if chave_da_assinatura(a) == chave
        ]
        assert depois == ["Mostarda"], (
            "a lista viva nao recebeu o nome: a tela continuaria dizendo "
            "Membro N ate o proximo arranque, e o usuario batizaria de novo "
            "achando que falhou"
        )

    def test_o_snapshot_de_nomes_reservados_ganha_o_nome(
        self, tmp_path, pixels, calibracao
    ):
        chave, rastreador = self._cenario(tmp_path, pixels, calibracao)

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        assert "Mostarda" in rastreador.nomes_reservados

    def test_o_proximo_extrair_sobre_o_MESMO_frame_ja_diz_o_nome(
        self, tmp_path, pixels, calibracao
    ):
        chave, rastreador = self._cenario(tmp_path, pixels, calibracao)

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        linha = observar_frame(pixels, calibracao).linhas[LINHA_DA_FATIA]
        assert linha.nome == "Mostarda", (
            "o nome tinha que valer no MESMO tick, sem reiniciar nada"
        )


class TestOTerceiroElo:
    """O elo que quase ninguem escreve, e ele e a metade do criterio 2.

    `nomes_reservados` e um SNAPSHOT do arranque, tirado de
    `cal.nomes_com_assinatura`. Ele existe para que um nome que JA TEM
    assinatura visual nunca seja emprestado por POSICAO.
    """

    def test_antes_o_nick_e_emprestado_por_posicao_e_depois_nao(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        # O caso real: o nick esta em `cal.nomes` (o usuario digitou a lista)
        # e NUNCA foi calibrado, entao ele nao esta em `nomes_reservados`.
        outra_linha = 3
        nomes = list(calibracao.nomes)
        nomes[outra_linha] = "Mostarda"
        rastreador = Rastreador(
            nomes=nomes,
            nomes_reservados=set(calibracao.nomes_com_assinatura),
            assinaturas_configuradas=identidades.configuradas,
        )
        assert rastreador.nome_de(outra_linha) == "Mostarda", (
            "premissa: hoje o nick e emprestado por POSICAO para uma linha "
            "que nao e dele"
        )

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
            rastreador=rastreador,
        )

        assert rastreador.nome_de(outra_linha) == f"Membro {outra_linha + 1}", (
            "sem `nomes_reservados.add(nick)` a tela mostra DOIS Mostarda, e "
            "um deles e mentira. E exatamente a familia de defeito que a Fase "
            "1 gastou uma onda inteira consertando, chegando pela porta nova "
            "desta fase"
        )


# ---------------------------------------------------------------------------
# A ESCRITA DO NOME E DEFENSIVA NA ORIGEM
# ---------------------------------------------------------------------------


class TestAEscritaDoNomeEDefensiva:
    """`CHAVE_VALIDA` no ESCRITOR, e nao so na leitura.

    A string vem de uma mensagem de WhatsApp. A validacao aqui e ESTRUTURAL e
    nao redundante: e o que torna travessia de caminho impossivel POR
    CONSTRUCAO, o mesmo argumento que a Fase 1 ja escreveu para o lado da
    leitura. Duas travas na mesma porta e o desenho.
    """

    CHAVE_BOA = "a" * 64

    @pytest.mark.parametrize(
        "chave",
        [
            "",
            "nao-e-hex",
            "A" * 64,  # hex maiusculo nao e a lingua do acervo
            "a" * 63,
            "a" * 65,
            "../" + "a" * 61,
            "a" * 32 + os.sep + "a" * 31,
        ],
    )
    def test_uma_chave_que_nao_e_64_hex_e_invalida_e_nao_escreve_nada(
        self, tmp_path, chave
    ):
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        assert acervo.nomear(chave, "Mostarda") == "invalido"
        assert retrato_da_pasta(tmp_path) == antes, (
            "uma chave invalida escreveu arquivo; e por aqui que a travessia "
            "de caminho entraria"
        )

    @pytest.mark.parametrize(
        "nome", ["", "x", "a" * 17, "Mos tarda", "Mostarda\n", "Mos-tarda", "../x"]
    )
    def test_um_nome_fora_do_charset_e_invalido_e_nao_escreve_nada(
        self, tmp_path, nome
    ):
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        assert acervo.nomear(self.CHAVE_BOA, nome) == "invalido"
        assert retrato_da_pasta(tmp_path) == antes

    def test_nada_e_escrito_FORA_da_pasta(self, tmp_path):
        """A prova de que a travessia nao acontece, e nao so que ela e recusada."""
        pasta = tmp_path / "identidades"
        vizinha = tmp_path / "vizinha"
        vizinha.mkdir()
        acervo = AcervoDeIdentidades(pasta)

        for chave in ("../vizinha/" + "a" * 52, ".." + os.sep + "a" * 62):
            assert acervo.nomear(chave, "Mostarda") == "invalido"

        assert list(vizinha.iterdir()) == []
        assert retrato_da_pasta(pasta) == {}

    def test_um_nome_valido_grava_e_a_leitura_ja_o_ve(
        self, tmp_path, pixels, calibracao
    ):
        """Guarda contra prova vazia: a escrita FUNCIONA quando deve."""
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)

        assert acervo.nomear(chave, "Mostarda") == "nomeado"
        assert acervo.nomeados() == {chave: "Mostarda"}
        assert acervo.anonimas() == []
        assert [a.nome for a in acervo.assinaturas()] == ["Mostarda"]

    def test_nomear_de_novo_TROCA_o_conteudo_e_nao_duplica(
        self, tmp_path, pixels, calibracao
    ):
        """D-06: a correcao do BATI-05 e a MESMA operacao do batismo."""
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)
        acervo.nomear(chave, "Kaus")

        assert acervo.nomear(chave, "Mostarda") == "nomeado"
        assert acervo.nomeados() == {chave: "Mostarda"}
        arquivos = sorted(c.name for c in tmp_path.iterdir())
        assert len(arquivos) == 2, f"sobrou temporario na pasta: {arquivos}"


class TestAnonimasEONomeados:
    def test_anonimas_devolve_so_quem_nao_tem_nome_na_ordem_de_chaves(
        self, tmp_path, pixels, calibracao
    ):
        chaves = [
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, i))
            for i in range(4)
        ]
        acervo = AcervoDeIdentidades(tmp_path)
        acervo.nomear(chaves[0], "Mostarda")

        assert acervo.anonimas() == [c for c in acervo.chaves() if c != chaves[0]]
        assert acervo.nomeados() == {chaves[0]: "Mostarda"}

    def test_pendentes_do_acervo_nascem_SEM_posicao(
        self, tmp_path, pixels, calibracao
    ):
        """A varredura de arranque nao tem posicao nenhuma para citar.

        Aquela entrada foi aprendida numa sessao anterior, possivelmente por
        outra instancia, e nenhuma posicao de agora corresponde a ela.
        Inventar uma seria a primeira mentira do caminho, no recurso inteiro
        que existe para nao mentir.
        """
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, 0))
        pendentes = pendentes_do_acervo(AcervoDeIdentidades(tmp_path))

        assert [p.indice for p in pendentes] == [None]
        assert isinstance(pendentes[0], Pendente)


# ---------------------------------------------------------------------------
# O MODULO NAO CONHECE O MUNDO, E NAO TEM RELOGIO
# ---------------------------------------------------------------------------


class TestOBatismoNaoConheceOMundo:
    """Igualdade de CONJUNTOS sobre os irmaos importados, e nunca um grep.

    A ausencia de `loot` e deliberada e tem precedente escrito: `acervo.py` ja
    se recusou a importar `loot.NICK_VALIDO` porque `loot` importa `agenda`, e
    arrastar essa cadeia para um modulo que precisa NAO ter relogio nenhum
    trocaria uma linha de regex por um acoplamento que o portao AST depois
    teria de raciocinar sobre.
    """

    PROIBIDOS = frozenset(
        {"visao", "sessao", "rastreador", "calibracao", "loot", "agenda", "presenca"}
    )

    @staticmethod
    def _irmaos_importados(caminho: Path) -> set[str]:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        achados: set[str] = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.ImportFrom) and no.level:
                if no.module:
                    achados.add(no.module.split(".")[0])
            elif isinstance(no, ast.Import):
                for alias in no.names:
                    achados.add(alias.name.split(".")[-1])
        return achados

    def test_o_conjunto_de_irmaos_importados(self):
        achados = self._irmaos_importados(RAIZ / "l2scanner" / "batismo.py")
        vazados = achados & self.PROIBIDOS
        assert vazados == set(), (
            f"batismo.py passou a conhecer {sorted(vazados)}. Ele fala "
            "`AcervoDeIdentidades`, `Assinatura` e stdlib, e so"
        )

    def test_a_prova_pega_um_import_proibido_enfiado(self):
        """Guarda contra prova vazia: o detector acha o que deveria achar."""
        import tempfile

        fonte = (RAIZ / "l2scanner" / "batismo.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as pasta:
            envenenado = Path(pasta) / "batismo.py"
            envenenado.write_text(fonte + "\nfrom .agenda import x\n", encoding="utf-8")
            assert "agenda" in self._irmaos_importados(envenenado)


class TestBatismoNaoTemRelogioProprio:
    """A guarda estrutural mora em `tests/test_presenca.py`.

    Este caso existe para que quem ler `test_batismo.py` saiba ONDE ela esta:
    um `datetime.now()` que aparecesse no batismo para "so perguntar de novo
    depois de 24 horas" reabriria, por dentro, a repeticao que D-04 fecha por
    construcao.
    """

    def test_o_modulo_esta_na_tupla_do_portao(self):
        from tests.test_presenca import TestSemRelogioProprio

        assert "batismo.py" in TestSemRelogioProprio.MODULOS


class TestOApelidoTemSeisDigitos:
    def test_o_apelido_e_o_prefixo_da_chave(self):
        chave = "15caecfa21ad274e57604cab1f5c44b51b10cff23368245de568c47d513b651c"
        assert apelido_da_chave(chave) == chave[:DIGITOS_DO_APELIDO]
        assert apelido_da_chave(chave) == "15caec"

    def test_as_duas_entradas_REAIS_do_usuario_nao_colidem(self):
        """Medido no acervo real do usuario em 31/08/2026.

        As duas diferem no PRIMEIRO digito, entao ate um apelido de 1 digito
        bastaria. Os seis sao folga para o dia em que a pasta tiver dezenas.
        """
        uma = "15caecfa21ad274e57604cab1f5c44b51b10cff23368245de568c47d513b651c"
        outra = "f19e3c9255f748cd5b4517d9cad268c46f1186d3db75a7154ec79ff1fa96d548"
        assert apelido_da_chave(uma) != apelido_da_chave(outra)


class TestRespondeSemLista:
    """Os dois parametros opcionais sao `None` no laco da agenda.

    La nao existe nem lista viva nem rastreador, porque nao existe tela. O
    disco JA FOI ESCRITO nesse caso: o nome vale a partir do proximo arranque
    do scanner. Ver T-03-07.
    """

    def test_o_disco_e_escrito_mesmo_sem_lista_viva_nem_rastreador(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)

        resposta = responder_batismo(
            acervo, f"{apelido_da_chave(chave)} Mostarda"
        )

        assert acervo.nomeados() == {chave: "Mostarda"}
        assert "Mostarda" in resposta.privado
        assert resposta.grupo is not None
        assert resposta.grupo != resposta.privado, (
            "o grupo recebe uma redacao CURTA e diferente"
        )


class TestSemTravessaoNoQueOUsuarioLe:
    """cp1252: o travessao vira `?` no console e quebra no WhatsApp.

    Afirmado sobre os textos que este modulo PRODUZ, e nao sobre o fonte: uma
    busca no fonte acusaria a prosa das docstrings, que e livre.
    """

    def test_nem_a_pergunta_nem_as_recusas_tem_travessao(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)
        apelido = apelido_da_chave(chave)

        textos = [
            montar_pergunta(acervo, pendentes_do_acervo(acervo)),
            responder_batismo(acervo, "").privado,
            responder_batismo(acervo, "zzz Mostarda").privado,
            responder_batismo(acervo, "ffffff Mostarda").privado,
            responder_batismo(acervo, f"{apelido} Mostarda").privado,
        ]
        for texto in textos:
            assert texto is not None
            assert "—" not in texto, f"travessao em: {texto!r}"
            assert "–" not in texto, f"meia risca em: {texto!r}"
            texto.encode("cp1252")
