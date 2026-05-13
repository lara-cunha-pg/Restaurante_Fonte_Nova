# PG_RELEASE_POLICY

## Objetivo
Este documento define quando e como o `_pg_template` passa de alteracoes em curso para uma release utilizavel como baseline.

Nao e um documento conceptual.
E a regra operacional minima para publicar versoes estaveis da framework.

## Principios

- o `_pg_template` e a source of truth
- nenhuma alteracao transversal fica apenas em repositorios piloto
- uma release so existe quando houver commit, changelog, tag e criterio de fecho explicito
- `main` pode continuar a evoluir, mas a baseline recomendada para adocao deve ser sempre identificavel por tag

## Tipos de versao

- `v2.x.y`:
  - `x` muda quando ha mudanca estrutural relevante na framework
  - `y` muda quando ha melhoria incremental compativel
- exemplos:
  - `v2.4.4` = baseline validada de piloto
  - `v2.4.6` = endurecimento compativel sem quebra estrutural
  - `v2.5.0` = nova iteracao fechada com objetivo proprio

## Quando promover uma release

Uma release do `_pg_template` deve ser promovida quando:

- o objetivo da iteracao esta implementado
- os documentos centrais estao coerentes
- o working tree esta limpo
- existe evidencia minima de validacao
- o `CHANGELOG.md` foi atualizado
- a tag da versao vai ser publicada no remoto

## Gate minimo por tipo de alteracao

### Documentacao apenas

Minimo exigido:
- revisao dos documentos alterados
- `CHANGELOG.md` atualizado
- versao revista se a alteracao tiver impacto real de uso

### Scripts ou template de ficheiros

Minimo exigido:
- validacao local do script ou fluxo alterado
- quando aplicavel, `pg_smoke_test_repo.ps1`
- `CHANGELOG.md` e docs operacionais atualizados

### Addon `pg_brodoo`

Minimo exigido:
- `scripts/pg_run_odoo_addon_tests.ps1` a passar
- instalacao e upgrade do modulo validados no runner
- docs relevantes atualizadas se o comportamento mudou

### Mudanca estrutural da framework

Minimo exigido:
- validacao em projeto piloto real ou repositorio de reprodutibilidade
- smoke test estrutural
- testes automatizados do addon, se o addon foi tocado
- criterio de fecho da iteracao revisto

## Sequencia obrigatoria de release

1. concluir implementacao
2. validar localmente o que mudou
3. atualizar docs afetadas
4. atualizar `CHANGELOG.md`
5. atualizar referencia de versao, quando aplicavel
6. confirmar `git status` limpo ou apenas com os ficheiros esperados
7. criar commit final da iteracao
8. fazer `push` para `origin/main`
9. criar tag anotada da release
10. fazer `push` da tag

## Comandos de referencia

### Publicar `main`

```powershell
cd C:\Users\Utilizador\Desktop\Repos\_pg_template
git push origin main
```

### Criar e publicar tag

```powershell
cd C:\Users\Utilizador\Desktop\Repos\_pg_template
git tag -a vX.Y.Z -m "release: vX.Y.Z"
git push origin vX.Y.Z
```

## O que entra no `CHANGELOG.md`

Cada release deve registar:

- numero da versao
- data
- tipo de mudanca
- resumo curto do que mudou
- se houve impacto em bootstrap, sync, addon, testes ou docs

## O que nao conta como release

Os seguintes casos nao devem ser tratados como release estavel por si so:

- alteracoes locais nao publicadas no remoto
- mudancas testadas apenas num piloto sem consolidacao no `_pg_template`
- ajustes ainda sem changelog
- commits experimentais sem criterio de fecho

## Regra de adocao por projetos

- projetos novos devem preferir bootstrap a partir de tag estavel
- `main` pode ser usada quando o objetivo for testar iteracao em curso
- repositorios piloto nao definem baseline; apenas a validam

## Regra para ronda de validacao piloto

Quando uma baseline ja estiver fechada no repo canonico, mas a ronda seguinte for de validacao operacional e adocao controlada:

- o objetivo imediato deixa de ser abrir nova frente estrutural
- a baseline deve ser testada com runbook proprio e relatorio factual
- o resultado da ronda deve terminar numa classificacao explicita:
  - `READY`
  - `READY WITH GUARDRAILS`
  - `NOT READY`
- a proxima frente estrutural so deve abrir depois dessa classificacao ficar registada no repo canonico
- o piloto valida a baseline existente; nao cria sozinho uma baseline nova

## Responsabilidade de fecho

Antes de declarar uma release como baseline utilizavel, deve ser possivel responder `sim` a estas perguntas:

- a alteracao esta consolidada no `_pg_template`?
- existe evidencia minima de validacao?
- o changelog explica a release?
- a tag identifica de forma unica a baseline?
- um projeto novo consegue reproduzir a baseline sem depender de contexto informal?
- se a baseline entrou em ronda de piloto, o resultado `READY / READY WITH GUARDRAILS / NOT READY` ficou registado?
