# PG_SCOPE_INTAKE_SPEC

`PG_SCOPE_INTAKE.yaml` e um ficheiro local ao projeto.
Serve como fonte estruturada para semear e atualizar os blocos auto-geridos do `PG_CONTEXT.md`.

Nao substitui o `PG_CONTEXT.md`.
O `PG_CONTEXT.md` continua a ser a memoria funcional e decisoria do projeto.

## Finalidade

Usar este ficheiro para registar de forma mais estruturada:

- identificacao do projeto
- fase atual
- edicao e ambiente
- restricoes contratuais
- objetivo de negocio
- pedido atual
- processo atual
- trigger, frequencia, volumes e urgencia
- utilizadores, papeis, excecoes e aprovacoes
- documentos, integracoes e reporting
- o que ja foi tentado no standard
- porque isso foi considerado insuficiente

## Como usar

1. O bootstrap copia `PG_SCOPE_INTAKE.yaml` para o repositorio do projeto.
2. `scripts/pg_init_scope_intake.ps1` pode inicializar o ficheiro.
3. A equipa preenche ou reve o intake.
4. `scripts/pg_build_pg_context.ps1` atualiza os blocos auto-geridos do `PG_CONTEXT.md`.

## Regra de ownership

- `PG_SCOPE_INTAKE.yaml` e local ao projeto
- pode ser atualizado manualmente pela equipa
- pode ser usado como input estruturado antes de discovery, proposta ou refinamento do contexto
- nao deve ser promovido automaticamente para memoria global reutilizavel
