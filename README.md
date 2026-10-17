# 🔍 Auditoria de QA para Sebo em Marketplace: Estante Virtual

**Projeto PAC — TripleTen Brasil | Autor: Brunno Cesar, Analista de QA**

## 📖 Sobre o projeto

Auditoria de qualidade aplicada à operação de um livreiro independente que vende exclusivamente na Estante Virtual e controla o estoque de forma manual, seja num caderno, seja numa lista simples. Esse é o perfil mais comum do livreiro na plataforma: muitos não têm sistema, e o controle do acervo fica no papel ou na memória.

A tese: sem um controle de catálogo, a vitrine publicada deriva do estoque real e da política de preços. Ela anuncia livro que não existe, exibe preço que não é o planejado, omite avarias e conta estoque que não corresponde à prateleira. O resultado é venda de produto que o lojista não tem, perda de margem sem perceber e devolução por defeito que o comprador nunca foi avisado.

A suíte de testes compara a vitrine publicada contra a **Lista do Livreiro** (a fonte da verdade do projeto) e demonstra com evidência material que esse controle é imprescindível para saber o que se tem, o que se lucra e o que se perde.

## 🎯 Modelo operacional

**Escrita manual / verificação automatizada.**

- Os cenários de teste, inclusive os erros propositais que demonstram a tese, são criados manualmente pelo analista
- O Playwright atua como observador puro: navega na vitrine pública da Estante Virtual como um comprador, lê o estado visível dos anúncios (título, preço, contagem de fotos, descrição, presença ou ausência) e compara contra a Lista do Livreiro
- Nenhum teste automatiza login, edição, pausa ou compra

## 🔄 Alteração de escopo: registro de decisão

O escopo original (v2.0) contemplava verificação em dois canais, Estante Virtual e Mercado Livre, sem sistema integrador. O piloto da suíte foi executado na Estante Virtual em 07/10/2026 com sucesso ([evidências do piloto](evidencias/2026-10-07/)).

Na tentativa de replicar a verificação no Mercado Livre em 08/10/2026, a plataforma bloqueou a automação em camadas sucessivas:

1. **Popup de frete/CEP** sobreposto à galeria de fotos, impedindo a interação com os anúncios
2. **Overlay de onboarding** do próprio site, interceptando os cliques do script
3. **reCAPTCHA do Google**, apresentado duas vezes seguidas na mesma sessão; ao resolver, a plataforma exigia ainda identificação de cliente novo ou antigo e login em conta
4. **Muro de login** que impede a visualização de qualquer anúncio sem autenticação

As evidências fotográficas e os logs do terminal estão versionados em [evidencias/2026-10-08/](evidencias/2026-10-08/), e o script da tentativa permanece no repositório como registro histórico, sem alteração ([test_tc18_fotos_ml.py](playwright/tests/test_tc18_fotos_ml.py)).

Com a verificação automatizada inviabilizada empiricamente pela plataforma, o projeto ativou o cenário real do livreiro de canal único com controle manual de estoque, e o cross-channel passou a constar como **Fase 2 do roadmap**, condicionada à aprovação da API oficial do Mercado Livre.

> O piloto da v2.0, o caso TC-18, corresponde ao TC-16 da v2.1. O registro permanece no histórico preservado, e o mesmo cenário foi renumerado no novo plano.

## 🧪 Escopo da suíte — 23 casos (v2.1)

| Frente | Foco | Casos | Status |
|---|---|---|---|
| F1 — Conferência de estoque | Lista do livreiro × vitrine: existência, título, preço, descrição, fotos, estoque e venda fantasma | TC-01 a TC-09 | Em execução |
| F2 — Precificação e lucro | Régua de R$ 19, saldo operacional e rentabilidade por anúncio | TC-10 a TC-15 | Em execução |
| F3 — Fotos e avarias | Régua 2/4 fotos, dicionário de avarias e transparência visual | TC-16 a TC-23 | Em execução |
| Fase 2 — API (Mercado Livre) | Comparação página vs API (preço, status, fotos) | TC-27 a TC-29 (v2.0) | ⚠️ Condicionada ao token da API oficial |

