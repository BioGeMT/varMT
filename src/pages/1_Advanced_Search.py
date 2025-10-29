import streamlit as st
from streamlit_searchbox import st_searchbox
import pandas as pd

from utils.streamlit_db import DatabaseClient
from queries.variant_queries import get_variants_advanced_search

st.set_page_config(page_title="Advanced Variant Search")

db = DatabaseClient()

st.title("Advanced Variant Search")
st.write("Search variants by gene symbol, chromosome, and/or position range with detailed frequency analysis.")

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

# Search form
st.header("Search Parameters")

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

def build_query_and_params():
    """Build the SQL query with dynamic filters based on user input."""
    base_query = get_variants_advanced_search()

    where_parts = []
    having_parts = []
    params = []

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
    # Validate input
    if not (gene_symbol and gene_symbol.strip()) and not chromosome and start_pos is None and end_pos is None:
        st.error("⚠️ Please provide at least one search parameter (gene symbol, chromosome, or position range).")
    elif start_pos is not None and end_pos is not None and start_pos > end_pos:
        st.error("⚠️ Start position must be less than or equal to end position.")
    else:
        try:
            with st.spinner("Searching database..."):
                query, params = build_query_and_params()

                if params:
                    results = db.execute_query_with_params(query, params)
                else:
                    results = db.execute_query(query)

            if len(results) == 0:
                st.warning("No variants found matching your search criteria.")
            else:
                st.header("Query Results")

                display_results = results.copy()

                # Rename columns for better display
                column_mapping = {
                    'gene': 'Gene',
                    'chromosome': 'Chr',
                    'position': 'Position',
                    'reference_allele': 'Ref',
                    'alternate_allele': 'Alt',
                    'rs_id': 'RS ID',
                    'sample_count': 'Samples',
                    'alternate_allele_count': 'Alt Count',
                    'ref_allele_freq': 'Ref Freq',
                    'alt_allele_freq': 'Alt Freq'
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
                    hide_index=True
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Total rows returned:** {len(results)}")
                with col2:
                    total_samples = results['sample_count'].iloc[0] if 'sample_count' in results.columns and len(results) > 0 else 0
                    st.write(f"**Samples in collection:** {total_samples}")

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