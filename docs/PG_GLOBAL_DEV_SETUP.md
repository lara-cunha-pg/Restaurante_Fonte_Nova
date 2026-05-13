# Parametro Global - Setup global para projetos Odoo

Este documento descreve a configuracao de maquina esperada para trabalhar com o template consultivo Odoo.

## Estrutura recomendada

Repositorios:
`C:\Users\Utilizador\Desktop\Repos`

Cada projeto bootstrapado deve guardar o source Odoo no proprio repositorio:

```text
NOME_DO_REPO\
|-- vendor\
|   `-- odoo_src\
|       |-- community
|       `-- enterprise
`-- .pg_framework
```

## Regras globais

- o source Odoo e apenas referencia tecnica
- nunca alterar `vendor/odoo_src`
- nunca versionar `vendor/odoo_src` em Git
- cada projeto deve apontar para uma unica versao ativa
- a versao real deve ser detetada a partir do checkout em `vendor/odoo_src/community` e sincronizada para `PG_CONTEXT.md`

## Fontes de verdade

Sempre que houver duvida ou conflito, prevalece:
1. codigo do projeto
2. `vendor/odoo_src`
3. `PG_CONTEXT.md`
4. documentacao oficial da mesma versao
