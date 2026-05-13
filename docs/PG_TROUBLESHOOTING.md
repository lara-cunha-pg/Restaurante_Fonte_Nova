# PG_TROUBLESHOOTING

## Objetivo
Este documento regista problemas reais encontrados durante a validacao do piloto e a forma correta de os resolver sem improviso.

## 1. Scripts nao existem em `.\scripts\` no repositorio bootstrapado

**Sintoma**
- o guia ou o utilizador tenta correr `.\scripts\pg_refresh_pg_context.ps1`
- o projeto bootstrapado nao tem pasta `scripts` na raiz

**Causa**
- os scripts operacionais vivem em `.pg_framework/scripts/`
- o bootstrap cria uma referencia local ao framework partilhado, nao uma copia integral da pasta `scripts`

**Resolucao**
- usar `.\.pg_framework\scripts\...`
- ou correr os scripts a partir do proprio `_pg_template` apontando `-RepoPath`

**Exemplo**
```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Utilizador\Desktop\Repos\brodoo_v2\.pg_framework\scripts\pg_refresh_pg_context.ps1 -RepoPath 'C:\Users\Utilizador\Desktop\Repos\brodoo_v2'
```

## 2. Placeholder `.pg/PG_SCOPE_SYNC.json` nao passa no validator

**Sintoma**
- `pg_validate_scope_sync.ps1` falha logo apos bootstrap

**Causa**
- o ficheiro bootstrapado e apenas placeholder
- o validator espera um snapshot real publicado pelo Odoo

**Resolucao**
- nao usar o validator diretamente sobre o placeholder inicial
- primeiro publicar um snapshot real a partir do Odoo
- no refresh normal, o script ja faz fallback para o intake quando nao existe snapshot valido

## 3. PowerShell bloqueia scripts com `ExecutionPolicy`

**Sintoma**
- erro `running scripts is disabled on this system`

**Causa**
- politica local do PowerShell no Windows

**Resolucao**
- correr o script com `ExecutionPolicy Bypass`

**Exemplo**
```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Utilizador\Desktop\Repos\brodoo_v2\.pg_framework\scripts\pg_refresh_pg_context.ps1 -RepoPath 'C:\Users\Utilizador\Desktop\Repos\brodoo_v2'
```

## 4. Odoo 19 rejeita `numbercall` em `ir.cron`

**Sintoma**
- build falha com `ValueError: Invalid field 'numbercall' in 'ir.cron'`

**Causa**
- Odoo 19 removeu esse campo do modelo `ir.cron`

**Resolucao**
- remover `numbercall` do XML
- definir explicitamente `user_id` no cron quando necessario

## 5. Campo `PG Repository` gera RPC error em `name_search`

**Sintoma**
- abrir o many2one de repositório rebenta com erro no servidor

**Causa**
- em Odoo 19, `name_search` usa `domain` e nao `args` na chamada ao `super()`

**Resolucao**
- alinhar o override com a assinatura e chamada corretas de Odoo 19

## 6. Falta de `GitHub Token` no Odoo

**Sintoma**
- ao tentar escolher repositório ou sincronizar conta GitHub aparece erro `Configuracao em falta: GitHub Token.`

**Causa**
- token GitHub nao configurado no `Settings`

**Resolucao**
- criar um fine-grained personal access token no GitHub
- configurar pelo menos permissões de `Contents` e `Pull requests`
- colar no campo `GitHub Token`
- correr `Importar e Sync GitHub`

## 7. `https://github.com/odoo/enterprise` devolve `404`

**Sintoma**
- clone ou abertura do repositório devolve `Repository not found`

**Causa**
- o repositório existe, mas e privado
- a conta GitHub atual nao tem acesso efetivo

**Resolucao**
- para parceiros: garantir que o username GitHub foi associado corretamente no lado Odoo e que o convite foi aceite
- para nao parceiros: usar o bundle oficial de download Enterprise em vez de GitHub

