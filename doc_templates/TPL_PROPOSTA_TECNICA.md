# Template — Proposta Técnica / Fit-Gap

## Finalidade
Documento que apresenta a análise de um requisito funcional e a recomendação técnica correspondente. Produzido após análise consultiva. Serve de base à decisão do cliente e ao planeamento de implementação.

## Tom de Discurso
- Técnico mas acessível — o cliente deve conseguir ler e compreender sem ser especialista Odoo
- Baseado em evidência — citar fontes (código do projecto, vendor/odoo_src, documentação oficial)
- Transparente sobre limitações e riscos — não esconder complexidade
- A recomendação é clara e classificada — o cliente não deve ter dúvidas sobre o que se propõe
- Separar claramente factos de inferências de pontos por validar

## Instruções para o Agente
1. Seguir obrigatoriamente a ordem de decisão: standard → módulo adicional → Studio → custom
2. Nunca recomendar custom sem documentar porque as opções anteriores não resolvem
3. Classificar a recomendação final numa das categorias obrigatórias
4. Citar paths de `vendor/odoo_src` e links de documentação oficial consultados
5. Marcar explicitamente: `FACTO OBSERVADO` / `INFERÊNCIA` / `PONTO POR VALIDAR`
6. Validar restrições contratuais do projecto antes de propor qualquer solução (ler secção "Contrato e Parâmetros Odoo" do `PG_CONTEXT.md`)

---

## Estrutura do Documento

---

# [Nome do Projecto] — Proposta Técnica: [Título do Requisito]

**Versão:** 1.0
**Data:** DD/MM/AAAA
**Autor:** [Nome]
**Estado:** Rascunho / Para revisão interna / Para apresentação ao cliente

---

## 1. Objectivo Funcional

[O que o cliente quer atingir e qual a dor de negócio associada. Deve ser compreensível por um não-técnico. Máximo 3 frases.]

---

## 2. Contexto Técnico

**Versão Odoo:** [ex: 19.0 Enterprise]
**Ambiente:** [Odoo.sh / SaaS / On-Premise]
**Restrições contratuais relevantes:**
- Configuração standard: [PERMITIDO / NÃO PERMITIDO / Não definido]
- Módulos adicionais: [PERMITIDO / NÃO PERMITIDO / Não definido]
- Odoo Studio: [PERMITIDO / NÃO PERMITIDO / Não definido]
- Desenvolvimento custom: [PERMITIDO / NÃO PERMITIDO / Não definido]

---

## 3. Factos Observados

[O que foi confirmado com evidência: código do projecto, PG_CONTEXT.md, vendor/odoo_src ou documentação oficial.]

- `FACTO OBSERVADO`: [Descrição + fonte: path ou link]
- `FACTO OBSERVADO`: [Descrição + fonte: path ou link]

---

## 4. Inferências

[Conclusões prováveis não confirmadas. O consultor deve validar antes de implementar.]

- `INFERÊNCIA`: [Descrição — razão pela qual é inferência e não facto]

---

## 5. Pontos por Validar

[Informação necessária antes de decidir ou implementar.]

- `PONTO POR VALIDAR`: [Questão] — responsável: [Nome], prazo: DD/MM
- `PONTO POR VALIDAR`: [Questão] — responsável: [Nome], prazo: DD/MM

---

## 6. Análise de Opções

### 6.1 Configuração Standard

[Existe solução com configuração standard já disponível no projecto? Se sim, descrever como. Se não, justificar explicitamente.]

**Conclusão:** Resolve / Resolve parcialmente / Não resolve — porque [razão]

### 6.2 Módulo Standard Adicional

[Existe módulo Odoo standard (mesmo que não instalado) que cobre o requisito? Consultar `vendor/odoo_src` e documentação oficial da versão activa.]

**Módulo identificado:** [Nome do módulo ou "Nenhum identificado"]
**Cobertura do requisito:** TOTAL / PARCIAL / PARCIAL COM ADAPTAÇÃO DE PROCESSO
**Implicações de adopção:** [Impacto funcional, impacto no processo, gaps remanescentes]
**Conclusão:** Resolve / Resolve parcialmente / Não resolve — porque [razão]

### 6.3 Odoo Studio

[O Studio resolve o requisito sem código? Se não, justificar explicitamente.]

**Conclusão:** Resolve / Resolve parcialmente / Não resolve / Não recomendado — porque [razão]

### 6.4 Desenvolvimento Custom

[Solução via código Python/XML. Preencher apenas se as opções anteriores não resolvem.]

**Descrição técnica:** [O que seria desenvolvido]
**Impacto em upgrades:** [Alto / Médio / Baixo — justificação]
**Conclusão:** Necessário / Não recomendado — porque [razão]

---

## 7. Recomendação

**Classificação:** `[Configuração standard / Módulo standard adicional / Odoo Studio / Customização leve / Customização estrutural / Não recomendado / alto risco]`

[Descrição clara da solução recomendada. O que se propõe, como funciona, o que cobre e o que não cobre.]

---

## 8. Estimativa de Esforço

| Componente | Descrição | Esforço |
|---|---|---|
| [Análise / Configuração / Desenvolvimento / Testes] | [Descrição breve] | [X dias/horas] |
| **Total** | | **[X dias]** |

*Pressupostos desta estimativa:*
- [Pressuposto 1]
- [Pressuposto 2]

---

## 9. Riscos e Impactos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| [Risco 1] | Alta / Média / Baixa | Alto / Médio / Baixo | [Medida] |

---

## 10. Próximos Passos

1. [Acção 1] — responsável: [Nome] — prazo: DD/MM
2. [Acção 2] — responsável: [Nome] — prazo: DD/MM

---

## 11. Referências

- `PG_CONTEXT.md` — secções consultadas: [listar]
- `vendor/odoo_src/[path consultado]`
- `vendor/odoo_src/[path consultado]`
- [Link documentação oficial Odoo versão activa]
