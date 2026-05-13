# PG - Checklist rapido de bootstrap

## Pre-requisitos

- Repositorios em `C:\Users\Utilizador\Desktop\Repos`
- Template `_pg_template` disponivel
- Git disponivel no PATH
- acesso ao GitHub oficial do Odoo para clonar `odoo/odoo`
- acesso ao repositrio `odoo/enterprise`, quando o projeto for Enterprise

## Passos

1. Fluxo curto recomendado:

```powershell
cd C:\Users\Utilizador\Desktop\Repos\_pg_template
.\scripts\pg_bootstrap_assisted.ps1 -RepoName "NOME_DO_REPO" -SyncAddon -CloneOdooSource -Series 19.0 -Edition community
```

2. Em alternativa, fluxo faseado:

```powershell
cd C:\Users\Utilizador\Desktop\Repos\_pg_template
.\scripts\pg_bootstrap_repo.ps1 -RepoName "NOME_DO_REPO"
```

3. Fazer checkout do source Odoo:

```cmd
cd /d C:\Users\Utilizador\Desktop\Repos\_pg_template
.\scripts\pg_clone_odoo_source.cmd NOME_DO_REPO [19.0|19e] [community|enterprise]
```

4. Confirmar no repositorio bootstrapado:
- `AGENTS.md`
- `CLAUDE.md`
- `.pg_framework/`
- `.github/workflows/pg_refresh_pg_context.yml`
- `PG_CONTEXT.md`
- `PG_SCOPE_INTAKE.yaml`
- `config.toml`
- `.pg/PG_PROJECT_STATUS_SYNC.json`
- `vendor/odoo_src/community`
- `vendor/odoo_src/enterprise` quando aplicavel

5. Inicializar ou rever `PG_SCOPE_INTAKE.yaml`.

6. Materializar o contexto inicial:

```powershell
.\scripts\pg_build_pg_context.ps1 -RepoPath "C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO"
```

7. Validar e complementar no `PG_CONTEXT.md`:
- edicao
- ambiente
- restricoes contratuais
- pedido funcional atual
- processo atual
- dor / impacto

8. Quando existir sync vindo do Odoo:

```powershell
.\scripts\pg_validate_project_status_sync.ps1 -RepoPath "C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO"
.\scripts\pg_apply_project_status_sync.ps1 -RepoPath "C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO"
```

9. Validar rapidamente o repositorio bootstrapado:

```powershell
.\scripts\pg_smoke_test_repo.ps1 -RepoPath "C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO" -RequireOdooSource
```

Se o projeto tambem versionar o addon:

```powershell
.\scripts\pg_smoke_test_repo.ps1 -RepoPath "C:\Users\Utilizador\Desktop\Repos\NOME_DO_REPO" -RequireOdooSource -CheckPgAiDevAssistant
```

10. Quando o `_pg_template` evoluir e for preciso alinhar um repositorio ja bootstrapado:

```powershell
.\scripts\pg_sync_shared_assets.ps1 -RepoName "NOME_DO_REPO"
```

Depois da sincronizacao, no GitHub do projeto:
- criar o secret `PG_TEMPLATE_REPO_TOKEN`
- opcionalmente definir `PG_TEMPLATE_REPO`
- opcionalmente definir `PG_TEMPLATE_REF`

Se tambem quiseres alinhar a copia local do addon no projeto:

```powershell
.\scripts\pg_sync_shared_assets.ps1 -RepoName "NOME_DO_REPO" -SyncAddon
```

## Garantias esperadas

- source Odoo visivel no projeto e fora do Git
- framework partilhado acessivel via `.pg_framework/`
- versao e links oficiais sincronizados automaticamente no `PG_CONTEXT.md`
- ambito inicial estruturado em `PG_SCOPE_INTAKE.yaml`
- snapshot operacional reservado em `.pg/PG_PROJECT_STATUS_SYNC.json`
- workflow GitHub reservado para refresh remoto de `PG_CONTEXT.md`
- Codex e Claude disciplinados para decidir `standard -> modulo adicional -> Studio -> custom` a partir do mesmo contrato local
