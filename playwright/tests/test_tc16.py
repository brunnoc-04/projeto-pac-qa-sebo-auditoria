# -*- coding: utf-8 -*-
# TC-16: Livro em bom estado (2 fotos) — valida a régua de fotos na página de detalhe
# Massa: Livro 1 'A Psicologia da Alquimia Financeira' (frente3_livros.json)
# Régua: 2 fotos para bom estado; descrição sem termos do dicionário de avarias

import json
import os
import time
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/frente3_livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-20"

ID_ALVO = "L-1"

# Dicionário de avarias: descrição de livro em bom estado não pode citar nenhum termo
TERMOS_AVARIA = [
    "avariado", "avaria", "rasgo", "rasura", "mancha", "amarelado", "oxidação",
    "oxidacao", "grifo", "sublinhado", "fita adesiva", "lombada gasta",
    "marca de manuseio", "marcas de manuseio", "danificado", "dobrado"
]


def abrir_vitrine(pagina, url):
    pagina.goto(url, wait_until="domcontentloaded")
    pagina.wait_for_timeout(2000)
    print("Vitrine carregada (DOM pronto)")
    try:
        pagina.locator("g > path").click(timeout=8000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu na vitrine, seguindo")


def fechar_popup_se_aparecer(pagina, onde):
    # O pop-up aparece depois da navegação ao detalhe
    try:
        pagina.locator("g > path").click(timeout=5000)
        print(f"Pop-up de aniversário fechado ({onde})")
    except Exception:
        print(f"Pop-up não apareceu ({onde}), seguindo")


def rolar_pagina(pagina):
    # Cards só renderizam ao entrar na tela
    altura_total = pagina.evaluate("document.body.scrollHeight")
    posicao = 0
    while posicao < altura_total:
        posicao += 600
        pagina.evaluate(f"window.scrollTo(0, {posicao})")
        pagina.wait_for_timeout(400)
        altura_total = pagina.evaluate("document.body.scrollHeight")
    pagina.evaluate("window.scrollTo(0, 0)")
    pagina.wait_for_timeout(1000)


def src_foto_principal(pagina):
    # A foto principal é a maior imagem renderizada da página
    return pagina.evaluate("""() => {
        const imgs = Array.from(document.querySelectorAll('img'));
        let maior = null, area = 0;
        for (const im of imgs) {
            const r = im.getBoundingClientRect();
            const a = r.width * r.height;
            if (a > area && im.src) { area = a; maior = im; }
        }
        return maior ? maior.src : null;
    }""")


def esperar_src_mudar(pagina, src_anterior, timeout_ms):
    inicio = time.time()
    while (time.time() - inicio) * 1000 < timeout_ms:
        atual = src_foto_principal(pagina)
        if atual and atual != src_anterior:
            return atual
        pagina.wait_for_timeout(300)
    return src_foto_principal(pagina)


def contar_por_diretorio(pagina):
    # As fotos do anúncio dividem o diretório do CDN (o código do livro está no path).
    # O carrossel clona os slides, então a contagem é por src ÚNICO — e a query
    # string (que contém barras) é removida antes de derivar o diretório.
    src_principal = src_foto_principal(pagina)
    if not src_principal:
        print("Camada 2: sem imagem principal")
        return 0, []
    diretorio = src_principal.split("?")[0].rsplit("/", 1)[0] + "/"
    srcs = pagina.evaluate("""(dir) => {
        const imgs = Array.from(document.querySelectorAll('img'));
        const unicos = new Set();
        for (const im of imgs) {
            const r = im.getBoundingClientRect();
            if (im.src && im.src.startsWith(dir) && r.width > 100) {
                unicos.add(im.src.split('?')[0]);
            }
        }
        return Array.from(unicos);
    }""", diretorio)
    print(f"Camada 2: diretório das fotos do anúncio: {diretorio}")
    return len(srcs), srcs


def contar_fotos(pagina):
    # Camada 1: walk com espera ativa (carrossel que troca o src da foto ativa)
    # Camada 2: carrossel deslizante (clona slides, src não muda) — contagem
    # por srcs únicos do diretório do anúncio
    botao_next = pagina.get_by_role("button", name="Next slide")
    if botao_next.count() == 0:
        print("Botão 'Next slide' ausente — galeria de foto única")
        return 1, ["foto única (sem botão Next)"]
    botao = botao_next.first
    vistos = []
    for passo in range(10):
        src = src_foto_principal(pagina)
        if src and src in vistos:
            print(f"Walk: src repetiu no passo {passo + 1} — fim da galeria")
            break
        if src:
            vistos.append(src)
        try:
            if botao.is_disabled():
                print("Walk: botão desabilitado — última foto alcançada")
                break
        except Exception:
            break
        botao.click()
        novo_src = esperar_src_mudar(pagina, src, 5000)
        if novo_src == src:
            print(f"Walk: src NÃO mudou após o Next (passo {passo + 1}) — carrossel desliza, fotos já no DOM")
            return contar_por_diretorio(pagina)
    return len(vistos), vistos


def contar_miniaturas(pagina):
    # Diagnóstico: imagens de tamanho de miniatura na página
    return pagina.evaluate("""() => {
        const imgs = Array.from(document.querySelectorAll('img'));
        let n = 0;
        for (const im of imgs) {
            const r = im.getBoundingClientRect();
            if (r.width >= 40 && r.width <= 250 && r.height >= 40 && im.src) n++;
        }
        return n;
    }""")


def ler_descricao(pagina):
    # O bloco pode vir truncado com um 'Veja mais' embutido — o clique precisa ser
    # DENTRO do bloco de descrição (outras seções da página também têm 'Veja mais')
    resultado = pagina.evaluate("""() => {
        const els = Array.from(document.querySelectorAll('*'));
        let bloco = null;
        for (const el of els) {
            const t = (el.innerText || '').trim();
            if (t.startsWith('Descrição:') && (!bloco || t.length > (bloco.innerText || '').trim().length)) bloco = el;
        }
        if (!bloco) return 'bloco não encontrado';
        for (const a of bloco.querySelectorAll('*')) {
            if ((a.textContent || '').trim() === 'Veja mais') { a.click(); return 'expandido'; }
        }
        return 'sem veja mais';
    }""")
    if resultado == "expandido":
        pagina.wait_for_timeout(1000)
        print("Bloco de descrição expandido ('Veja mais' interno)")
    else:
        print(f"Expansão: {resultado}")
    texto = pagina.evaluate("""() => {
        const els = Array.from(document.querySelectorAll('*'));
        let melhor = '';
        for (const el of els) {
            const t = (el.innerText || '').trim();
            if (t.startsWith('Descrição:') && t.length > melhor.length) melhor = t;
        }
        return melhor;
    }""")
    return texto.replace("\n", " ").replace("Veja mais", "").strip()


with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

livro = None
for item in dados["livros"]:
    if item["id"] == ID_ALVO:
        livro = item
if livro is None:
    print(f"ATENÇÃO: o id {ID_ALVO} não existe no frente3_livros.json (validar a massa)")
    raise SystemExit

termo = livro["titulo"][:20]
regua = dados["regua_fotos"]
minimo_regua = regua["bom_estado"] if livro["estado"] == "bom" else regua["avariado"]
rotulo_estado = "em bom estado" if livro["estado"] == "bom" else "avariado"
print(f"Testando {livro['id']}: {livro['titulo']} (estado na lista: {livro['estado']}; régua: {minimo_regua} fotos)")

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    # Viewport 1440x900: o padrão (1280x720) deixa a página com aparência de zoom
    contexto = navegador.new_context(locale="pt-BR", viewport={"width": 1440, "height": 900})
    pagina = contexto.new_page()

    # PASSO 1: vitrine, rolagem e abertura do anúncio
    abrir_vitrine(pagina, dados["vitrine_ev"])
    rolar_pagina(pagina)
    print("Rolagem concluída — cards renderizados")

    link_card = pagina.get_by_role("link", name=termo).first
    if link_card.count() == 0:
        total_cards = pagina.locator(".product-list__items .product-item").count()
        print(f"ATENÇÃO: link do card não encontrado após a rolagem | cards no DOM: {total_cards}")
        if total_cards > 0:
            primeiro = pagina.locator(".product-list__items .product-item").first.inner_text()
            print("Texto do 1º card:", primeiro.replace("\n", " | ")[:150])
        raise SystemExit

    link_card.click()
    pagina.wait_for_load_state("domcontentloaded")
    pagina.wait_for_timeout(2000)
    print("Página de detalhe aberta:", pagina.url)
    if "/livro/" not in pagina.url:
        print("ATENÇÃO: a URL não é de página de detalhe — conferir evidência")

    fechar_popup_se_aparecer(pagina, "página de detalhe")

    # PASSO 2: contar as fotos da galeria
    total_fotos, fontes = contar_fotos(pagina)
    print(f"Fotos contadas na galeria: {total_fotos}")
    for f in fontes[:6]:
        print("  foto:", str(f)[:100])
    print(f"Anunciadas na massa: {livro['fotos_anunciadas']}")
    print(f"Miniaturas detectadas (diagnóstico): {contar_miniaturas(pagina)}")

    # PASSO 3: ler a descrição publicada
    descricao = ler_descricao(pagina)
    print("Descrição publicada:", descricao[:300])

    # PASSO 4: aplicar a régua e os checks do caso
    print("---")
    if total_fotos >= minimo_regua:
        print(f"Régua de fotos ATENDIDA: {total_fotos} fotos >= mínimo de {minimo_regua} para livro {rotulo_estado}")
    else:
        print(f"ATENÇÃO: {total_fotos} fotos < mínimo de {minimo_regua} da régua para livro {rotulo_estado}")

    estado_ok = "bom estado" in descricao.lower()
    if livro["estado"] == "bom":
        print("Estado declarado na descrição:", "CONFERE com a Lista (bom estado)" if estado_ok else "NÃO menciona 'bom estado' — conferir")

        termos_encontrados = [t for t in TERMOS_AVARIA if t in descricao.lower()]
        if termos_encontrados:
            print(f"ATENÇÃO: descrição de livro em bom estado cita termos do dicionário de avarias: {termos_encontrados}")
        else:
            print("Descrição SEM termos do dicionário de avarias (conforme a régua para bom estado)")

        if total_fotos >= minimo_regua and estado_ok and not termos_encontrados:
            print("TC-16: Aprovado — anúncio CONFORME a régua (2 fotos, estado declarado, descrição limpa)")
        else:
            print("TC-16: ATENÇÃO — conferir os itens acima antes de protocolar")
    else:
        print("TC-16: caso desenhado para livro em bom estado — conferir a massa se este log for de outro livro")

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-16_livro1_detalhe_fotos.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    contexto.close()
    navegador.close()