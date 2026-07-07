"""Tests for config.validate() — fail fast on a misconfigured plane."""
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402


@pytest.fixture()
def fresh_config():
    """Reload config so mutations in one test don't leak into another."""
    importlib.reload(config)
    yield config
    importlib.reload(config)


def test_default_config_is_valid(fresh_config):
    fresh_config.validate()  # ships valid


def test_rejects_bad_endpoint_type(fresh_config):
    fresh_config.VS_ENDPOINT_TYPE = "TURBO"
    with pytest.raises(ValueError, match="VS_ENDPOINT_TYPE"):
        fresh_config.validate()


def test_rejects_bad_capacity(fresh_config):
    fresh_config.ONLINE_STORE_CAPACITY = "CU_3"
    with pytest.raises(ValueError, match="ONLINE_STORE_CAPACITY"):
        fresh_config.validate()


def test_rejects_overlap_ge_size(fresh_config):
    fresh_config.CHUNK_OVERLAP_CHARS = fresh_config.CHUNK_SIZE_CHARS
    with pytest.raises(ValueError, match="CHUNK_OVERLAP_CHARS"):
        fresh_config.validate()


def test_rejects_empty_required(fresh_config):
    fresh_config.CATALOG = ""
    with pytest.raises(ValueError, match="CATALOG"):
        fresh_config.validate()


def test_column_contract_holds(fresh_config):
    assert fresh_config.EMBEDDING_SOURCE_COLUMN in fresh_config.CHUNK_COLUMNS
    assert fresh_config.INDEX_PRIMARY_KEY in fresh_config.CHUNK_COLUMNS
    assert set(fresh_config.INDEX_QUERY_COLUMNS) <= set(fresh_config.CHUNK_COLUMNS)


def test_require_genie_space_raises_when_empty(fresh_config):
    fresh_config.GENIE_SPACE_ID = ""
    with pytest.raises(ValueError, match="GENIE_SPACE_ID"):
        fresh_config.require_genie_space()
    fresh_config.GENIE_SPACE_ID = "abc123"
    assert fresh_config.require_genie_space() == "abc123"


def test_thresholds_in_unit_range(fresh_config):
    fresh_config.EVAL_MIN_HIT_RATE = 1.5
    with pytest.raises(ValueError, match="EVAL_MIN_HIT_RATE"):
        fresh_config.validate()
