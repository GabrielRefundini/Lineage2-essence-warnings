"""Os SEIS numeros da secao `[renda]`, e o arranque recusando cada um mal escrito.

ERAM CINCO ATE 2026-09-04, e o sexto tem casa diferente dos outros: os cinco
primeiros governam a CONTA (o que e "agora", o que e cegueira, o que e digito
ganho, os dois pisos), e `tamanho_do_pack_de_adena` governa uma META DO USUARIO —
de quanto em quanto ele quer ser avisado. As tres regras de leitura e o portao de
booleano valem igual para os seis, e por isso o sexto entrou aqui em vez de
inventar secao propria.

O QUE ESTE ARQUIVO EXISTE PARA IMPEDIR
======================================
**Um limiar torto entrando calado e mudando toda taxa da noite.**

Os cinco numeros desta secao governam a conta inteira da Fase 2: o que e "agora"
(a janela movel), o que e cegueira (o limiar de lacuna), o que e digito ganho ou
perdido (o fator de salto), e os dois pisos abaixo dos quais a resposta e o
motivo e nunca um numero. Um deles escrito como `true` viraria, em silencio, o
inteiro `1` — e `fator_de_salto_da_adena = 1` recusaria TODA amostra em que a
adena mudou. Quem escreveu `true` nao quis dizer isso.

AS TRES REGRAS DE LEITURA, E ELAS VEM DE UM PRECEDENTE LITERAL
==============================================================
O molde e `ler_ajustes_do_aprendiz` (`l2scanner/config.py:1516`), cuja secao
`[identidade]` o usuario **nunca preencheu** — ela esta comentada no
`config.toml` ate hoje. Um leitor que exigisse a secao teria derrubado o scanner
no dia em que nasceu. Daí:

1. `config.toml` **ausente** nao e erro: devolve os seis defaults.
2. Secao `[renda]` **ausente** nao e erro: devolve os seis defaults.
3. Chave ausente devolve o default **DAQUELA** chave, e nao o conjunto inteiro.
   Quem escreveu so `lacuna_maxima_segundos` nao esta pedindo para os outros
   quatro voltarem ao padrao.

E a quarta, que e o contrario das tres: `config.toml` PRESENTE e mal formado e
erro de ARRANQUE, alto, com a chave nomeada e o exemplo pronto para copiar.

A SETA APONTA CASCA -> PURO, E NUNCA O CONTRARIO
================================================
`config.py` e a casca: ela sabe o que e um arquivo TOML e onde os defaults
moram. `renda_conta.py` e o modulo puro: ele recebe os cinco por parametro
somente-nomeado e **sem valor de fabrica**, e nao sabe que o `config.toml`
existe. Quem junta os dois e a Fase 3. Ha teste aqui prendendo as duas metades
disso.

ESTE ARQUIVO NAO PULA POR NADA
==============================
Todo caminho de disco mora em `tmp_path`. Um `skip` aqui e falha, e nao
configuracao de maquina.
"""

from __future__ import annotations

import inspect

import pytest

from l2scanner import renda_conta
from l2scanner.config import (
    CHAVE_DA_JANELA_MOVEL,
    CHAVE_DA_LACUNA,
    CHAVE_DO_FATOR_DE_SALTO,
    CHAVE_DO_PISO_DA_JANELA,
    CHAVE_DO_PISO_DE_AMOSTRAS,
    CHAVE_DO_TAMANHO_DO_PACK,
    SECAO_DA_RENDA,
    AgendaInvalida,
    AjustesDaRenda,
    ler_ajustes_da_renda,
)

# As chaves, derivadas do modulo e nunca reescritas a mao. A tupla se chamava
# `AS_CINCO` ate 2026-09-04 e o comentario dizia *"uma lista escrita aqui
# envelheceria em silencio no dia em que uma sexta nascesse"* — a sexta nasceu, e
# como os nomes vem do modulo o unico ajuste foi acrescentar a linha.
AS_SEIS = (
    CHAVE_DA_JANELA_MOVEL,
    CHAVE_DA_LACUNA,
    CHAVE_DO_FATOR_DE_SALTO,
    CHAVE_DO_PISO_DE_AMOSTRAS,
    CHAVE_DO_PISO_DA_JANELA,
    CHAVE_DO_TAMANHO_DO_PACK,
)


def escrever(tmp_path, texto: str):
    alvo = tmp_path / "config.toml"
    alvo.write_text(texto, encoding="utf-8")
    return alvo


