# Re-export of ML page with plain filename for correct URL routing
import streamlit as st
from utils.theme import inject, inject_topbar
inject()
try:
    from utils.supabase_auth import get_current_user
except Exception:
    def get_current_user(): return None
user = get_current_user()
inject_topbar(user=user)

# Run the actual ML page logic
exec(open("pages/04_🤖_ML_Predictions.py", encoding="utf-8").read())
