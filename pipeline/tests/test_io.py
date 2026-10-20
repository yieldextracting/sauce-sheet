import json

import pytest

from pipeline.io import ImmutableFileError, write_json, write_once


def test_write_once_refuses_overwrite(tmp_path):
    p = tmp_path / "first-seen" / "20261020-BOS-DET.json"
    write_once(p, {"spreadHome": 1.5})
    with pytest.raises(ImmutableFileError):
        write_once(p, {"spreadHome": 2.5})
    assert json.loads(p.read_text()) == {"spreadHome": 1.5}


def test_write_json_reports_changes(tmp_path):
    p = tmp_path / "x.json"
    assert write_json(p, {"a": 1}) is True
    assert write_json(p, {"a": 1}) is False
    assert write_json(p, {"a": 2}) is True
