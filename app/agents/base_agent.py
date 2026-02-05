# agents/base_agent.py
from typing import Any, Dict
from core.error_handler import handle_error
from core.logger import get_logger

logger = get_logger(__name__)


class BaseAgent:
    """
    Base class for all agents.

    Responsibilities:
    - Provide a common TASK_NAME
    - Provide a shared failure-handling helper
    """

    TASK_NAME: str = "base"

    def handle_failure(
        self,
        error: Exception,
        retry_callback,
    ) -> Dict[str, Any]:
        """
        Delegate failure handling to the diagnostic error handler.
        """
        try:
            return handle_error(
                error=error,
                task=self.TASK_NAME,
                retry_callback=retry_callback,
            )
        except Exception as retry_error:
            logger.critical(
                f"Diagnostic handling failed for task '{self.TASK_NAME}': {retry_error}",
                exc_info=True,
            )
            return {
                "status": "failed",
                "artifact": None,
                "error_message": str(retry_error),
            }
