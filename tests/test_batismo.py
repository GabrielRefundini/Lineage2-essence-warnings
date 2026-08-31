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
    PREFIXO_PERGUNTA,
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
    apelidos_para_escolher,
    interpretar_batismo,
    montar_pergunta,
    pendentes_do_acervo,
    resolver,
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
    """Todo ARQUIVO da pasta com o conteudo, para comparar antes e depois.

    So arquivos: varios casos apontam o acervo para o proprio `tmp_path`, e a
    `.agenda/` da `Sessao` nasce ao lado. Um retrato que tentasse ler a pasta
    irma estaria medindo o cenario do teste, e nao o acervo.
    """
    if not pasta.exists():
        return {}
    return {
        c.name: c.read_bytes() for c in sorted(pasta.iterdir()) if c.is_file()
    }


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


# ---------------------------------------------------------------------------
# TAREFA 2: o PINO, provado contra uma party que se reorganizou
# ---------------------------------------------------------------------------


# Onde mora a entrada B do cenario de reorganizacao.
#
# A entrada A mora em `LINHA_DA_FATIA`, e e ELA que a pergunta cita. Depois da
# reorganizacao as duas trocam de lugar: B passa a ocupar a linha que a
# pergunta citou, e A vai parar aqui.
LINHA_DA_OUTRA = 3


def party_reorganizada(px: np.ndarray, cal: Calibracao, um: int, outro: int):
    """O MESMO frame com os recortes de NOME de duas linhas TROCADOS.

    A reorganizacao e MONTADA e nao suposta: os blocos de pixel do nome trocam
    de lugar de verdade, entao o `extrair` seguinte le a pessoa de `um` na
    posicao de `outro` exatamente como leria se a party window tivesse
    compactado em jogo.

    So o recorte do NOME troca, e nao a linha inteira, porque e o recorte do
    nome que carrega a identidade: HP e MP nao entram na assinatura.
    """
    novo = px.copy()
    a = cal.regiao_do_nome(um)
    b = cal.regiao_do_nome(outro)
    assert (a.altura, a.largura) == (b.altura, b.largura)

    fatia_a = (
        slice(a.topo, a.topo + a.altura),
        slice(a.esquerda, a.esquerda + a.largura),
    )
    fatia_b = (
        slice(b.topo, b.topo + b.altura),
        slice(b.esquerda, b.esquerda + b.largura),
    )
    novo[fatia_a] = px[fatia_b].copy()
    novo[fatia_b] = px[fatia_a].copy()
    return novo


def chave_vista_na_linha(px: np.ndarray, cal: Calibracao, indice: int) -> str:
    """De quem e a assinatura que esta NESTA linha, agora, neste frame.

    Derivada do MATERIAL (a chave e o sha256 do conteudo da mascara), e nao do
    reconhecedor: e assim que o teste consegue afirmar quem esta na linha
    citada ANTES de afirmar o desfecho do batismo.
    """
    return chave_da_assinatura(assinatura_da_linha(px, cal, indice))


def prefixos_presentes(pasta: Path) -> set[str]:
    """Os prefixos de arquivo que existem na pasta, por igualdade de conjuntos.

    Nao e um grep negativo por "indice" ou "mapa": um grep negativo passaria
    por engano no dia em que um segundo estado nascesse com outro nome. Um
    arquivo que nao case nenhum dos tres prefixos entra no conjunto com o nome
    INTEIRO, entao a igualdade acusa e ainda diz qual e.
    """
    conhecidos = (PREFIXO_ASSINATURA, PREFIXO_NOME, PREFIXO_PERGUNTA)
    achados = set()
    for arquivo in pasta.iterdir():
        if not arquivo.is_file():
            continue
        for prefixo in conhecidos:
            if arquivo.name.startswith(prefixo):
                achados.add(prefixo)
                break
        else:
            achados.add(arquivo.name)
    return achados


class TestOPinoAtravessaAReorganizacaoDaParty:
    """A PROVA CENTRAL DO BATI-03, e ela e comportamental.

    A sequencia e a real: a pergunta sai citando uma linha, o usuario volta ao
    jogo, a party se reorganiza, e a resposta chega minutos depois. Se o alvo
    fosse a linha, o nome iria para a pessoa errada em SILENCIO, com a mensagem
    parecendo perfeitamente normal.
    """

    def _cenario(self, tmp_path, pixels, calibracao):
        """Duas entradas anonimas: A na linha da fatia, B na outra linha."""
        chave_a = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        chave_b = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_OUTRA)
        )
        carregar_na_calibracao(calibracao, tmp_path)
        return chave_a, chave_b

    def test_a_pergunta_cita_a_linha_e_a_resposta_vai_para_a_CHAVE(
        self, tmp_path, pixels, calibracao
    ):
        chave_a, chave_b = self._cenario(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)

        # (1) a pergunta sai citando a linha onde A foi vista.
        pergunta = montar_pergunta(
            acervo, [Pendente(chave=chave_a, indice=LINHA_DA_FATIA)]
        )
        assert f"linha {LINHA_DA_FATIA + 1}" in pergunta

        # (2) a party se REORGANIZA: agora quem esta na linha citada e B.
        reorganizado = party_reorganizada(
            pixels, calibracao, LINHA_DA_FATIA, LINHA_DA_OUTRA
        )
        assert (
            chave_vista_na_linha(reorganizado, calibracao, LINHA_DA_FATIA) == chave_b
        ), (
            "premissa do caso: a entrada B tem de estar MESMO na linha citada "
            "na segunda observacao. Um caso que reorganizasse 'mais ou menos' "
            "e depois afirmasse o desfecho estaria provando outra coisa"
        )

        # (3) a resposta chega, apontando para o apelido de A.
        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Mostarda",
            tmp_path,
            acervo=acervo,
            assinaturas_vivas=calibracao.assinaturas,
        )

        # A AFIRMACAO E SOBRE O NOME DO ARQUIVO NO ACERVO, e nunca sobre "a
        # linha N ficou com o nome": um caso escrito sobre a linha passaria por
        # ACIDENTE quando a reorganizacao devolvesse a pessoa a mesma posicao.
        assert (tmp_path / f"{PREFIXO_NOME}{chave_a}").read_text(
            encoding="utf-8"
        ) == "Mostarda"
        assert not (tmp_path / f"{PREFIXO_NOME}{chave_b}").exists(), (
            "o nome foi para a entrada que estava na LINHA citada, e nao para "
            "a que a pergunta PINOU. Resolver por posicao batiza a pessoa "
            "errada em silencio, e a mensagem parece perfeitamente normal"
        )

    def test_a_linha_citada_continua_SEM_NOME_depois_do_batismo(
        self, tmp_path, pixels, calibracao
    ):
        """O outro lado da mesma prova, agora na TELA."""
        chave_a, _ = self._cenario(tmp_path, pixels, calibracao)
        reorganizado = party_reorganizada(
            pixels, calibracao, LINHA_DA_FATIA, LINHA_DA_OUTRA
        )

        responder_pelo_whatsapp(
            f"/batizar {apelido_da_chave(chave_a)} Mostarda",
            tmp_path,
            acervo=AcervoDeIdentidades(tmp_path),
            assinaturas_vivas=calibracao.assinaturas,
        )

        linhas = observar_frame(reorganizado, calibracao).linhas
        assert linhas[LINHA_DA_FATIA].nome == "", (
            "quem esta AGORA na linha citada ganhou o nome: o alvo virou a "
            "posicao em algum lugar do caminho"
        )
        assert linhas[LINHA_DA_OUTRA].nome == "Mostarda", (
            "e a pessoa certa aparece com o nome onde quer que ela esteja "
            "agora — e o que 'a assinatura diz onde a pessoa esta' significa"
        )


