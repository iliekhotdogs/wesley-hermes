"""Keep the Hermes gateway supervisor alive outside the Hermes gateway."""
from __future__ import annotations

import time

from hermes_gateway_supervisor import main as check_once


while True:
    try:
        check_once()
    except Exception:
        # The one-shot supervisor logs expected failures; this guard keeps a
        # transient unexpected exception from taking down the external loop.
        pass
    time.sleep(30)
