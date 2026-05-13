# Instruções globais — Parametro Global

## AGENTS.md obrigatório

No início de cada sessão, antes de qualquer análise, recomendação ou proposta técnica:

1. Verificar se existe `AGENTS.md` na raiz do projeto.
2. Se existir, ler e seguir as instruções nele contidas.
3. Se o `AGENTS.md` referenciar um ficheiro de framework partilhado (ex: `.pg_framework/templates/AGENTS_SHARED.md`), ler também esse ficheiro antes de prosseguir.
4. `.pg_framework` é um symlink/atalho Windows — não é uma pasta real. Se uma leitura ou pesquisa falhar, resolver primeiro o alvo do symlink (ex: com `cmd /c dir .pg_framework` ou `(Get-Item .pg_framework).Target`) e usar o caminho real nas operações seguintes. Só parar e pedir relink se o alvo também não estiver acessível.

Esta instrução tem prioridade sobre o comportamento por defeito e aplica-se a todos os projetos.
