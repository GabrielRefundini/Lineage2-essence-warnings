# API Coverage — Fase 1 (Fundacao: firewall, gravador e spike de campo)

No external API integration: a fase e 100% intra-repo e offline — conserta a escrita em
disco do gravador, planta um teste de firewall de dependencias, corta calibracao a partir
de frames PNG ja gravados e mede correlacao de template com OpenCV local. Nenhum servico
externo, SDK, endpoint HTTP, webhook ou credencial entra em cena, e `requirements.txt`
nao muda (RESEARCH: "Package Legitimacy Audit — auditoria vazia por construcao").

O detector determinístico foi executado no escopo da fase (secao do ROADMAP + CONTEXT.md)
em 2026-08-27 e devolveu `{"detected": false, "signals": []}`.

Nota: a unica integracao externa do projeto (a API do Chatwoot, no caminho de alerta de
party) nao e tocada nesta fase — ela e pre-existente e fica fora do escopo do milestone
v1-mercado, cuja entrega e console-only por decisao do usuario.
