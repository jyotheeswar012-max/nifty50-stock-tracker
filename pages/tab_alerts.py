"""Tab 7 — Price Alerts."""
import streamlit as st

from utils.logger import get_logger
from utils.constants import NIFTY50
from utils.data import fetch_ticker
from utils.calculations import safe_float
from utils.alerts import get_alerts, add_alert, remove_alert, fire_alerts
from utils.notifications import smtp_configured, send_email

log = get_logger(__name__)

USER_KEY = "nifty50_user"


def render(build_stock_rows_cached) -> None:
    from utils.app_helpers import hero, divider, sec
    hero("\U0001f514 Price Alerts")

    # ── Email config ────────────────────────────────────────────────────
    stored_email = st.session_state.get("alert_email", "").strip()
    alert_email_input = st.text_input(
        "\U0001f4e7 Email for alert notifications (optional)",
        value=stored_email,
        placeholder="you@example.com",
        key="alert_email_input",
    )
    if alert_email_input.strip() != stored_email:
        st.session_state["alert_email"] = alert_email_input.strip().lower()
        st.rerun()
    alert_email = st.session_state.get("alert_email", "").strip().lower()

    if smtp_configured():
        st.success("\U0001f4e7 Email alerts: **configured**")
    else:
        st.warning(
            "\U0001f4e7 Email alerts: **NOT configured** \u2014 add [smtp] to Streamlit Cloud Secrets"
        )

    if alert_email and smtp_configured():
        if st.button("\U0001f4e7 Send Test Email", use_container_width=False):
            try:
                ok, err = send_email(
                    alert_email,
                    "Nifty50 Alert - Test Email",
                    f"Hi! This is a test from NSE & Nifty 50 Tracker.\nSMTP is working.\n"
                    f"Alerts will be sent to: {alert_email}\n\n-- NSE Tracker",
                )
            except Exception as exc:  # noqa: BLE001
                log.error("tab_alerts: send_email raised: %s", exc, exc_info=True)
                st.error("Email send failed unexpectedly.")
            else:
                if ok:
                    st.success(f"Test email sent to {alert_email}!")
                else:
                    log.warning("tab_alerts: send_email returned error: %s", err)
                    st.error(f"Email failed: {err}")

    divider()
    sec("Add New Alert")

    if st.session_state.get("_alert_added_msg"):
        st.success(st.session_state.pop("_alert_added_msg"))

    r2c1, r2c2 = st.columns([2, 1])
    with r2c1:
        al_stock_name = st.selectbox("Stock", [s["name"] for s in NIFTY50], key="al_stock")
    with r2c2:
        al_direction = st.selectbox("Alert when price", ["rises above \u2191", "drops below \u2193"], key="al_dir")

    al_sym = next(s["symbol"] for s in NIFTY50 if s["name"] == al_stock_name)
    _px_key = f"_al_live_px_{al_sym}"
    if _px_key not in st.session_state:
        live_px = 100.0
        try:
            live_data = fetch_ticker(al_sym, "5d")
            if not live_data.empty and "Close" in live_data.columns:
                live_px = round(safe_float(live_data["Close"].iloc[-1]), 2)
            else:
                log.warning("tab_alerts: empty data for alert symbol '%s'", al_sym)
        except OSError as exc:
            log.error("tab_alerts: network error fetching '%s': %s", al_sym, exc, exc_info=True)
            st.warning(f"Could not fetch live price for {al_stock_name}; defaulting to Rs.\ 100.")
        except Exception as exc:  # noqa: BLE001
            log.error("tab_alerts: unexpected error fetching '%s': %s", al_sym, exc, exc_info=True)
        st.session_state[_px_key] = live_px
    live_px = st.session_state[_px_key]

    st.caption(f"Current price of **{al_stock_name}**: **Rs.{live_px:,.2f}**")

    with st.form("add_alert_form", clear_on_submit=True):
        al_thresh = st.number_input("Target Price (Rs.)", min_value=0.01, value=live_px, step=1.0)
        submitted = st.form_submit_button("Set Alert", type="primary", use_container_width=True)
        if submitted:
            if al_thresh <= 0:
                st.error("Target price must be greater than zero.")
            else:
                direction = "above" if "above" in al_direction else "below"
                try:
                    add_alert(
                        stock=al_stock_name,
                        symbol=al_sym,
                        direction=direction,
                        threshold=al_thresh,
                        email=alert_email or USER_KEY,
                        phone="",
                    )
                except Exception as exc:  # noqa: BLE001
                    log.error("tab_alerts: add_alert failed: %s", exc, exc_info=True)
                    st.error("Failed to save alert.")
                else:
                    st.session_state["_alert_added_msg"] = (
                        f"Alert set: {al_stock_name} "
                        f"{'>' if direction == 'above' else '<'} Rs.{al_thresh:,.2f}"
                        + (f" \u2014 will email {alert_email}" if alert_email else "")
                    )
                    st.session_state.pop(_px_key, None)
                    st.rerun()

    divider()

    price_map: dict = {}
    try:
        live_rows = build_stock_rows_cached()
        if "_curr" in live_rows.columns:
            price_map = dict(
                zip([s["symbol"] for s in NIFTY50], live_rows["_curr"].fillna(0).tolist())
            )
    except Exception as exc:  # noqa: BLE001
        log.error("tab_alerts: price_map build failed: %s", exc, exc_info=True)

    try:
        alerts = get_alerts(alert_email or USER_KEY)
    except Exception as exc:  # noqa: BLE001
        log.error("tab_alerts: get_alerts failed: %s", exc, exc_info=True)
        st.error("Could not load alerts.")
        return

    active = [a for a in alerts if not a["triggered"]]
    fired = [a for a in alerts if a["triggered"]]

    sec(f"Active Alerts ({len(active)})")
    if not active:
        st.caption("No active alerts. Add one above.")
    else:
        for al in active:
            col_info, col_del = st.columns([6, 1])
            live_px_al = price_map.get(al["symbol"], 0)
            arrow = "\u2191" if al["direction"] == "above" else "\u2193"
            gap = (
                live_px_al - al["threshold"]
                if al["direction"] == "above"
                else al["threshold"] - live_px_al
            )
            gap_str = f"Rs.{abs(gap):,.2f} {'above' if gap >= 0 else 'below'} target"
            triggered_now = (
                al["direction"] == "above" and live_px_al >= al["threshold"]
            ) or (
                al["direction"] == "below" and live_px_al <= al["threshold"]
            )
            status_icon = "\U0001f7e2" if triggered_now else "\U0001f7e1"
            with col_info:
                st.markdown(
                    f"{status_icon} **{al['stock']}** {arrow} Rs.{al['threshold']:,.2f} "
                    f"| Live: **Rs.{live_px_al:,.2f}** | {gap_str} \xb7 `#{al['id']}`"
                )
            with col_del:
                if st.button("\U0001f5d1\ufe0f", key=f"del_{al['id']}", help="Remove"):
                    try:
                        remove_alert(al["id"], alert_email or USER_KEY)
                    except Exception as exc:  # noqa: BLE001
                        log.error("tab_alerts: remove_alert id=%s failed: %s", al["id"], exc, exc_info=True)
                        st.error("Could not remove alert.")
                    else:
                        st.rerun()

    if active and price_map:
        try:
            n_fired = fire_alerts(price_map, alert_email or USER_KEY)
            if n_fired:
                st.toast(f"{n_fired} alert(s) triggered!", icon="\U0001f514")
                st.rerun()
        except Exception as exc:  # noqa: BLE001
            log.error("tab_alerts: fire_alerts failed: %s", exc, exc_info=True)

    if fired:
        with st.expander(f"Triggered Alerts ({len(fired)})", expanded=False):
            for al in fired:
                arrow = "\u2191" if al["direction"] == "above" else "\u2193"
                st.markdown(
                    f"~~**{al['stock']}**~~ {arrow} Rs.{al['threshold']:,.2f} "
                    f"\xb7 `#{al['id']}` \xb7 {al['created']}"
                )

    alert_log = st.session_state.get("_alert_log", {})
    user_log = alert_log.get(alert_email or USER_KEY, []) if isinstance(alert_log, dict) else []
    if user_log:
        with st.expander("Notification Log", expanded=True):
            for entry in user_log:
                st.text(entry)
