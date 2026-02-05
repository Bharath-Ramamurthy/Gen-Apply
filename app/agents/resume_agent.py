import os
import json
import re
from typing import Dict, Any

from app.file_utils import file_parser, pdf_generator
from core.logger import get_logger
from core.prompt_loader import PROMPTS
from core import error_handler
from app.connectors import get_connector
from core.contract import AgentResult   # ✅ contract import
from .base_agent import BaseAgent

logger = get_logger(__name__)


class ResumeAgent(BaseAgent):
    TASK_NAME = "resume"
    PROMPT_KEY = "resume_generator"

    def __init__(self, resume_file: str, job_description: str, job_role: str, **kwargs):
        super().__init__(**kwargs)
        self.resume_file = resume_file
        self.job_description = job_description
        self.job_role = job_role
        self.connector = get_connector(self.TASK_NAME)

    def run(self) -> AgentResult:   # ✅ contract used
        try:
            if not os.path.exists(self.resume_file):
                raise FileNotFoundError("Resume file not found")

            resume_latex = file_parser.read_tex_file(self.resume_file)
            prompt = PROMPTS[self.PROMPT_KEY].format(
                resume_latex_code=resume_latex,
                job_description=self.job_description,
                position=self.job_role,
            )

            response = self.connector.send_query(prompt)
            raw = response["response"]

            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not json_match:
                raise ValueError("Invalid JSON returned by LLM")

            data = json.loads(json_match.group())

            pdf_path = pdf_generator.generate_pdf(
                data["latex_code"], "resume", os.getenv("RESUME_DIR", ".")
            )

            return {
                "status": "success",
                "artifact": pdf_path,
                "message": "",   
            }

        except Exception as e:
            result = error_handler.handle_error(
                error=e,
                task=self.TASK_NAME,
                retry_callback=lambda: ResumeAgent(
                    resume_file=self.resume_file,
                    job_description=self.job_description,
                    job_role=self.job_role,
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
