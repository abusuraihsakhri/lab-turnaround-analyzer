"""Tests for tat_analyzer module."""
import os
import pathlib
import pytest
import tat_analyzer as m


def test_lookup():
    """Test basic lookup returns expected structure and matches."""
    r = m.lookup('creatinine')
    assert 'top_hit' in r and 'score' in r
    assert r['score'] > 0
    assert 'creatinine' in r['top_hit'].lower() or r['top_hit'] != 'no match'


def test_lookup_with_extra_slug():
    """Test lookup with extra parameter selecting a specific dictionary."""
    r = m.lookup('A02', extra='hla-compatibility-matcher')
    assert r['score'] > 0
    # top_hit returns the label from the bank, which is "A*02:01" for key "A02"
    assert 'A*02:01' in r['top_hit']


def test_lookup_with_extra_candidates():
    """Test lookup with extra parameter providing custom candidates."""
    r = m.lookup('aspirin', extra={'candidates': [('Aspirin', 'aspirin')]})
    assert r['score'] > 0
    assert 'Aspirin' in r['top_hit']


def test_lookup_bank_dictionaries():
    """Test that LOOKUP_BANK contains expected domain dictionaries."""
    assert "lab-turnaround-analyzer" in m.LOOKUP_BANK
    assert "loinc-lab-mapper" in m.LOOKUP_BANK
    assert len(m.LOOKUP_BANK["lab-turnaround-analyzer"]) > 0


def test_process_csv():
    """Test batch CSV processing."""
    pdir = pathlib.Path(__file__).parent
    rows = m.process_csv(str(pdir / 'sample.csv'), str(pdir / 'tmp_test_out.csv'))
    assert len(rows) >= 1
    # Verify output file was created
    assert (pdir / 'tmp_test_out.csv').exists()
    # Clean up temp file
    (pdir / 'tmp_test_out.csv').unlink()


def test_process_csv_path_traversal():
    """Test that path traversal attempts are blocked."""
    with pytest.raises(ValueError, match="Path traversal blocked"):
        m.process_csv('../../../etc/passwd', 'output.csv')

    with pytest.raises(ValueError, match="Path traversal blocked"):
        m.process_csv('sample.csv', '../../etc/output.csv')


def test_process_csv_missing_input():
    """Test that missing input file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        m.process_csv('nonexistent_file_12345.csv', 'output.csv')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
