import streamlit as st
st.set_page_config(layout="wide")

from streamlit_searchbox import st_searchbox
import pandas as pd

from utils.streamlit_db import DatabaseClient
from queries.variant_queries import get_variants_advanced_search
from utils.csv_parser import detect_csv_format, validate_csv_data, build_query_conditions

st.set_page_config(page_title="Advanced Variant Search")

db = DatabaseClient()

st.title("Advanced Variant Search")
st.write("Search variants by gene symbol, chromosome, and/or position range with detailed frequency analysis.")
st.info("ℹ️ Reference genome: **GRCh38**")

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
    return matches[:10]  # Limit to top 10 matches

# CSV Upload Section
with st.expander("📁 Bulk Search via CSV Upload", expanded=False):
    st.markdown("""
    Upload a CSV file to search for multiple variants at once.

    **Required columns (case-insensitive):**
    - `gene_symbol`: Gene symbol (e.g., BRCA1, TP53)
    - `chromosome`: Chromosome (1-22, X, Y, MT)
    - `start_position`: Start position (for single positions, set start = end)
    - `end_position`: End position

    **Example CSV:**
    ```
    gene_symbol,chromosome,start_position,end_position
    BRCA1,,,
    ,17,43044295,43044295
    TP53,17,7600000,7700000
    ```
    """)

    # Download example CSV template
    sample_csv = "gene_symbol,chromosome,start_position,end_position\nBRCA1,,,\n,17,43044295,43044295\nTP53,17,7600000,7700000"

    st.download_button(
        label="📥 Download Example CSV",
        data=sample_csv,
        file_name="variant_search_example.csv",
        mime="text/csv"
    )

    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=['csv'],
        help="CSV must have gene_symbol, chromosome, start_position, and/or end_position columns"
    )

    csv_data = None
    csv_conditions = None
    csv_params = None

    if uploaded_file:
        try:
            csv_df = pd.read_csv(uploaded_file)
            st.success(f"✅ Loaded {len(csv_df)} rows from CSV")

            # Detect format
            detected_format = detect_csv_format(csv_df)

            # Validate
            validation_errors = validate_csv_data(csv_df, detected_format)

            if validation_errors:
                st.error(f"❌ CSV validation failed with {len(validation_errors)} error(s):")
                for error in validation_errors[:10]:  # Show first 10 errors
                    st.error(error)
                if len(validation_errors) > 10:
                    st.warning(f"... and {len(validation_errors) - 10} more errors")
            else:
                st.success("✅ CSV validation passed")

                # Build query conditions
                csv_conditions, csv_params = build_query_conditions(csv_df, detected_format)
                st.info(f"Ready to search {len(csv_conditions)} variant queries")

        except Exception as e:
            st.error(f"❌ Error processing CSV: {str(e)}")

st.divider()

# Manual Search form
st.header("Manual Search Parameters")

col1, col2 = st.columns(2)

with col1:
    gene_symbol = st_searchbox(
        search_genes,
        placeholder="e.g., BRCA1, TP53, APOE",
        label="Gene Symbol",
        key="gene_searchbox"
    )

    chromosome = st.selectbox(
        "Chromosome (optional)",
        options=[""] + [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
            "21", "22", "X", "Y"
        ],
    )

with col2:
    start_pos = st.number_input(
        "Start Position (optional)",
        min_value=1,
        value=None,
    )

    end_pos = st.number_input(
        "End Position (optional)",
        min_value=1,
        value=None,
    )

# Frequency filters in collapsible section
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

st.info("You can search by gene alone, position range alone, or combine both for more specific results.")

search_button = st.button("Search Variants", type="primary")

