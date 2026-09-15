#!/usr/bin/env python3
"""scripts/btc_sheet_sync.py 단위 테스트 (stdlib unittest만 사용)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import btc_sheet_sync as sync  # noqa: E402


class TestParseTrendFinal(unittest.TestCase):
    def test_extracts_value_after_arrow(self):
        self.assertEqual(sync.parse_trend_final("1.3652→1.3753"), 1.3753)

    def test_single_value_without_arrow(self):
        self.assertEqual(sync.parse_trend_final("103570.45"), 103570.45)

    def test_none_and_empty(self):
        self.assertIsNone(sync.parse_trend_final(None))
        self.assertIsNone(sync.parse_trend_final(""))

    def test_unparseable_returns_none(self):
        self.assertIsNone(sync.parse_trend_final("n/a"))


class TestTrendDirection(unittest.TestCase):
    def test_missing_prev_or_cur_is_none(self):
        self.assertIsNone(sync.trend_direction(None, None, 100.0, band=0.1))
        self.assertIsNone(sync.trend_direction(None, 100.0, None, band=0.1))
        self.assertIsNone(sync.trend_direction(None, None, None, band=0.1))

    def test_prev_zero_is_none(self):
        self.assertIsNone(sync.trend_direction(None, 0.0, 10.0, band=0.1))

    def test_zero_change_is_flat(self):
        self.assertEqual(sync.trend_direction(None, 100.0, 100.0, band=0.1), "flat")

    def test_price_boundary_exactly_at_band_is_flat(self):
        # 100 -> 100.1 은 정확히 +0.1% — 경계값 자체는 "flat"(엄격 부등호 기준)
        self.assertEqual(sync.trend_direction(None, 100.0, 100.1, band=0.1), "flat")
        self.assertEqual(sync.trend_direction(None, 100.0, 99.9, band=0.1), "flat")

    def test_price_just_beyond_band_is_up_or_down(self):
        self.assertEqual(sync.trend_direction(None, 100.0, 100.11, band=0.1), "up")
        self.assertEqual(sync.trend_direction(None, 100.0, 99.89, band=0.1), "down")

    def test_oi_boundary_exactly_at_band_is_flat(self):
        # 100 -> 100.3 은 정확히 +0.3%
        self.assertEqual(sync.trend_direction(None, 100.0, 100.3, band=0.3), "flat")
        self.assertEqual(sync.trend_direction(None, 100.0, 99.7, band=0.3), "flat")

    def test_oi_just_beyond_band_is_up_or_down(self):
        self.assertEqual(sync.trend_direction(None, 100.0, 100.31, band=0.3), "up")
        self.assertEqual(sync.trend_direction(None, 100.0, 99.69, band=0.3), "down")

    def test_zero_band_any_nonzero_move_counts(self):
        self.assertEqual(sync.trend_direction(None, 1.0, 1.0001, band=0.0), "up")
        self.assertEqual(sync.trend_direction(None, 1.0, 0.9999, band=0.0), "down")
        self.assertEqual(sync.trend_direction(None, 1.0, 1.0, band=0.0), "flat")


class TestClassifyVerdictMatrix(unittest.TestCase):
    """9개 (price_dir, oi_dir) 조합을 전부 검증한다."""

    EXPECTED = {
        ("up", "up"): "신규 롱 유입 가능성",
        ("up", "flat"): "완만한 롱 우위 가능성",
        ("up", "down"): "숏 커버링 가능성",
        ("flat", "up"): "포지션 확대 가능성",
        ("flat", "flat"): "중립·박스권",
        ("flat", "down"): "정리·관망 가능성",
        ("down", "up"): "신규 숏 유입 가능성",
        ("down", "flat"): "완만한 숏 우위 가능성",
        ("down", "down"): "롱 청산 가능성",
    }

    def test_all_nine_combinations(self):
        for (price_dir, oi_dir), expected_label in self.EXPECTED.items():
            with self.subTest(price_dir=price_dir, oi_dir=oi_dir):
                self.assertEqual(sync.classify_verdict(price_dir, oi_dir), expected_label)

    def test_all_labels_are_covered_exactly_once(self):
        self.assertEqual(len(sync._VERDICT_MATRIX), 9)

    def test_invalid_combo_raises(self):
        with self.assertRaises(ValueError):
            sync.classify_verdict("sideways", "up")
        with self.assertRaises(ValueError):
            sync.classify_verdict("up", None)


class TestInterpret(unittest.TestCase):
    def _row(self, price, oi, acc="1.0→1.0", pos="1.0→1.0"):
        return {
            sync.PRICE_COL: str(price),
            sync.OI_COL: str(oi),
            sync.LS_ACCOUNTS_COL: acc,
            sync.LS_POSITIONS_COL: pos,
        }

    def test_first_row_has_no_previous_data(self):
        rows = [self._row(100, 1000)]
        result = sync.interpret(rows)
        self.assertEqual(result[0]["해석(자동)"], "데이터 부족")

    def test_missing_price_marks_data_insufficient(self):
        rows = [self._row(100, 1000), {sync.OI_COL: "1010"}]
        result = sync.interpret(rows)
        self.assertEqual(result[1]["해석(자동)"], "데이터 부족")

    def test_divergence_appended_when_accounts_and_positions_disagree(self):
        rows = [
            self._row(100, 1000, acc="1.0", pos="2.0"),
            # 가격·OI 모두 up, 계정 L/S는 상승(1.0→1.1), 포지션 L/S는 하락(2.0→1.9)
            self._row(100.2, 1010, acc="1.0→1.1", pos="2.0→1.9"),
        ]
        result = sync.interpret(rows)
        self.assertIn("신규 롱 유입 가능성", result[1]["해석(자동)"])
        self.assertIn("디버전스", result[1]["해석(자동)"])

    def test_no_divergence_when_accounts_and_positions_agree(self):
        rows = [
            self._row(100, 1000, acc="1.0", pos="2.0"),
            self._row(100.2, 1010, acc="1.0→1.1", pos="2.0→2.1"),
        ]
        result = sync.interpret(rows)
        self.assertEqual(result[1]["해석(자동)"], "신규 롱 유입 가능성")
        self.assertNotIn("디버전스", result[1]["해석(자동)"])

    def test_no_divergence_when_one_side_flat(self):
        rows = [
            self._row(100, 1000, acc="1.0", pos="2.0"),
            self._row(100.2, 1010, acc="1.0→1.0", pos="2.0→2.1"),
        ]
        result = sync.interpret(rows)
        self.assertNotIn("디버전스", result[1]["해석(자동)"])


if __name__ == "__main__":
    unittest.main()
