import clickhouse_connect
from datetime import datetime
from src.core.config import settings
from src.models.schemas import EvalRunSchema


# All columns that write_run() inserts — using ADD COLUMN IF NOT EXISTS makes this
# safe to run on both fresh tables and old persisted tables from Docker volumes.
_ALL_COLUMNS = [
    # Original schema columns (may be absent in old volume tables)
    ("correctness_score",    "Nullable(UInt8)"),
    ("completeness_score",   "Nullable(UInt8)"),
    ("faithfullness_score",  "Nullable(UInt8)"),   # legacy typo kept for back-compat
    ("groundedness_score",   "Nullable(UInt8)"),
    ("clarity_score",        "Nullable(UInt8)"),
    ("verdict",              "Nullable(String)"),
    ("rationale",            "Nullable(String)"),
    # New columns added in this upgrade
    ("judge_verdict",        "Nullable(String)"),
    ("task_type",            "Nullable(String)"),
    ("prompt_version",       "Nullable(String)"),
    ("faithfulness_score",   "Nullable(Float64)"),  # ragas faithfulness (Float64)
    ("rag_groundedness_score", "Nullable(Float64)"), # ragas answer_relevancy (Float64)
]


class ClickHouseWriter:
    def __init__(self):
        self.client = None

    def connect(self, max_retries=5, retry_delay=3):
        import time
        for attempt in range(max_retries):
            try:
                self.client = clickhouse_connect.get_client(
                    host=settings.CLICKHOUSE_HOST,
                    password=settings.CLICKHOUSE_PASSWORD,
                    username="default"
                )
                self._init_table()
                print("Successfully connected to ClickHouse")
                return
            except Exception as e:
                print(f"Failed to connect to ClickHouse (attempt {attempt+1}/{max_retries}). Retrying in {retry_delay}s...")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    print("Could not connect to ClickHouse after multiple attempts.")
                    raise


    def _init_table(self):
        # Minimal base table — only non-nullable columns that must be present at creation.
        # All nullable columns are handled by the ALTER TABLE loop below so this is
        # safe for both fresh starts and existing persisted Docker volumes.
        create_query = """
        CREATE TABLE IF NOT EXISTS eval_runs (
            run_id    UUID,
            timestamp DateTime,
            prompt    String,
            model     String,
            response  String,
            latency_ms UInt32,
            cost       Float64,
            cache_hit  Bool
        ) ENGINE = MergeTree()
        ORDER BY timestamp;
        """
        self.client.command(create_query)

        # Ensure every column the writer uses is present, regardless of how old
        # the table schema in the persisted volume is.
        for col_name, col_type in _ALL_COLUMNS:
            try:
                self.client.command(
                    f"ALTER TABLE eval_runs ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                )
            except Exception as e:
                print(f"[ClickHouse] Could not add column {col_name}: {e}")

    def write_run(self, run: EvalRunSchema):
        if not self.client:
            self.connect()
        row = [
            run.run_id,
            datetime.utcnow(),
            run.prompt,
            run.model,
            run.response,
            run.latency_ms,
            run.cost,
            run.cache_hit,
            run.correctness_score,
            run.completeness_score,
            run.faithfullness_score,
            run.groundedness_score,   
            run.clarity_score,
            run.verdict,
            run.rationale,
            run.judge_verdict,         
            run.task_type,             
            run.prompt_version,        
            run.faithfulness_score,    
            run.rag_groundedness_score, 
        ]
        self.client.insert(
            'eval_runs',
            [row],
            column_names=[
                'run_id', 'timestamp', 'prompt', 'model', 'response', 'latency_ms',
                'cost', 'cache_hit',
                'correctness_score', 'completeness_score',
                'faithfullness_score', 'groundedness_score', 'clarity_score',
                'verdict', 'rationale',
                'judge_verdict', 'task_type', 'prompt_version',
                'faithfulness_score', 'rag_groundedness_score',  # Float64 columns
            ]
        )
clickhouse_writer = ClickHouseWriter()
