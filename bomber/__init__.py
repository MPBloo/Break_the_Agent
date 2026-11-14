"""Water Bomber: a reinforcement-learning environment about calibrating an
unknown system with a few costly experiments, then acting once."""
from .config import Config
from .episode import Episode

__all__ = ["Config", "Episode"]
