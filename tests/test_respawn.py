"""A janela de respawn: o disco como memoria de um ciclo de seis a oito horas.

Este arquivo prova a metade PURA da fase — a que nao tem tela, nem rede, nem
relogio proprio. O caminho inteiro (nascimento na tela -> ancora em disco ->
mensagem no grupo) e provado em `tests/test_sessao.py`, porque so la existe um
`tick`.

A PROPRIEDADE CENTRAL, e a razao de o modulo existir: o instante do nascimento
NUNCA mora em memoria. Ele e gravado como nome de arquivo vazio em `.agenda/` e
lido de volta seis horas depois, possivelmente por outro processo, possivelmente
depois de um reinicio. Um teste que guardasse o instante numa variavel de sessao
passaria sem provar nada disso.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from l2scanner.agenda import PREFIXO_NASCIMENTO, RegistroEmDisco
from l2scanner.bosses import Boss, OrigemDoAviso
from l2scanner.respawn import (
    Ancora,
    AvisoDeJanela,
    TipoDeJanela,
    ancora_de_chave,
    ancoras_mais_recentes,
    anunciar_janelas,
    chave_do_nascimento,
    janelas_devidas,
    texto_da_janela,
)

# O boss e CONSTRUIDO AQUI, e nunca lido do `config.toml` do repositorio.
# Aquele arquivo e do usuario e ele o edita: um teste ancorado nas horas de la
# fica vermelho no dia em que ele trocar 6 por 5, sem defeito nenhum.
NORTH = Boss(nome="Tiat North", respawn_horas_min=6, respawn_horas_max=8)
SOUTH = Boss(nome="Tiat South", respawn_horas_min=6, respawn_horas_max=8)

NASCIMENTO = datetime(2026, 8, 30, 14, 30)
ABRE_EM = NASCIMENTO + timedelta(hours=6)
LIMITE_EM = NASCIMENTO + timedelta(hours=8)


def ancoras_de(*chaves: str) -> dict[str, Ancora]:
    return ancoras_mais_recentes(chaves)


def so_north(instante=NASCIMENTO, origem=OrigemDoAviso.CHAT) -> dict[str, Ancora]:
    return ancoras_de(chave_do_nascimento("Tiat North", instante, origem))


class TestAFormaDuravelDaChave:
    """D-18: a forma do nome de arquivo, que e uma porta de mao unica.

    Depois do primeiro arquivo gravado em `.agenda/`, mudar esta forma faz o
    marcador antigo deixar de casar: a contagem reinicia do nada e um aviso ja
    enviado sai de novo no grupo. E o defeito que a docstring de `Aviso.chave`
    existe para impedir, e por isso a forma e afirmada literalmente aqui.
    """

    def test_a_chave_do_nascimento_tem_data_apelido_hora_e_origem(self):
        chave = chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.CHAT)
        assert chave == "2026-08-30_tiat-north-1430_chat"

    def test_a_origem_do_alvo_entra_no_nome(self):
        chave = chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.ALVO)
        assert chave == "2026-08-30_tiat-north-1430_alvo"

    def test_a_origem_dupla_tem_sublinhado_e_mesmo_assim_volta_inteira(self):
        """`chat_e_alvo` contem sublinhado, que e o proprio separador.

        Uma volta ingenua por `split('_')` produziria cinco campos em vez de
        tres e a origem voltaria truncada em `chat` — a mensagem passaria a
        citar so metade do sinal que ancorou, e nada levantaria.
        """
        chave = chave_do_nascimento(
            "Tiat North", NASCIMENTO, OrigemDoAviso.CHAT_E_ALVO
        )
        assert chave == "2026-08-30_tiat-north-1430_chat_e_alvo"
        assert ancora_de_chave(chave).origem is OrigemDoAviso.CHAT_E_ALVO

    @pytest.mark.parametrize(
        "origem",
        [OrigemDoAviso.CHAT, OrigemDoAviso.ALVO, OrigemDoAviso.CHAT_E_ALVO],
    )
    def test_a_ida_e_a_volta_fecham(self, origem):
        chave = chave_do_nascimento("Tiat North", NASCIMENTO, origem)
        ancora = ancora_de_chave(chave)
        assert ancora == Ancora(
            boss="tiat-north", instante=NASCIMENTO, origem=origem
        )

    def test_o_apelido_com_hifens_sobrevive_a_volta(self):
        """O apelido tem hifens, e a hora e separada por hifen tambem.

        Partir o campo do meio pelo PRIMEIRO hifen devolveria `tiat` e o resto
        viraria hora — o boss voltaria com outro nome e a ancora seria de
        outra criatura.
        """
        ancora = ancora_de_chave("2026-08-30_tiat-north-1430_chat")
        assert ancora.boss == "tiat-north"
        assert ancora.instante == NASCIMENTO


class TestUmArquivoTortoNaoDerrubaOLaco:
    """`.agenda/` e uma pasta que o usuario pode abrir e editar (T-02-07).

    Um arquivo criado ou renomeado a mao nao pode derrubar o laco que anuncia
    morte de party. `ancora_de_chave` devolve `None` e NUNCA levanta.
    """

    @pytest.mark.parametrize(
        "torto",
        [
            "lixo",
            "nascimento_lixo",
            "2026-13-45_x-9999_chat",
            "2026-08-30_tiat-north-1430_inventada",
            "2026-08-30_tiat-north-9999_chat",
            "2026-08-30_semhora_chat",
            "2026-08-30_tiat-north-1430",
            "",
        ],
    )
    def test_nome_torto_devolve_none_sem_levantar(self, torto):
        assert ancora_de_chave(torto) is None

    def test_as_tortas_somem_e_a_valida_fica(self):
        boas = ancoras_mais_recentes(
            [
                "lixo",
                "2026-13-45_x-9999_chat",
                "2026-08-30_tiat-north-1430_inventada",
                "2026-08-30_tiat-north-1430_chat",
            ]
        )
        assert set(boas) == {"tiat-north"}


class TestSoAAncoraMaisRecente:
    """JANE-04 / D-20: cancelar por AUSENCIA, e nao por marcador.

    Um nascimento novo grava uma ancora nova; a chave dos avisos do ciclo
    anterior deixa de ser gerada e eles param de vencer sozinhos. Nao ha um
    segundo estado que possa divergir do primeiro.
    """

    def test_entre_duas_do_mesmo_boss_vence_a_mais_nova(self):
        ancoras = ancoras_de(
            chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.CHAT),
            chave_do_nascimento(
                "Tiat North", datetime(2026, 8, 30, 19, 0), OrigemDoAviso.CHAT
            ),
        )
        assert ancoras["tiat-north"].instante == datetime(2026, 8, 30, 19, 0)

    def test_o_aviso_do_ciclo_velho_nunca_sai(self):
        """O CORACAO DE JANE-04, e ele nao usa marcador de cancelamento.

        As 20:30 o ciclo das 14:30 venceria. Com a ancora das 19:00 em disco,
        a chave das 14:30 simplesmente nao e mais gerada — nao ha nada para
        cancelar porque nao ha nada para vencer.
        """
        ancoras = ancoras_de(
            chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.CHAT),
            chave_do_nascimento(
                "Tiat North", datetime(2026, 8, 30, 19, 0), OrigemDoAviso.CHAT
            ),
        )
        assert janelas_devidas(ABRE_EM, [NORTH], ancoras, set()) == []

    def test_bosses_diferentes_nao_disputam_a_mesma_ancora(self):
        ancoras = ancoras_de(
            chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.CHAT),
            chave_do_nascimento(
                "Tiat South", datetime(2026, 8, 30, 19, 0), OrigemDoAviso.CHAT
            ),
        )
        assert ancoras["tiat-north"].instante == NASCIMENTO
        assert ancoras["tiat-south"].instante == datetime(2026, 8, 30, 19, 0)

    def test_no_empate_de_minuto_vence_quem_carrega_o_anuncio(self):
        """As duas instancias do usuario podem gravar o mesmo minuto.

        Uma leu o chat, a outra so o alvo. O anuncio e PROVA de nascimento e o
        alvo nao e — deixar o desempate para a ordem de leitura do diretorio
        faria a mesma pasta produzir citacoes diferentes em maquinas
        diferentes.
        """
        ancoras = ancoras_de(
            chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.ALVO),
            chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.CHAT),
        )
        assert ancoras["tiat-north"].origem is OrigemDoAviso.CHAT

    def test_o_desempate_nao_depende_da_ordem_da_lista(self):
        invertido = ancoras_de(
            chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.CHAT),
            chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.ALVO),
        )
        assert invertido["tiat-north"].origem is OrigemDoAviso.CHAT


class TestAChaveDoAvisoSaiDaAncora:
    """A chave do aviso deriva da ANCORA, e nunca do alvo do aviso.

    Tres razoes, e as tres tem consequencia observavel: (a) e o que faz D-20
    funcionar sem marcador de cancelamento; (b) a data da ancora e a que a poda
    de 3 dias enxerga, e ela e sempre menor ou igual a do alvo; (c) e a mesma
    forma de `Aviso.chave`, entao os dois namespaces podam pela mesma linha.
    """

    def test_a_chave_cita_a_data_e_a_hora_do_nascimento(self):
        aviso = janelas_devidas(ABRE_EM, [NORTH], so_north(), set())[0]
        assert aviso.chave == "2026-08-30_tiat-north-1430_abre"

    def test_a_chave_do_limite_cita_o_mesmo_nascimento(self):
        aviso = janelas_devidas(LIMITE_EM, [NORTH], so_north(), set())[0]
        assert aviso.chave == "2026-08-30_tiat-north-1430_limite"

    def test_a_data_da_chave_e_a_da_ancora_mesmo_virando_o_dia(self):
        """A ancora das 22:00 abre as 04:00 do dia seguinte.

        Se a chave saisse do ALVO, a poda de 3 dias enxergaria uma data um dia
        a frente da que o marcador representa. Sai da ancora, que e sempre a
        data menor.
        """
        noite = datetime(2026, 8, 30, 22, 0)
        aviso = janelas_devidas(
            noite + timedelta(hours=6), [NORTH], so_north(noite), set()
        )[0]
        assert aviso.chave.startswith("2026-08-30_")
        assert aviso.alvo.date() == datetime(2026, 8, 31).date()

    def test_os_sufixos_de_tipo_nao_colidem_com_os_da_agenda(self):
        """A unica colisao concebivel, e a razao de ela nao acontecer.

        Um `[[evento]]` chamado como um `[[boss]]`, no mesmo minuto, produziria
        a mesma raiz de chave. Os sufixos sao disjuntos, entao os nomes de
        arquivo nunca coincidem.
        """
        from l2scanner.agenda import TipoDeAviso

        da_janela = {tipo.value for tipo in TipoDeJanela}
        da_agenda = {tipo.value for tipo in TipoDeAviso}
        assert not (da_janela & da_agenda)


class TestJanelasDevidasEPura:
    """Mesmo instante, mesmas regras, mesmas ancoras -> mesma lista. Sempre.

    Sem disco, sem rede, sem relogio. E o que permite afirmar as bordas de
    tolerancia em milissegundos, com o jogo fechado.
    """

    def test_um_minuto_antes_nao_sai_nada(self):
        assert (
            janelas_devidas(
                ABRE_EM - timedelta(minutes=1), [NORTH], so_north(), set()
            )
            == []
        )

    def test_no_alvo_exato_sai_um_aviso_de_abertura(self):
        devidos = janelas_devidas(ABRE_EM, [NORTH], so_north(), set())
        assert len(devidos) == 1
        assert devidos[0].tipo is TipoDeJanela.ABRE
        assert devidos[0].boss == "Tiat North"
        assert devidos[0].horas == 6

    def test_no_alvo_do_limite_sai_o_limite_e_nao_a_abertura(self):
        devidos = janelas_devidas(LIMITE_EM, [NORTH], so_north(), set())
        assert [a.tipo for a in devidos] == [TipoDeJanela.LIMITE]
        assert devidos[0].horas == 8

    def test_a_chave_ja_enviada_nao_volta(self):
        assert (
            janelas_devidas(
                ABRE_EM, [NORTH], so_north(), {"2026-08-30_tiat-north-1430_abre"}
            )
            == []
        )

    def test_boss_sem_ancora_e_pulado(self):
        devidos = janelas_devidas(ABRE_EM, [NORTH, SOUTH], so_north(), set())
        assert [a.boss for a in devidos] == ["Tiat North"]

    def test_ancora_de_boss_que_saiu_do_config_nao_levanta(self):
        """O usuario apagou o `[[boss]]` e a ancora dele ficou em disco.

        Varrer as ANCORAS em vez dos bosses faria esta ancora orfa procurar
        uma regra de respawn que nao existe. O laco e sobre os bosses.
        """
        orfa = ancoras_de(
            chave_do_nascimento("Boss Apagado", NASCIMENTO, OrigemDoAviso.CHAT)
        )
        assert janelas_devidas(ABRE_EM, [NORTH], orfa, set()) == []


class TestAJanelaDeToleranciaEUmaDecisao:
    """D-22: um aviso vencido ha tres horas NAO sai quando o processo sobe.

    A consequencia e deliberada e custa um aviso: um processo desligado durante
    os cinco minutos inteiros PERDE aquele aviso para sempre. Isso e preferivel
    a um lembrete de uma janela que abriu ha tres horas chegando as 22h.
    """

    def test_quatro_minutos_e_cinquenta_e_nove_segundos_ainda_sai(self):
        quase = ABRE_EM + timedelta(minutes=4, seconds=59)
        assert len(janelas_devidas(quase, [NORTH], so_north(), set())) == 1

    def test_cinco_minutos_depois_nao_sai_mais(self):
        assert (
            janelas_devidas(
                ABRE_EM + timedelta(minutes=5), [NORTH], so_north(), set()
            )
            == []
        )

    def test_tres_horas_depois_o_aviso_vencido_nao_ressuscita(self):
        assert (
            janelas_devidas(
                ABRE_EM + timedelta(hours=3), [NORTH], so_north(), set()
            )
            == []
        )


class TestOMarcarEADecisaoDeDespachar:
    """JANE-06 / D-21: exatamente um envio por aviso, entre duas instancias.

    O `marcar` E a decisao. O filtro por `enviados()` e otimizacao do caminho
    comum, e nao garantia — entre aquela leitura e o `marcar` a outra instancia
    pode ter escrito.
    """

    def semear(self, pasta, instante=NASCIMENTO, origem=OrigemDoAviso.CHAT):
        registro = RegistroEmDisco(pasta)
        registro.registrar_nascimento(
            chave_do_nascimento("Tiat North", instante, origem)
        )
        return registro

    def test_duas_instancias_produzem_exatamente_um_par(self, tmp_path):
        pasta = tmp_path / "agenda"
        self.semear(pasta)
        yaza = RegistroEmDisco(pasta)
        faer = RegistroEmDisco(pasta)

        primeiro = anunciar_janelas(yaza, [NORTH], ABRE_EM)
        segundo = anunciar_janelas(faer, [NORTH], ABRE_EM)

        assert len(primeiro) + len(segundo) == 1, (
            "o mesmo aviso saiu em dobro, ou nao saiu de ninguem"
        )

    def test_o_mesmo_registro_nao_repete_dentro_da_tolerancia(self, tmp_path):
        pasta = tmp_path / "agenda"
        registro = self.semear(pasta)

        assert len(anunciar_janelas(registro, [NORTH], ABRE_EM)) == 1
        assert (
            anunciar_janelas(registro, [NORTH], ABRE_EM + timedelta(minutes=1))
            == []
        )

    def test_um_processo_que_nunca_viu_o_nascimento_anuncia_igual(self, tmp_path):
        """O instante veio do DISCO, e nunca da memoria.

        Este registro e construido depois de a ancora ja existir e nunca
        chamou `registrar_nascimento`. Se a contagem morasse em memoria, ele
        nao teria o que anunciar.
        """
        pasta = tmp_path / "agenda"
        self.semear(pasta)

        outro = RegistroEmDisco(pasta)
        saida = anunciar_janelas(outro, [NORTH], ABRE_EM)

        assert len(saida) == 1
        assert "14:30" in saida[0][1]

    def test_a_pasta_com_arquivo_torto_nao_derruba_o_anuncio(self, tmp_path):
        pasta = tmp_path / "agenda"
        registro = self.semear(pasta)
        (pasta / f"{PREFIXO_NASCIMENTO}lixo").touch()

        assert len(anunciar_janelas(registro, [NORTH], ABRE_EM)) == 1


class TestADecisaoDeAncorarNaoVazaEmSimulacao:
    """`--dry-run` nao pode gravar ancora na pasta COMPARTILHADA.

    Herdado de `marcar`, e nao reimplementado: uma simulacao rodando ao lado do
    scanner de verdade que gravasse ancora faria o scanner real contar a partir
    de um nascimento que a simulacao inventou.
    """

    def test_registrar_nascimento_simulando_devolve_true_sem_tocar_no_disco(
        self, tmp_path
    ):
        pasta = tmp_path / "agenda"
        registro = RegistroEmDisco(pasta, simulando=True)

        assert registro.registrar_nascimento("2026-08-30_x-1430_chat") is True
        assert not pasta.exists()

    def test_a_prova_nao_e_vazia_fora_da_simulacao_o_arquivo_aparece(self, tmp_path):
        pasta = tmp_path / "agenda"
        registro = RegistroEmDisco(pasta)

        assert registro.registrar_nascimento("2026-08-30_x-1430_chat") is True
        assert (pasta / f"{PREFIXO_NASCIMENTO}2026-08-30_x-1430_chat").exists()

    def test_em_simulacao_n_chamadas_produzem_n_avisos(self, tmp_path):
        """O comportamento e HERDADO e ACEITO, e nao regressao.

        `marcar` devolve True sem encostar no disco quando simulando, entao a
        1 Hz sao ~300 linhas por aviso dentro dos cinco minutos de tolerancia.
        `_processar_agenda` ja se comporta assim para os avisos de TvT. A
        alternativa (um teto em memoria) trocaria o ruido do console pelo risco
        de o `--dry-run` deixar de mostrar um aviso que o modo existe para
        mostrar.
        """
        pasta = tmp_path / "agenda"
        real = RegistroEmDisco(pasta)
        real.registrar_nascimento(
            chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.CHAT)
        )

        simulando = RegistroEmDisco(pasta, simulando=True)
        saidas = [
            len(anunciar_janelas(simulando, [NORTH], ABRE_EM)) for _ in range(3)
        ]

        assert saidas == [1, 1, 1]


class TestOTextoDoTracer:
    """As duas frases do caminho ancorado no anuncio, ja no formato final.

    A matriz inteira das quatro frases, o portao de D-19 e a prova de que ele
    acusa um texto de controle moram em `TestNenhumaAfirmacaoDeEncerramento`.
    """

    def texto(self, tipo, origem=OrigemDoAviso.CHAT):
        ancora = Ancora(boss="tiat-north", instante=NASCIMENTO, origem=origem)
        alvo = ABRE_EM if tipo is TipoDeJanela.ABRE else LIMITE_EM
        horas = 6 if tipo is TipoDeJanela.ABRE else 8
        return texto_da_janela(
            AvisoDeJanela(
                boss="Tiat North",
                tipo=tipo,
                ancora=ancora,
                alvo=alvo,
                horas=horas,
            )
        )

    def test_a_abertura_comeca_pelo_boss_e_cita_o_nascimento(self):
        texto = self.texto(TipoDeJanela.ABRE)
        assert texto.startswith("Tiat North")
        assert "14:30" in texto
        assert "30/08" in texto

    def test_a_abertura_atribui_a_citacao_ao_servidor(self):
        assert "servidor" in self.texto(TipoDeJanela.ABRE)

    def test_o_limite_cita_as_horas_do_boss(self):
        assert "8h" in self.texto(TipoDeJanela.LIMITE)


# ---------------------------------------------------------------------------
# AS QUATRO MENSAGENS: a matriz {ABRE, LIMITE} x {ancorado no anuncio,
# ancorado no alvo}, e o portao que recusa a afirmacao que a conta nao
# autoriza.
# ---------------------------------------------------------------------------

# Toda forma de afirmar que a janela acabou ou que a party perdeu o boss.
#
# RADICAIS, e nao palavras inteiras: `fech` pega "fechou", "fechada",
# "fechamento" e "fecha"; `perd` pega "perdemos", "perdeu", "perdido" e
# "perda". Uma lista de palavras inteiras seria contornada pela primeira
# conjugacao que ninguem pensou em escrever.
TOKENS_PROIBIDOS = (
    "fech",
    "perd",
    "tarde demais",
    "ultima chance",
    "nao nasce mais",
    "passou da hora",
)


def acusacoes(texto: str) -> list[str]:
    """Os tokens proibidos que este texto contem, sem considerar caixa.

    RODA SOBRE A SAIDA DAS FUNCOES, E NUNCA SOBRE O ARQUIVO-FONTE. E a mesma
    razao pela qual os portoes de importacao deste projeto usam AST em vez de
    busca textual: as docstrings de `respawn.py` CITAM as palavras proibidas de
    proposito, para explicar por escrito qual afirmacao e proibida e por que.
    Uma varredura do fonte acusaria justamente a documentacao que protege a
    regra, e o portao morreria de falso alarme na primeira leitura.
    """
    minusculo = texto.lower()
    return [token for token in TOKENS_PROIBIDOS if token in minusculo]


def todos_os_textos() -> list[str]:
    """As quatro frases da matriz, e o ponto de extensao do plano 02-02.

    Parametrizado sobre uma LISTA para que acrescentar a quinta origem de texto
    (as linhas de previsao do console, que o plano 02-02 cria) seja acrescentar
    um item, e nao escrever um segundo portao que pode divergir deste.
    """
    textos = []
    for origem in (OrigemDoAviso.CHAT, OrigemDoAviso.ALVO):
        for tipo, horas, alvo in (
            (TipoDeJanela.ABRE, 6, ABRE_EM),
            (TipoDeJanela.LIMITE, 8, LIMITE_EM),
        ):
            textos.append(
                texto_da_janela(
                    AvisoDeJanela(
                        boss="Tiat North",
                        tipo=tipo,
                        ancora=Ancora(
                            boss="tiat-north",
                            instante=NASCIMENTO,
                            origem=origem,
                        ),
                        alvo=alvo,
                        horas=horas,
                    )
                )
            )
    return textos


def aviso_de(tipo, origem, horas=None, boss="Tiat North"):
    alvo = ABRE_EM if tipo is TipoDeJanela.ABRE else LIMITE_EM
    if horas is None:
        horas = 6 if tipo is TipoDeJanela.ABRE else 8
    return AvisoDeJanela(
        boss=boss,
        tipo=tipo,
        ancora=Ancora(boss="tiat-north", instante=NASCIMENTO, origem=origem),
        alvo=alvo,
        horas=horas,
    )


class TestNenhumaAfirmacaoDeEncerramento:
    """D-19: a mensagem de `max` NAO pode dizer que a janela fechou.

    A RAZAO E ARITMETICA, e nao de tom. A conta parte do NASCIMENTO e nao da
    MORTE, e entre os dois ha `k` — o tempo que o boss ficou vivo, que o
    scanner nao tem como medir. Os dois avisos saem `k` CEDO, nunca tarde:
    no instante do limite otimista a janela real pode nem ter aberto. Afirmar
    encerramento ali seria falso na direcao que custa caro, mandando a party
    desistir de um boss que ainda vai nascer.
    """

    @pytest.mark.parametrize("texto", todos_os_textos())
    def test_nenhuma_das_quatro_frases_afirma_encerramento(self, texto):
        assert acusacoes(texto) == [], f"a frase afirma o que a conta nao autoriza: {texto}"

    def test_a_prova_nao_e_vazia_o_detector_acusa_o_texto_de_controle(self):
        """Guarda contra prova vazia, no molde de
        `test_a_prova_pega_de_verdade_um_relogio_proprio`.

        Um detector com a lista vazia — ou com tokens que nenhuma frase
        plausivel conteria — passaria nos quatro testes acima sem provar coisa
        alguma. Este afirma que ele ACUSA um texto escrito a mao que diz
        exatamente o que D-19 proibe.
        """
        controle = "Tiat North: a janela fechou, perdemos o boss."
        assert acusacoes(controle) == ["fech", "perd"]

    @pytest.mark.parametrize(
        "controle",
        [
            "Tiat North: a janela fechou.",
            "Tiat North: perdemos o boss.",
            "Tiat North: tarde demais para ir.",
            "Tiat North: ultima chance de pegar.",
            "Tiat North: nao nasce mais hoje.",
            "Tiat North: passou da hora dele.",
        ],
    )
    def test_cada_token_da_lista_pega_alguma_coisa(self, controle):
        """Um token que nunca acusa nada e um item morto na lista.

        Sem isto, alguem poderia acrescentar um token com erro de digitacao e
        a lista continuaria parecendo mais forte do que e.
        """
        assert acusacoes(controle) != []


class TestAsQuatroFrases:
    """A matriz inteira, com a citacao da origem funcionando como ressalva."""

    def test_a_abertura_do_anuncio_atribui_ao_servidor(self):
        texto = texto_da_janela(aviso_de(TipoDeJanela.ABRE, OrigemDoAviso.CHAT))
        assert texto.startswith("Tiat North")
        assert "servidor" in texto
        assert "14:30 de 30/08" in texto
        assert "seu alvo" not in texto

    def test_a_abertura_do_alvo_atribui_ao_alvo_e_carrega_a_ressalva(self):
        """D-16: a citacao E a ressalva, e nao ha uma quinta frase generica.

        Sem esta linha, D-15 vira armadilha: o usuario escolheu COBERTURA
        sabendo que ter o boss no alvo nao prova nascimento, com a condicao de
        o erro ser LEGIVEL. Esta e a linha onde ele fica legivel.
        """
        texto = texto_da_janela(aviso_de(TipoDeJanela.ABRE, OrigemDoAviso.ALVO))
        assert "seu alvo virou Tiat North" in texto
        assert "nao prova que ele tinha acabado de nascer" in texto
        assert "servidor" not in texto

    def test_a_origem_dupla_cai_no_caminho_do_anuncio(self):
        """Quando os dois sinais estao presentes, o anuncio ja e a prova.

        O alvo nao acrescenta nada a honestidade do numero — uma quinta frase
        citando os dois daria a impressao de mais certeza sem haver mais
        certeza.
        """
        dupla = texto_da_janela(
            aviso_de(TipoDeJanela.ABRE, OrigemDoAviso.CHAT_E_ALVO)
        )
        so_chat = texto_da_janela(aviso_de(TipoDeJanela.ABRE, OrigemDoAviso.CHAT))
        assert dupla == so_chat

    @pytest.mark.parametrize(
        "origem", [OrigemDoAviso.CHAT, OrigemDoAviso.ALVO]
    )
    def test_as_duas_frases_de_limite_afirmam_o_piso(self, origem):
        """AFIRMA o que E verdade, em vez de negar o que nao e.

        A tentacao seria escrever a negacao de uma afirmacao de encerramento;
        ela seria honesta, mas poria dentro do texto de PRODUCAO as palavras
        que o portao acima existe para proibir, e o portao passaria a acusar a
        frase que deveria aprovar.
        """
        texto = texto_da_janela(aviso_de(TipoDeJanela.LIMITE, origem))
        assert "pode nascer a qualquer momento" in texto
        assert "limite otimista" in texto

    def test_o_limite_do_anuncio_explica_por_que_o_aviso_sai_cedo(self):
        texto = texto_da_janela(aviso_de(TipoDeJanela.LIMITE, OrigemDoAviso.CHAT))
        assert "o tempo em que o boss ficou vivo ainda nao entrou nela" in texto

    @pytest.mark.parametrize("texto", todos_os_textos())
    def test_toda_frase_comeca_pelo_boss_e_cita_o_nascimento(self, texto):
        assert texto.startswith("Tiat North:")
        assert "14:30 de 30/08" in texto


class TestOsNumerosVemDoConfigENaoDoCodigo:
    """Um boss novo no `config.toml` tem que produzir a frase com as horas
    dele."""

    @pytest.mark.parametrize(
        "tipo,horas,esperado",
        [
            (TipoDeJanela.ABRE, 3, "3h"),
            (TipoDeJanela.LIMITE, 4.5, "4.5h"),
        ],
    )
    def test_as_horas_saem_do_bloco_boss(self, tipo, horas, esperado):
        texto = texto_da_janela(aviso_de(tipo, OrigemDoAviso.CHAT, horas=horas))
        assert esperado in texto
        assert "6h" not in texto
        assert "8h" not in texto

    def test_o_nome_do_boss_sai_do_config_e_nunca_do_ocr(self):
        """T-02-09: nenhum byte lido pelo OCR entra no texto.

        O texto lido do chat serve so como predicado booleano e e descartado —
        e o que garante que nada escrito por um jogador no chat do jogo
        atravesse para o grupo de WhatsApp.
        """
        texto = texto_da_janela(
            aviso_de(TipoDeJanela.ABRE, OrigemDoAviso.ALVO, boss="Orfen")
        )
        assert texto.startswith("Orfen:")
        assert "seu alvo virou Orfen" in texto


class TestAVozDaCasa:
    """Portugues SEM ACENTO e SEM TRAVESSAO no texto que o usuario le.

    A regra vale para todo texto de WhatsApp e console deste projeto, e ja
    custou dois consertos numa fase anterior. Ela nao e estetica: a ponte
    Baileys e o console do Windows ja entregaram acento como lixo, e um
    travessao numa mensagem de alerta e indistinguivel de um caractere
    corrompido.
    """

    @pytest.mark.parametrize("texto", todos_os_textos())
    def test_nenhum_caractere_fora_do_ascii(self, texto):
        fora = sorted({c for c in texto if ord(c) > 127})
        assert fora == [], f"caractere nao-ascii no texto: {fora}"

    @pytest.mark.parametrize("texto", todos_os_textos())
    def test_nenhum_travessao(self, texto):
        assert "—" not in texto
        assert "–" not in texto


class TestAsArestasDeTempoRestantes:
    """As bordas que faltavam para fechar as nove do plano, sobre
    `janelas_devidas` pura — sem disco e sem `Sessao`."""

    def test_um_segundo_antes_do_alvo_nao_sai_nada(self):
        assert (
            janelas_devidas(
                ABRE_EM - timedelta(seconds=1), [NORTH], so_north(), set()
            )
            == []
        )

    def test_com_min_igual_a_max_os_dois_avisos_saem_juntos(self):
        """Um boss de regra FIXA, sem faixa aleatoria.

        Os dois alvos vencem no MESMO instante e os dois tem que sair, com
        chaves distintas: colapsa-los em um esconderia metade da informacao, e
        reusar a chave faria o segundo nunca ser gravado.
        """
        fixo = Boss(nome="Tiat North", respawn_horas_min=6, respawn_horas_max=6)

        devidos = janelas_devidas(ABRE_EM, [fixo], so_north(), set())

        assert [a.tipo for a in devidos] == [
            TipoDeJanela.ABRE,
            TipoDeJanela.LIMITE,
        ]
        assert len({a.chave for a in devidos}) == 2

    def test_dois_bosses_com_ancora_produzem_dois_avisos(self):
        ancoras = ancoras_mais_recentes(
            [
                chave_do_nascimento("Tiat North", NASCIMENTO, OrigemDoAviso.CHAT),
                chave_do_nascimento("Tiat South", NASCIMENTO, OrigemDoAviso.ALVO),
            ]
        )
        devidos = janelas_devidas(ABRE_EM, [NORTH, SOUTH], ancoras, set())
        assert sorted(a.boss for a in devidos) == ["Tiat North", "Tiat South"]
