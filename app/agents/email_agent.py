import json
import re
from typing import Dict, Any

from app.email_utils.gmail_sender import send_email_with_attachment
from app.file_utils import file_parser
from core.logger import get_logger
from core.prompt_loader import PROMPTS
from core import error_handler
from core.contract import AgentResult
from app.connectors import get_connector
from .base_agent import BaseAgent

logger = get_logger(__name__)


class EmailAgent(BaseAgent):
    TASK_NAME = "email"
    PROMPT_KEY = "email_generator"

    def __init__(
        self,
        resume_path: str,
        position: str,
        job_description: str,
        company: str,
        receiver_email: str,
        attach_cover_letter: bool = False,
        cover_letter_path: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.resume_path = resume_path
        self.position = position
        self.job_description = job_description
        self.company = company
        self.receiver_email = receiver_email
        self.attach_cover_letter = attach_cover_letter
        self.cover_letter_path = cover_letter_path
        self.connector = get_connector(self.TASK_NAME)

    def run(self) -> AgentResult:
        try:
            # -----------------------------
            # 1. Extract resume text
            # -----------------------------
            resume_text = file_parser.extract_text_from_pdf(self.resume_path)

            # -----------------------------
            # 2. Build prompt
            # -----------------------------
            prompt = PROMPTS[self.PROMPT_KEY].format(
                resume_text=resume_text,
                job_description=self.job_description,
                position=self.position,
                company=self.company,
            )

            # -----------------------------
            # 3. Call LLM
            # -----------------------------
            response = self.connector.send_query(prompt)
            raw = response.get("response", "")

            # -----------------------------
            # 4. Parse JSON safely
            # -----------------------------
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not json_match:
                raise ValueError("Invalid JSON returned by LLM")

            data = json.loads(json_match.group())

            if "email_subject" not in data or "html_code" not in data:
                raise ValueError("LLM JSON missing required keys")

            # -----------------------------
            # 5. Send email
            # -----------------------------
            send_email_with_attachment(
                receiver_email=self.receiver_email,
                email_subject=data["email_subject"],
                email_body_text=data["html_code"],
                resume_path=self.resume_path,
                cover_letter_path=self.cover_letter_path if self.attach_cover_letter else None,
            )

            # -----------------------------
            # 6. Success (AgentResult)
            # -----------------------------
            return {
                "status": "success",
                "artifact": self.receiver_email,
                "message": "Email sent successfully",
            }

        except Exception as e:
         logger.exception("EmailAgent failed – not retrying or diagnosing")
         return {"status": "failed","artifact": None,"message": str(e),}