class TestOsTresEstadosLegITIMOS:
    """Arquivo ausente, secao ausente e chave ausente. Nenhum dos tres e erro."""

    def test_ARQUIVO_AUSENTE_DEVOLVE_OS_SEIS_DEFAULTS(self, tmp_path):
        ajustes = ler_ajustes_da_renda(tmp_path / "nunca-existiu.toml")
        assert ajustes == AjustesDaRenda()

    def test_O_PACK_PADRAO_E_O_DE_CINCO_MILHOES_QUE_O_USUARIO_PEDIU(
        self, tmp_path
    ):
        """`5.000.000` e a escala em que o proprio jogo fala de adena.

        O usuario pediu *"o prox pack de adena de +5kk"*, e a coluna do World
        Exchange se chama `5 mln increment`. O default nao e escolha nossa; o
        que e escolha e o usuario poder muda-lo, e por isso ele e chave e nao
        constante.
        """
        assert (
            ler_ajustes_da_renda(
                tmp_path / "nunca-existiu.toml"
            ).tamanho_do_pack_de_adena
            == 5_000_000
        )

    def test_SECAO_AUSENTE_NUM_ARQUIVO_REAL_DEVOLVE_OS_SEIS_DEFAULTS(
        self, tmp_path
    ):
        """O precedente e literal: a `[identidade]` nunca foi preenchida."""
        caminho = escrever(
            tmp_path,
            "[discord]\nguild = 1\ncanais = [2]\n",
        )
        assert ler_ajustes_da_renda(caminho) == AjustesDaRenda()

    def test_UMA_CHAVE_ESCRITA_NAO_ARRASTA_AS_OUTRAS_CINCO(self, tmp_path):
        """Chave ausente devolve o default DAQUELA chave, e nao o conjunto."""
        padroes = AjustesDaRenda()
        caminho = escrever(
            tmp_path, f"[{SECAO_DA_RENDA}]\n{CHAVE_DA_LACUNA} = 45\n"
        )

        ajustes = ler_ajustes_da_renda(caminho)

        assert ajustes.lacuna_maxima_segundos == 45
        assert ajustes.janela_movel_minutos == padroes.janela_movel_minutos
        assert ajustes.fator_de_salto_da_adena == padroes.fator_de_salto_da_adena
        assert (
            ajustes.amostras_minimas_para_taxa
            == padroes.amostras_minimas_para_taxa
        )
        assert (
            ajustes.janela_minima_para_taxa_segundos
            == padroes.janela_minima_para_taxa_segundos
        )
        assert (
            ajustes.tamanho_do_pack_de_adena == padroes.tamanho_do_pack_de_adena
        )

    def test_AS_SEIS_CHAVES_ESCRITAS_CHEGAM_TODAS(self, tmp_path):
        caminho = escrever(
            tmp_path,
            f"[{SECAO_DA_RENDA}]\n"
            f"{CHAVE_DA_JANELA_MOVEL} = 5\n"
            f"{CHAVE_DA_LACUNA} = 30\n"
            f"{CHAVE_DO_FATOR_DE_SALTO} = 20\n"
            f"{CHAVE_DO_PISO_DE_AMOSTRAS} = 4\n"
            f"{CHAVE_DO_PISO_DA_JANELA} = 300\n"
            f"{CHAVE_DO_TAMANHO_DO_PACK} = 10000000\n",
        )

        assert ler_ajustes_da_renda(caminho) == AjustesDaRenda(
            janela_movel_minutos=5,
            lacuna_maxima_segundos=30,
            fator_de_salto_da_adena=20,
            amostras_minimas_para_taxa=4,
            janela_minima_para_taxa_segundos=300,
            tamanho_do_pack_de_adena=10_000_000,
        )

    def test_A_SEXTA_CHAVE_APARECE_NO_EXEMPLO_QUE_A_RECUSA_MOSTRA(
        self, tmp_path
    ):
        """O exemplo e a coisa que o usuario COPIA, e ele tem de estar inteiro.

        Uma mensagem que mostra cinco das seis chaves ensina o usuario a apagar
        a sexta. O exemplo e escrito UMA vez no fonte e viaja em toda recusa da
        secao; este teste prende as duas pontas.
        """
        caminho = escrever(
            tmp_path, f"[{SECAO_DA_RENDA}]\n{CHAVE_DA_LACUNA} = true\n"
        )

        with pytest.raises(AgendaInvalida) as erro:
            ler_ajustes_da_renda(caminho)

        for chave in AS_SEIS:
            assert chave in str(erro.value), (
                f"a chave {chave} sumiu do exemplo que a recusa mostra. Saiu: "
                f"{erro.value}"
            )


