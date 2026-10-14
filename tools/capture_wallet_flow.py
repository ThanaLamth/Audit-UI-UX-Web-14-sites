"""
tools/capture_wallet_flow.py
Automate MetaMask setup + KyberSwap connect + tip link flow.
Captures screenshots at every key step.
"""
import asyncio, os, shutil, json
from pathlib import Path
from playwright.async_api import async_playwright

MNEMONIC   = "napkin innocent ugly turn pigeon sport dentist series split normal page require"
WALLET_PW  = "Kyber@Demo2026!"
MM_EXT_ID  = "nkbihfbeogaeaoehlefnkodbefgpgknn"
MM_EXT_PATH = rf"C:\Users\admin\AppData\Local\Google\Chrome\User Data\Default\Extensions\{MM_EXT_ID}\13.48.0.0_0"
USER_DATA  = rf"C:\Users\admin\AppData\Local\Temp\pw-mm-demo"
TIP_URL    = (
    "https://kyberswap.com/swap/ethereum"
    "?inputCurrency=ETH"
    "&outputCurrency=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    f"&feeReceiver=0x0DA2a82ED2c387d1751ccbAf999A80b65bdb269E"
    "&enableTip=true"
)
OUT_DIR    = Path(r"C:\Users\admin\AppData\Local\Temp\audit-web-14-sites\screenshots\kyberswap\wallet-flow")

async def shot(page, name: str, msg: str = ""):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / f"{name}.png"
    await page.screenshot(path=str(p), full_page=False)
    kb = p.stat().st_size // 1024
    print(f"  [SHOT] {name}.png ({kb}KB)  {msg}")
    return str(p)

async def wait_mm_page(context, timeout=15000):
    """Wait for MetaMask background/popup page to appear."""
    deadline = asyncio.get_event_loop().time() + timeout / 1000
    while asyncio.get_event_loop().time() < deadline:
        for pg in context.pages:
            if MM_EXT_ID in pg.url:
                return pg
        await asyncio.sleep(0.3)
    return None

async def click_if_visible(page, selector, timeout=3000):
    """Click element if visible, silently skip if not."""
    try:
        el = page.locator(selector).first
        if await el.is_visible(timeout=timeout):
            await el.click()
            return True
    except Exception:
        pass
    return False

async def setup_metamask(context):
    """Full MetaMask v13 onboarding: import wallet with seed phrase."""
    mm_url = f"chrome-extension://{MM_EXT_ID}/home.html"
    mm_page = None

    for pg in context.pages:
        if MM_EXT_ID in pg.url:
            mm_page = pg
            break
    if not mm_page:
        mm_page = await context.new_page()
        await mm_page.goto(mm_url)

    await mm_page.bring_to_front()
    await mm_page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(2)
    await shot(mm_page, "01_mm_welcome", "MetaMask welcome — Create or import")

    # Handle unlock screen if wallet already set up (re-runs with same user data)
    try:
        pw_field = mm_page.locator('input[type="password"]').first
        unlock_btn = mm_page.locator('button:has-text("Unlock")').first
        if await pw_field.is_visible(timeout=3000):
            await pw_field.fill(WALLET_PW)
            await unlock_btn.click()
            await asyncio.sleep(2)
            await shot(mm_page, "01b_mm_unlocked", "MetaMask unlocked with password")
            return mm_page
    except Exception:
        pass

    # Step 1: "I have an existing wallet"
    await mm_page.get_by_text("I have an existing wallet", exact=True).click(timeout=8000)
    await asyncio.sleep(2)
    await shot(mm_page, "02_mm_import_options", "Import options: Google / Apple / Telegram / Seed Phrase")

    # Step 2: "Import using Secret Recovery Phrase"
    await mm_page.get_by_text("Import using Secret Recovery Phrase", exact=True).click(timeout=8000)
    await asyncio.sleep(2)
    await shot(mm_page, "03_mm_seed_input", "Secret Recovery Phrase input screen")

    # Step 3: Type seed phrase word-by-word (triggers React events natively)
    ta = mm_page.locator('textarea').first
    await ta.click()
    # type() simulates real keystrokes — React picks up onChange
    await ta.type(MNEMONIC, delay=40)
    await asyncio.sleep(2)
    await shot(mm_page, "04_mm_seed_filled", "Seed phrase typed — Continue should activate")

    # Continue button is now active — click it
    await shot(mm_page, "04b_mm_continue_active", "Continue button active — all 12 words filled")
    await mm_page.locator('button:has-text("Continue")').first.click(timeout=8000)
    await asyncio.sleep(2)
    await shot(mm_page, "05_mm_after_seed", "After seed — password screen")

    # Step 4: Set password if prompted
    pws = await mm_page.locator('input[type="password"]').all()
    if len(pws) >= 1:
        await pws[0].fill(WALLET_PW)
        if len(pws) >= 2:
            await pws[1].fill(WALLET_PW)
        # Check terms
        await click_if_visible(mm_page, 'input[type="checkbox"]')
        # Click import/confirm
        for label in ["Create password", "Import my wallet", "Import", "Confirm"]:
            try:
                btn = mm_page.locator(f'button:has-text("{label}")').first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    await asyncio.sleep(3)
                    break
            except Exception:
                pass
        await shot(mm_page, "06_mm_importing", "Wallet importing...")

    # Click through any remaining onboarding steps
    await asyncio.sleep(2)
    for label in ["Got it!", "Done", "Next", "Skip", "Continue"]:
        await click_if_visible(mm_page, f'button:has-text("{label}")', timeout=2000)
        await asyncio.sleep(0.8)

    await asyncio.sleep(2)
    await shot(mm_page, "07_mm_ready", "MetaMask ready — wallet imported")
    return mm_page