class TestNaoExisteSintaxeQueAlcanceUmaLinha:
    """D-03 nao precisou de trava: ele e uma AUSENCIA.

    `/batizar 3` cai em "apelido desconhecido" porque "3" e so um prefixo hex
    que nao casa chave nenhuma. Ninguem deve "consertar" isso acrescentando um
    ramo que aceite numero de linha.
    """

    @pytest.mark.parametrize(
        "argumento", ["3 Mostarda", "linha3 Mostarda", "#linha3 Mostarda"]
    )
    def test_nenhuma_das_tres_formas_escreve_coisa_alguma(
        self, tmp_path, pixels, calibracao, argumento
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        resposta = responder_batismo(acervo, argumento)

        assert resposta.grupo is None, "uma recusa nao ecoa no grupo"
        assert retrato_da_pasta(tmp_path) == antes, f"{argumento!r} mexeu na pasta"

    def test_um_numero_de_linha_cai_em_apelido_DESCONHECIDO(
        self, tmp_path, pixels, calibracao
    ):
        """O "3" e hex valido; ele so nao aponta para nada."""
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)

        privado = responder_batismo(acervo, "3 Mostarda").privado

        assert "nao e numero de linha" in privado, (
            "a recusa precisa DIZER que apelido nao e numero de linha: '3' e "
            "exatamente o que um usuario distraido digitaria pensando na "
            f"terceira linha.\n{privado}"
        )

    @pytest.mark.parametrize("argumento", ["linha3 Mostarda", "#linha3 Mostarda"])
    def test_o_que_nao_e_hex_cai_em_MALFORMADO(
        self, tmp_path, pixels, calibracao, argumento
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)

        privado = responder_batismo(acervo, argumento).privado

        assert "Nao entendi" in privado
        assert "PRIMEIRO" in privado, (
            "o erro humano mais provavel e inverter os dois argumentos, entao "
            f"a recusa tem de dizer qual e qual.\n{privado}"
        )


def par_de_assinaturas_com_prefixo_COMUM(px, cal):
    """Duas assinaturas REAIS cujas chaves comecam igual, e o tamanho do comum.

    QUAL DAS DUAS ESTRATEGIAS DO PLANO FOI USADA, E POR QUE. O plano oferecia
    chamar `resolver` direto com chaves fabricadas — e isso e feito, no
    `TestResolverJamaisDesempata`, porque `resolver` e uma funcao PURA e
    testa-la direto e o caminho certo para o combinatorio, exatamente como a
    Fase 2 alimentou o `Aprendiz` direto com `Candidata`.

    Mas o criterio de aceite tambem pede que a PASTA fique inalterada numa
    recusa ambigua, e isso exige duas entradas de verdade no acervo — o
    `_ler` recalcula a chave a partir do conteudo e descarta o que nao bate,
    entao nao ha como enfiar uma chave inventada la dentro. Por isso este
    helper: ele PROCURA, de forma deterministica, um par que colida.

    A busca vira um bit da mascara de um recorte real por vez e agrupa as
    chaves pelos tres primeiros digitos. Com algumas centenas de variantes o
    par existe com folga (o aniversario sobre 4096 baldes), e a ordem da
    varredura e fixa, entao o par encontrado e sempre o mesmo.
    """
    base = assinatura_da_linha(px, cal, LINHA_DA_FATIA).mascara
    plano = base.flatten()
    baldes: dict[str, tuple[str, Assinatura]] = {}

    for celula in range(min(600, plano.size)):
        virado = plano.copy()
        virado[celula] = 0 if virado[celula] else 1
        assinatura = Assinatura(nome="", mascara=virado.reshape(base.shape))
        chave = chave_da_assinatura(assinatura)
        balde = chave[:3]
        if balde in baldes:
            outra_chave, outra = baldes[balde]
            comum = 0
            while chave[comum] == outra_chave[comum]:
                comum += 1
            return outra, assinatura, comum
        baldes[balde] = (chave, assinatura)

    raise AssertionError(
        "nenhum par de chaves com prefixo comum foi encontrado em 600 "
        "variantes; a busca precisa de mais amostras"
    )


