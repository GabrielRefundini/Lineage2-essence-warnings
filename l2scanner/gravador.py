"""Gravador de sessao — a peca que destrava todo o resto.

Por que isto existe antes de qualquer logica de deteccao:

O evento que o scanner existe para pegar (alguem da PT morrer) e raro e nao se
reproduz sob demanda. Sem uma gravacao real, cada ajuste de limiar seria um
chute testado contra um jogo ao vivo esperando alguem morrer. Com gravacao, o
usuario farma uma hora com `--record` ligado, banca uma morte de verdade, e
aquela sessao vira ao mesmo tempo a base de calibracao e um teste de regressao
permanente.

Formato: PNG por frame (sem perda — compressao com perda destruiria justamente
as bordas de barra que precisamos medir) mais um JSONL com uma linha por frame.

**Escrita confirmada e o portao das TRES saidas.** O contador, a linha do
`observacoes.jsonl` e o resumo final da sessao ficam todos atras do retorno do
`cv2.imwrite`. Consertar so o contador deixaria o indice citando arquivos que
nao existem — que e a mesma mentira, um nivel abaixo. Uma gravacao serve para
sustentar evidencia; uma gravacao que mente sobre si mesma e pior que nenhuma.

**Modo janela completa (`fonte_completa`).** Por padrao o PNG gravado e
`frame.pixels`: o recorte da party window. Isso basta para regressao de morte,
e nao basta para nada que ainda nao foi calibrado — o painel do World Exchange,
por exemplo, nunca entra num PNG assim. E ha um ovo-e-galinha: a regiao do
mercado so sera conhecida DEPOIS da calibracao, e a calibracao roda sobre
frames GRAVADOS. Gravar a janela inteira quebra o ciclo, porque o calibrador
recorta qualquer regiao depois.

Custo medido em `recordings/inv3/f000_JANELA.png`: 1720x1392 = **3,5 MB por
PNG**, ou cerca de **210 MB por minuto** a 1 Hz. Por isso o modo e uma flag
propria e nao o padrao, e por isso o roteiro do spike prescreve sessoes de 30
a 60 segundos.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .frames import Frame

if TYPE_CHECKING:  # pragma: no cover - so para o verificador de tipos
    from collections.abc import Callable

    import numpy as np

log = logging.getLogger(__name__)

# A cada quantas falhas ACUMULADAS o erro volta a ser gritado.
#
# A gravacao roda a ~1 Hz durante o farm. Com o disco cheio TODA volta falha, e
# um `log.error` por volta viraria milhares de linhas iguais que enterram o
# resto do log — inclusive os alertas de party, que sao o produto. A primeira
# falha grita (e a que o usuario precisa ver), depois a cada dez. O total exato
# nunca se perde: o resumo final o reporta.
FALHAS_ENTRE_GRITOS = 10


class Gravador:
    """Grava frames e metadados de uma sessao em disco."""

    def __init__(
        self,
        pasta_base: Path,
        rotulo: str | None = None,
        fonte_completa: "Callable[[], np.ndarray | None] | None" = None,
    ) -> None:
        carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
        nome = f"{carimbo}-{rotulo}" if rotulo else carimbo
        self.pasta = pasta_base / nome
        self.pasta.mkdir(parents=True, exist_ok=True)

        self._arquivo_meta = (self.pasta / "observacoes.jsonl").open(
            "w", encoding="utf-8"
        )
        self.frames_gravados = 0
        self.falhas_de_gravacao = 0
        self._fonte_completa = fonte_completa

    def gravar(self, frame: Frame, momento: float) -> bool:
        """Grava UM frame. Devolve se a escrita foi confirmada no disco.

        Nunca levanta. `Sessao.tick` chama este metodo ANTES do seu proprio
        try/except, e o laco principal nao envolve o tick em try/except
        nenhum — uma excecao aqui derrubaria o scanner inteiro por causa de
        disco cheio, levando os alertas de morte da party junto. A doutrina da
        casa e degradar a feature, nunca o produto.

        Medido nesta maquina (mesmo levantamento que sustenta
        `calibrar._gravar_conferencia`): destino somente-leitura, destino
        ocupado por um diretorio e pasta inexistente devolvem `False`, e
        nenhum dos tres levanta excecao — por isso ninguem percebia.
        """
        caminho = self.pasta / f"frame_{frame.indice:06d}.png"

        imagem = frame.pixels
        if self._fonte_completa is not None:
            completa = self._fonte_completa()
            if completa is None:
                # NUNCA cair de volta em `frame.pixels`. Gravar o recorte
                # errado em silencio gastaria as sessoes do usuario — o
                # recurso escasso desta fase, porque so ele pode grava-las — e
                # ele so descobriria o engano depois de gastar todas.
                self._contabilizar_falha(caminho, "a janela nao produziu frame")
                return False
            imagem = completa

        if not self._escrever(caminho, imagem):
            self._contabilizar_falha(caminho, "o cv2.imwrite nao confirmou a escrita")
            return False

        linha = {
            "indice": frame.indice,
            "momento": momento,
            "saude": frame.saude.value,
            "arquivo": caminho.name,
        }
        # MESMO caminho de falha do imwrite, e pelo mesmo motivo. Esta metade
        # estava crua: um `OSError(28)` aqui subia por `Sessao.tick` (que chama
        # `gravar` ANTES do proprio try/except) e pelo laco principal (que nao
        # tem try nenhum) ate derrubar o scanner — disco cheio matando os
        # alertas de morte da party, que e exatamente o que a docstring acima
        # promete que nao acontece.
        try:
            self._arquivo_meta.write(json.dumps(linha, ensure_ascii=False) + "\n")
            self._arquivo_meta.flush()  # sobrevive a um Ctrl+C ou queda de energia
        except Exception:  # noqa: BLE001
            # O PNG ja esta no disco e o indice nao vai cita-lo. Um PNG orfao
            # faz a conferencia 4 de `tools/conferir_gravacoes_do_spike.py`
            # (linhas do JSONL == PNGs no disco) condenar a sessao INTEIRA por
            # causa de um solucar de metadado — e as sessoes do spike sao
            # irrecuperaveis. Entao ele sai junto: o disco e o indice nunca
            # discordam.
            self._descartar(caminho)
            self._contabilizar_falha(caminho, "o indice nao aceitou a linha do frame")
            return False

        self.frames_gravados += 1
        return True

    @staticmethod
    def _descartar(caminho: Path) -> None:
        """Apaga o PNG que ficou sem linha no indice. Nunca levanta.

        Se ate o `unlink` falhar (o mesmo disco doente que derrubou a linha),
        nao ha nada melhor a fazer aqui: o frame ja esta contabilizado como
        falha e a conferencia do spike vai apontar a divergencia com o nome da
        pasta. Levantar por causa da limpeza seria repetir o defeito que este
        bloco acabou de fechar.
        """
        try:
            caminho.unlink(missing_ok=True)
        except OSError:
            pass

    @staticmethod
    def _escrever(caminho: Path, imagem: "np.ndarray") -> bool:
        import cv2

        # O try/except existe ALEM do retorno booleano para que o `False`
        # documentado e uma excecao inesperada caiam no MESMO caminho de
        # falha. Tratar so um dos dois deixaria a outra metade calada, que e
        # exatamente o defeito que este modulo veio consertar.
        try:
            return bool(cv2.imwrite(str(caminho), imagem))
        except Exception:  # noqa: BLE001
            return False

    def _contabilizar_falha(self, caminho: Path, motivo: str) -> None:
        """A falha e visivel AQUI, no modulo que possui a verdade do disco.

        Logar em `Sessao.tick` obrigaria o chamador a saber o caminho do
        arquivo e a manter a contagem — e deixaria `sessao.py` responsavel por
        uma verdade que nao e dele.
        """
        self.falhas_de_gravacao += 1
        gritar = (
            self.falhas_de_gravacao == 1
            or self.falhas_de_gravacao % FALHAS_ENTRE_GRITOS == 0
        )
        registrar = log.error if gritar else log.debug
        registrar(
            "Nao consegui gravar %s (%s) — o frame NAO foi contado. "
            "Falhas de gravacao ate agora: %d",
            caminho,
            motivo,
            self.falhas_de_gravacao,
        )

    def fechar(self) -> None:
        self._arquivo_meta.close()

    def __enter__(self) -> "Gravador":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()
