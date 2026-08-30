"""Reconhecimento do anuncio de nascimento de boss, no chat e no alvo.

O jogo nao oferece uma API de spawn para o scanner (e o projeto nao le memoria
nem trafego). Este modulo recebe apenas o texto que o OCR conseguiu enxergar em
duas regioes que o usuario calibra: o chat e o nome do alvo.

O QUE MUDOU, E POR QUE. Ate a Fase 1 bastava ver o nome raro `Tiat` em qualquer
um dos dois recortes. O chat geral do usuario e MOVIMENTADO — o print de
2026-08-30 mostra varias conversas simultaneas — e um party-mate perguntando
`tiat ja nasceu?` disparava o alerta. Agora o gatilho e a FRASE DO SERVIDOR
inteira, e a identidade do boss vem do `config.toml`:

    Tiat North [Lv. 60] has spawned!

FROUXO DE PROPOSITO, e a assimetria e a decisao mais importante do arquivo.
O `!` final e OPCIONAL, os colchetes sao OPCIONAIS, a parte fixa
(`Lv`, `has spawned`) passa pela mesma folga de OCR que o nome, o nivel aceita
letra no lugar de digito, e o padrao NAO e ancorado no inicio da linha. A razao
e que os dois erros nao custam a mesma coisa:

- Um portao frouxo demais custa uma mensagem inutil, que um humano le e
  descarta em dois segundos.
- Um portao estrito demais custa um falso NEGATIVO SILENCIOSO: o aviso
  simplesmente nao sai, e ninguem percebe que nao saiu (R-02, T-01-05).

Pontuacao e o que o OCR mais perde, e a linha do servidor vem com ICONE
PROPRIO — cujo OCR produz lixo no comeco da linha. Exigir o `!` ou ancorar em
`^` trocaria o falso positivo de hoje pelo modo de falha pior.

O NIVEL ENTRA NO PADRAO E SAI DA DECISAO (D-11). `[Lv. NN]` existe para provar
que a linha veio do SERVIDOR e nao de alguem digitando; o numero em si e casado
e descartado. Nao e conferido contra o config e nao vai para a mensagem — se o
servidor mudar o nivel do Tiat, nada quebra e ninguem edita config. (O ROADMAP
supunha `[Lv. 80]`; o print real mostra 60. E exatamente por isso.)

AS CHAVES DE CALIBRACAO CONTINUAM `tiat_chat` E `tiat_alvo`, e isso e
deliberado. `Calibracao.de_dict` as le com `dados.get(...)` e devolve `None`
quando faltam: renomea-las desligaria a vigilancia de boss, EM SILENCIO, em
todo `calibration.json` que ja existe na maquina do usuario. Degradacao
silenciosa e a familia de defeito que este projeto mais paga. As regioes sao do
CHAT e do ALVO — o nome da chave e historico, nao uma promessa sobre qual mob e
vigiado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class BossInvalido(Exception):
    """Um bloco `[[boss]]` do config.toml nao serve, e o arranque para.

    Mora aqui, e nao em `config.py`, pela direcao das importacoes ja fixa no
    pacote: este modulo importa SO stdlib, entao `config.py` pode importar dele
    sem fechar ciclo.
    """


@dataclass(frozen=True)
class Boss:
    """Um mob vigiado, exatamente como o usuario o escreveu no `config.toml`.

    `respawn_horas_min` e `respawn_horas_max` sao LIDOS e VALIDADOS aqui e
    IGNORADOS nesta fase — a Fase 2 os usa para calcular a janela. Moram no
    esquema desde ja para o usuario nao precisar editar o mesmo arquivo duas
    vezes, que e a mesma tecnica que `silenciar_minutos` usou na Fase 6 e que
    `tests/test_agenda.py::test_as_duracoes_de_silencio_estao_no_esquema_para_a_fase_7`
    guarda por escrito.

    A regra do servidor que alimenta os dois campos: 6 horas fixas mais 0 a 2
    horas aleatorias, contadas a partir da MORTE.
    """

    nome: str
    respawn_horas_min: float
    respawn_horas_max: float


# A folga de OCR, medida na fonte fina do jogo: para cada letra minuscula, os
# caracteres que o OCR devolve no lugar dela. Substitui o `_TIAT` da v1, que
# cobria so I/A/T e so o nome — a parte fixa da frase (`Lv`, `has spawned`)
# degrada exatamente do mesmo jeito e precisa da mesma tolerancia (D-09).
_FOLGA_DE_OCR: dict[str, str] = {
    "a": "aA4@",
    "b": "bB8",
    "e": "eE3",
    "g": "gG69",
    "i": "iI1l|",
    "l": "lL1I|",
    "o": "oO0Q",
    "s": "sS5$",
    "t": "tT7+",
    "z": "zZ2",
}

# A classe de caracteres do NIVEL. Digitos mais as letras que o OCR troca por
# eles: `OoQD` por zero, `lI|i` por um, `SsZz` por dois/cinco, `Bb` por oito,
# `gG` por nove, `Aa` por quatro.
#
# ISTO NAO E EXCESSO DE ZELO, e `\d+` no lugar disto seria um defeito: o
# criterio 3 da fase exige que `T1a7 Nor7h [Lv. 8O] has spawned!` produza o
# mesmo alerta, e ali o segundo caractere do nivel e a LETRA O. Um `\d+`
# reprovaria naquele criterio — e reprovaria em silencio, que e o modo de falha
# caro (T-01-05).
_DIGITO_COM_FOLGA = "0123456789OoQDlI|iSsZzBbgGAa"


def _classe(caracteres: str) -> str:
    """Uma classe de regex com cada caractere escapado, um por um."""
    return "[" + "".join(re.escape(c) for c in caracteres) + "]"


def _com_folga_de_ocr(texto: str) -> str:
    """Monta a fonte de uma regex que casa `texto` como o OCR o entrega.

    Percorre CARACTERE A CARACTERE: espaco vira `\\s+`, letra da tabela vira
    uma classe montada com `re.escape`, e qualquer outro caractere vira
    `re.escape(caractere)`.

    ESTA FUNCAO E A MITIGACAO DE T-01-03, e nao so conveniencia. O `nome` do
    boss vem do `config.toml` — texto escrito a mao que vira fonte de expressao
    regular. Porque nenhum trecho dele chega CRU ao `re.compile`, um bloco
    declarando `nome = "Tiat.*"` produz um padrao que casa aquele nome
    literalmente, e nao um curinga que dispararia com qualquer linha do chat.
    Um nome com `(` tambem nao levanta `re.error` no arranque.

    Quem for "simplificar" isto para uma concatenacao de `nome` com a parte
    fixa precisa esbarrar nesta razao antes.
    """
    partes = []
    for caractere in texto:
        if caractere.isspace():
            partes.append(r"\s+")
            continue
        alternativas = _FOLGA_DE_OCR.get(caractere.lower())
        if alternativas:
            partes.append(_classe(alternativas))
        else:
            partes.append(re.escape(caractere))
    return "".join(partes)


def padrao_do_nome(nome: str) -> re.Pattern:
    """So o nome, para o recorte do ALVO — ali nao existe frase nenhuma."""
    return re.compile(_com_folga_de_ocr(nome), re.IGNORECASE)


def padrao_do_anuncio(nome: str) -> re.Pattern:
    """A frase inteira do servidor: `<nome> [Lv. NN] has spawned!`.

    Montada por concatenacao, com folga de OCR nos DOIS lados (o nome e a parte
    fixa) e com toda a pontuacao opcional — ver a docstring do modulo para a
    assimetria de custo que decide isso.

    O NIVEL E OBRIGATORIO e o resto e opcional, e essa e a linha inteira da
    defesa contra RECO-01: `Fulano: tiat ja nasceu?` nao tem `Lv <numero>`
    seguido de `has spawned` na MESMA linha, e por isso nao dispara.
    """
    fonte = (
        _com_folga_de_ocr(nome)
        + r"\s*"
        # Colchete OPCIONAL: o OCR perde delimitador com a mesma facilidade
        # com que perde pontuacao. Aceita `[`, `(` e `{` porque sao as tres
        # leituras possiveis do mesmo desenho numa fonte fina.
        + r"[\[\(\{]?"
        + r"\s*"
        + _com_folga_de_ocr("Lv")
        + r"\s*\.?\s*"
        + _classe(_DIGITO_COM_FOLGA)
        + r"{1,3}"
        + r"\s*"
        + r"[\]\)\}]?"
        + r"\s*"
        + _com_folga_de_ocr("has spawned")
        + r"\s*"
        + r"!?"
    )
    # SEM `^`. Ancorar seria a mitigacao tentadora contra a linha digitada por
    # um jogador com prefixo de remetente — mas a linha do servidor vem com
    # icone proprio, e o OCR de um icone produz lixo no comeco da linha.
    # Ancorar trocaria um falso positivo barato por um falso negativo
    # silencioso, que e exatamente o erro que R-02 nomeia.
    return re.compile(fonte, re.IGNORECASE)


class OrigemDoAviso(Enum):
    CHAT = "chat"
    ALVO = "alvo"
    CHAT_E_ALVO = "chat_e_alvo"


@dataclass(frozen=True)
class AvisoDeBoss:
    """Um nascimento novo, antes de ser entregue ao WhatsApp."""

    boss: str
    origem: OrigemDoAviso

    @property
    def texto(self) -> str:
        """A mensagem COMECA pelo nome do boss (D-14).

        O nome primeiro porque e a informacao que decide para onde a party se
        desloca; o `TIAT DETECTADO —` da v1 enterrava isso atras de um rotulo.
        """
        # O nome interpolado e SEMPRE o do `[[boss]]`, nunca o texto que o OCR
        # leu. E o que garante que nada escrito por um jogador no chat do jogo
        # atravesse para o grupo de WhatsApp (T-01-04): o texto lido serve so
        # como predicado booleano e e descartado.
        if self.origem is OrigemDoAviso.CHAT:
            return f"{self.boss} nasceu! (visto no chat do jogo)"
        if self.origem is OrigemDoAviso.ALVO:
            return f"{self.boss} nasceu! (seu alvo virou {self.boss})"
        return (
            f"{self.boss} nasceu! (visto no chat do jogo e seu alvo virou "
            f"{self.boss})"
        )


class VigiaDeBosses:
    """Transforma aparicoes de boss em um unico aviso por ocorrencia visual.

    A mesma linha fica no chat por varios frames e o alvo normalmente fica
    selecionado por minutos. Portanto, enquanto qualquer sinal continuar
    presente, nao ha segundo aviso. Duas leituras limpas consecutivas rearmam
    o vigia para o proximo spawn/novo target; uma falha isolada de OCR nao
    basta para rearmar e transformar o mesmo boss em spam.

    O REARME E POR BOSS, e nao um flag global — e esta e a mudanca de FORMA que
    o criterio 4 da Fase 1 exige. Com um flag unico, um `Tiat South` alvejado
    durante os minutos em que o anuncio de `Tiat North` ainda persiste no
    recorte do chat seria engolido: o vigia estaria desarmado por causa de
    OUTRO mob.
    """

    def __init__(
        self,
        ler_texto,
        bosses=(),
        leituras_limpas_para_rearmar: int = 2,
        segundos_entre_leituras: float = 2.0,
    ) -> None:
        if leituras_limpas_para_rearmar < 1:
            raise ValueError("leituras_limpas_para_rearmar deve ser >= 1")
        if segundos_entre_leituras <= 0:
            raise ValueError("segundos_entre_leituras deve ser > 0")
        self._ler_texto = ler_texto
        self._limpas_para_rearmar = leituras_limpas_para_rearmar
        self._intervalo = segundos_entre_leituras
        self._ultima_leitura: datetime | None = None

        # OS PADROES SAO PRE-COMPILADOS AQUI, e nao por tick. Nao e
        # micro-otimizacao: e o que garante que um `nome` malformado exploda no
        # ARRANQUE, com o usuario olhando para o console, e nao as 3h da manha
        # no meio do farm.
        self._bosses: list[tuple[str, re.Pattern, re.Pattern]] = []
        for boss in bosses:
            nome = str(getattr(boss, "nome", boss))
            self._bosses.append(
                (nome, padrao_do_anuncio(nome), padrao_do_nome(nome))
            )

        self._armado: dict[str, bool] = {n: True for n, _, _ in self._bosses}
        self._limpas: dict[str, int] = {n: 0 for n, _, _ in self._bosses}

    def _ler(self, pixels) -> str | None:
        if pixels is None:
            return None
        try:
            return self._ler_texto(pixels)
        except Exception:
            # OCR e complementar ao rastreador: jamais pode derrubar o tick.
            return None

    def avaliar(
        self, pixels_do_chat, pixels_do_alvo, agora: datetime
    ) -> list[AvisoDeBoss]:
        """Os avisos deste tick, na ordem em que os bosses estao no config.

        DEVOLVE UMA LISTA, e nao um aviso unico, porque o criterio 4 exige que
        chat e alvo mostrando bosses DIFERENTES no mesmo tick produzam DOIS
        alertas — e um retorno unico nao tem como carregar dois. O intervalo
        minimo entre leituras devolve `[]`, nunca `None`.

        A ordem segue a ordem do config para o teste poder afirmar sem ordenar.
        """
        if (
            self._ultima_leitura is not None
            and (agora - self._ultima_leitura).total_seconds() < self._intervalo
        ):
            return []
        self._ultima_leitura = agora

        # Os dois recortes sao lidos UMA vez por tick, antes do laco dos
        # bosses: com N bosses configurados, ler por boss custaria N OCRs por
        # tick sobre os mesmos pixels.
        texto_do_chat = self._ler(pixels_do_chat)
        texto_do_alvo = self._ler(pixels_do_alvo)

        # LINHA A LINHA, e nunca sobre o blob inteiro do OCR (T-01-02). Sobre o
        # blob, o `\s+` da parte fixa costuraria o fim de uma linha escrita por
        # um jogador com o comeco da linha de outro, produzindo um casamento
        # que nenhuma linha real contem.
        linhas_do_chat = (texto_do_chat or "").splitlines()

        avisos: list[AvisoDeBoss] = []
        for nome, anuncio, so_o_nome in self._bosses:
            no_chat = any(anuncio.search(linha) for linha in linhas_do_chat)
            no_alvo = bool(texto_do_alvo and so_o_nome.search(texto_do_alvo))

            if no_chat or no_alvo:
                self._limpas[nome] = 0
                if not self._armado[nome]:
                    continue
                self._armado[nome] = False
                if no_chat and no_alvo:
                    origem = OrigemDoAviso.CHAT_E_ALVO
                elif no_chat:
                    origem = OrigemDoAviso.CHAT
                else:
                    origem = OrigemDoAviso.ALVO
                avisos.append(AvisoDeBoss(boss=nome, origem=origem))
                continue

            self._limpas[nome] += 1
            if self._limpas[nome] >= self._limpas_para_rearmar:
                self._armado[nome] = True

        return avisos