class TestUmPrefixoAmbiguoERecusadoENuncaDesempatado:
    """D-02. O desempate silencioso e a mentira plausivel de sempre.

    Duas assinaturas que comecam igual sao DUAS PESSOAS. Escolher uma delas
    por ordem, por data ou por qualquer outro criterio produz uma mensagem que
    parece normal e batiza a pessoa errada.
    """

    def _acervo_com_o_par(self, tmp_path, pixels, calibracao):
        uma, outra, comum = par_de_assinaturas_com_prefixo_COMUM(
            pixels, calibracao
        )
        acervo = AcervoDeIdentidades(tmp_path)
        assert acervo.gravar(uma) == "criado"
        assert acervo.gravar(outra) == "criado"
        return acervo, chave_da_assinatura(uma), chave_da_assinatura(outra), comum

    def test_a_recusa_cita_TODOS_os_candidatos_e_a_pasta_fica_inalterada(
        self, tmp_path, pixels, calibracao
    ):
        acervo, uma, outra, comum = self._acervo_com_o_par(
            tmp_path, pixels, calibracao
        )
        antes = retrato_da_pasta(tmp_path)

        resposta = responder_batismo(acervo, f"{uma[:comum]} Mostarda")

        candidatos = apelidos_para_escolher((uma, outra))
        for candidato in candidatos:
            assert candidato in resposta.privado, (
                f"a recusa nao cita {candidato!r}. Sem a lista o usuario nao "
                f"tem como agir.\n{resposta.privado}"
            )
        assert "mais digitos" in resposta.privado, (
            "a recusa precisa dizer O QUE FAZER: uma recusa que so diz 'nao' "
            "manda o usuario tentar de novo do mesmo jeito"
        )
        assert retrato_da_pasta(tmp_path) == antes, (
            "um prefixo ambiguo escreveu alguma coisa: em algum lugar do "
            "caminho houve um desempate"
        )

    def test_com_um_digito_a_mais_a_MESMA_chamada_resolve(
        self, tmp_path, pixels, calibracao
    ):
        """A guarda que prova que a recusa era sobre AMBIGUIDADE.

        Sem este caso irmao, a recusa acima passaria igualzinho se o comando
        estivesse simplesmente quebrado.
        """
        acervo, uma, _, comum = self._acervo_com_o_par(tmp_path, pixels, calibracao)

        resposta = responder_batismo(acervo, f"{uma[: comum + 1]} Mostarda")

        assert acervo.nomeados() == {uma: "Mostarda"}, resposta.privado


class TestUmPrefixoDesconhecidoERecusadoDizendoOQueExiste:
    def test_a_recusa_lista_os_apelidos_que_estao_sem_nome(
        self, tmp_path, pixels, calibracao
    ):
        chaves = [
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, i))
            for i in range(3)
        ]
        acervo = AcervoDeIdentidades(tmp_path)
        acervo.nomear(chaves[0], "Titander")

        privado = responder_batismo(acervo, "ffffff Mostarda").privado

        assert "ffffff" in privado, "a recusa diz qual apelido nao existe"
        for chave in chaves[1:]:
            assert apelido_da_chave(chave) in privado, (
                "a recusa lista os apelidos que estao SEM NOME agora; sem "
                f"isso o usuario nao tem como agir.\n{privado}"
            )
        assert apelido_da_chave(chaves[0]) not in privado, (
            "quem ja tem nome nao esta esperando batismo, e listar essa "
            "entrada convidaria um rebatismo que ninguem pediu"
        )


