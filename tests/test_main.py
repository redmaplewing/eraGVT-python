from eragvt.__main__ import main


def test_check_data_runs(capsys):
    assert main(["--check-data"]) == 0
    out = capsys.readouterr().out
    assert "角色" in out and "77" in out
    assert "開局狀態存讀檔：OK" in out
