import streamlit as st
import pandas as pd
from utils.streamlit_db import DatabaseClient
from queries.variant_queries import get_variants_advanced_search

st.set_page_config(page_title="Advanced Variant Search")

db = DatabaseClient()

st.title("Advanced Variant Search")
st.write("Search variants by gene symbol, chromosome, and/or position range with detailed frequency analysis.")

# Search form
with st.form("search_form"):
    st.header("Search Parameters")

    col1, col2 = st.columns(2)

    with col1:
        gene_symbol = st.text_input(
            "Gene Symbol",
            placeholder="e.g., BRCA1, TP53, APOE",
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

    st.info("You can search by gene alone, position range alone, or combine both for more specific results.")

    search_button = st.form_submit_button("Search Variants", type="primary")

def build_query_and_params():
    """Build the SQL query with dynamic filters based on user input."""
    base_query = get_variants_advanced_search()

    where_parts = []
    params = []

    # Gene filter
    if gene_symbol.strip():
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

    # Build WHERE clause
    where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    # Format the query with WHERE clause
    final_query = base_query.format(where_clause=where_clause)

    return final_query, tuple(params)

if search_button:
    # Validate input
    if not gene_symbol.strip() and not chromosome and start_pos is None and end_pos is None:
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
                    'alt_allele_freq': 'Alt Freq',
                    'homozygous_ref_freq': 'AA Freq',
                    'heterozygous_freq': 'AB Freq',
                    'homozygous_alt_freq': 'BB Freq'
                }

                display_results = display_results.rename(columns=column_mapping)

                # Format frequency columns for better readability
                freq_cols = ['Ref Freq', 'Alt Freq', 'AA Freq', 'AB Freq', 'BB Freq']
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
                    use_container_width=True,
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