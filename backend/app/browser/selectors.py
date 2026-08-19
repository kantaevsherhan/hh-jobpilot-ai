"""Все селекторы HH — только здесь (§9, §33 п.7).

Когда HH поменяет вёрстку (а он поменяет), чинится один этот файл.
Ни одного page.locator("...") со строкой в другом месте быть не должно.
"""

from typing import Final


class HH:
    """Адреса и селекторы hh.kz."""

    BASE_URL: Final = "https://hh.kz"
    SEARCH_URL: Final = "https://hh.kz/search/vacancy"
    RESUME_URL: Final = "https://hh.kz/applicant/resumes"
    APPLICATIONS_URL: Final = "https://hh.kz/applicant/negotiations"

    # Признак того, что пользователь вошёл: блок личного кабинета в шапке
    LOGGED_IN: Final = (
        '[data-qa="mainmenu_applicantProfile"], '
        '[data-qa="mainmenu_myResumes"], '
        '[data-qa="mainmenu_negotiations"]'
    )
    # Признак обратного: кнопка входа
    LOGIN_BUTTON: Final = '[data-qa="login"], [data-qa="mainmenu_login"]'

    CAPTCHA: Final = (
        '[data-qa="account-captcha"], iframe[src*="captcha"], '
        'iframe[src*="recaptcha"], .captcha-container'
    )

    # Выдача поиска: карточки и ссылки на вакансии
    SEARCH_RESULT_ITEM: Final = '[data-qa="vacancy-serp__vacancy"], [data-qa="serp-item"]'
    SEARCH_ITEM_LINK: Final = (
        '[data-qa="serp-item__title"], a[data-qa="vacancy-serp__vacancy-title"]'
    )
    SEARCH_ITEM_COMPANY: Final = '[data-qa="vacancy-serp__vacancy-employer"]'
    SEARCH_ITEM_SALARY: Final = (
        '[data-qa="vacancy-serp__vacancy-compensation"], '
        '[data-qa="vacancy-serp__vacancy_compensation"]'
    )
    SEARCH_NEXT_PAGE: Final = '[data-qa="pager-next"]'

    # Карточка вакансии
    VACANCY_TITLE: Final = '[data-qa="vacancy-title"]'
    VACANCY_DESCRIPTION: Final = '[data-qa="vacancy-description"]'
    VACANCY_COMPANY: Final = (
        '[data-qa="vacancy-company-name"], [data-qa="vacancy-company__details"]'
    )
    VACANCY_SALARY: Final = (
        '[data-qa="vacancy-salary"], [data-qa="vacancy-salary-compensation-type-net"]'
    )
    VACANCY_EXPERIENCE: Final = '[data-qa="vacancy-experience"]'
    VACANCY_EMPLOYMENT: Final = '[data-qa="vacancy-view-employment-mode"]'
    VACANCY_ADDRESS: Final = (
        '[data-qa="vacancy-view-location"], [data-qa="vacancy-view-raw-address"]'
    )
    VACANCY_ARCHIVED: Final = '[data-qa="vacancy-archive-message"], .vacancy-archive'

    # Отклик
    APPLY_BUTTON: Final = (
        '[data-qa="vacancy-response-link-top"], '
        '[data-qa="vacancy-response-link-bottom"], '
        'a[data-qa="vacancy-serp__vacancy_response"]'
    )
    ALREADY_APPLIED: Final = '[data-qa="vacancy-response-link-view-topic"]'
    EXTERNAL_APPLY: Final = '[data-qa="vacancy-response-link-top-redirect"]'

    LETTER_TOGGLE: Final = '[data-qa="vacancy-response-letter-toggle"]'
    LETTER_FIELD: Final = (
        '[data-qa="vacancy-response-popup-form-letter-input"], textarea[name="letter"]'
    )
    SUBMIT_BUTTON: Final = '[data-qa="vacancy-response-submit-popup"]'
    APPLY_SUCCESS: Final = '[data-qa="vacancy-response-success"], [data-qa="chat-title"]'

    RESUME_SELECT: Final = '[data-qa="resume-select"]'
    QUESTION_ITEM: Final = '[data-qa="task-body"], [data-qa="vacancy-response-question"]'

    # Отклики в личном кабинете
    NEGOTIATION_ITEM: Final = '[data-qa="negotiations-item"]'
    NEGOTIATION_STATUS: Final = '[data-qa="negotiations-item-status"]'


# Встроенный в страницу JSON с данными вакансии. Он устойчивее CSS-классов,
# которые меняются каждый релиз HH (§10)
TEMPLATE_STATE_KEYS: Final = ("HH-Lux-InitialState", "HH-Lux-UserDetails", "__INITIAL_STATE__")
