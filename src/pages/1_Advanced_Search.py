import streamlit as st
from streamlit_searchbox import st_searchbox
import pandas as pd

from utils.streamlit_db import DatabaseClient
from queries.variant_queries import get_variants_advanced_search
from utils.csv_parser import validate_csv_columns, get_required_columns, validate_csv_data, build_query_conditions
from utils.browser_policy import MAX_QUERY_BASES, MIN_MAF
from utils.query_limits import validate_query_window

st.set_page_config(page_title="Advanced Variant Search", layout="wide")

# Hide only CSV download, preserving search, fullscreen, and row selection. Streamlit does not support this hiding
st.html("""
<style>
[data-testid="stDataFrame"] button[aria-label="Download as CSV"] {
    display: none !important;
}
</style>
""")

db = DatabaseClient()
query_limit_label = f"{MAX_QUERY_BASES / 1000:g} kb"
min_maf_label = f"{MIN_MAF * 100:g}%"

st.title("Advanced Variant Search")
st.write("Search variants by gene symbol, chromosome, and/or position range with detailed frequency analysis.")
st.info("ℹ️ Reference genome: **GRCh38**")
st.info(f"This browser shows common variants only (MAF ≥ {min_maf_label}). Variants below this threshold are not displayed and may still be present in DwarnaBio.")

@st.cache_data
def load_genes_suggestions() -> list[str]:
    """Load gene symbols from the database for suggestions while searching."""
    query = "SELECT DISTINCT symbol FROM genes ORDER BY symbol;"
    results = db.execute_query(query)
    return results['symbol'].tolist() if not results.empty else []

def search_genes(search_term: str) -> list[str]:
    """Return a list of gene symbols matching the search term."""
    if not search_term:
        return []

    suggestions = load_genes_suggestions()
    search_term_upper = search_term.upper()
    matches = [gene for gene in suggestions if search_term_upper in gene.upper()]
    return matches[:7]  # Limit to top 7 matches

# CSV Upload Section
with st.expander("📁 Bulk Search via CSV Upload", expanded=False):
    sample_start = 43044295
    sample_end = sample_start + MAX_QUERY_BASES - 1
    sample_csv = (
        "gene_symbol,rs_id,chromosome,start_position,end_position\n"
        f"BRCA1,,17,{sample_start},{sample_end}\n"
        f",,17,{sample_start},{sample_start}"
    )

    st.markdown(f"""
    Upload a CSV file to search within one window of at most {MAX_QUERY_BASES:,} bases ({query_limit_label}) on one chromosome.

    **Required columns (case-insensitive):**
    - `gene_symbol`: Gene symbol (e.g., BRCA1, TP53)
    - `rs_id`: dbSNP rsID (e.g., rs80357906)
    - `chromosome`: Chromosome (1-22, X, Y, MT)
    - `start_position`: Start position (for single positions, set start = end)
    - `end_position`: End position

    Every row requires `chromosome`, `start_position`, and `end_position`.
    Gene symbols and rsIDs are optional filters. All rows together must fit within one {query_limit_label} window.
    """)
    st.markdown("**Example CSV:**")
    st.code(sample_csv, language="csv")

    # Download example CSV template
    st.download_button(
        label="📥 Download Example CSV",
        data=sample_csv,
        file_name="variant_search_example.csv",
        mime="text/csv"
    )

    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=['csv'],
        help="CSV must have exactly these columns: gene_symbol, rs_id, chromosome, start_position, end_position"
    )

    csv_data = None
    csv_conditions = None
    csv_params = None

    if uploaded_file:
        try:
            csv_df = pd.read_csv(uploaded_file, dtype={'chromosome': str})
            st.success(f"✅ Loaded {len(csv_df)} rows from CSV")

            errors_required_not_in, errors_provided_not_in = validate_csv_columns(csv_df)

            if errors_required_not_in:
                st.error(f"❌ Provided CSV is missing the following expected columns: {errors_required_not_in}.")

            if errors_provided_not_in:
                st.error(f"❌ Provided CSV contains unexpected columns: {errors_provided_not_in}. Expected columns: {get_required_columns()}")

            if not errors_required_not_in and not errors_provided_not_in:
                # Validate row data
                validation_errors = validate_csv_data(csv_df)

                if validation_errors:
                    st.error(f"❌ CSV validation failed with {len(validation_errors)} error(s):")
                    for error in validation_errors[:10]:  # Show first 10 errors
                        st.error(error)
                    if len(validation_errors) > 10:
                        st.warning(f"... and {len(validation_errors) - 10} more errors")
                else:
                    st.success("✅ CSV validation passed")

                    # Build query conditions
                    csv_conditions, csv_params = build_query_conditions(csv_df)
                    st.info(f"Ready to search {len(csv_conditions)} variant queries")

        except Exception as e:
            st.error(f"❌ Error processing CSV: {str(e)}")

