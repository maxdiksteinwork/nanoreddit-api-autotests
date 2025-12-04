# conftest.py

import os
import shutil
import pytest
from dotenv import load_dotenv
from settings import get_settings

SECRET_PLACEHOLDER = "***"
ALLURE_DIR = "reports/allure-results"

pytest_plugins = (
    "utils.fixtures.base",
    "utils.fixtures.auth",
    "utils.fixtures.admin",
    "utils.fixtures.posts",
    "utils.fixtures.comments",
    "utils.fixtures.apis"
)


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    --env=local|dev|stg|prod-test
    """

    parser.addoption(
        "--env",
        action="store",
        default="local",
        choices=["local", "dev", "stg", "prod-test"],
        help=(
            "Target environment for tests. "
            "Controls which .env.* file will be loaded "
            "(local -> .env, dev -> .env.dev, stg -> .env.stg, prod-test -> .env.prod-test)."
        ),
    )


def _load_env_for_pytest(config: pytest.Config) -> str:
    """
    выбирает .env-файл на основе опции --env и подгружает его в переменные окружения.
    """
    env_name: str = config.getoption("--env")
    env_file_map = {
        "local": ".env",
        "dev": ".env.dev",
        "stg": ".env.stg",
        "prod-test": ".env.prod-test",
    }
    env_file = env_file_map.get(env_name, ".env")
    os.environ["TEST_ENV"] = env_name

    load_dotenv(dotenv_path=env_file, override=True)
    return env_file


def pytest_configure(config: pytest.Config):
    _load_env_for_pytest(config)
    # лёгкая проверка, что настройки читаются (и чтобы быстрее поймать проблемы с env)
    _ = get_settings()

    config.addinivalue_line("markers", "doc_issue: тест формально проходит, но есть ошибка в документации")
    config.addinivalue_line("markers", "no_validation_for_max_value: отсутствует валидация верхних значений")
    config.addinivalue_line(
        "markers",
        "password_special_symbol_issue: разные требования к паролю на этапе регистрации и логина",
    )

    # очистка результатов Allure перед каждым прогоном
    if os.path.exists(ALLURE_DIR):
        try:
            shutil.rmtree(ALLURE_DIR)
        except (PermissionError, OSError):
            try:
                for filename in os.listdir(ALLURE_DIR):
                    file_path = os.path.join(ALLURE_DIR, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except (PermissionError, OSError):
                        # пропускаем заблокированные файлы
                        pass
            except (PermissionError, OSError):
                pass

    os.makedirs(ALLURE_DIR, exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    os.makedirs(ALLURE_DIR, exist_ok=True)

    settings = get_settings()

    env_file = os.path.join(ALLURE_DIR, "environment.properties")
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"Base URL={settings.base_url}\n")
        f.write(f"DB Host={settings.db_host}\n")
        f.write(f"DB Port={settings.db_port}\n")
        f.write(f"DB Name={settings.db_name}\n")
        f.write(f"DB User={settings.db_user}\n")
        f.write("DB Password=not logged (stored securely)\n")
        f.write(f"Test Env={os.environ.get('TEST_ENV', 'local')}\n")
        f.write(f"Build ID={os.environ.get('CI_PIPELINE_ID', 'manual')}\n")

    print(f"\n[ALLURE] environment.properties generated at: {os.path.abspath(env_file)}")


def pytest_report_teststatus(report):
    if report.when != "call":
        return

    keywords = {k.lower() for k in report.keywords}

    if "doc_issue" in keywords:
        if report.failed:
            return "doc_issue", "D", "DOCISSUE-FAIL"
        else:
            return "doc_issue", "D", "DOCISSUE"

    if "no_validation_for_max_value" in keywords:
        if report.failed:
            return "maxval", "M", "MAXVAL-FAIL"
        else:
            return "maxval", "M", "MAXVAL"

    if "password_special_symbol_issue" in keywords:
        if report.failed:
            return "password_issue", "P", "PASSISSUE-FAIL"
        else:
            return "password_issue", "P", "PASSISSUE"


def pytest_terminal_summary(terminalreporter, exitstatus):
    tr = terminalreporter

    # собираем все репорты по кастомным статусам
    for mark_name, label in [
        ("doc_issue", "DOC ISSUE"),
        ("maxval", "MAX VALUE ISSUE"),
        ("password_issue", "PASSWORD SYMBOL ISSUE"),
    ]:
        reps = tr.stats.get(mark_name, [])
        if reps:
            tr.write_sep("-", f"{label} ({len(reps)})")
            for rep in reps:
                # rep.nodeid — путь к тесту, rep.outcome — passed/failed
                tr.write_line(f"{rep.nodeid} -> {rep.outcome.upper()}")
