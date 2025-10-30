import streamlit as st
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
        # Manual search validation
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

                if params:
                    results = db.execute_query_with_params(query, params)
                else:
                    results = db.execute_query(query)

            if len(results) == 0:
                st.warning("No variants found matching your search criteria.")
            else:
                st.header("Query Results")

                display_results = results.copy()

                # Add Gnomad hyperlink column
                def create_gnomad_link(row):
                    chrom = row['chromosome']
                    pos = row['position']
                    ref = row['reference_allele']
                    alt = row['alternate_allele']
                    return f"https://gnomad.broadinstitute.org/variant/{chrom}-{pos}-{ref}-{alt}"

                display_results['gnomad_url'] = display_results.apply(create_gnomad_link, axis=1)

                # Rename columns for better display
                column_mapping = {
                    'gene': 'Gene',
                    'chromosome': 'Chr',
                    'position': 'Position',
                    'reference_allele': 'Ref',
                    'alternate_allele': 'Alt',
                    'rs_id': 'RS ID',
                    'alternate_allele_count': 'Alt Count',
                    'allele_number': 'Total Alleles',
                    'ref_allele_freq': 'Ref Freq',
                    'alt_allele_freq': 'Alt Freq',
                    'gnomad_url': 'Gnomad'
                }

                display_results = display_results.rename(columns=column_mapping)

                # Format frequency columns for better readability
                freq_cols = ['Ref Freq', 'Alt Freq']
                for col in freq_cols:
                    if col in display_results.columns:
                        display_results[col] = display_results[col].apply(lambda x: f"{x:.4f}")

                styled_results = display_results.style.format({
                    "Position": lambda x : '{:,.0f}'.format(x)
                },
                thousands=' '
                )

                st.dataframe(
                    styled_results,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "Gnomad": st.column_config.LinkColumn(
                            "Gnomad",
                            help="View variant in Gnomad browser",
                            display_text="View"
                        )
                    }
                )

                st.write(f"**Total variants returned:** {len(results)}")

                # Download button
                csv = display_results.to_csv(index=False)
                filename = f"variant_search_{gene_symbol}_{chromosome}" if gene_symbol else f"variant_search_{chromosome}"
                filename = filename.replace(" ", "_").replace(",", "_") + ".csv"

                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=filename,
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"❌ Search failed: {str(e)}")
            st.info("Please check your database connection and ensure the database contains data.")
            with st.expander("Error Details"):
                st.code(str(e))