class TestOApelidoEDerivadoENadaEGuardado:
    """D-02: nao existe indice, nao existe mapa. So os tres irmaos."""

    def test_depois_de_uma_pergunta_e_um_batismo_so_ha_os_tres_prefixos(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        acervo = AcervoDeIdentidades(tmp_path)

        montar_pergunta(acervo, pendentes_do_acervo(acervo))
        responder_batismo(acervo, f"{apelido_da_chave(chave)} Mostarda")

        assert prefixos_presentes(tmp_path) == {
            PREFIXO_ASSINATURA,
            PREFIXO_NOME,
            PREFIXO_PERGUNTA,
        }


class TestOPinoAtravessaOReinicio:
    """A pergunta sai numa instancia; o comando e obedecido por OUTRA.

    O apelido continua resolvendo para a mesma chave porque ele e DERIVADO do
    conteudo, e o conteudo nao mudou.
    """

    def test_o_apelido_resolve_igual_numa_instancia_nova(
        self, tmp_path, pixels, calibracao
    ):
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        quem_perguntou = AcervoDeIdentidades(tmp_path)
        pergunta = montar_pergunta(
            quem_perguntou, pendentes_do_acervo(quem_perguntou)
        )
        apelido = apelido_da_chave(chave)
        assert apelido in pergunta

        # O reinicio, ou a outra instancia do usuario: objeto novo, mesma pasta.
        quem_respondeu = AcervoDeIdentidades(tmp_path)
        responder_batismo(quem_respondeu, f"{apelido} Mostarda")

        assert quem_respondeu.nomeados() == {chave: "Mostarda"}


class TestResolverJamaisDesempata:
    """A funcao PURA, alimentada direto com chaves fabricadas.

    E o caminho certo para o combinatorio, exatamente como a Fase 2 alimentou o
    `Aprendiz` direto com `Candidata`: aqui nao ha disco, nao ha frame e nao ha
    nada a montar, so a pergunta "a que chave este prefixo aponta".
    """

    UMA = "15caecfa" + "0" * 56
    OUTRA = "15caec00" + "1" * 56
    TERCEIRA = "f19e3c92" + "2" * 56
    TODAS = (UMA, OUTRA, TERCEIRA)

    def test_um_so_candidato_resolve(self):
        achado = resolver("f19e", self.TODAS)
        assert (achado.motivo, achado.chave) == ("ok", self.TERCEIRA)

    def test_dois_candidatos_RECUSAM_com_os_dois_na_lista(self):
        achado = resolver("15caec", self.TODAS)
        assert achado.motivo == "ambiguo"
        assert achado.chave is None, "jamais um desempate"
        assert set(achado.candidatos) == {self.UMA, self.OUTRA}

    def test_o_digito_que_separa_resolve(self):
        assert resolver("15caecf", self.TODAS).chave == self.UMA
        assert resolver("15caec0", self.TODAS).chave == self.OUTRA

    def test_nenhum_candidato_e_desconhecido(self):
        achado = resolver("3", self.TODAS)
        assert (achado.motivo, achado.chave) == ("desconhecido", None)

    @pytest.mark.parametrize(
        "prefixo", ["", "linha3", "#linha3", "15CAEC", "15caecg", "a" * 65]
    )
    def test_o_que_nao_e_hex_e_malformado(self, prefixo):
        achado = resolver(prefixo, self.TODAS)
        assert (achado.motivo, achado.chave) == ("malformado", None)

    def test_a_chave_inteira_tambem_e_um_prefixo_valido(self):
        assert resolver(self.UMA, self.TODAS).chave == self.UMA

    def test_apelidos_para_escolher_ESTICA_quando_seis_digitos_empatam(self):
        """A recusa ambigua nao pode virar um beco.

        Duas chaves que compartilham os seis primeiros digitos produziriam uma
        lista com o MESMO apelido duas vezes, e o "mande mais digitos" nao
        teria como ser seguido.
        """
        escolhas = apelidos_para_escolher((self.UMA, self.OUTRA))
        assert len(set(escolhas)) == 2, escolhas
        for escolha, chave in zip(escolhas, (self.UMA, self.OUTRA)):
            assert chave.startswith(escolha)
            assert resolver(escolha, self.TODAS).chave == chave


class TestAGramaticaEUmaSo:
    """`interpretar_batismo` valida na leitura e le no responder.

    Duas gramaticas divergiriam no primeiro ajuste e o comando passaria a
    aceitar o que nao executa.
    """

    INVALIDOS = [
        None,
        "",
        "   ",
        "15caec",  # uma palavra so
        "Mostarda",
        "15caec Mostarda demais",  # tres palavras
        "zzzzzz Mostarda",  # fora do hex
        "15caec M",  # nick de 1 caractere
        "15caec " + "M" * 17,  # nick de 17
        "15caec Mos-tarda",  # fora do charset de nick
        "Mostarda 15caec",  # os dois invertidos
    ]

    @pytest.mark.parametrize("argumento", INVALIDOS)
    def test_a_interpretacao_recusa(self, argumento):
        assert interpretar_batismo(argumento) is None, argumento

    @pytest.mark.parametrize("argumento", INVALIDOS)
    def test_e_o_responder_recusa_O_MESMO_conjunto(
        self, tmp_path, pixels, calibracao, argumento
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        resposta = responder_batismo(acervo, argumento)

        assert "Nao entendi" in resposta.privado, argumento
        assert retrato_da_pasta(tmp_path) == antes, (
            f"{argumento!r} foi recusado pela interpretacao e ESCREVEU pelo "
            "responder: as duas gramaticas divergiram"
        )

    def test_o_apelido_em_maiusculo_e_aceito_e_normalizado(self):
        """Copiar `15CAEC` de algum lugar continua funcionando.

        Isso nao alarga o charset nem um caractere: o `fullmatch` roda sobre a
        forma ja minuscula, e `15CAECG` continua recusado.
        """
        assert interpretar_batismo("15CAEC Mostarda") == ("15caec", "Mostarda")
        assert interpretar_batismo("15CAECG Mostarda") is None

    def test_o_nick_e_preservado_como_digitado(self):
        assert interpretar_batismo("15caec MoStArDa") == ("15caec", "MoStArDa")


# ---------------------------------------------------------------------------
# TAREFA 3: a pergunta que nao vira spam, e o marcador que nao e queimado a toa
# ---------------------------------------------------------------------------


class TestUmaPerguntaPorAssinaturaParaSempre:
    """D-04. O marcador E a decisao, e nunca uma checagem anterior."""

    CHAVE = "a" * 64

    def test_a_primeira_chamada_marca_e_as_seguintes_nao(self, tmp_path):
        acervo = AcervoDeIdentidades(tmp_path)

        assert acervo.marcar_pergunta(self.CHAVE) is True
        assert acervo.marcar_pergunta(self.CHAVE) is False
        assert acervo.marcar_pergunta(self.CHAVE) is False

    def test_uma_instancia_NOVA_sobre_a_mesma_pasta_tambem_nao_marca(
        self, tmp_path
    ):
        assert AcervoDeIdentidades(tmp_path).marcar_pergunta(self.CHAVE) is True
        assert AcervoDeIdentidades(tmp_path).marcar_pergunta(self.CHAVE) is False

    def test_duas_instancias_disputando_produzem_UMA_pergunta(
        self, tmp_path, pixels, calibracao
    ):
        """A premissa do projeto: Yazalaque e Faerlina rodando ao mesmo tempo.

        As duas veem partys DIFERENTES (cada cliente mostra os OUTROS
        membros), entao as duas vao aprender e as duas vao querer perguntar. O
        `O_CREAT|O_EXCL` decide a corrida no kernel.
        """
        chave = semear(
            tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA)
        )
        yazalaque = AcervoDeIdentidades(tmp_path)
        faerlina = AcervoDeIdentidades(tmp_path)

        desfechos = [
            yazalaque.marcar_pergunta(chave),
            faerlina.marcar_pergunta(chave),
        ]
        assert sorted(desfechos) == [False, True]

    def test_montar_pergunta_produz_texto_num_e_None_no_outro(
        self, tmp_path, pixels, calibracao
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        yazalaque = AcervoDeIdentidades(tmp_path)
        faerlina = AcervoDeIdentidades(tmp_path)

        primeira = montar_pergunta(yazalaque, pendentes_do_acervo(yazalaque))
        segunda = montar_pergunta(faerlina, pendentes_do_acervo(faerlina))

        assert primeira is not None
        assert segunda is None, (
            "as duas instancias mandaram a mesma pergunta para o mesmo grupo"
        )

    def test_uma_chave_que_nao_e_64_hex_nunca_marca(self, tmp_path):
        acervo = AcervoDeIdentidades(tmp_path)
        antes = retrato_da_pasta(tmp_path)

        for chave in ("", "3", "linha3", "../" + "a" * 61):
            assert acervo.marcar_pergunta(chave) is False, chave

        assert retrato_da_pasta(tmp_path) == antes


class TestFalhaDeDiscoNaoManda:
    """D-05, e ela e o CONTRARIO da agenda. As duas razoes, lado a lado.

    `agenda.RegistroEmDisco.marcar` colapsa `OSError` em True porque aviso
    duplicado vence aviso perdido: a party ignora uma repeticao, mas nao
    adivinha um TvT que ninguem anunciou.

    Aqui e ao contrario. Uma pergunta perdida custa uma pessoa que continua
    como "Membro 4" ate o proximo arranque, e o proximo arranque tenta de novo.
    Uma pergunta REPETIDA repete A CADA TICK, para sempre, porque o marcador
    nunca chega ao disco.
    """

    def _quebrar_o_marcador(self, monkeypatch, pasta: Path):
        """`os.open` que so falha para o marcador desta pasta.

        Patchar a funcao inteira derrubaria a propria pytest junto, e um caso
        que dependesse de permissao real de sistema de arquivos nao rodaria
        igual em duas maquinas. Mesmo idioma de `falhar_dentro_de` na Fase 1.
        """
        real = os.open

        def falso(alvo, *args, **kwargs):
            if str(pasta) in str(alvo) and PREFIXO_PERGUNTA in str(alvo):
                raise OSError("disco cheio (simulado)")
            return real(alvo, *args, **kwargs)

        monkeypatch.setattr(os, "open", falso)

    def test_marcar_devolve_FALSE_quando_o_disco_falha(
        self, tmp_path, monkeypatch
    ):
        acervo = AcervoDeIdentidades(tmp_path)
        self._quebrar_o_marcador(monkeypatch, tmp_path)

        assert acervo.marcar_pergunta("a" * 64) is False, (
            "colapsar OSError em True aqui produziria a mensagem no grupo A "
            "CADA TICK, para sempre, porque o marcador nunca chega ao disco. "
            "Na agenda o colapso e para True pela razao OPOSTA: la aviso "
            "duplicado vence aviso perdido"
        )

    def test_montar_pergunta_devolve_None_quando_o_disco_falha(
        self, tmp_path, pixels, calibracao, monkeypatch
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path)
        self._quebrar_o_marcador(monkeypatch, tmp_path)

        assert montar_pergunta(acervo, pendentes_do_acervo(acervo)) is None

    def test_a_agenda_continua_fazendo_o_CONTRARIO(self, tmp_path, monkeypatch):
        """O par que torna a assimetria visivel, e nao so afirmada aqui."""
        registro = RegistroEmDisco(tmp_path / "agenda")
        real = os.open

        def falso(alvo, *args, **kwargs):
            if str(tmp_path / "agenda") in str(alvo):
                raise OSError("disco cheio (simulado)")
            return real(alvo, *args, **kwargs)

        monkeypatch.setattr(os, "open", falso)

        assert registro.marcar("qualquer-chave") is True, (
            "a agenda manda assim mesmo, e e por isso que o acervo NAO manda: "
            "os dois tri-estados sao opostos de proposito"
        )


class TestODryRunNaoQueimaOMarcador:
    """O incidente de 2026-08-26 19:30, agora numa pasta mais cara.

    Em `--dry-run` o `montar_despachante` devolve um `Despachante` de CONSOLE,
    real e vivo — entao a simulacao PERGUNTA de verdade. Sem `simulando`, ela
    gravaria `perguntado_<chave>` na `.identidades/` COMPARTILHADA e apagaria
    PARA SEMPRE a pergunta do scanner de verdade.
    """

    def test_simulando_marca_sem_encostar_no_disco(
        self, tmp_path, pixels, calibracao
    ):
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        acervo = AcervoDeIdentidades(tmp_path, simulando=True)
        antes = retrato_da_pasta(tmp_path)

        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))

        assert pergunta is not None, (
            "o TEXTO e o produto inteiro do modo simulacao: sem ele nao ha o "
            "que imprimir no console"
        )
        assert retrato_da_pasta(tmp_path) == antes, (
            "a simulacao queimou o marcador da instancia real. E a forma "
            "exata do incidente de 2026-08-26 19:30, numa pasta que nao tem "
            "desfazer e nao tem comando de esquecer"
        )

    def test_simulando_pode_perguntar_a_vontade(self, tmp_path):
        acervo = AcervoDeIdentidades(tmp_path, simulando=True)
        chave = "a" * 64

        assert acervo.marcar_pergunta(chave) is True
        assert acervo.marcar_pergunta(chave) is True

    def test_o_scanner_de_verdade_continua_com_a_pergunta_dele(
        self, tmp_path, pixels, calibracao
    ):
        """A guarda que prova que o `simulando` protegeu alguma coisa."""
        semear(tmp_path, assinatura_da_linha(pixels, calibracao, LINHA_DA_FATIA))
        simulacao = AcervoDeIdentidades(tmp_path, simulando=True)
        montar_pergunta(simulacao, pendentes_do_acervo(simulacao))

        real = AcervoDeIdentidades(tmp_path)
        assert montar_pergunta(real, pendentes_do_acervo(real)) is not None


