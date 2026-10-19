# -*- coding: utf-8 -*-
# TC-11: Livro entre R$ 15,00 e R$ 18,99 (classe de equivalência da subfaixa intermediária)
# Livro 11 'Patinando no Gelo de Europa' — R$ 18,00 na lista, lucro esperado 10,94
# Passos: 1) aplicar filtro de preço 15,00 a 18,99 na vitrine 2) localizar o Livro 11
#         3) conferir preço exibido vs lista 4) registrar na planilha (lucro, classificação)
#         5) constatar a violação do mínimo de venda (RN-01) — achado vai para o Jira
# v2 (19/10/2026): Máximo com vírgula via fill — REJEITADO pelo navegador
#   ('Cannot type text into input[type=number]'): o campo é um <input type="number">
#   nativo (id inputValueMax) e o fill valida a string inteira contra o formato
#   estrito de número, onde vírgula é inválida no contexto padrão (en-US).
# v3 (19/10/2026): contexto com locale pt-BR + digitação caractere a caractere
#   (press_sequentially) — o caminho do comprador real: cada tecla é validada pelo
#   locale do navegador, e a vírgula passa. Inclui leitura forense dos valores
#   gravados nos campos (#inputValueMin / #inputValueMax) após aplicar o filtro.
# Padrão da suíte embutido: goto domcontentloaded (flake), comparação numérica (\xa0),
# diagnóstico de filtro (19 = não aplicou; 15 = só-mínimo)

import json
import os
import re
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-19"

# Locators herdados da Frente 1 + filtro calibrado no codegen de 19/10
CARDS = ".product-list__items .product-item"

ID_ALVO = "L-11"
PRECO_MINIMO = "15"
PRECO_MAXIMO = "18,99"  # vírgula: a página é pt-BR; quem entrega a vírgula é a digitação
MINIMO_VENDA = 19.00  # RN-01: mínimo de venda definido pelo dono


def preco_para_float(texto):
    # Converte 'R$ 18,00' (com espaço comum ou invisível \xa0) em 18.00
    limpo = texto.replace("R$", "").replace("\xa0", "").replace(" ", "")
    limpo = limpo.replace(".", "").replace(",", ".")
    return float(limpo)


def fmt_brl(valor):
    # 18.0 -> 'R$ 18,00' (padrão pt-BR no log)
    return f"R$ {valor:.2f}".replace(".", ",")


def digitar(campo, texto):
    # Digita caractere por caractere, como um comprador real.
    # O fill() insere a string inteira e o navegador valida contra o formato estrito
    # de input[type=number] — vírgula é rejeitada. Tecla por tecla, o locale manda.
    try:
        campo.press_sequentially(texto, delay=60)
    except (AttributeError, TypeError):
        campo.type(texto, delay=60)


with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]

# Achar o livro pelo id (padrão da suíte)
livro = None
for item in dados["livros"]:
    if item["id"] == ID_ALVO:
        livro = item
if livro is None:
    print(f"ATENÇÃO: o id {ID_ALVO} não existe no livros.json (validar a massa)")
    raise SystemExit