st.divider()

# Manual Search form
st.header("Search Parameters")

col1, col2 = st.columns(2, border=True)

with col1:
    chromosome = st.selectbox(
        label = "**Chromosome** (required)",
        options=[""] + [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
            "21", "22", "X", "Y"
        ],
    )

    start_pos = st.number_input(
        label = "**Start Position** (required)",
        min_value=1,
        value=None,
    )

    end_pos = st.number_input(
        label = "**End Position** (required)",
        min_value=1,
        value=None,
    )

with col2:
    gene_symbol = st_searchbox(
        search_genes,
        placeholder="e.g., BRCA1, TP53, APOE",
        label="Gene Symbol (optional)",
        key="gene_searchbox"
    )
    with st.expander("Advanced Filters (Optional)", expanded=False):
        freq_col1, freq_col2 = st.columns(2)

        with freq_col1:
            min_alt_freq = st.number_input(
                "Min Alt Frequency",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.01,
                format="%.3f"
            )

        with freq_col2:
            max_alt_freq = st.number_input(
                "Max Alt Frequency",
                min_value=0.0,
                max_value=1.0,
                value=1.0,
                step=0.01,
                format="%.3f"
            )

st.info(f"Every search requires a chromosome and a start/end interval of at most {MAX_QUERY_BASES:,} bases ({query_limit_label}), inclusive. A gene symbol optionally narrows that interval.")

search_button = st.button("Search Variants", type="primary")

def build_query_and_params(use_csv=False):
    """Build the SQL query with dynamic filters based on user input or CSV."""
    base_query = get_variants_advanced_search()

    where_parts = []
    params = []

    # Use CSV conditions if available
    if use_csv and csv_conditions:
        # Combine all CSV row conditions with OR
        where_parts.append("(" + " OR ".join(csv_conditions) + ")")
        params.extend(csv_params)
    else:
        query_chromosome, query_start, query_end = validate_query_window(chromosome, start_pos, end_pos, limit=MAX_QUERY_BASES)
        # Manual search filters
        # Gene filter
        if gene_symbol and gene_symbol.strip():
            where_parts.append("UPPER(g.symbol) = UPPER(%s)")
            params.append(gene_symbol.strip())

        # Chromosome filter
        where_parts.append("vl.chromosome = %s")
        params.append(query_chromosome)

        # Position range filter
        where_parts.append("vl.position BETWEEN %s AND %s")
        params.extend([query_start, query_end])

    # Mandatory release rule: placeholders follow the WHERE clause in the template
    params.extend([MIN_MAF, MIN_MAF])

    # Frequency filters (optional - only applied if user changes defaults)
    freq_filter = ""
    if min_alt_freq > 0.0 or max_alt_freq < 1.0:
        freq_filter = "AND b.af_max BETWEEN %s AND %s"
        params.extend([min_alt_freq, max_alt_freq])

    where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    final_query = base_query.format(where_clause=where_clause, freq_filter=freq_filter)

    return final_query, tuple(params)

