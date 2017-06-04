import os

from hypothesis import settings

local_settings = settings(
    max_examples=int(os.getenv('HYPOTHESIS_MAX_EXAMPLES', 100)),
    perform_health_check=False,
)
settings.register_profile("fuzztests", local_settings)
settings.load_profile("fuzztests")
