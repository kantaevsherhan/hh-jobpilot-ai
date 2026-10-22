"""Всплывающее окно не должно перекрывать кнопку или скрывать капчу."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.browser.apply import open_form
from app.browser.selectors import HH
from app.core.errors import AppError


def make_page(*, overlay: bool = True, closable: bool = True, captcha: bool = False):
    page = MagicMock()
    state = {"overlay": overlay, "captcha": captcha}
    locators = {}

    async def escape(_key):
        if closable:
            state["overlay"] = False

    async def click_apply():
        # До исправления нажатие происходило при перекрытой кнопке.
        assert not state["overlay"]

    def locator(selector):
        if selector not in locators:
            item = MagicMock()
            item.first = item
            item.count = AsyncMock(return_value=0)
            item.is_visible = AsyncMock(return_value=False)
            locators[selector] = item
        return locators[selector]

    page.locator.side_effect = locator
    page.keyboard.press = AsyncMock(side_effect=escape)
    page.wait_for_timeout = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock()
    locator(HH.CAPTCHA).count.side_effect = lambda: int(state["captcha"])
    locator(HH.DIALOG).count.side_effect = lambda: int(state["overlay"])
    locator(HH.APPLY_BUTTON).count.return_value = 1
    locator(HH.APPLY_BUTTON).click = AsyncMock(side_effect=click_apply)
    locator(HH.RESUME_DELIVERED).count.return_value = 1
    return page


@pytest.mark.parametrize("overlay", [True, False])
async def test_окно_закрывается_перед_нажатием_отклика(overlay: bool) -> None:
    page = make_page(overlay=overlay)

    form = await open_form(page)

    assert form.sent_on_click is True
    page.locator(HH.APPLY_BUTTON).click.assert_awaited_once()


async def test_незакрытое_окно_блокирует_отклик() -> None:
    page = make_page(closable=False)

    with pytest.raises(AppError) as exc:
        await open_form(page)

    assert exc.value.error_code == "APPLY_FORM_UNKNOWN"
    page.locator(HH.APPLY_BUTTON).click.assert_not_awaited()


async def test_капча_не_закрывается_и_блокирует_отклик() -> None:
    page = make_page(captcha=True)

    with pytest.raises(AppError) as exc:
        await open_form(page)

    assert exc.value.error_code == "HH_CAPTCHA"
    page.keyboard.press.assert_not_awaited()
    page.locator(HH.APPLY_BUTTON).click.assert_not_awaited()


async def test_капча_после_закрытия_окна_тоже_блокирует_отклик() -> None:
    page = make_page()
    page.locator(HH.CAPTCHA).count.side_effect = [0, 1]

    with pytest.raises(AppError) as exc:
        await open_form(page)

    assert exc.value.error_code == "HH_CAPTCHA"
    page.locator(HH.APPLY_BUTTON).click.assert_not_awaited()