async def connect_to_kyberswap(context, mm_page):
    """Navigate to KyberSwap tip link and connect MetaMask."""
    ks_page = await context.new_page()
    await ks_page.goto(TIP_URL, timeout=60000, wait_until="domcontentloaded")
    await asyncio.sleep(6)
    await shot(ks_page, "06_kyberswap_with_reflink", "KyberSwap opened with tip/ref link — ETH→USDC pre-filled")

    # Click Connect button - KyberSwap uses green "Connect" button top-right
    await asyncio.sleep(3)
    connect_btn = ks_page.get_by_role("button", name="Connect").first
    await connect_btn.click(timeout=15000)
    await asyncio.sleep(2)
    await shot(ks_page, "07_wallet_picker", "Wallet selection modal — MetaMask, WalletConnect, Rabby...")

    # Accept Terms of Use checkbox first (required before wallets become clickable)
    try:
        terms_cb = ks_page.locator('input[type="checkbox"]').first
        if await terms_cb.is_visible(timeout=3000):
            await terms_cb.click()
            await asyncio.sleep(0.5)
    except Exception:
        pass
    await shot(ks_page, "07b_terms_accepted", "Terms accepted — wallet options now active")

    # Click MetaMask
    await ks_page.get_by_text("MetaMask", exact=True).first.click(timeout=8000)

    await asyncio.sleep(3)

    # Listen for MetaMask popup via page event
    popup = None
    popup_future = asyncio.get_event_loop().create_future()
    def on_page(pg):
        if MM_EXT_ID in pg.url and not popup_future.done():
            popup_future.set_result(pg)
    context.on("page", on_page)
    try:
        popup = await asyncio.wait_for(popup_future, timeout=10.0)
    except asyncio.TimeoutError:
        for pg in context.pages:
            if MM_EXT_ID in pg.url and pg != mm_page:
                popup = pg
                break
    context.remove_listener("page", on_page)
    if popup:
        await asyncio.sleep(1.5)
        await popup.bring_to_front()
        await asyncio.sleep(1)
        await shot(popup, "08_mm_connect_popup", "MetaMask: Connect to KyberSwap popup")
        for label in ["Next", "Connect"]:
            try:
                btn = popup.locator(f'button:has-text("{label}")').last
                if await btn.is_visible(timeout=4000):
                    await btn.click()
                    await asyncio.sleep(1.5)
                    await shot(popup, f"09_mm_{label.lower()}", f"MetaMask: clicked {label}")
            except Exception:
                pass
    else:
        print("  [WARN] MetaMask popup not caught")

    await asyncio.sleep(3)
    await ks_page.bring_to_front()
    await asyncio.sleep(2)
    await shot(ks_page, "10_kyberswap_connected", "KyberSwap with wallet connected — shows address")

    return ks_page

async def capture_swap_with_tip(context, ks_page):
    """Enter amount and capture the tip section in swap details."""
    # Enter amount
    try:
        amount_inp = ks_page.locator('input[data-testid="swap-currency-input"], .token-amount-input, input[placeholder*="0.0"]').first
        await amount_inp.fill("0.01")
        await asyncio.sleep(3)
        await shot(ks_page, "11_swap_amount_entered", "Swap: 0.01 ETH → USDC with tip link active")
    except Exception as e:
        print(f"  ⚠️ Could not fill amount: {e}")

    # Click Swap button to see confirmation
    try:
        swap_btn = ks_page.locator('button:has-text("Swap"), [data-testid="swap-button"]').first
        if await swap_btn.is_visible(timeout=3000):
            await swap_btn.click()
            await asyncio.sleep(2)
            await shot(ks_page, "12_swap_confirm_dialog", "Swap confirmation — tip prompt visible here")
    except Exception as e:
        print(f"  ⚠️ Swap button: {e}")

async def main():
    print(f"\nWallet: {MNEMONIC[:30]}...")
    print(f"Output: {OUT_DIR}\n")

    # Fresh user data dir
    if os.path.exists(USER_DATA):
        shutil.rmtree(USER_DATA, ignore_errors=True)
    os.makedirs(USER_DATA, exist_ok=True)

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=USER_DATA,
            headless=False,
            args=[
                f"--disable-extensions-except={MM_EXT_PATH}",
                f"--load-extension={MM_EXT_PATH}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-popup-blocking",
            ],
            proxy={"server": "http://103.82.22.77:12775", "username": "29dt", "password": "29dt"},
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )

        await asyncio.sleep(3)  # wait for extension to load

        mm_page = await setup_metamask(context)
        ks_page = await connect_to_kyberswap(context, mm_page)
        await capture_swap_with_tip(context, ks_page)

        await asyncio.sleep(2)
        print(f"\nAll done! Screenshots in {OUT_DIR}")
        await context.close()

asyncio.run(main())