def build_query_and_params(use_csv=False):
    """Build the SQL query with dynamic filters based on user input or CSV."""
    base_query = get_variants_advanced_search()

    where_parts = []
    having_parts = []
    params = []

    # Use CSV conditions if available
    if use_csv and csv_conditions:
        # Combine all CSV row conditions with OR
        where_parts.append("(" + " OR ".join(csv_conditions) + ")")
        params.extend(csv_params)
    else:
        # Manual search filters
        # Gene filter
        if gene_symbol and gene_symbol.strip():
            where_parts.append("UPPER(g.symbol) = UPPER(%s)")
            params.append(gene_symbol.strip())

        # Chromosome filter
        if chromosome:
            where_parts.append("vl.chromosome = %s")
            params.append(chromosome)

        # Position range filter
        if start_pos is not None and end_pos is not None:
            where_parts.append("vl.position BETWEEN %s AND %s")
            params.extend([start_pos, end_pos])
        elif start_pos is not None:
            where_parts.append("vl.position >= %s")
            params.append(start_pos)
        elif end_pos is not None:
            where_parts.append("vl.position <= %s")
            params.append(end_pos)

    # Frequency filters (optional - only applied if user changes defaults)
    # Uses HAVING since it filters on aggregated values
    if min_alt_freq > 0.0 or max_alt_freq < 1.0:
        having_parts.append("(SUM(vf.alternate_allele_count)::numeric / SUM(vf.allele_number)) BETWEEN %s AND %s")
        params.extend([min_alt_freq, max_alt_freq])

    # Build WHERE and HAVING clauses
    where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    having_clause = "HAVING " + " AND ".join(having_parts) if having_parts else ""

    # Format the query with WHERE and HAVING clauses
    final_query = base_query.format(where_clause=where_clause, having_clause=having_clause)

    return final_query, tuple(params)

if search_button:
    # Determine search mode: CSV or manual
    use_csv_search = csv_conditions is not None and len(csv_conditions) > 0

    # Validate input
    if not use_csv_search:
        if not (gene_symbol and gene_symbol.strip()) and not chromosome and start_pos is None and end_pos is None:
            st.error("⚠️ Please provide at least one search parameter (gene symbol, chromosome, or position range) or upload a CSV file.")
        elif start_pos is not None and end_pos is not None and start_pos > end_pos:
            st.error("⚠️ Start position must be less than or equal to end position.")
        else:
            use_csv_search = False  # Proceed with manual search

    if use_csv_search or (gene_symbol and gene_symbol.strip()) or chromosome or start_pos is not None or end_pos is not None:
        try:
            with st.spinner("Searching database..."):
                query, params = build_query_and_params(use_csv=use_csv_search)
                results = db.execute_query_with_params(query, params) if params else db.execute_query(query)

            if len(results) == 0:
                st.warning("No variants found matching your search criteria.")
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
                summary = summary.rename(columns={
                    'gene': 'Gene', 'chromosome': 'Chr', 'position': 'Position',
                    'reference_allele': 'Ref', 'alternate_allele': 'Alt', 'rs_id': 'RS ID',
                    'alternate_allele_count': 'Alt Count', 'allele_number': 'Total Alleles',
                    'ref_allele_freq': 'Ref Freq', 'alt_allele_freq': 'Alt Freq', 'gnomad_url': 'gnomAD',
                })
                for col in ['Ref Freq', 'Alt Freq']:
                    summary[col] = summary[col].apply(lambda x: round(float(x), 4) if pd.notna(x) else None)

                # Store in session state so reruns (from row selection) can access them
                st.session_state['search_results'] = results
                st.session_state['search_summary'] = summary
                st.session_state['search_filename'] = (
                    f"variant_search_{gene_symbol}_{chromosome}" if gene_symbol else f"variant_search_{chromosome}"
                ).replace(" ", "_").replace(",", "_") + ".csv"

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
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "gnomAD": st.column_config.LinkColumn(
                "gnomAD",
                help="View variant in gnomAD browser",
                display_text="View"
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
        ann_df = ann_df.fillna('—')

        with st.expander(f"Annotations: {chrom}:{pos} {ref} > {alt}", expanded=True):
            st.dataframe(ann_df, hide_index=True, use_container_width=True)

    # Download button
    csv = results.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=st.session_state.get('search_filename', 'variant_search.csv'),
        mime="text/csv"
    )