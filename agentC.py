"""Legacy generation-plus-compilation adapter."""

from agent import AgentAI
from agentCompiler import AgentCompiler


class AgentAIC(AgentAI):
    def __init__(
        self, server_address, model_name, my_role, max_tokens=16000, api_key=""
    ):
        super().__init__(server_address, model_name, my_role, max_tokens, api_key)
        self.temperature = 0.3
        self.compiler = AgentCompiler(
            server_address, model_name, 3, self.api_key, max_tokens
        )
        self.last_result = {}

    def get_response(self, prompt):
        with self._lock:
            response = super().get_response(prompt)
            if response is None:
                return None
            code = self.compiler.get_response(response)
            self.last_result = self.compiler.last_result
            self.messages[-1]["content"] = code
            return code

    def close(self):
        self.compiler.close()
        super().close()
