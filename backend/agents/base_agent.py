import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from utils.logging_config import AgentLogger
from utils.helpers import timestamp_now

class BaseAgent(ABC):

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = AgentLogger(name)
        self.tools: Dict[str, Callable] = {}
        self.memory: List[Dict[str, Any]] = []
        self.status = 'idle'
        self.last_run: Optional[str] = None
        self.metrics: Dict[str, Any] = {'runs': 0, 'errors': 0, 'avg_latency_ms': 0}

    def register_tool(self, name: str, handler: Callable):
        self.tools[name] = handler
        self.logger.logger.info(f'Registered tool: {name}')

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered")
        start = datetime.utcnow()
        try:
            result = await self.tools[tool_name](**kwargs) if asyncio.iscoroutinefunction(self.tools[tool_name]) else self.tools[tool_name](**kwargs)
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            self._update_metrics(latency, success=True)
            return result
        except Exception as e:
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            self._update_metrics(latency, success=False)
            self.logger.log_error(e, {'tool': tool_name, 'args': kwargs})
            raise

    def _update_metrics(self, latency_ms: float, success: bool):
        self.metrics['runs'] += 1
        if not success:
            self.metrics['errors'] += 1
        n = self.metrics['runs']
        self.metrics['avg_latency_ms'] = (self.metrics['avg_latency_ms'] * (n - 1) + latency_ms) / n

    def add_to_memory(self, entry: Dict[str, Any]):
        entry['timestamp'] = timestamp_now()
        entry['agent'] = self.name
        self.memory.append(entry)
        max_mem = self.config.get('memory_window', 100)
        if len(self.memory) > max_mem:
            self.memory = self.memory[-max_mem:]

    def get_memory(self, n: int=10) -> List[Dict[str, Any]]:
        return self.memory[-n:]

    def get_status(self) -> Dict[str, Any]:
        return {'name': self.name, 'status': self.status, 'last_run': self.last_run, 'metrics': self.metrics, 'tools': list(self.tools.keys()), 'memory_size': len(self.memory)}

    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        pass

    async def initialize(self):
        self.status = 'ready'
        self.logger.logger.info(f'Agent {self.name} initialized')

    async def shutdown(self):
        self.status = 'stopped'
        self.logger.logger.info(f'Agent {self.name} shutdown')