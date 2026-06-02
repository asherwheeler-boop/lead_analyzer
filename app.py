import io
        import os
        import pandas as pd
        import streamlit as st

        from auth.login import require_login
        from core.analysis import (
            infer_xy_columns,
            infer_curvature_column,
            infer_segment_column,
            infer_wire_column,
            load_uploaded_table,
            build_segment_summary,
            make_trace_plot,
            make_threshold_plot,
            make_overlay_plot,
            make_metric_cards,
            to_excel_bytes,
        )

        st.set_page_config(
            page_title="Pacing Lead Analyzer",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        require_login()

        st.title("Pacing Lead Analyzer")
        st.caption("Render-ready rebuild with team-only access, upload workflows, curvature views, threshold checks, and report export.")

        with st.sidebar:
            st.header("Controls")
            threshold = st.number_input("Curvature limit (cm⁻¹)", min_value=0.0, value=0.88, step=0.01)
            app_mode = st.radio(
                "Analysis mode",
                ["Single file", "Two-file comparison"],
                horizontal=False,
            )
            st.markdown("---")
            st.subheader("Data upload")
            file_a = st.file_uploader("Primary file (.xlsx or .csv)", type=["xlsx", "csv"], key="file_a")
            file_b = None
            if app_mode == "Two-file comparison":
                file_b = st.file_uploader("Comparison file (.xlsx or .csv)", type=["xlsx", "csv"], key="file_b")
            st.markdown("---")
            st.info("Set Render environment variables TEAM_APP_USERNAME and TEAM_APP_PASSWORD to control access.")

        if not file_a:
            st.warning("Upload at least one file to begin. The app is fully deployable now; once you add your existing data/logic, the site can keep the same workflow while running cleanly on Render.")
            st.stop()

        primary = load_uploaded_table(file_a)
        comparison = load_uploaded_table(file_b) if file_b is not None else None

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Overview",
            "Wire Tracings",
            "Curvature & Segments",
            "Threshold Check",
            "Validation Summary",
            "Export",
        ])

        with tab1:
            st.subheader("Dataset overview")
            c1, c2 = st.columns(2)
            with c1:
                st.write("Primary dataset preview")
                st.dataframe(primary.head(25), use_container_width=True)
            with c2:
                if comparison is not None:
                    st.write("Comparison dataset preview")
                    st.dataframe(comparison.head(25), use_container_width=True)
                else:
                    st.write("Comparison dataset preview")
                    st.info("Upload a second file in the sidebar to enable side-by-side comparison.")
            metrics = make_metric_cards(primary, threshold)
            mcols = st.columns(len(metrics))
            for idx, (label, value) in enumerate(metrics.items()):
                mcols[idx].metric(label, value)

        with tab2:
            st.subheader("Wire tracings")
            pfig, pmsg = make_trace_plot(primary, title="Primary wire tracing")
            if pfig is not None:
                st.plotly_chart(pfig, use_container_width=True)
            else:
                st.info(pmsg)

            if comparison is not None:
                cfig, cmsg = make_trace_plot(comparison, title="Comparison wire tracing")
                if cfig is not None:
                    st.plotly_chart(cfig, use_container_width=True)
                else:
                    st.info(cmsg)

                ofig, omsg = make_overlay_plot(primary, comparison, title="Overlay of uploaded tracings")
                if ofig is not None:
                    st.plotly_chart(ofig, use_container_width=True)
                else:
                    st.info(omsg)

        with tab3:
            st.subheader("Curvature and segment summary")
            summary_a = build_segment_summary(primary)
            st.write("Primary data")
            st.dataframe(summary_a, use_container_width=True)
            if comparison is not None:
                summary_b = build_segment_summary(comparison)
                st.write("Comparison data")
                st.dataframe(summary_b, use_container_width=True)

        with tab4:
            st.subheader("Threshold check")
            tfig, tmsg = make_threshold_plot(primary, threshold, title="Primary threshold check")
            if tfig is not None:
                st.plotly_chart(tfig, use_container_width=True)
            else:
                st.info(tmsg)
            if comparison is not None:
                tfig2, tmsg2 = make_threshold_plot(comparison, threshold, title="Comparison threshold check")
                if tfig2 is not None:
                    st.plotly_chart(tfig2, use_container_width=True)
                else:
                    st.info(tmsg2)

        with tab5:
            st.subheader("Validation summary")
            xa = infer_xy_columns(primary)
            ca = infer_curvature_column(primary)
            sa = infer_segment_column(primary)
            wa = infer_wire_column(primary)
            st.markdown(f"**Primary field detection**  
XY columns: `{xa}`  
Curvature: `{ca}`  
Segment: `{sa}`  
Wire: `{wa}`")
            if comparison is not None:
                xb = infer_xy_columns(comparison)
                cb = infer_curvature_column(comparison)
                sb = infer_segment_column(comparison)
                wb = infer_wire_column(comparison)
                st.markdown(f"**Comparison field detection**  
XY columns: `{xb}`  
Curvature: `{cb}`  
Segment: `{sb}`  
Wire: `{wb}`")
                if 'summary_b' not in locals():
                    summary_b = build_segment_summary(comparison)
                merged = summary_a.merge(summary_b, on=['wire', 'segment'], suffixes=('_primary', '_comparison'))
                st.write("Segment-level merged summary")
                st.dataframe(merged, use_container_width=True)
            else:
                st.info("Upload a comparison file to build cross-file validation tables.")

        with tab6:
            st.subheader("Export")
            export_sheets = {"primary_summary": summary_a}
            if comparison is not None:
                if 'summary_b' not in locals():
                    summary_b = build_segment_summary(comparison)
                export_sheets["comparison_summary"] = summary_b
            export_sheets["primary_raw"] = primary
            if comparison is not None:
                export_sheets["comparison_raw"] = comparison
            xlsx_data = to_excel_bytes(export_sheets)
            st.download_button(
                label="Download results workbook",
                data=xlsx_data,
                file_name="pacing_lead_analysis_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.success("This repo is already structured for Render. Replace or extend the helper functions in core/analysis.py with your exact existing logic to keep the same website behavior while deploying cleanly.")
