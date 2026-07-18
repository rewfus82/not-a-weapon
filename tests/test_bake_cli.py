import json

import pytest

from resolver.bake.__main__ import main
from resolver.bake.run import write_records
from resolver.bake.schema import BakeRecord, contract_fingerprint


def test_select_writes_a_reviewable_selection(tmp_path, capsys):
    out = tmp_path / "combos.json"
    assert main(["select", "--n", "80", "--seed", "1", "--out", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["n"] == 80 and len(payload["combos"]) == 80
    assert "80" in capsys.readouterr().out


def test_run_without_key_exits_loud_without_spending(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    combos = tmp_path / "combos.json"
    main(["select", "--n", "10", "--seed", "1", "--out", str(combos)])
    code = main(["run", "--combos", str(combos), "--out", str(tmp_path / "s.jsonl")])
    assert code == 1
    assert not (tmp_path / "s.jsonl").exists()


def test_dedup_without_key_exits_loud(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    scaffolds = tmp_path / "s.jsonl"
    write_records(scaffolds, {})
    assert main(["dedup", "--scaffolds", str(scaffolds),
                 "--names", str(tmp_path / "names.json")]) == 1


def test_report_runs_offline(tmp_path):
    combos = tmp_path / "combos.json"
    main(["select", "--n", "10", "--seed", "1", "--out", str(combos)])
    scaffolds = tmp_path / "s.jsonl"
    payload = json.loads(combos.read_text(encoding="utf-8"))
    cid = payload["combos"][0]["combo_id"]
    write_records(scaffolds, {cid: BakeRecord(
        combo_id=cid, status="unresolved",
        contract_fingerprint=contract_fingerprint(), baked_at="t")})
    out = tmp_path / "report.md"
    assert main(["report", "--scaffolds", str(scaffolds), "--combos", str(combos),
                 "--wave", "test", "--out", str(out)]) == 0
    assert "unresolved: 1/1" in out.read_text(encoding="utf-8")


def test_unknown_command_fails():
    with pytest.raises(SystemExit):
        main(["frobnicate"])
