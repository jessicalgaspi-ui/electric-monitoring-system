"""Resident bill payment: Statement -> Gateway -> Receipt (+ history)."""
import streamlit as st

from functions import fetch_payments_for_household, get_unpaid_bills, record_payment
from kit import empty, kv, panel, receipt, show_toasts, strip, toast
from theme import apply_theme, page_header
from ui import peso, refresh_data

apply_theme()

if st.session_state.get("role") != "user":
    st.error("Please sign in as a resident to view this page.")
    st.stop()

household = st.session_state["household"]
page_header("card", "Pay a Bill", f"Outstanding statements for {household['account_number']}")
show_toasts()

unpaid = get_unpaid_bills(household["household_id"])
paid = fetch_payments_for_household(household["household_id"])
last_receipt = st.session_state.get("_receipt")

with strip():
    if unpaid:
        options = {f"{r['billing_period']} — {peso(r['estimated_cost'])}": r for r in unpaid}
        with panel("statement", "Statement", f"{len(unpaid)} unpaid", size="m",
                   hint="Choose a statement, pick a gateway, and press Pay. "
                        "A receipt reference is generated automatically."):
            label = st.radio("Statement", list(options), label_visibility="collapsed")
            target = options[label]
            kv([("Period", target["billing_period"]),
                ("Usage", f"{target['consumption_kwh']:,.1f} kWh"),
                ("Amount due", peso(target["estimated_cost"]))])

        with panel("gateway", "Payment", "Choose how to pay", size="m"):
            gateway = st.segmented_control("Gateway", ["GCash", "Maya", "Bank Transfer"],
                                           default="GCash", key="pay_gateway") or "GCash"
            receipt("Summary", [("Statement", target["billing_period"]), ("Gateway", gateway)],
                    "Total", peso(target["estimated_cost"]))
            if st.button(f"Pay {peso(target['estimated_cost'])} via {gateway}", type="primary",
                         icon=":material/bolt:", width="stretch"):
                with st.spinner("Processing payment…"):
                    ok, msg = record_payment(household["household_id"], target["reading_id"],
                                             target["estimated_cost"], gateway)
                if ok:
                    refresh_data()
                    st.session_state["_receipt"] = {
                        "period": target["billing_period"], "gateway": gateway,
                        "amount": peso(target["estimated_cost"]), "msg": msg}
                    toast(msg, "success")
                    st.rerun()
                else:
                    st.error(msg)
    else:
        with panel("settled", "All settled", "No outstanding statements", size="m"):
            empty("bolt", "You're all paid up", "New statements appear here once your next reading is recorded.")

    if last_receipt:
        with panel("receipt", "Receipt", "Payment recorded", size="s"):
            receipt("Payment receipt",
                    [("Period", last_receipt["period"]), ("Gateway", last_receipt["gateway"]),
                     ("Status", "Paid")],
                    "Paid", last_receipt["amount"], ok=True)
            st.caption(last_receipt["msg"])
            if st.button("Dismiss", key="dismiss_receipt"):
                st.session_state.pop("_receipt", None)
                st.rerun()

    with panel("history", "Payment history", f"{len(paid)} payments", size="l"):
        if paid:
            st.dataframe(
                [{"Period": p["billing_period"], "Amount": peso(p["amount_paid"]), "Gateway": p["gateway"],
                  "Reference": p["reference_no"], "Paid at": p["paid_at"]} for p in paid],
                hide_index=True, width="stretch", height=380)
        else:
            empty("receipt", "No payments yet", "Your paid statements will be listed here.")