if search_button:
    # Determine search mode: CSV or manual
    use_csv_search = csv_conditions is not None and len(csv_conditions) > 0

    if uploaded_file and not use_csv_search:
        st.error("Please correct the uploaded CSV before searching.")
        st.session_state.pop('search_results', None)
        st.session_state.pop('search_summary', None)
        st.stop()

    # Validate before executing any variant query.
    if not use_csv_search:
        try:
            validate_query_window(chromosome, start_pos, end_pos, limit=MAX_QUERY_BASES)
        except ValueError as error:
            st.error(str(error))
            st.session_state.pop('search_results', None)
            st.session_state.pop('search_summary', None)
            st.stop()

    if use_csv_search or (gene_symbol and gene_symbol.strip()) or chromosome or start_pos is not None or end_pos is not None:
        try:
            with st.spinner("Searching database..."):
                query, params = build_query_and_params(use_csv=use_csv_search)
                results = db.execute_query_with_params(query, params) if params else db.execute_query(query)

            if len(results) == 0:
                st.warning(f"No common variants (MAF ≥ {min_maf_label}) to display for this search. Rarer variants are not shown and may still be present in DwarnaBio.")
                st.session_state.pop('search_results', None)
                st.session_state.pop('search_summary', None)
            else:
                annotation_cols = ['transcript_id', 'hgvs_c', 'hgvs_p', 'consequence', 'impact']

                # Sort by chromosome, position, alt allele, then impact (HIGH first)
                impact_order = {'HIGH': 0, 'MODERATE': 1, 'LOW': 2, 'MODIFIER': 3}
                results = results.copy()
                results['_impact_rank'] = results['impact'].map(impact_order).fillna(99)
                results = results.sort_values(
                    ['chromosome', 'position', 'alternate_allele', '_impact_rank']
                ).drop(columns=['_impact_rank'])

                # Build one-row-per-variant summary dataframe
                summary = (
                    results
                    .drop(columns=annotation_cols)
                    .drop_duplicates(subset=['chromosome', 'position', 'reference_allele', 'alternate_allele'])
                    .reset_index(drop=True)
                )
                summary['gnomad_url'] = summary.apply(
                    lambda r: f"https://gnomad.broadinstitute.org/variant/{r['chromosome']}-{r['position']}-{r['reference_allele']}-{r['alternate_allele']}",
                    axis=1
                )
                summary['rs_id'] = summary['rs_id'].apply(
                    lambda rs: f"https://www.ncbi.nlm.nih.gov/snp/{rs}" if pd.notna(rs) and rs else None
                )
                summary = summary.rename(columns={
                    'gene': 'Gene', 'chromosome': 'Chr', 'position': 'Position',
                    'reference_allele': 'Ref', 'alternate_allele': 'Alt', 'rs_id': 'RS ID',
                    'ref_allele_freq': 'Ref Freq (MT)', 'alt_allele_freq': 'Alt Freq (MT)', 'gnomad_url': 'gnomAD',
                })
                for col in ['Ref Freq (MT)', 'Alt Freq (MT)']:
                    summary[col] = summary[col].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) else None)

                # Store in session state so reruns (from row selection) can access them
                st.session_state['search_results'] = results
                st.session_state['search_summary'] = summary

        except Exception as e:
            st.error(f"❌ Search failed: {str(e)}")
            st.info("Please check your database connection and ensure the database contains data.")
            with st.expander("Error Details"):
                st.code(str(e))

# Render results (persists across reruns triggered by row selection)
if 'search_results' in st.session_state and 'search_summary' in st.session_state:
    results = st.session_state['search_results']
    summary = st.session_state['search_summary']
    annotation_cols = ['transcript_id', 'hgvs_c', 'hgvs_p', 'consequence', 'impact']

    st.header("Query Results")
    st.caption("Click a row to see annotation details below.")

    event = st.dataframe(
        summary,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "gnomAD": st.column_config.LinkColumn(
                "gnomAD",
                help="View variant in gnomAD browser",
                display_text="View"
            ),
            "RS ID": st.column_config.LinkColumn(
                "RS ID",
                help="View in dbSNP database",
                validate=r"^https://www\.ncbi\.nlm\.nih\.gov/snp/rs\d+$",
                display_text=r"https://www\.ncbi\.nlm\.nih\.gov/snp/(.*)"
            )
        }
    )

    # Annotation detail panel
    selected_rows = event.selection.rows
    if selected_rows:
        sel = summary.iloc[selected_rows[0]]
        chrom, pos, ref, alt = sel['Chr'], sel['Position'], sel['Ref'], sel['Alt']

        mask = (
            (results['chromosome'] == chrom) &
            (results['position'] == pos) &
            (results['reference_allele'] == ref) &
            (results['alternate_allele'] == alt)
        )
        ann_df = results.loc[mask, annotation_cols].reset_index(drop=True)
        ann_df.columns = ['Transcript', 'HGVS c.', 'HGVS p.', 'Consequence', 'Impact']
        ann_df['Transcript'] = ann_df['Transcript'].apply(
            lambda t: f"https://www.ensembl.org/id/{t}" if pd.notna(t) and t != '—' else None
        )
        ann_df = ann_df.fillna('—')

        with st.expander(f"Annotations: {chrom}:{pos} {ref} > {alt}", expanded=True):
            st.dataframe(
                ann_df,
                hide_index=True,
                width='stretch',
                column_config={
                    "Transcript": st.column_config.LinkColumn(
                        "Transcript",
                        help="View in Ensembl",
                        validate=r"^https://www\.ensembl\.org/id/.*$",
                        display_text=r"https://www\.ensembl\.org/id/(.*)"
                    )
                }
            )