termo = livro["titulo"][:20]
print(f"Testando {livro['id']}: {livro['titulo']} (preço na lista: {fmt_brl(livro['preco'])})")

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    # v3: contexto pt-BR — o navegador fala a língua da página (e do comprador)
    contexto = navegador.new_context(locale="pt-BR")
    pagina = contexto.new_page()

    # PASSO 1: acessar a vitrine (domcontentloaded — lição do flake do TC-10)
    pagina.goto(url_vitrine, wait_until="domcontentloaded")
    pagina.wait_for_timeout(2000)
    print("Vitrine carregada (DOM pronto)")

    # POPUP DE ANIVERSÁRIO: pode demorar, esperamos até 8s
    try:
        pagina.locator("g > path").click(timeout=8000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu, seguindo")

    # PASSO 2: aplicar o filtro de faixa 15,00 a 18,99 (digitação caractere a caractere)
    campo_minimo = pagina.get_by_role("spinbutton", name="Mínimo:")
    digitar(campo_minimo, PRECO_MINIMO)
    campo_minimo.press("Enter")
    campo_maximo = pagina.get_by_role("spinbutton", name="Máximo:")
    digitar(campo_maximo, PRECO_MAXIMO)
    campo_maximo.press("Enter")
    pagina.wait_for_timeout(2000)
    print(f"Filtro aplicado: faixa R$ {PRECO_MINIMO},00 a R$ {PRECO_MAXIMO}")

    # Leitura forense dos campos (o que ficou gravado de fato nos inputs)
    val_min = pagina.evaluate("() => { const el = document.querySelector('#inputValueMin'); return el ? el.value : 'campo não encontrado'; }")
    val_max = pagina.evaluate("() => { const el = document.querySelector('#inputValueMax'); return el ? el.value : 'campo não encontrado'; }")
    print(f"Campos do filtro após aplicar: Mínimo='{val_min}' | Máximo='{val_max}'")

    # Rolagem progressiva antes de ler (carregamento preguiçoso, lição do TC-08)
    altura_total = pagina.evaluate("document.body.scrollHeight")
    posicao = 0
    while posicao < altura_total:
        posicao += 600
        pagina.evaluate(f"window.scrollTo(0, {posicao})")
        pagina.wait_for_timeout(400)
        altura_total = pagina.evaluate("document.body.scrollHeight")
    pagina.evaluate("window.scrollTo(0, 0)")
    pagina.wait_for_timeout(1000)

    # PASSO 3: localizar o Livro 11 nos resultados filtrados
    anuncios = pagina.locator(CARDS).filter(has_text=termo)
    total_anuncios = anuncios.count()
    print(f"Anúncios do Livro 11 nos resultados do filtro: {total_anuncios}")

    # Diagnóstico do filtro: esperado ~4 cards na faixa (Livros 2, 7, 11 e 17 da lista)
    total_cards = pagina.locator(CARDS).count()
    print(f"Total de cards nos resultados do filtro: {total_cards}")
    print("Esperado na faixa 15,00-18,99: ~4 cards (Livros 2, 7, 11 e 17 da lista)")
    if total_cards == 19:
        print("ATENÇÃO: 19 cards = vitrine inteira — o filtro não aplicou")
    elif total_cards == 15:
        print("ATENÇÃO: 15 cards = assinatura de filtro só-mínimo (11 >= 19 + 4 da subfaixa) — o Máximo não aplicou (conferir os valores impressos acima)")

    if total_anuncios > 0:
        texto_card = anuncios.first.inner_text()
        print("Texto do card:", texto_card.replace("\n", " | ")[:200])

        # PASSO 4: conferir o preço exibido contra a Lista (comparação numérica)
        preco_card = re.search(r"R\$\s*[\d.,]+", texto_card)
        if preco_card:
            preco_encontrado = preco_card.group(0)
            print("Preço publicado no card:", preco_encontrado)
            try:
                valor_card = preco_para_float(preco_encontrado)
                if abs(valor_card - livro["preco"]) < 0.005:
                    print("Preço CONSISTENTE com a Lista do Livreiro")
                else:
                    print(f"ATENÇÃO: preço na vitrine ({fmt_brl(valor_card)}) difere da lista ({fmt_brl(livro['preco'])})")

                # PASSO 5: veredito do caso — política de precificação (RN-01)
                if valor_card < MINIMO_VENDA:
                    print(f"TC-11: REPROVADO — anúncio à venda por {fmt_brl(valor_card)}, abaixo do mínimo de venda de R$ 19,00 (RN-01)")
                    print("Achado vai para o Jira; ressalva RN-03: o livreiro confirma se é promoção antes de qualquer ação corretiva")
                else:
                    print("TC-11: Aprovado — preço dentro do mínimo de venda (RN-01)")
            except ValueError:
                print("ATENÇÃO: preço do card ilegível:", repr(preco_encontrado))

        # Apoio ao registro na planilha
        lucro = 0.83 * livro["preco"] - 4.00
        classificacao = "verde (saldo > R$ 10,00)" if lucro > 10.00 else "saldo <= R$ 10,00"
        print(f"Lucro pela fórmula (0,83 x preço - 4,00): {fmt_brl(lucro)} — {classificacao}; registrar na planilha")
    else:
        print("TC-11: ATENÇÃO: Livro 11 NÃO apareceu nos resultados do filtro (conferir evidência)")

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-11_livro11_filtro_preco.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    contexto.close()
    navegador.close()