class TestAPerguntaNaoViraEnxurrada:
    """T-03-06. O usuario ja desligou `avisar_no_horario` do Solo Boss por
    volume, e uma pergunta por tick seria muito pior que doze por dia."""

    def test_trezentos_ticks_produzem_UMA_pergunta(
        self, tmp_path, pixels, calibracao
    ):
        """A afirmacao e que o numero NAO CRESCE com o numero de ticks.

        Herdado do molde da Fase 2 (o caso de 300 recusas): um numero magico de
        mensagens estaria medindo a fixture, e nao a cadencia.
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
        marcos = {}
        for indice in range(300):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            if indice in (9, 99, 299):
                marcos[indice] = len(despachante.perguntas)

        assert marcos == {9: 1, 99: 1, 299: 1}, (
            f"a contagem de perguntas cresceu com os ticks: {marcos}"
        )

    def test_uma_sessao_que_nao_aprende_nada_produz_ZERO_perguntas(
        self, tmp_path, pixels, calibracao
    ):
        for indice in range(4):
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path),
            despachante=despachante,
            identidades=identidades,
        )
        for indice in range(30):
            sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )

        assert despachante.perguntas == []

    def test_duas_assinaturas_no_MESMO_tick_produzem_UM_despacho(
        self, tmp_path, pixels, calibracao
    ):
        """UMA MENSAGEM PARA N ENTRADAS, e isso e decisao de produto.

        E ha um segundo ganho, que e o que torna a divida T-02-18 legivel:
        quando a mesma pessoa foi aprendida duas vezes, as duas entradas
        aparecem como duas linhas da MESMA mensagem, uma embaixo da outra, em
        vez de duas perguntas soltas que o usuario le como dois desconhecidos.
        """
        desconhecidas = (1, 3)
        for indice in range(4):
            if indice not in desconhecidas:
                semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
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

        assert len(aprendidas) == 2, "premissa: duas entradas nasceram"
        assert len(despachante.perguntas) == 1, (
            f"duas bolhas no WhatsApp em vez de uma: {despachante.perguntas}"
        )
        pergunta = despachante.perguntas[0]
        for aprendizado in aprendidas:
            assert apelido_da_chave(aprendizado.chave) in pergunta


class TestAPerguntaAtravessaOSilencioNoTRANSPORTE:
    """Um `Despachante` DE VERDADE, porque o corte mora dentro do `despachar`.

    Um despachante falso que so grava tuplas nunca exercitaria o corte, e o
    caso estaria afirmando a categoria contra si mesmo.
    """

    def _despachante_em_silencio(self, tmp_path):
        from l2scanner.notificador import Despachante

        class NotificadorMudo:
            def enviar(self, texto):
                return None

        despachante = Despachante(
            NotificadorMudo(), arquivo_outbox=tmp_path / "outbox.jsonl"
        )
        despachante.em_silencio = lambda: True
        return despachante

    def test_a_pergunta_passa_e_um_evento_NORMAL_e_cortado(self, tmp_path):
        """O par que prova que a categoria e deliberada, e nao um default.

        O outbox e a prova publica: a mensagem SILENCIADA nao entra nele, e a
        que atravessa entra.
        """
        despachante = self._despachante_em_silencio(tmp_path)

        despachante.despachar("Mostarda morreu", Categoria.NORMAL)
        despachante.despachar("Aprendi 1 pessoa: 15caec", Categoria.SEMPRE)

        assert despachante.silenciados == 1, (
            "o evento NORMAL tinha que ser cortado; sem isso o caso nao prova "
            "que havia silencio nenhum"
        )
        entregues = [
            json.loads(linha)["texto"]
            for linha in (tmp_path / "outbox.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        assert entregues == ["Aprendi 1 pessoa: 15caec"], (
            "a pergunta foi cortada pelo silencio de TvT. O marcador de D-04 e "
            "de MAO UNICA: uma pergunta silenciada e uma pergunta perdida para "
            "sempre, e TvT e justamente quando a party muda de gente"
        )


class TestAVarreduraDeArranque:
    """O caso que DEFINE a fase: as entradas que ja estao no disco.

    Elas nunca produzem `Aprendizado` (ver
    `TestOGatilhoDoAprendizadoNaoAlcancaOQueJaEstaNoDisco`), entao este e o
    unico caminho que as alcanca.
    """

    def _duas_anonimas(self, tmp_path, pixels, calibracao):
        return [
            semear(tmp_path, assinatura_da_linha(pixels, calibracao, indice))
            for indice in (LINHA_DA_FATIA, LINHA_DA_OUTRA)
        ]

    def test_duas_entradas_anonimas_produzem_UMA_mensagem_com_os_dois_apelidos(
        self, tmp_path, pixels, calibracao
    ):
        chaves = self._duas_anonimas(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))

        assert pergunta is not None
        for chave in chaves:
            assert apelido_da_chave(chave) in pergunta, pergunta
        assert "/batizar" in pergunta, "a mensagem ensina a sintaxe da resposta"
        assert pergunta.count("Aprendi") == 1, (
            f"duas mensagens coladas em vez de uma:\n{pergunta}"
        )

    def test_a_varredura_NAO_cita_posicao_nenhuma(
        self, tmp_path, pixels, calibracao
    ):
        """O desvio deliberado do criterio 1, e ele e deliberado.

        Aquelas entradas foram aprendidas numa sessao anterior, possivelmente
        por outra instancia, e nenhuma posicao de AGORA corresponde a elas.
        Inventar uma seria a primeira mentira do caminho, no recurso inteiro
        que existe para nao mentir. Quem cumpre o criterio 1 ao pe da letra e o
        gatilho do APRENDIZADO, que cita.
        """
        self._duas_anonimas(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)

        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))

        assert "linha" not in pergunta.lower(), (
            f"a varredura inventou uma posicao:\n{pergunta}"
        )

    def test_rodar_o_arranque_de_novo_nao_produz_mensagem_nenhuma(
        self, tmp_path, pixels, calibracao
    ):
        self._duas_anonimas(tmp_path, pixels, calibracao)
        primeiro = AcervoDeIdentidades(tmp_path)
        assert montar_pergunta(primeiro, pendentes_do_acervo(primeiro)) is not None

        segundo = AcervoDeIdentidades(tmp_path)
        assert montar_pergunta(segundo, pendentes_do_acervo(segundo)) is None

    def test_quem_ja_tem_nome_nunca_entra_na_varredura(
        self, tmp_path, pixels, calibracao
    ):
        chaves = self._duas_anonimas(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)
        acervo.nomear(chaves[0], "Titander")

        pergunta = montar_pergunta(acervo, pendentes_do_acervo(acervo))

        assert apelido_da_chave(chaves[0]) not in pergunta
        assert apelido_da_chave(chaves[1]) in pergunta

    def test_o_arranque_e_o_tick_dividem_o_MESMO_marcador(
        self, tmp_path, pixels, calibracao
    ):
        """Dois gatilhos, um marcador. D-04 e por ASSINATURA, e nao por evento.

        A sequencia e a de um dia de uso: o scanner sobe e pergunta pelas que
        ja estavam no disco; durante o farm ele aprende mais uma e pergunta por
        ela; e o arranque do dia seguinte nao repete nenhuma das duas.
        """
        semeadas = semear_tres_das_quatro(tmp_path, pixels, calibracao)
        identidades = carregar_na_calibracao(calibracao, tmp_path)

        # (1) O ARRANQUE pergunta pelas tres que ja estavam no disco.
        acervo = AcervoDeIdentidades(tmp_path)
        do_arranque = montar_pergunta(acervo, pendentes_do_acervo(acervo))
        assert do_arranque is not None
        for chave in semeadas:
            assert apelido_da_chave(chave) in do_arranque

        # (2) O TICK aprende a quarta e pergunta SO por ela.
        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=acervo,
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

        assert len(despachante.perguntas) == 1, "premissa: o tick perguntou"
        do_tick = despachante.perguntas[0]
        assert apelido_da_chave(aprendidas[0].chave) in do_tick
        for chave in semeadas:
            assert apelido_da_chave(chave) not in do_tick, (
                "o tick repetiu uma pergunta que o ARRANQUE ja tinha feito: os "
                "dois gatilhos nao estao dividindo o mesmo marcador"
            )

        # (3) O ARRANQUE SEGUINTE nao repete nenhuma das duas.
        novo = AcervoDeIdentidades(tmp_path)
        assert montar_pergunta(novo, pendentes_do_acervo(novo)) is None, (
            "o arranque seguinte repetiu o que o tick ja perguntou"
        )

    def test_sem_nada_anonimo_o_arranque_nao_manda_mensagem_nenhuma(
        self, tmp_path, pixels, calibracao
    ):
        """Quem so tem gente batizada nao recebe pergunta no arranque.

        E a guarda contra a varredura virar uma linha de ruido por reinicio
        para quem ja respondeu tudo.
        """
        chaves = self._duas_anonimas(tmp_path, pixels, calibracao)
        acervo = AcervoDeIdentidades(tmp_path)
        for chave, nome in zip(chaves, ("Mostarda", "Titander")):
            assert acervo.nomear(chave, nome) == "nomeado"

        assert pendentes_do_acervo(acervo) == []
        assert montar_pergunta(acervo, pendentes_do_acervo(acervo)) is None


class TestDepoisDeUmDryRunODiscoMostraAAssimetria:
    """As duas metades juntas, e elas parecem contraditorias ate serem lidas.

    `gravar` NAO e simulado: a entrada que a simulacao escreve e byte a byte a
    que o scanner de verdade escreveria, e o `O_EXCL` faz a segunda receber
    `ja_existia`. O MARCADOR e simulado, porque ele e um recurso de uma vez so
    e consumi-lo nao tem desfazer.
    """

    def _sessao_simulada(self, tmp_path, pixels, calibracao):
        identidades = carregar_na_calibracao(calibracao, tmp_path)
        despachante = DespachanteQueGrava()
        sessao = montar_sessao(
            tmp_path,
            calibracao,
            acervo=AcervoDeIdentidades(tmp_path, simulando=True),
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
        return aprendidas, despachante

    def test_a_assinatura_FICA_e_o_marcador_NAO(
        self, tmp_path, pixels, calibracao
    ):
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        aprendidas, despachante = self._sessao_simulada(
            tmp_path, pixels, calibracao
        )

        assert len(aprendidas) == 1, "premissa: a simulacao aprendeu alguem"
        chave = aprendidas[0].chave
        assert (tmp_path / f"{PREFIXO_ASSINATURA}{chave}.json").exists(), (
            "o gravar NAO e simulado, e prometer que nada e escrito na "
            ".identidades/ seria mentira"
        )
        assert not (tmp_path / f"{PREFIXO_PERGUNTA}{chave}").exists(), (
            "a simulacao queimou o marcador do scanner de verdade"
        )
        assert len(despachante.perguntas) == 1, (
            "e a simulacao IMPRIME a pergunta: e o produto inteiro do modo"
        )

    def test_na_sequencia_dry_run_e_depois_real_a_varredura_e_quem_salva(
        self, tmp_path, pixels, calibracao
    ):
        """O efeito colateral CONHECIDO e COBERTO, e nao um bug a consertar.

        Uma entrada criada por um `--dry-run` existe em disco de verdade.
        Quando o scanner real aprender a mesma pessoa, `gravar` devolve
        `ja_existia`, e o gatilho do aprendizado so pergunta em `criado` —
        entao ele NAO pergunta naquele tick. Quem salva a pergunta e a
        varredura do proximo arranque.

        Ninguem deve "consertar" isso fazendo `ja_existia` perguntar tambem.
        """
        semear_tres_das_quatro(tmp_path, pixels, calibracao)
        self._sessao_simulada(tmp_path, pixels, calibracao)

        # Agora o scanner DE VERDADE, sobre a mesma pasta e o mesmo frame.
        cal2 = Calibracao.carregar(FIXTURES / "calibracao.json")
        cal2.assinaturas = []
        identidades2 = carregar_na_calibracao(cal2, tmp_path)
        despachante = DespachanteQueGrava()
        acervo = AcervoDeIdentidades(tmp_path)
        sessao = montar_sessao(
            tmp_path,
            cal2,
            acervo=acervo,
            despachante=despachante,
            identidades=identidades2,
        )
        aprendidas = []
        for indice in range(10):
            resultado = sessao.tick(
                Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK),
                momento=1_700_000_000 + indice,
            )
            aprendidas.extend(resultado.aprendizados)

        assert [a.desfecho for a in aprendidas] == [], (
            "a entrada ja estava em disco pelo dry-run, entao ela nem chega a "
            "ser candidata: a lista viva do arranque ja a carregava"
        )
        assert despachante.perguntas == [], (
            "o tick nao pergunta neste caso, e isso e o esperado"
        )

        # E a varredura do arranque seguinte e quem pergunta.
        seguinte = AcervoDeIdentidades(tmp_path)
        pergunta = montar_pergunta(seguinte, pendentes_do_acervo(seguinte))
        assert pergunta is not None, (
            "a varredura de arranque e a rede que pega toda pergunta que nao "
            "saiu, e ela nao se importa com qual processo gravou a entrada"
        )


class TestSemDespachanteONemOArranqueNemOTickMarcam:
    def test_o_arranque_sem_despachante_nao_marca(
        self, tmp_path, pixels, calibracao
    ):
        """A trava e o `if despachante is not None` do laco, e nao o acervo.

        `montar_pergunta` MARCA. Chama-la sem despachante queimaria o marcador
        de uma pergunta que nao vai para lugar nenhum, e o marcador e para
        sempre.
        """
        import inspect

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.laco_principal)
        arvore = ast.parse(fonte)
        chamadas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == "montar_pergunta"
        ]
        assert chamadas, "laco_principal nao varre o acervo no arranque"

        guardas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.If)
            and any(
                isinstance(dentro, ast.Call)
                and isinstance(dentro.func, ast.Name)
                and dentro.func.id == "montar_pergunta"
                for dentro in ast.walk(no)
            )
            and "despachante" in ast.dump(no.test)
        ]
        assert guardas, (
            "a varredura de arranque nao esta atras de um `if despachante`: "
            "ela queimaria o marcador de uma pergunta que nao vai para lugar "
            "nenhum, e quem roda sem .env ficaria com a pessoa como Membro N "
            "ate alguem apagar um arquivo a mao"
        )


class TestOsDoisLacosPassamOAcervo:
    """A familia de defeito que este projeto ja pagou DUAS vezes.

    O marcador `comando_<id>` da `.agenda/` e COMPARTILHADO: exatamente uma
    instancia obedece cada comando. Se o laco da agenda receber a mensagem
    primeiro e nao tiver acervo, ele consome o marcador, responde "nao consigo
    mexer nas identidades agora" e o batismo do usuario e PERDIDO.

    LE O FONTE, e nao o comportamento, pela mesma razao do portao irmao em
    `tests/test_janela_sob_demanda.py`: os lacos tem `while True` e captura de
    tela dentro.
    """

    def _chamada(self, nome_do_laco) -> ast.Call:
        import inspect

        from l2scanner import __main__ as principal

        arvore = ast.parse(inspect.getsource(getattr(principal, nome_do_laco)))
        for no in ast.walk(arvore):
            if (
                isinstance(no, ast.Call)
                and isinstance(no.func, ast.Name)
                and no.func.id == "atender_comandos"
            ):
                return no
        raise AssertionError(f"{nome_do_laco} nao chama atender_comandos")

    @pytest.mark.parametrize("laco", ["laco_principal", "laco_da_agenda"])
    def test_os_dois_passam_acervo(self, laco):
        nomeados = {palavra.arg for palavra in self._chamada(laco).keywords}
        assert "acervo" in nomeados, (
            f"{laco} nao passa `acervo` para atender_comandos: se ele obedecer "
            "o comando primeiro, o batismo do usuario e consumido e perdido"
        )

    @pytest.mark.parametrize("laco", ["laco_principal", "laco_da_agenda"])
    def test_o_que_e_passado_e_a_VARIAVEL_e_nao_um_None(self, laco):
        """Guarda contra o conserto preguicoso.

        `acervo=None` satisfaria o teste acima e deixaria o defeito inteiro de
        pe: a chamada existe, o comando responde, e a resposta e sempre "nao
        consigo mexer nas identidades agora".
        """
        chamada = self._chamada(laco)
        passado = next(p.value for p in chamada.keywords if p.arg == "acervo")
        assert isinstance(passado, ast.Name), (
            f"{laco} passa um literal para `acervo` em vez do acervo de verdade"
        )

    def test_o_laco_principal_passa_tambem_a_lista_viva(self):
        """So o principal: no laco da agenda nao existe tela."""
        chamada = self._chamada("laco_principal")
        nomeados = {palavra.arg for palavra in chamada.keywords}
        assert "assinaturas_vivas" in nomeados, (
            "sem a lista viva o nome so vale no proximo arranque, e o usuario "
            "batiza de novo achando que falhou (D-08)"
        )


class TestOsDoisAcervosNascemComSimulando:
    """O `--dry-run` alcanca os DOIS lacos, entao os dois construtores pagam."""

    @pytest.mark.parametrize("laco", ["laco_principal", "laco_da_agenda"])
    def test_o_acervo_e_construido_com_simulando(self, laco):
        import inspect

        from l2scanner import __main__ as principal

        arvore = ast.parse(inspect.getsource(getattr(principal, laco)))
        construcoes = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == "AcervoDeIdentidades"
        ]
        assert construcoes, f"{laco} nao constroi AcervoDeIdentidades"
        for construcao in construcoes:
            nomeados = {palavra.arg for palavra in construcao.keywords}
            assert "simulando" in nomeados, (
                f"o AcervoDeIdentidades de {laco} nasce sem `simulando`: um "
                "--dry-run ao lado do scanner de verdade queimaria as "
                "perguntas dele para sempre"
            )


class TestAFraseDoDryRunEVERDADE:
    """Ela ja foi consertada uma vez neste projeto. Nao piorar de novo.

    A tentacao e escrever que nada e gravado tambem na `.identidades/`, e isso
    e FALSO: o `Aprendiz` roda em `--dry-run` e `acervo.gravar` escreve
    `assinatura_*` na pasta compartilhada. Aquela frase reintroduziria
    exatamente a promessa mentirosa que este bloco existe para consertar.
    """

    def _frase(self, caplog):
        import argparse
        import logging

        from l2scanner.__main__ import montar_despachante

        args = argparse.Namespace(dry_run=True)
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            montar_despachante(args)
        return "\n".join(r.getMessage() for r in caplog.records)

    def test_a_frase_fala_de_PERGUNTA(self, caplog):
        frase = self._frase(caplog)
        assert "pergunta" in frase.lower(), (
            f"o --dry-run nao conta o que o `simulando` do acervo garante:\n{frase}"
        )

    def test_a_frase_NAO_promete_que_nada_e_gravado_na_identidades(self, caplog):
        frase = self._frase(caplog).lower()
        for mentira in (
            "nada e gravado em .identidades",
            "nada e gravado na .identidades",
            "nada e escrito em .identidades",
        ):
            assert mentira not in frase, (
                f"a frase promete o que nao cumpre: o gravar NAO e simulado.\n{frase}"
            )
