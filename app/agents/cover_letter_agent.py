import os
import json
import re
from typing import Dict, Any
from functools import partial

from app.file_utils import file_parser, pdf_generator
from core.logger import get_logger
from core.prompt_loader import PROMPTS
from core import error_handler
from core.contract import AgentResult
from app.connectors import get_connector
from .base_agent import BaseAgent

logger = get_logger(__name__)


class CoverLetterAgent(BaseAgent):
    TASK_NAME = "cover_letter"
    PROMPT_KEY = "cover_letter_generator"

    def __init__(
        self,
        refined_resume_path: str,
        job_role: str,
        job_description: str,
        company: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.refined_resume_path = refined_resume_path
        self.job_role = job_role
        self.job_description = job_description
        self.company = company
        self.connector = get_connector(self.TASK_NAME)

    def run(self) -> AgentResult:
        try:
            resume_text = file_parser.extract_text_from_pdf(self.refined_resume_path)
            prompt = PROMPTS[self.PROMPT_KEY].format(
                resume_text=resume_text,
                job_description=self.job_description,
                company=self.company,
                position=self.job_role,
            )

            response = self.connector.send_query(prompt)
            raw = response["response"]

            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not json_match:
                raise ValueError("Invalid JSON returned by LLM")

            data = json.loads(json_match.group())

            pdf_path = pdf_generator.generate_pdf(
                data["latex_code"],
                "cover_letter",
                os.getenv("COVER_LETTER_DIR", "."),
            )

            return {
                "status": "success",
                "artifact": pdf_path,
                "message": None,
            }

        except Exception as e:
            result = error_handler.handle_error(
                error=e,
                task=self.TASK_NAME,
                retry_callback=lambda: CoverLetterAgent(
                    refined_resume_path=self.refined_resume_path,
                    job_role=self.job_role,
                    job_description=self.job_description,
                    company=self.company,
                ),
            )

            return {
                "status": "failed",
                "artifact": None,
                "message": (
                    result.get("message")
                    or result.get("error_message")
                    or result.get("error")
                    or str(e)
                ),
            }
