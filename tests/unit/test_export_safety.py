from __future__ import annotations

import pytest

from medical_desert.application.services import spreadsheet_safe_cell


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_spreadsheet_safe_cell_neutralizes_formula_prefixes(prefix: str) -> None:
    value = f"  {prefix}DANGEROUS()"
    assert spreadsheet_safe_cell(value) == f"'  {prefix}DANGEROUS()"


def test_spreadsheet_safe_cell_preserves_normal_values_and_numbers() -> None:
    assert spreadsheet_safe_cell("Darbhanga Medical College") == "Darbhanga Medical College"
    assert spreadsheet_safe_cell(42) == 42
