from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from app.agents import ResumeAgent, CoverLetterAgent, EmailAgent
from core.logger import get_logger

logger = get_logger(__name__)


class ResumeWorkflowState(TypedDict):
    resume_file: str
    job_role: str
    job_description: str
    company: str
    receiver_email: str

    generate_cover_letter: bool
    send_email: bool

    refined_resume_path: Optional[str]
    cover_letter_path: Optional[str]

    status: str
    error_message: Optional[str]


def resume_node(state: ResumeWorkflowState) -> ResumeWorkflowState:
    logger.info("Running ResumeAgent")

    result = ResumeAgent(
        resume_file=state["resume_file"],
        job_role=state["job_role"],
        job_description=state["job_description"],
    ).run()

    if result["status"] == "failed":
        return {**state, "status": "failed", "error_message": result["message"]}

    return {
        **state,
        "refined_resume_path": result["artifact"],
        "status": "resume_done",
    }


def cover_letter_node(state: ResumeWorkflowState) -> ResumeWorkflowState:
    logger.info("Running CoverLetterAgent")

    result = CoverLetterAgent(
        refined_resume_path=state["refined_resume_path"],
        job_role=state["job_role"],
        job_description=state["job_description"],
        company=state["company"],
    ).run()

    if result["status"] == "failed":
        return {**state, "status": "failed", "error_message": result["message"]}

    return {
        **state,
        "cover_letter_path": result["artifact"],
        "status": "cover_letter_done",
    }


def email_node(state: ResumeWorkflowState) -> ResumeWorkflowState:
    logger.info("Running EmailAgent")

    result = EmailAgent(
        resume_path=state["refined_resume_path"],
        position=state["job_role"],
        job_description=state["job_description"],
        company=state["company"],
        receiver_email=state["receiver_email"],
        attach_cover_letter=state["generate_cover_letter"],
        cover_letter_path=state.get("cover_letter_path"),
    ).run()

    if result["status"] == "failed":
        return {**state, "status": "failed", "error_message": result["message"]}

    return {**state, "status": "completed"}


def resume_router(state: ResumeWorkflowState) -> str:
    if state["status"] == "failed":
        return END
    return "cover_letter" if state["generate_cover_letter"] else "email"


def cover_letter_router(state: ResumeWorkflowState) -> str:
    if state["status"] == "failed":
        return END
    return "email" if state["send_email"] else END


def build_resume_workflow():
    graph = StateGraph(ResumeWorkflowState)

    graph.add_node("resume", resume_node)
    graph.add_node("cover_letter", cover_letter_node)
    graph.add_node("email", email_node)

    graph.set_entry_point("resume")

    graph.add_conditional_edges(
        "resume",
        resume_router,
        {"cover_letter": "cover_letter", "email": "email", END: END},
    )

    graph.add_conditional_edges(
        "cover_letter",
        cover_letter_router,
        {"email": "email", END: END},
    )

    graph.add_edge("email", END)

    return graph.compile()
