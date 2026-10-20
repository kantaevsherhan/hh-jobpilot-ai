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

    # Признак входа: пункты личного кабинета в шапке. Имена сверены с живой
    # страницей hh.kz — угадывать их нельзя, у HH они называются не так,
    # как кажется логичным. Ссылки на /applicant/* оставлены запасным
    # вариантом: они переживают переименование data-qa
    LOGGED_IN: Final = (
        '[data-qa="mainmenu_profileAndResumes"], '
        '[data-qa="mainmenu_applicantProfilePage"], '
        '[data-qa="mainmenu_vacancyResponses"], '
        '[data-qa="mainmenu_applicantProfileDesktopDrop"], '
        'a[href^="/applicant/resumes"], '
        'a[href^="/applicant/negotiations"]'
    )
    # Признак обратного: кнопка входа
    LOGIN_BUTTON: Final = '[data-qa="login"], [data-qa="mainmenu_login"], a[href*="/account/login"]'

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
    # Занятость, график и формат работы лежат в трёх разных узлах и названы
    # не «vacancy-*», а по-своему — сверено с живой страницей hh.kz
    VACANCY_EMPLOYMENT: Final = '[data-qa="common-employment-text"]'
    VACANCY_SCHEDULE: Final = '[data-qa="work-schedule-by-days-text"]'
    VACANCY_WORK_FORMAT: Final = '[data-qa="work-formats-text"]'
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
    # После отклика HH показывает блок «Резюме доставлено» без своего data-qa,
    # поэтому он ищется по тексту — и для «уже откликались», и для подтверждения
    RESUME_DELIVERED: Final = ':text("Резюме доставлено")'
    ALREADY_APPLIED: Final = f'[data-qa="vacancy-response-link-view-topic"], {RESUME_DELIVERED}'
    EXTERNAL_APPLY: Final = '[data-qa="vacancy-response-link-top-redirect"]'

    LETTER_TOGGLE: Final = '[data-qa="vacancy-response-letter-toggle"]'
    LETTER_FIELD: Final = (
        '[data-qa="vacancy-response-popup-form-letter-input"], textarea[name="letter"]'
    )
    SUBMIT_BUTTON: Final = '[data-qa="vacancy-response-submit-popup"]'
    # Поле письма под «Резюме доставлено» имеет тот же data-qa, что и в форме,
    # а отправляется своей кнопкой
    LETTER_SUBMIT_AFTER_APPLY: Final = '[data-qa="vacancy-response-letter-submit"]'
    # Предупреждения HH при отклике («вакансия в другой стране») — magritte-alert,
    # без role=dialog
    DIALOG: Final = '[role="dialog"]:visible, [data-qa="magritte-alert"]:visible'
    WARNING_ABORT: Final = '[data-qa="relocation-warning-abort"]'
    APPLY_SUCCESS: Final = (
        f'[data-qa="vacancy-response-success"], [data-qa="chat-title"], {RESUME_DELIVERED}'
    )

    RESUME_SELECT: Final = '[data-qa="resume-select"]'
    # Атрибут содержит два токена через пробел («vacancy-response-question
    # vacancy-response-question_salary_options»), точное совпадение не сработает
    # На странице вакансии есть виджет «Задать вопрос работодателю» с data-qa
    # vacancy-response-question_* — это не вопросы формы. Вопросы, без ответа на
    # которые нельзя откликнуться, HH объявляет этим текстом над формой
    QUESTION_ITEM: Final = (
        '[data-qa="task-body"], :text("ответить на несколько вопросов работодателя")'
    )
    # Резюме скрыто от работодателя — отклик невозможен, пока пользователь сам
    # не поменяет видимость резюме на HH
    HIDDEN_RESUME_WARNING: Final = '[data-qa="hidden-resume-warning"]'

    # Отклики в личном кабинете
    NEGOTIATION_ITEM: Final = '[data-qa="negotiations-item"]'
    NEGOTIATION_STATUS: Final = '[data-qa="negotiations-item-status"]'


# Встроенный в страницу JSON с данными вакансии. Он устойчивее CSS-классов,
# которые меняются каждый релиз HH (§10)
TEMPLATE_STATE_KEYS: Final = ("HH-Lux-InitialState", "HH-Lux-UserDetails", "__INITIAL_STATE__")
