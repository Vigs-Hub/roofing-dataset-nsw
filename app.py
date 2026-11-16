#!/usr/bin/env python3
"""Local demo UI for the NSW roofing dataset project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent
SUBURB_CSV = ROOT / "data" / "processed" / "suburb_list.csv"
OUTPUT = ROOT / "output"
CONFIG = ROOT / "config" / "areas.yaml"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

st.set_page_config(
    page_title="Roofing Dataset NSW",
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --ink: #13202b;
        --panel: #1b2a38;
        --line: #2f4558;
        --mist: #d7e2ec;
        --amber: #e0a045;
        --ok: #3d9a6a;
        --wait: #c48a2a;
        --blocked: #b4574a;
      }
      .stApp {
        background:
          radial-gradient(1200px 500px at 10% -10%, #24384a 0%, transparent 55%),
          radial-gradient(900px 420px at 100% 0%, #1a2f28 0%, transparent 45%),
          linear-gradient(180deg, #0f1820 0%, #13202b 45%, #101820 100%);
        color: var(--mist);
      }
      [data-testid="stSidebar"] {
        background: #0c141c;
        border-right: 1px solid var(--line);
      }
      h1, h2, h3, h4 { color: #f3f7fb !important; letter-spacing: -0.02em; }
      .hero-brand {
        font-size: 2.4rem; font-weight: 700; color: #f7fafc;
        margin: 0 0 0.25rem 0; letter-spacing: -0.03em;
      }
      .hero-sub {
        color: #9db0c2; font-size: 1.05rem; margin-bottom: 1.4rem;
      }
      .metric-card {
        background: linear-gradient(180deg, #1d2f3f, #162533);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 1rem 1.1rem;
        min-height: 96px;
      }
      .metric-label { color: #8ea3b7; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.06em; }
      .metric-value { color: #fff; font-size: 1.8rem; font-weight: 700; margin-top: 0.25rem; }
      .status-pill {
        display: inline-block; padding: 0.2rem 0.55rem; border-radius: 999px;
        font-size: 0.75rem; font-weight: 600; margin-right: 0.35rem;
      }
      .ok { background: rgba(61,154,106,0.2); color: #7ddeb0; border: 1px solid #3d9a6a; }
      .wait { background: rgba(196,138,42,0.2); color: #f0c57a; border: 1px solid #c48a2a; }
      .blocked { background: rgba(180,87,74,0.2); color: #f0a399; border: 1px solid #b4574a; }
      .step-row {
        background: rgba(255,255,255,0.03);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
      }
      div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_suburbs() -> pd.DataFrame:
    if not SUBURB_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(SUBURB_CSV)


@st.cache_data
def load_config() -> dict:
    if not CONFIG.exists():
        return {}
    with CONFIG.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def latest_csv(prefix: str) -> Path | None:
    files = sorted(OUTPUT.glob(f"{prefix}_*.csv"), reverse=True)
    return files[0] if files else None


def env_ready() -> dict[str, bool]:
    keys = {
        "ABN_GUID": False,
        "DATAFORSEO_LOGIN": False,
        "DATAFORSEO_PASSWORD": False,
        "GOOGLE_PLACES_API_KEY": False,
    }
    if not ENV_FILE.exists():
        return keys
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k in keys and v.strip():
            keys[k] = True
    return keys


def pill(label: str, kind: str) -> str:
    return f'<span class="status-pill {kind}">{label}</span>'


def section_overview(suburbs: pd.DataFrame, cfg: dict) -> None:
    st.markdown('<p class="hero-brand">Roofing Dataset NSW</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-sub">Local public-business roofing dataset for Wollongong, Shellharbour, '
        "Shoalhaven &amp; Wingecarribee — fold-in targets + hub ranking facts.</p>",
        unsafe_allow_html=True,
    )

    lga_counts = suburbs["lga"].value_counts().to_dict() if not suburbs.empty else {}
    main_n = int((suburbs["is_main_suburb"] == "yes").sum()) if not suburbs.empty else 0
    biz_path = latest_csv("businesses_raw") or latest_csv("businesses_filtered")
    biz_n = len(pd.read_csv(biz_path)) if biz_path else 0

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "Suburbs", f"{len(suburbs)}"),
        (c2, "LGAs", f"{len(lga_counts) or 4}"),
        (c3, "Main suburbs", f"{main_n}"),
        (c4, "Businesses found", f"{biz_n}" if biz_n else "—"),
    ]
    for col, label, value in cards:
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("### Coverage by LGA")
    if lga_counts:
        chart_df = (
            pd.DataFrame({"LGA": list(lga_counts.keys()), "Suburbs": list(lga_counts.values())})
            .sort_values("Suburbs", ascending=False)
        )
        st.bar_chart(chart_df.set_index("LGA"), color="#e0a045")
    else:
        st.info("Suburb list missing. Run: `python scripts/build_suburb_list.py`")

    st.markdown("### Credential status")
    keys = env_ready()
    search_ok = keys["DATAFORSEO_LOGIN"] and keys["DATAFORSEO_PASSWORD"]
    places_ok = keys["GOOGLE_PLACES_API_KEY"]
    abn_ok = keys["ABN_GUID"]
    bits = [
        pill("Suburb list ready", "ok" if not suburbs.empty else "blocked"),
        pill("DataForSEO", "ok" if search_ok else "blocked"),
        pill("Places backup", "ok" if places_ok else "wait"),
        pill("ABN Lookup", "ok" if abn_ok else "blocked"),
    ]
    st.markdown(" ".join(bits), unsafe_allow_html=True)
    if not search_ok:
        st.caption("Business search is blocked until DataForSEO (or Places) is in `.env`.")

    terms = cfg.get("search_terms") or []
    if terms:
        st.markdown("### Search terms")
        st.write(", ".join(terms))


def section_pipeline() -> None:
    st.markdown("### Pipeline")
    steps = [
        ("1 Setup", "Folder, sheet tabs, suburb list, API keys", "ok", "Suburb list + templates done; keys pending"),
        ("2 Find roofers", "DataForSEO / Places per suburb", "blocked", "Needs DATAFORSEO_* or GOOGLE_PLACES_API_KEY"),
        ("3 Business facts", "ABN, licence, website, reviews", "blocked", "Needs ABN_GUID + business rows"),
        ("4 Area demand", "ABS Census 2021 by suburb", "wait", "Can start without paid APIs"),
        ("5 Roof signals", "DA / CDC + BOM storm/hail", "wait", "Public sources; mark MISSING where unpublished"),
        ("6 Map pack", "Top 3 roofer results per main suburb", "blocked", "Needs search API"),
        ("7 Clean + check", "Notes tab; Neal spot-checks 20 rows", "wait", "After data lands"),
        ("8 Repeatable", "Parameterise [AREA] + [TRADE]", "ok", "config/areas.yaml already drives scripts"),
    ]
    for title, detail, kind, note in steps:
        st.markdown(
            f'<div class="step-row">{pill(title, kind)} <strong>{detail}</strong><br/>'
            f'<span style="color:#9db0c2;font-size:0.9rem">{note}</span></div>',
            unsafe_allow_html=True,
        )


def section_suburbs(suburbs: pd.DataFrame) -> None:
    st.markdown("### Suburb driver list")
    if suburbs.empty:
        st.warning("No suburb list found.")
        return
    lgas = ["All"] + sorted(suburbs["lga"].unique().tolist())
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        lga = st.selectbox("LGA", lgas)
    with c2:
        main_only = st.checkbox("Main suburbs only (map pack)", value=False)
    with c3:
        q = st.text_input("Search suburb", "")

    view = suburbs.copy()
    if lga != "All":
        view = view[view["lga"] == lga]
    if main_only:
        view = view[view["is_main_suburb"] == "yes"]
    if q.strip():
        view = view[view["suburb"].str.contains(q.strip(), case=False, na=False)]

    st.caption(f"{len(view)} suburbs shown · source ABS ASGS Ed3 SAL→LGA")
    st.dataframe(
        view[["suburb", "lga", "area_label", "sal_code", "is_main_suburb", "collection_date"]],
        use_container_width=True,
        hide_index=True,
        height=480,
    )


def section_businesses() -> None:
    st.markdown("### Businesses")
    path = latest_csv("businesses_filtered") or latest_csv("businesses_abn") or latest_csv("businesses_raw")
    if not path:
        st.info(
            "No business CSV yet. After credentials are set, run:\n\n"
            "`python scripts/search_businesses.py --limit-suburbs 1`"
        )
        st.markdown(
            """
            **Will collect (public data only):** name, address, suburb, phone, website,
            rating, review count, Place ID, Maps URL — then ABN / licence enrich.
            """
        )
        return
    df = pd.read_csv(path)
    st.caption(f"Loaded `{path.name}` · {len(df)} rows")
    lgas = ["All"] + sorted([x for x in df.get("lga", pd.Series(dtype=str)).dropna().unique().tolist()])
    lga = st.selectbox("Filter LGA", lgas, key="biz_lga")
    view = df if lga == "All" else df[df["lga"] == lga]
    cols = [c for c in ["name", "suburb", "lga", "phone", "website", "rating", "review_count", "include_flag", "source_link", "collection_date"] if c in view.columns]
    st.dataframe(view[cols], use_container_width=True, hide_index=True, height=480)


def section_outputs() -> None:
    st.markdown("### Local outputs")
    bundles = sorted(OUTPUT.glob("sheet_bundle_*"), reverse=True)
    csvs = sorted(OUTPUT.glob("*.csv"), reverse=True)
    if bundles:
        st.write("**Sheet bundles**")
        for b in bundles[:5]:
            st.code(str(b.relative_to(ROOT)))
    if csvs:
        st.write("**CSV runs**")
        for c in csvs[:12]:
            st.code(str(c.relative_to(ROOT)))
    if not bundles and not csvs:
        st.info("No outputs yet. Run `python scripts/init_sheet_bundle.py`.")


def section_rules() -> None:
    st.markdown("### Rules & done line")
    st.markdown(
        """
        - Public business data only — no homeowner PII, no bought lists  
        - Engineer never contacts businesses (outreach: Matt; send: Neal)  
        - Nic privacy check before outreach uses the list  
        - **Done:** one Google Sheet — Businesses, Area demand, Roof signals, Map pack + Notes  
        - Every row needs `source_link` + `collection_date`  
        - Neal spot-checks **20** rows  
        """
    )
    st.markdown("### Still missing from Neal")
    st.markdown("- Deadline  \n- DataForSEO spend cap  \n- Google Places spend cap")


def main() -> None:
    with st.sidebar:
        st.markdown("## Roofing Dataset")
        st.caption("NSW · Illawarra / Highlands")
        page = st.radio(
            "View",
            ["Overview", "Pipeline", "Suburbs", "Businesses", "Outputs", "Rules"],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("Owner: Isuru · Checker: Neal")
        st.caption("Run UI: `streamlit run app.py`")

    suburbs = load_suburbs()
    cfg = load_config()

    if page == "Overview":
        section_overview(suburbs, cfg)
    elif page == "Pipeline":
        section_pipeline()
    elif page == "Suburbs":
        section_suburbs(suburbs)
    elif page == "Businesses":
        section_businesses()
    elif page == "Outputs":
        section_outputs()
    else:
        section_rules()


if __name__ == "__main__":
    main()