class TestOBooleanoNaoPassaPorInteiro:
    """`True` E um `int` de valor 1 em Python, e essa armadilha e classica."""

    @pytest.mark.parametrize("chave", AS_SEIS)
    def test_TRUE_NUMA_CHAVE_INTEIRA_E_RECUSADO_COM_O_NOME_DA_CHAVE(
        self, tmp_path, chave
    ):
        caminho = escrever(tmp_path, f"[{SECAO_DA_RENDA}]\n{chave} = true\n")

        with pytest.raises(AgendaInvalida) as erro:
            ler_ajustes_da_renda(caminho)

        assert chave in str(erro.value), (
            "a mensagem tem de NOMEAR a chave: o usuario esta com o arquivo "
            f"aberto e precisa saber qual linha consertar. Saiu: {erro.value}"
        )

    @pytest.mark.parametrize("chave", AS_SEIS)
    def test_CONTROLE_O_INTEIRO_1_NO_MESMO_LUGAR_PASSA(self, tmp_path, chave):
        """Sem o par, um validador que recusasse TUDO passaria no teste de cima.

        `1` e o valor que `true` viraria se a checagem de `bool` viesse depois
        da de `int` — entao ele e exatamente o controle certo: o mesmo numero,
        escrito do jeito que o usuario quis dizer.
        """
        caminho = escrever(tmp_path, f"[{SECAO_DA_RENDA}]\n{chave} = 1\n")

        ajustes = ler_ajustes_da_renda(caminho)

        assert getattr(ajustes, chave) == 1


class TestZeroENegativoSaoRecusadosNoArranque:
    """Nenhum dos seis faz sentido em zero, e nenhum faz sentido negativo.

    O sexto pela sua propria razao: um pack de tamanho zero nao tem "proximo
    multiplo", e um negativo produziria um alvo ABAIXO da adena que o usuario ja
    tem — faltas negativas com cara de conta. `tempo_ate_o_pack` tambem levanta,
    e os dois portoes existem porque o modulo puro pode ser chamado por outro
    caminho que nao o `config.toml`.
    """

    @pytest.mark.parametrize("chave", AS_SEIS)
    @pytest.mark.parametrize("valor", [0, -1, -600])
    def test_A_MENSAGEM_NOMEIA_A_CHAVE(self, tmp_path, chave, valor):
        caminho = escrever(tmp_path, f"[{SECAO_DA_RENDA}]\n{chave} = {valor}\n")

        with pytest.raises(AgendaInvalida) as erro:
            ler_ajustes_da_renda(caminho)

        assert chave in str(erro.value), (
            f"{chave} = {valor} tem de ser recusado com o nome da chave na "
            f"mensagem. Saiu: {erro.value}"
        )

    def test_UM_FATOR_DE_SALTO_ZERADO_NAO_PASSA_CALADO(self, tmp_path):
        """O caso concreto que este portao existe para pegar.

        Com `fator_de_salto_da_adena = 0`, `a_adena_saltou_ordem_de_grandeza`
        compara `maior <= menor * 0` e recusa TODA amostra em que a adena mudou
        — que e toda amostra util de uma noite de farm. O arquivo encheria de
        recusas e a taxa nunca sairia, e ninguem ligaria uma coisa a outra.
        """
        caminho = escrever(
            tmp_path, f"[{SECAO_DA_RENDA}]\n{CHAVE_DO_FATOR_DE_SALTO} = 0\n"
        )
        with pytest.raises(AgendaInvalida):
            ler_ajustes_da_renda(caminho)


class TestOsOutrosDoisJeitosDeEscreverErrado:
    """Texto onde se espera numero, e um arquivo que nem TOML e."""

    @pytest.mark.parametrize("chave", AS_SEIS)
    def test_TEXTO_ONDE_SE_ESPERA_NUMERO_TRAZ_O_TIPO_QUE_VEIO(
        self, tmp_path, chave
    ):
        caminho = escrever(tmp_path, f'[{SECAO_DA_RENDA}]\n{chave} = "dez"\n')

        with pytest.raises(AgendaInvalida) as erro:
            ler_ajustes_da_renda(caminho)

        assert chave in str(erro.value)
        assert "str" in str(erro.value), (
            "a mensagem tem de dizer o TIPO que veio: 'precisa ser um numero' "
            f"faz o usuario adivinhar o que ele escreveu. Saiu: {erro.value}"
        )

    def test_UM_FRACIONARIO_TAMBEM_E_RECUSADO(self, tmp_path):
        """`1.5` nao descreve limiar nenhum, e `10.0` cai junto de proposito.

        Aceitar o float redondo e recusar o quebrado seria uma regra que o
        usuario descobre por tentativa — a mesma razao ja escrita em
        `_inteiro_positivo` da receita.
        """
        caminho = escrever(
            tmp_path, f"[{SECAO_DA_RENDA}]\n{CHAVE_DA_JANELA_MOVEL} = 10.0\n"
        )
        with pytest.raises(AgendaInvalida):
            ler_ajustes_da_renda(caminho)

    def test_A_SECAO_QUE_NAO_E_SECAO_E_RECUSADA(self, tmp_path):
        caminho = escrever(tmp_path, f'{SECAO_DA_RENDA} = "dez minutos"\n')
        with pytest.raises(AgendaInvalida) as erro:
            ler_ajustes_da_renda(caminho)
        assert SECAO_DA_RENDA in str(erro.value)

    def test_TOML_INVALIDO_LEVANTA_A_EXCECAO_QUE_O_ARQUIVO_JA_USA(self, tmp_path):
        """E `AgendaInvalida`, e NAO uma classe nova.

        A razao ja esta escrita em `ler_membros` e em
        `ler_watchlist_do_mercado`: ela JA e a excecao de "o `config.toml` nao
        faz sentido", ja e capturada onde o arranque quer capturar, e uma classe
        nova duplicaria esse tratamento sem ganhar nada.
        """
        caminho = escrever(tmp_path, f"[{SECAO_DA_RENDA}\nisto nao fecha = = =\n")

        with pytest.raises(AgendaInvalida):
            ler_ajustes_da_renda(caminho)


