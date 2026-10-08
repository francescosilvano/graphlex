import importlib
import json
from pathlib import Path


def test_search_params_omit_initial_cursor():
    from app.main import _search_params

    params = _search_params("Green Transition")

    assert params.q == "green transition"
    assert params.cursor is None


def test_progress_indicator_reports_percentage_and_eta():
    from app.main import ProgressIndicator

    progress = ProgressIndicator()
    progress.start("Working", total=4)
    progress.update("Working", completed=2)

    rendered = progress._render()
    progress.stop()

    assert "50.0%" in rendered
    assert "ETA" in rendered
    assert "V:OFF" in rendered


def test_verbose_log_is_single_line_when_not_interactive(capsys):
    from app.main import ProgressIndicator

    progress = ProgressIndicator(verbose=True)
    progress.verbose_log("page 2, 99 posts")

    output = capsys.readouterr().out
    assert output.count("[verbose]") == 1
    assert "\033[K" not in output


def test_main_handles_keyboard_interrupt(capsys, monkeypatch):
    from app import main as main_module

    def interrupt():
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "_run_collection_and_analysis", interrupt)

    assert main_module.main() == 130
    output = capsys.readouterr().out
    assert "Operation cancelled by user (Ctrl+C)." in output
    assert "No further posts or analysis will be processed." in output


def test_verbose_toggle_hides_and_restores_history(capsys):
    from app.main import ProgressIndicator

    progress = ProgressIndicator(verbose=True)
    progress._interactive = True
    progress.verbose_log("page 2, 99 posts")
    progress._toggle_verbose()
    hidden_output = capsys.readouterr().out

    assert progress._verbose is False
    assert progress._verbose_history == ["page 2, 99 posts"]
    assert "\033[1A" in hidden_output

    progress._toggle_verbose()
    restored_output = capsys.readouterr().out
    assert progress._verbose is True
    assert restored_output.count("[verbose]") == 1
    assert "page 2, 99 posts" in restored_output


def test_verbose_history_keeps_pages_logged_while_hidden(capsys):
    from app.main import ProgressIndicator

    progress = ProgressIndicator(verbose=False)
    progress._interactive = True
    progress.verbose_log("page 5, 97 posts")
    progress.verbose_log("page 35, 99 posts")
    progress.verbose_log("page 36, 96 posts")

    assert progress._verbose_history == [
        "page 5, 97 posts",
        "page 35, 99 posts",
        "page 36, 96 posts",
    ]
    assert capsys.readouterr().out == ""

    progress._toggle_verbose()
    restored_output = capsys.readouterr().out
    assert restored_output.count("[verbose]") == 3
    assert "page 5, 97 posts" in restored_output
    assert "page 35, 99 posts" in restored_output
    assert "page 36, 96 posts" in restored_output


def test_import_networklens():
    networklens = importlib.import_module("networklens")
    assert getattr(networklens, "__version__", None)


def test_keywords_include_required():
    from networklens import config

    expected = [
        "green transition", "greenhouse effect", "loss of biodiversity", "extreme weather events",
        "CO2", "emissions", "global warming", "melting glaciers", "renewable energy", "misinformation",
        "ecosystem", "fossil fuels", "energy consumption", "normatives", "deforestation",
        "flooding", "tesla", "green policies", "rain", "electric vehicles",
        "natural disaster", "clean energy", "net zero", "AI", "heatwaves"
    ]

    actual_lower = {k.lower() for k in config.KEYWORDS}
    for kw in expected:
        assert kw.lower() in actual_lower, f"Missing keyword: {kw}"


def test_user_keyword_file_is_valid_and_used():
    settings_file = Path(__file__).parents[1] / "settings.json"
    settings = json.loads(settings_file.read_text(encoding="utf-8"))

    assert settings["1ST_GROUP"]
    assert settings["2ND_GROUP"]
    assert settings["3RD_GROUP"]
    assert settings["DATE_START"] == "2023-01-01"
    assert settings["DATE_END"] == "2025-11-25"

    from app import config

    assert config.KEYWORDS == (
        settings["1ST_GROUP"]
        + settings["2ND_GROUP"]
        + settings["3RD_GROUP"]
    )
