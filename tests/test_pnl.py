"""Unit tests for P&L calculation functions."""
import pytest
import pandas as pd


# ── inline helpers ─────────────────────────────────────────────────────────────

def calc_pnl(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["invested"]   = df["shares"] * df["avg_buy_price"]
    df["market_val"] = df["shares"] * df["current_price"]
    df["pnl"]        = df["market_val"] - df["invested"]
    df["pnl_pct"]    = (df["pnl"] / df["invested"]) * 100
    return df


def calc_portfolio_summary(df: pd.DataFrame) -> dict:
    pnl_df = calc_pnl(df)
    return {
        "total_invested":   pnl_df["invested"].sum(),
        "total_market_val": pnl_df["market_val"].sum(),
        "total_pnl":        pnl_df["pnl"].sum(),
        "total_pnl_pct":    (pnl_df["pnl"].sum() / pnl_df["invested"].sum()) * 100,
    }


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestCalcPnL:
    def test_pnl_columns_exist(self, holdings_data):
        result = calc_pnl(holdings_data)
        for col in ["invested", "market_val", "pnl", "pnl_pct"]:
            assert col in result.columns

    def test_positive_pnl_when_price_rose(self, holdings_data):
        result = calc_pnl(holdings_data)
        rose = result[result["current_price"] > result["avg_buy_price"]]
        assert (rose["pnl"] > 0).all()

    def test_negative_pnl_when_price_fell(self, holdings_data):
        result = calc_pnl(holdings_data)
        fell = result[result["current_price"] < result["avg_buy_price"]]
        assert (fell["pnl"] < 0).all()

    def test_invested_equals_shares_times_avg_price(self, holdings_data):
        result = calc_pnl(holdings_data)
        expected = holdings_data["shares"] * holdings_data["avg_buy_price"]
        pd.testing.assert_series_equal(result["invested"].reset_index(drop=True),
                                       expected.reset_index(drop=True),
                                       check_names=False)

    def test_pnl_pct_within_reasonable_bounds(self, holdings_data):
        result = calc_pnl(holdings_data)
        assert (result["pnl_pct"].abs() < 200).all()

    def test_does_not_mutate_input(self, holdings_data):
        original = holdings_data.copy()
        calc_pnl(holdings_data)
        pd.testing.assert_frame_equal(holdings_data, original)


class TestPortfolioSummary:
    def test_summary_keys_present(self, holdings_data):
        summary = calc_portfolio_summary(holdings_data)
        for key in ["total_invested", "total_market_val", "total_pnl", "total_pnl_pct"]:
            assert key in summary

    def test_total_pnl_equals_market_minus_invested(self, holdings_data):
        s = calc_portfolio_summary(holdings_data)
        assert abs(s["total_pnl"] - (s["total_market_val"] - s["total_invested"])) < 0.01

    def test_pnl_pct_sign_matches_pnl_sign(self, holdings_data):
        s = calc_portfolio_summary(holdings_data)
        assert (s["total_pnl"] >= 0) == (s["total_pnl_pct"] >= 0)

    def test_zero_shares_gives_zero_invested(self):
        zero_df = pd.DataFrame({
            "symbol": ["TEST.NS"],
            "shares": [0],
            "avg_buy_price": [100.0],
            "current_price": [110.0],
        })
        s = calc_portfolio_summary(zero_df)
        assert s["total_invested"] == 0
