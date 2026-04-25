from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    """Inject a light, SaaS-style theme for the app."""
    st.markdown(
        """
        <style>
        :root {
          --bg-main: #F7F8FA;
          --bg-card: #FFFFFF;
          --bg-side: #F3F4F6;
          --border: #E5E7EB;
          --text-main: #111827;
          --text-secondary: #4B5563;
          --text-muted: #6B7280;
          --blue: #0A66C2;
          --blue-hover: #004182;
          --blue-soft: #EAF3FF;
          --coral: #FF5A5F;
          --coral-soft: #FFF1F2;
          --green: #16A34A;
          --green-soft: #ECFDF5;
          --amber: #F59E0B;
          --amber-soft: #FFFBEB;
        }

        html, body, [class*="css"] {
          font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          color: var(--text-main);
          -webkit-font-smoothing: antialiased;
          text-rendering: optimizeLegibility;
        }

        h1, h2, h3, h4, h5, h6 {
          color: var(--text-main) !important;
          letter-spacing: -0.01em;
        }

        .stMarkdown p {
          color: var(--text-secondary) !important;
        }

        .stMarkdown li, .stMarkdown span {
          color: var(--text-secondary) !important;
        }

        .stCaption {
          color: var(--text-muted) !important;
          opacity: 1 !important;
        }

        .stApp {
          background: var(--bg-main);
        }

        header[data-testid="stHeader"] {
          background: rgba(247, 248, 250, 0.92);
          border-bottom: 1px solid var(--border);
        }

        [data-testid="stDecoration"] {
          display: none;
        }

        section[data-testid="stSidebar"] {
          background: var(--bg-side);
          border-right: 1px solid var(--border);
          min-width: 236px !important;
          max-width: 236px !important;
        }

        section[data-testid="stSidebar"] * {
          color: var(--text-main) !important;
        }

        section[data-testid="stSidebar"] .stCaption {
          color: #4B5563 !important;
          opacity: 1 !important;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label p {
          color: #1F2937 !important;
          font-size: 0.9rem !important;
          font-weight: 500 !important;
          opacity: 1 !important;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] label {
          margin-bottom: 0.08rem !important;
          padding-top: 0.01rem !important;
          padding-bottom: 0.01rem !important;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] > label > div {
          border-radius: 10px !important;
          padding: 0.18rem 0.35rem !important;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] [aria-checked="true"] + div p {
          color: #0A66C2 !important;
          font-weight: 700 !important;
        }

        .pc-side-card {
          background: #FFFFFF;
          border: 1px solid var(--border);
          border-radius: 10px;
          padding: 0.52rem 0.62rem;
          margin-bottom: 0.45rem;
        }

        .pc-side-label {
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: #6B7280;
          margin-bottom: 0.25rem;
          font-weight: 700;
        }

        .pc-dbpath {
          color: #111827;
          font-size: 0.84rem;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
          background: #EEF2F7;
          border: 1px solid #CBD5E1;
          border-radius: 8px;
          padding: 0.26rem 0.4rem;
          word-break: break-all;
          font-weight: 600;
        }

        .main .block-container {
          max-width: 1240px;
          padding-top: 0.65rem;
          padding-bottom: 2.2rem;
        }

        .pc-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 16px;
          padding: 1rem 1.05rem;
          box-shadow: 0 2px 10px rgba(17, 24, 39, 0.04);
          margin-bottom: 0.85rem;
          transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
        }

        .pc-card:hover {
          transform: translateY(-1px);
          box-shadow: 0 8px 20px rgba(17, 24, 39, 0.07);
          border-color: #D5DEEB;
        }

        .pc-title {
          font-size: 1.6rem;
          font-weight: 700;
          color: var(--text-main);
          margin-bottom: 0;
          line-height: 1.15;
        }

        .pc-hero-inner {
          min-height: 96px;
          padding: 0.55rem 0.1rem 0.55rem 0.05rem;
          display: flex;
          flex-direction: column;
          justify-content: center;
        }

        .pc-header-row {
          margin-bottom: 0.34rem;
        }

        .pc-subtitle {
          color: var(--text-secondary);
          font-size: 0.95rem;
          line-height: 1.4;
          margin: 0;
        }

        .pc-section-title {
          font-size: 1rem;
          font-weight: 700;
          color: var(--text-main);
          margin-bottom: 0.15rem;
        }

        .pc-helper {
          color: var(--text-muted);
          font-size: 0.82rem;
          margin-bottom: 0.7rem;
        }

        .pc-chip {
          display: inline-block;
          border-radius: 999px;
          background: var(--blue-soft);
          color: var(--blue);
          border: 1px solid #CFE1F8;
          padding: 0.22rem 0.55rem;
          margin-right: 0.35rem;
          margin-bottom: 0.35rem;
          font-size: 0.78rem;
          font-weight: 600;
        }

        .pc-kpi-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 0.95rem 1rem 0.95rem 1rem;
          min-height: 132px;
          display: flex;
          flex-direction: column;
          justify-content: flex-start;
          box-shadow: 0 1px 6px rgba(17, 24, 39, 0.04);
          transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease, background-color 160ms ease;
        }

        .pc-kpi-head {
          display: flex;
          align-items: flex-start;
          min-height: 3.35rem;
          width: 100%;
        }

        .pc-kpi-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 22px rgba(17, 24, 39, 0.10);
          border-color: #0A66C2;
          background: #FCFDFE;
        }

        .pc-kpi-compact {
          background: #FFFFFF;
          border: 1px solid var(--border);
          border-radius: 12px;
          min-height: 84px;
          padding: 0.65rem 0.9rem;
          display: flex;
          flex-direction: column;
          justify-content: center;
          box-shadow: 0 1px 5px rgba(17, 24, 39, 0.04);
        }

        .pc-kpi-compact-label {
          color: #4B5563;
          font-size: 0.98rem;
          font-weight: 600;
          line-height: 1.2;
          margin-bottom: 0.22rem;
        }

        .pc-kpi-compact-value {
          color: #111827;
          font-size: 1.85rem;
          font-weight: 700;
          line-height: 1;
        }

        .pc-kpi-label {
          color: #4B5563;
          font-size: 24px;
          line-height: 1.15;
          min-height: 2.9rem;
          font-weight: 600;
          margin: 0;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .pc-kpi-value {
          color: var(--text-main);
          font-size: 28px;
          font-weight: 700;
          line-height: 1.1;
          margin-top: auto;
          padding-left: 0;
          letter-spacing: -0.01em;
        }

        @media (max-width: 1100px) {
          .pc-kpi-label {
            font-size: 21px;
            min-height: 2.5rem;
          }
          .pc-kpi-value {
            font-size: 25px;
          }
          .pc-kpi-card {
            min-height: 124px;
          }
        }

        .pc-badge {
          display: inline-block;
          border-radius: 999px;
          padding: 0.15rem 0.55rem;
          font-size: 0.74rem;
          font-weight: 700;
          border: 1px solid transparent;
        }

        .pc-badge-ok { background: var(--green-soft); color: var(--green); border-color: #BDECC9; }
        .pc-badge-mid { background: var(--amber-soft); color: #B45309; border-color: #FCD34D; }
        .pc-badge-low { background: #F9FAFB; color: #6B7280; border-color: var(--border); }

        .pc-icon {
          width: 30px;
          height: 30px;
          border-radius: 9px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          background: var(--blue-soft);
          color: var(--blue);
          font-size: 1rem;
          font-weight: 700;
          margin-right: 0.55rem;
          border: 1px solid #D5E3F5;
          flex-shrink: 0;
        }

        .pc-row {
          display: flex;
          align-items: center;
        }

        .pc-empty {
          background: #FFFFFF;
          border: 1px dashed #CDD5DF;
          border-radius: 14px;
          padding: 1rem 1rem 1.15rem 1rem;
          text-align: center;
        }

        .pc-empty-title {
          font-size: 0.96rem;
          color: var(--text-main);
          font-weight: 700;
          margin-top: 0.4rem;
        }

        .pc-empty-sub {
          color: var(--text-muted);
          font-size: 0.84rem;
          margin-top: 0.15rem;
        }

        .stTabs [data-baseweb="tab-list"] {
          gap: 0.35rem;
        }

        .stTabs [data-baseweb="tab"] {
          border-radius: 10px;
          border: 1px solid var(--border);
          background: #FFFFFF;
          padding: 0.3rem 0.8rem;
        }

        .stTabs [aria-selected="true"] {
          background: var(--blue-soft) !important;
          color: var(--blue) !important;
          border-color: #BFD8F6 !important;
        }

        .stButton > button {
          border-radius: 10px;
          border: 1px solid #AFC7E8;
          background: var(--blue);
          color: #ffffff;
          font-weight: 600;
          transition: all 140ms ease;
          box-shadow: 0 4px 10px rgba(10, 102, 194, 0.2);
        }

        .stFormSubmitButton > button {
          border-radius: 10px;
          border: 1px solid #AFC7E8;
          background: var(--blue);
          color: #ffffff;
          font-weight: 600;
          transition: all 140ms ease;
          box-shadow: 0 4px 10px rgba(10, 102, 194, 0.2);
        }

        .stButton > button:hover {
          background: var(--blue-hover);
          border-color: var(--blue-hover);
          transform: translateY(-1px);
          box-shadow: 0 8px 18px rgba(0, 65, 130, 0.3);
        }

        .stFormSubmitButton > button:hover {
          background: var(--blue-hover);
          border-color: var(--blue-hover);
          transform: translateY(-1px);
          box-shadow: 0 8px 18px rgba(0, 65, 130, 0.3);
        }

        .stButton > button:active,
        .stFormSubmitButton > button:active {
          transform: translateY(0px) scale(0.99);
          box-shadow: 0 2px 8px rgba(0, 65, 130, 0.2);
        }

        .stButton > button:focus-visible,
        .stFormSubmitButton > button:focus-visible {
          outline: none !important;
          box-shadow: 0 0 0 3px rgba(10, 102, 194, 0.18), 0 4px 10px rgba(10, 102, 194, 0.2);
        }

        .stSelectbox > div > div,
        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stNumberInput input,
        .stMultiSelect > div > div,
        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        input, textarea {
          border-radius: 10px !important;
          border-color: var(--border) !important;
          background: #FFFFFF !important;
          color: #111827 !important;
        }

        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stNumberInput input,
        [data-baseweb="input"] input,
        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div {
          border: 1px solid #D5DDE8 !important;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
        }

        .stTextInput > div > div > input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus,
        [data-baseweb="input"] input:focus,
        [data-baseweb="textarea"] textarea:focus {
          border-color: #9FC3EC !important;
          box-shadow: 0 0 0 3px rgba(10, 102, 194, 0.08) !important;
        }

        .stTextArea textarea::placeholder,
        .stTextInput input::placeholder {
          color: #94A3B8 !important;
        }

        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label,
        .stSlider label,
        .stSelectbox label,
        .stTextInput label,
        .stTextArea label,
        .stNumberInput label,
        .stMultiSelect label {
          color: #374151 !important;
          opacity: 1 !important;
          font-weight: 600 !important;
        }

        .stSlider [role="slider"] {
          background: #0A66C2 !important;
          border-color: #0A66C2 !important;
          box-shadow: 0 0 0 3px rgba(10, 102, 194, 0.14) !important;
        }

        .stSlider [data-baseweb="slider"] {
          padding-top: 0.2rem;
        }

        .stSlider [data-testid="stTickBarMin"] {
          background: #0A66C2 !important;
        }

        .stSlider [data-testid="stTickBarMax"] {
          background: #CFD8E6 !important;
        }

        .stSlider [data-testid="stThumbValue"] {
          background: #EAF3FF !important;
          color: #0A66C2 !important;
          border: 1px solid #BFD8F6 !important;
          border-radius: 999px !important;
          font-weight: 700 !important;
        }

        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div {
          background: #FFFFFF !important;
          color: var(--text-main) !important;
        }

        .stMultiSelect [data-baseweb="select"] > div {
          min-height: 3rem !important;
          padding: 0.38rem 0.55rem !important;
          align-items: flex-start !important;
          gap: 0.28rem !important;
        }

        .stMultiSelect [data-baseweb="tag"] > span:first-child {
          margin-left: 0 !important;
        }

        .stMultiSelect [data-baseweb="tag"] {
          background: var(--blue-soft) !important;
          color: var(--blue) !important;
          border: 1px solid #BFD8F6 !important;
          border-radius: 999px !important;
          margin: 0.08rem 0.22rem 0.12rem 0 !important;
          padding: 0.03rem 0.08rem !important;
        }

        .stMultiSelect [data-baseweb="tag"] span {
          color: var(--blue) !important;
        }

        .stAlert {
          border-radius: 12px !important;
          border: 1px solid #D5DDE8 !important;
        }

        .stAlert p, .stAlert div, .stAlert span {
          color: #1F2937 !important;
          opacity: 1 !important;
        }

        .pc-sidebar-title {
          font-size: 1.08rem;
          font-weight: 700;
          color: var(--text-main);
        }

        .pc-sidebar-sub {
          font-size: 0.84rem;
          color: var(--text-muted);
          margin-bottom: 0.7rem;
        }

        .pc-action-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          background: #ECFDF5;
          color: #166534;
          border: 1px solid #BBF7D0;
          border-radius: 999px;
          padding: 0.2rem 0.5rem;
          font-size: 0.78rem;
          font-weight: 700;
          margin-bottom: 0.25rem;
        }

        .pc-action-time {
          color: #6B7280;
          font-size: 0.77rem;
          font-weight: 500;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