class TestOsDefaultsMoramNaCascaENaoNoModuloPuro:
    """A metade executavel da frase "a seta aponta casca -> puro"."""

    # A ponte entre a chave que o usuario escreve e o parametro que o modulo
    # puro recebe. Os nomes sao DIFERENTES de proposito: a chave descreve o que
    # o usuario esta ajustando (`lacuna_maxima_segundos`) e o parametro descreve
    # o papel dele na conta (`limiar_de_lacuna_em_segundos`).
    PONTE = {
        CHAVE_DA_LACUNA: ("passo_entre", "limiar_de_lacuna_em_segundos"),
        CHAVE_DO_FATOR_DE_SALTO: ("passo_entre", "fator_de_salto"),
        CHAVE_DO_PISO_DE_AMOSTRAS: ("taxa_por_hora", "piso_de_amostras"),
        CHAVE_DO_PISO_DA_JANELA: ("taxa_por_hora", "piso_da_janela_em_segundos"),
    }

    def test_OS_QUATRO_LIMIARES_CHEGAM_SOMENTE_NOMEADOS_E_SEM_DEFAULT(self):
        for chave, (funcao, parametro) in self.PONTE.items():
            assinatura = inspect.signature(getattr(renda_conta, funcao))
            assert parametro in assinatura.parameters, (
                f"{funcao} deixou de receber `{parametro}`, que e onde a chave "
                f"`{chave}` do config.toml desemboca"
            )
            alvo = assinatura.parameters[parametro]
            assert alvo.kind == alvo.KEYWORD_ONLY, (
                f"{funcao}({parametro}) tem de ser SOMENTE-NOMEADO: um limiar "
                "posicional troca de lugar com o vizinho sem ninguem notar"
            )
            assert alvo.default is inspect.Parameter.empty, (
                f"{funcao}({parametro}) ganhou valor de fabrica. Um limiar por "
                "omissao e a definicao de constante magica, e este vem do "
                f"`config.toml` do usuario pela chave `{chave}`"
            )

    def test_NENHUM_PARAMETRO_SOMENTE_NOMEADO_DO_MODULO_PURO_TEM_DEFAULT(self):
        """A regra geral, e nao so os quatro que a ponte cobre hoje.

        Sem ela, um limiar novo nasceria com default e passaria: a `PONTE` acima
        so olha para os nomes que ela conhece.
        """
        achados = []
        for nome, objeto in vars(renda_conta).items():
            if not callable(objeto):
                continue
            if getattr(objeto, "__module__", "") != renda_conta.__name__:
                continue
            if not inspect.isfunction(objeto):
                continue
            for parametro in inspect.signature(objeto).parameters.values():
                if (
                    parametro.kind == parametro.KEYWORD_ONLY
                    and parametro.default is not inspect.Parameter.empty
                ):
                    achados.append(f"{nome}({parametro.name}={parametro.default!r})")
        assert not achados, achados

    def test_O_MODULO_PURO_NAO_SABE_QUE_O_CONFIG_TOML_EXISTE(self):
        """A seta aponta casca -> puro. Ela nunca aponta de volta.

        Se o modulo puro importasse `config`, ele deixaria de ser testavel sem
        um arquivo em disco — e `config` importa `notificador`, que importa
        `rastreador`, que importa `visao`, que importa `cv2`.
        """
        import ast
        from pathlib import Path

        fonte = Path(renda_conta.__file__)
        arvore = ast.parse(fonte.read_text(encoding="utf-8"))
        modulos = []
        for no in ast.walk(arvore):
            if isinstance(no, ast.ImportFrom):
                modulos.append(no.module or "")
            elif isinstance(no, ast.Import):
                modulos.extend(alias.name for alias in no.names)
        assert [m for m in modulos if "config" in m] == []
