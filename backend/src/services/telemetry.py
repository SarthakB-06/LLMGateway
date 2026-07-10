import clickhouse_connect
from datetime import datetime
from src.core.config import settings

class TelemetryService:
    def __init__(self):
        self.client = None
        self._initialized = False

    def _get_client(self):
        """Establishes a connection to ClickHouse."""
        if not self.client:
            # Connects to the local Docker container on the default HTTP port
            self.client = clickhouse_connect.get_client(
                host="localhost", 
                port=8123,
                username="default",
                password=settings.CLICKHOUSE_PASSWORD
            )
        return self.client

    def initialize_db(self):
        if not self._initialized:
            client = self._get_client()
            # Drop the old basic table so we can upgrade the schema
            client.command('DROP TABLE IF EXISTS gateway_logs')
            client.command('''
                CREATE TABLE IF NOT EXISTS gateway_logs (
                    timestamp DateTime,
                    model String,
                    latency_ms Float32,
                    cache_hit UInt8,
                    cache_type String,
                    total_tokens UInt32,    # 👈 NEW
                    estimated_cost Float64  # 👈 NEW
                ) ENGINE = MergeTree()
                ORDER BY timestamp
            ''')
            self._initialized = True

    def log_usage(self, model: str, latency_ms: float, cache_hit: bool, cache_type: str, total_tokens: int, estimated_cost: float):
        try:
            self.initialize_db()
            client = self._get_client()
            
            data = [[
                datetime.now(),
                model,
                latency_ms,
                1 if cache_hit else 0,
                cache_type if cache_type else "",
                total_tokens,     
                estimated_cost    
            ]]
            
            client.insert('gateway_logs', data, column_names=[
                'timestamp', 'model', 'latency_ms', 'cache_hit', 'cache_type', 'total_tokens', 'estimated_cost'
            ])
            print(f"📊 [TELEMETRY] Logged: {latency_ms:.2f}ms | Tokens: {total_tokens} | Cost: ${estimated_cost:.6f}")
        except Exception as e:
            print(f"⚠️ [TELEMETRY WARNING] {e}")

telemetry_service = TelemetryService()