## 8. Repositorio bootstrapado continua desfasado do template

**Sintoma**
- projeto piloto tem `AGENTS.md`, `.gitignore`, `config.toml` ou addon em versoes antigas

**Causa**
- bootstrap inicial nao reaplica alteracoes transversais posteriores

**Resolucao**
- correr `pg_sync_shared_assets.ps1`
- usar `-SyncAddon` quando tambem for necessario alinhar a copia local de `pg_brodoo`

**Exemplo**
```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Utilizador\Desktop\Repos\_pg_template\scripts\pg_sync_shared_assets.ps1 -RepoName brodoo_v2 -SyncAddon
```

## 9. Repositorio bootstrapado precisa de validacao rapida

**Sintoma**
- duvida sobre estrutura minima, snapshots, source Odoo ou addon

**Resolucao**
- correr `pg_smoke_test_repo.ps1`

**Exemplo**
```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Utilizador\Desktop\Repos\_pg_template\scripts\pg_smoke_test_repo.ps1 -RepoPath C:\Users\Utilizador\Desktop\Repos\brodoo_v2 -RequireOdooSource -CheckPgAiDevAssistant
```

## 10. Acentos corrompidos em `PG_CONTEXT.md`

**Sintoma**
- texto com caracteres partidos ou mojibake apos refresh

**Causa**
- escrita implicita com encoding errado em Windows

**Resolucao**
- usar os scripts atuais do template, que ja escrevem em UTF-8 explicito
- manter `.editorconfig` e `.gitattributes` sincronizados
- se necessario, regenerar o contexto a partir dos snapshots

## 11. Build Odoo.sh com `Warning` mas sem falha funcional

**Sintoma**
- estado `Test: Warning` no Odoo.sh

**Causa**
- warnings de labels duplicadas, deprecations ou ruido nao fatal

**Resolucao**
- abrir os logs de update e confirmar se existem `ERROR`, `CRITICAL` ou `Traceback`
- se o modulo carregar e o fluxo funcional estiver correto, tratar warnings documentais separadamente

## 12. `risks` e `next_steps` ficam com o mesmo texto

**Sintoma**
- o snapshot operacional publica o mesmo conteudo em `risks` e `next_steps`
- o `PG_CONTEXT.md` fica semanticamente incoerente apesar de tecnicamente valido

**Causa**
- classificacao incorreta do conteudo no Odoo

**Resolucao**
- manter em `risks` apenas o risco
- mover para `next_steps` a acao operacional correspondente
- republicar o `PG_PROJECT_STATUS_SYNC.json`
- voltar a correr `pg_refresh_pg_context.ps1`

**Referencia**
- ver `docs/PG_CONTENT_HYGIENE.md`

## 13. Workflow GitHub nao regenera `PG_CONTEXT.md`

**Sintoma**
- os snapshots `.pg` mudam no GitHub, mas `PG_CONTEXT.md` nao e atualizado automaticamente

**Causas tipicas**
- workflow `.github/workflows/pg_refresh_pg_context.yml` em falta no projeto
- secret `PG_TEMPLATE_REPO_TOKEN` nao configurado
- token sem acesso de leitura ao `_pg_template`
- variaveis `PG_TEMPLATE_REPO` ou `PG_TEMPLATE_REF` com valor incorreto

**Resolucao**
- sincronizar os assets partilhados do template para garantir que o workflow existe
- criar ou atualizar o secret `PG_TEMPLATE_REPO_TOKEN`
- validar manualmente o workflow com `workflow_dispatch`
- se necessario, correr refresh local como fallback diagnostico

**Referencia**
- ver `docs/PG_GITHUB_CONTEXT_AUTOMATION.md`

## Regra pratica final
- primeiro distinguir erro fatal de warning
- depois confirmar se o problema e do projeto piloto ou do `_pg_template`
- se for transversal, corrigir obrigatoriamente no `_pg_template` e so depois propagar para repositorios bootstrapados