**📚 Documentação:** [Documentação de Requisitos v2.1](https://brunnoc-04.github.io/projeto-pac-qa-sebo-auditoria/requisitos-v2.1.html) | [Plano de Testes v2.1](https://brunnoc-04.github.io/projeto-pac-qa-sebo-auditoria/plano-de-testes-v2.1.html)

## 🛠️ Stack

| Ferramenta | Papel |
|---|---|
| Python + Playwright | Verificação automatizada de leitura na vitrine da EV (nenhuma escrita) |
| Google Sheets | Consolidação financeira com fórmulas auditáveis |
| Jira | Registro formal de achados com evidência |
| GitHub | Versionamento de scripts, docs e evidências |
| Postman | Requisições à API do ML (bloco condicionado, Fase 2) |

## 📋 Regras de negócio (resumo)

- **Preço mínimo de venda:** R$ 19,00 (política do dono); abaixo disso, o QA sinaliza divergência e o livreiro confirma se é promoção
- **Saldo operacional:** (0,83 × preço) − R$ 4,00 (aquisição R$ 3,00 + embalagem R$ 1,00 + comissão EV de 17%); mensalidade de R$ 69,00 sem rateio unitário definido, portanto não é lucro líquido
- **Break-even (custos variáveis):** ≈ R$ 4,82, abaixo do piso da massa de teste (R$ 7,00)
- **Fotos:** 2 = bom estado • 4 = avaria evidenciada e descrita • 1 ou 3 = ERRO
- **Dicionário de avarias:** rasgo, grifo, mancha, oxidação, lombada gasta, amarelado, rasura, sublinhação, marcação de texto

## 🧩 Casos adicionais: registro de decisão (TC-24 e TC-25)

Dois casos foram acrescentados à suíte em 10/10/2026, fora do escopo descrito
no Plano de Testes v2.1, em consequência de um achado de plataforma identificado
durante a execução da Frente 1. Como o plano não os descreve integralmente,
este README é o registro formal deles — o que o Sheets testa, este README explica.

* **TC-24 — Piso de R$ 12,00 da plataforma (valor limite):** os Livros 4
  ("Nunca Minta para um Telepata", R$ 7,00) e 14 ("O Mago Mais Rico da
  Babilônia", R$ 7,42) constam na Lista do Livreiro, mas suas buscas retornam
  vazias na vitrine: abaixo do piso de R$ 12,00, o anúncio fica invisível para
  o comprador. O limiar é inclusivo — exatamente R$ 12,00 é exibido; abaixo
  disso, oculto. O comportamento é da plataforma (achado EV-01), não do
  livreiro, e orienta a precificação futura: anúncios precisam de R$ 12,00
  ou mais para existirem publicamente — piso que se sobrepõe ao mínimo de
  venda de R$ 19,00 do dono.


* **TC-25 — Anúncio fantasma (partição de equivalência):** o título
  "O Aprendiz da Torre das Sete Chaves" está publicado na vitrine (R$ 19,00)
  e não consta na Lista do Livreiro. O caso representa a partição "está na
  vitrine e não consta na lista" e demonstra o risco central da auditoria:
  venda de produto sem lastro no controle do livreiro.

## 📷 Caso migrado: registro de decisão (TC-05)

O TC-05 ("Volumetria de fotos por estado") não aparece na Frente 1: foi
mesclado à Frente 3 (Fotos e avarias), com a cobertura transferida para os
casos TC-16 e TC-17, e fica registrado no Sheets com status NA, preservando
a numeração contínua do plano. A decisão se sustenta em dois pontos: a massa
da vitrine conta com apenas 1 anúncio com mais de uma foto, de modo que uma
volumetria no nível da vitrine testaria um único espécime, sem valor
auditorável; e a régua de fotos (2 = bom estado • 4 = avaria evidenciada e
descrita • 1 ou 3 = ERRO) é verificada anúncio por anúncio na Frente 3, com
os locators de carrossel calibrados para essa leitura — o mesmo bloco que a
Frente 1 passou a reutilizar na expansão de descrição.

## 🗂️ Estrutura do repositório

    docs/          → documentação v2.1 (requisitos, plano de testes)
    playwright/    → suíte de automação (data, pages, tests)
    postman/       → bloco API condicionado (Fase 2)
    sheets/        → referências da planilha de consolidação
    jira/          → índice dos reportes de achados
    evidencias/    → screenshots por ciclo: AAAA-MM-DD/