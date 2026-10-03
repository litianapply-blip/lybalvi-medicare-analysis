"""Build readable SQL models into a staged, persistent DuckDB database."""
import duckdb
import pandas as pd


def model(root, stage, cleaned, config):
    con = duckdb.connect(str(stage / 'analytics.duckdb'))
    con.register('clean_input', cleaned)
    thresholds = pd.DataFrame({'claim_threshold': sorted(set(config['threshold_sensitivity'] + [config['segment_claim_threshold']]))})
    con.register('thresholds', thresholds)
    try:
        con.execute((root / 'sql/reporting.sql').read_text())
        if set(config['years']) == {2023, 2024}:
            con.execute((root / 'sql/growth.sql').read_text())
        return con
    except Exception:
        con.close()
        raise
