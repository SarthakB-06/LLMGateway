import clickhouse_connect
from datetime import datetime
from src.core.config import settings
from src.models.schemas import EvalRunSchema

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
        query = """
        CREATE TABLE IF NOT EXISTS eval_runs (
            run_id UUID,
            timestamp DateTime,
            prompt String,
            model String,
            response String,
            latency_ms UInt32,
            cost Float64,
            cache_hit Bool,
            correctness_score Nullable(UInt8),
            completeness_score Nullable(UInt8),
            clarity_score Nullable(UInt8),
            verdict Nullable(String),
            rationale Nullable(String)
        ) ENGINE = MergeTree()
        ORDER BY timestamp;
        """
        self.client.command(query)

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
            run.clarity_score,
            run.verdict,
            run.rationale
        ]
        
        self.client.insert(
            'eval_runs', 
            [row], 
            column_names=[
                'run_id', 'timestamp', 'prompt', 'model', 'response', 'latency_ms', 
                'cost', 'cache_hit', 'correctness_score', 'completeness_score', 
                'clarity_score', 'verdict', 'rationale'
            ]
        )

clickhouse_writer = ClickHouseWriter()
