"""Задержки: диапазон, множитель, невозможность нулевой паузы (§20, §30)."""

from app.pipeline.delays import DelayRange, Delays


def test_значение_попадает_в_заданный_диапазон() -> None:
    delays = Delays({"ranges": {"between_vacancies": [3, 8]}})

    values = [delays.seconds("between_vacancies") for _ in range(200)]

    assert all(3 <= value <= 8 for value in values)


def test_значения_не_повторяются() -> None:
    # Ровные интервалы — лишняя нагрузка ровными пачками, так делать нельзя
    delays = Delays({"ranges": {"between_vacancies": [3, 8]}})

    values = {delays.seconds("between_vacancies") for _ in range(50)}

    assert len(values) > 40


def test_множитель_применяется_ко_всем_задержкам() -> None:
    fast = Delays({"speed_multiplier": 0.1, "ranges": {"between_vacancies": [10, 10]}})
    slow = Delays({"speed_multiplier": 2.0, "ranges": {"between_vacancies": [10, 10]}})

    assert round(fast.seconds("between_vacancies"), 3) == 1.0
    assert round(slow.seconds("between_vacancies"), 3) == 20.0


def test_нулевая_задержка_невозможна() -> None:
    delays = Delays({"speed_multiplier": 0, "ranges": {"between_vacancies": [10, 10]}})

    assert delays.multiplier == 0.1
    assert delays.seconds("between_vacancies") > 0


def test_множитель_ограничен_сверху() -> None:
    assert Delays({"speed_multiplier": 99}).multiplier == 3.0


def test_перевёрнутый_диапазон_не_ломает_расчёт() -> None:
    assert 3 <= DelayRange(8, 3).pick() <= 8


def test_незаданные_ключи_берутся_из_дефолтов() -> None:
    delays = Delays({"ranges": {"between_vacancies": [1, 1]}})

    assert 1.0 <= delays.seconds("page_load") <= 2.5


def test_длинная_пауза_каждые_n_вакансий() -> None:
    delays = Delays({"long_pause_every": 12})

    assert delays.needs_long_break(12) is True
    assert delays.needs_long_break(11) is False
    assert delays.needs_long_break(0) is False


def test_оценка_прогона_считается_в_минутах() -> None:
    delays = Delays()

    assert delays.estimate_run_minutes(25) > 40
