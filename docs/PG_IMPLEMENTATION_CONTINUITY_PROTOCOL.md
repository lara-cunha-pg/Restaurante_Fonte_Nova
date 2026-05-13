# PG_IMPLEMENTATION_CONTINUITY_PROTOCOL

## Objetivo

Definir um protocolo curto e repetivel para qualquer futura implementacao deste trabalho, de modo a que a pergunta `qual o proximo passo logico?` tenha sempre resposta objetiva sem depender do historico do chat.

## Regra de continuidade

Para qualquer `IMP`, `REP` novo ou ronda corretiva:

1. confirmar contexto operativo
2. implementar no repo canonico
3. testar no repo canonico
4. propagar para o repo de deploy
5. fazer `Upgrade` no Odoo
6. repetir o sync relevante no piloto
7. medir no repo de destino
8. documentar o resultado

Nenhuma iteracao fica considerada fechada antes do passo 7.

## Passo 0 - Confirmar contexto operativo

Antes de mexer em codigo, confirmar:

- source of truth: `_pg_template`
- repo de deploy do addon: `Parametro_Global/TesteExo`
- repo de destino factual do espelho do piloto: `ancoravip/teste`
- piloto ativo: `Odoo - Ancoravip Produção`

Documento de referencia:
- `docs/PG_REAL_PILOT_OPERATING_CONTEXT.md`

## Passo 1 - Implementar no repo canonico

Local:
- `C:\Users\Utilizador\Desktop\Repos\_pg_template\_pg_template`

Objetivo:
- aplicar a alteracao no source of truth

Obrigatorio:
- ler o codigo atual relevante
- atualizar docs se a iteracao mudar regras ou topologia
- fazer branch de trabalho dedicada quando a ronda o justificar

## Passo 2 - Testar no repo canonico

Objetivo:
- garantir que a alteracao passa nos testes certos antes de sair do source of truth

Minimo esperado:
- testes focados nos ficheiros alterados
- quando aplicavel, suite do addon

Regra:
- uma iteracao nao deve seguir para deploy sem verificacao minima no repo canonico

## Passo 3 - Propagar para o repo de deploy

Local:
- `C:\Users\Utilizador\Desktop\Repos\Parametro_Global`

Branch:
- `TesteExo`

Objetivo:
- levar para o Odoo.sh apenas o delta necessario do addon ou da framework relevante

Regra:
- sempre que o worktree principal estiver sujo, usar um worktree limpo para a propagacao

## Passo 4 - Fazer `Upgrade` no Odoo

Local de execucao:
- Odoo.sh / base de staging ou teste

Objetivo:
- garantir que o runtime do addon no Odoo ja usa a nova versao

Regra:
- sem `Upgrade`, nao ha validacao real de comportamento novo

## Passo 5 - Repetir o sync relevante no piloto

Projeto:
- `Odoo - Ancoravip Produção`

Sequencia minima:

1. executar o onboarding ou migracao necessaria quando a iteracao tocar no circuito de espelho
2. correr o `mirror sync` ou publish factual relevante no projeto piloto
3. confirmar atualizacao dos artefactos do espelho no repo factual
4. confirmar refresh do `PG_CONTEXT.md` quando aplicavel

Regra:
- quando a iteracao mexer no espelho, repetir o `mirror sync`
- quando a iteracao mexer apenas em artefactos factuais legados, repetir o publish factual relevante

## Passo 6 - Medir no repo de destino

Local:
- `C:\Users\Utilizador\Desktop\Repos\ancoravip`

Branch:
- `teste`

Objetivo:
- observar o efeito real no espelho factual e no `PG_CONTEXT.md`

O que medir:
- novos commits de espelho e contexto
- diff dos artefactos factuais afetados
- warnings do `smoke test`
- melhoria ou regressao do problema alvo

## Passo 7 - Documentar a iteracao

Objetivo:
- fechar a ronda sem depender da memoria do operador

Minimo a registar:
- commit do repo canonico
- commit do repo de deploy
- commits do espelho/contexto no repo de destino
- resultado dos testes
- resultado do smoke
- residuos ou riscos

Documentos onde registar:
- backlog do `IMP` ou `REP` ativo
- nota tecnica da intervencao, quando justificavel
- roadmap, quando mudar a ordem ou a estrategia

## Como responder a `qual o proximo passo logico?`

A resposta deve seguir esta ordem de decisao:

1. a frente atual ja esta fechada ou validada no nivel exigido?
2. se nao, o proximo passo e o primeiro passo em falta do protocolo acima
3. se sim, abrir a proxima frente por ordem do backlog operativo dominante

Aplicacao atual desta regra:

- `IMP-004`, `IMP-005` e `IMP-006` ficaram fechados com validacao em piloto real
- a baseline `v2.9.0` fica fechada como release historica da linha anterior
- o piloto `PG AI Assistant V1 mirror redesign` fica fechado com `READY WITH GUARDRAILS`
- antes de abrir nova frente estrutural, a prioridade passa a ser corrigir qualidade do espelho factual publicado

## Como responder a `avanca com o proximo passo logico`

A execucao deve sempre declarar:

- em que repo a acao vai acontecer
- qual o objetivo dessa acao
- que validacao fica esperada depois

## Documento de backlog atualmente dominante

Backlog a seguir nas proximas frentes:
- `docs/PG_CURRENT_WORKING_STATE.md`
- `docs/PG_V1_PILOT_REPORT_2026-04-20.md`
- `docs/PG_FRAMEWORK_REPOSITIONING_BACKLOG.md`

## Regra adicional para backlog historico

Documentos `V29`, `IMP` ou `REP` anteriores podem continuar uteis como contexto ou historico de decisoes.
Mas deixam de ser backlog dominante quando um documento mais recente:

- fecha formalmente uma linha nova
- regista `READY`, `READY WITH GUARDRAILS` ou `NOT READY`
- redefine explicitamente o bloqueio principal e o proximo passo logico

Quando isso acontecer, a ronda nova passa a prevalecer sobre a anterior.

## Regra final

Se em algum momento o trabalho voltar a depender de contexto oral para perceber:

- que repo editar
- que repo fazer deploy
- que repo validar
- que branch usar

entao este protocolo ou o documento de contexto operativo ficaram incompletos e devem ser atualizados antes da iteracao seguinte.
