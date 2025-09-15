# Shim module to keep the original import path stable
# Delegates implementation to the clean Matrix exporter that preserves original JS logic
from .timeline_exporter_matrix_clean import export_event, generate_html  # noqa: F401
