"""Simple sequential agent ID manager."""

class AgentIDManager:
    """Manages sequential 2-digit agent IDs."""
    _counter = 0
    _max_id = 99
    
    @classmethod
    def get_next_id(cls):
        """Get next sequential agent ID (00-99).
        
        Returns:
            str: Two-digit agent ID (e.g., '00', '01', ..., '99')
        """
        if cls._counter > cls._max_id:
            # Reset counter if it exceeds max (wraparound at 100)
            cls._counter = 0
        
        agent_id = f"{cls._counter:02d}"
        cls._counter += 1
        return agent_id
    
    @classmethod
    def reset(cls):
        """Reset counter to 0. Useful for testing."""
        cls._counter = 0
