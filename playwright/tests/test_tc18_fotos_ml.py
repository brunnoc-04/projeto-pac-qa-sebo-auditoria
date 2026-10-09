import json
import re
from pathlib import Path
from playwright.sync_api import Page, expect

# --- Caminhos robustos ---
TESTS = Path(__file__).parent
RAIZ = TESTS.parent.parent

# --- Gabarito (massa de dados) ---
dados = json.loads((TESTS.parent / "data" / "livros.json").read_text(encoding="utf-8"))
LIVROS = dados["livros"]

# --- Seletores descobertos no DevTools (ML) ---
RADIOS_FOTOS = ".ui-pdp-gallery__input"
GALERIA = ".ui-pdp-gallery"
MINIATURAS = ".ui-pdp-gallery__label"
IMG_PRINCIPAL = ".ui-pdp-gallery__figure img"

DATA_CICLO = "2026-10-08"

# Tempo de paciência com o captcha: 2 minutos para o humano resolver
TEMPO_CAPTCHA = 120_000


def captcha_detectado(page: Page) -> bool:
    """Detecta sinais do desafio anti-bot (URL de captcha, título da página, iframes)."""
    sinais = ["captcha", "recaptcha", "verify"]
    url_baixa = page.url.lower()
    if any(s in url_baixa for s in sinais):
        return True
    if page.locator("iframe[src*='recaptcha'], iframe[title*='recaptcha'], .g-recaptcha").count() > 0:
        return True
    return False


def fechar_popup_frete(page: Page) -> None:
    """Fecha modais e overlays do ML (frete/CEP, onboarding, cookies), se aparecerem."""
    candidatos = [
        "button[aria-label='Fechar']",          # botão de fechar por acessibilidade
        "button[aria-label='Close']",
        ".ui-pdp-modal__close",                 # X do modal de frete/CEP
        ".onboarding-cp button",                # botão do overlay de onboarding
        "[class*='onboarding'] button",         # variações de onboarding
        "[class*='cookie'] button",             # banner de cookies, se aparecer
    ]
    for seletor in candidatos:
        botao = page.locator(seletor).first
        if botao.count() > 0 and botao.is_visible():
            botao.click(force=True)             # force=True: clica mesmo se algo sobrepor
            page.wait_for_timeout(500)
    page.keyboard.press("Escape")               # fecha o que sobrou (fallback)
    page.wait_for_timeout(300)


def esperar_foto_carregada(page: Page) -> None:
    """Espera condicional: só libera o print quando a imagem tem pixels de verdade."""
    img = page.locator(IMG_PRINCIPAL).first
    expect(img).to_be_visible(timeout=TEMPO_CAPTCHA)
    page.wait_for_function(
        "() => { const i = document.querySelector('.ui-pdp-gallery__figure img');"
        " return i && i.complete && i.naturalWidth > 0; }",
        timeout=TEMPO_CAPTCHA,
    )


def total_de_fotos(page: Page) -> int:
    """Fonte 1: conta os radio buttons. Fonte 2: aria-label 'Imagem 1 de 2'."""
    n_radios = page.locator(RADIOS_FOTOS).count()

    botao = page.locator(".ui-pdp-gallery__thumbnail").first
    rotulo = botao.get_attribute("aria-label") or ""
    match = re.search(r"Imagem\s+\d+\s+de\s+(\d+)", rotulo)
    n_rotulo = int(match.group(1)) if match else 0

    if n_rotulo:
        assert n_radios == n_rotulo, (
            f"Contagem inconsistente: radios = {n_radios}, rótulo diz {n_rotulo}"
        )
    return n_radios


def test_tc18_padrao_de_fotos_mercado_livre(page: Page):
    """TC-18 no ML (RN-08): cada anúncio deve ter exatamente as fotos
    esperadas pela regra de negócio (gabarito: 2 = bom estado)."""
    resultados = []

    for livro in LIVROS:
        page.goto(livro["url_ml"], wait_until="domcontentloaded")

        if captcha_detectado(page):
            print(f"\n>>> CAPTCHA em {livro['id']}! Resolva no navegador aberto — "
                  f"o teste espera até 2 minutos e segue sozinho. <<<")

        # Espera paciente pela galeria: cobre o tempo de resolver captcha
        galeria = page.locator(GALERIA)
        expect(galeria).to_be_visible(timeout=TEMPO_CAPTCHA)

        fechar_popup_frete(page)

        n_fotos = total_de_fotos(page)
        esperado = livro["fotos_esperadas"]
        assert n_fotos == esperado, (
            f"{livro['id']} ({livro['titulo']}): {n_fotos} foto(s), "
            f"esperado {esperado} — viola a régua de fotos (RN-08)"
        )

        destino_dir = RAIZ / "evidencias" / DATA_CICLO
        destino_dir.mkdir(parents=True, exist_ok=True)

        esperar_foto_carregada(page)
        page.screenshot(path=str(destino_dir / f"TC-18_{livro['id']}_ml_foto1.png"))
        if n_fotos > 1:
            page.locator(MINIATURAS).nth(1).click(force=True)   # <<< força o clique mesmo com overlay
            page.wait_for_timeout(1500)
            esperar_foto_carregada(page)
            page.screenshot(path=str(destino_dir / f"TC-18_{livro['id']}_ml_foto2.png"))

        resultados.append((livro["id"], livro["titulo"], n_fotos))

    with open(RAIZ / "evidencias" / DATA_CICLO / "TC-18_log_ml.csv", "w",
              encoding="utf-8", newline="") as f:
        f.write("id_livro;titulo;fotos_encontradas;veredito\n")
        for id_livro, titulo, n_fotos in resultados:
            f.write(f"{id_livro};{titulo};{n_fotos};PASSOU\n")