"""A SUM projection is private evidence, distinct from published corpus citations."""

from sum_contracts.ai import CreateRunRequest, RunResult


def is_sum_projection_answer(request: CreateRunRequest, result: RunResult) -> bool:
    analysis = result.student_analysis
    options = request.student_options
    return bool(
        request.audience == "student"
        and options
        and options.use_academic_context
        and options.connection_id
        and analysis
        and analysis.route == "personalized"
        and analysis.answer_basis == "sum_projection"
        and analysis.context.status == "available"
        and analysis.context.source in {"sum", "mock"}
        and analysis.context.snapshot_id
        and not result.evidence
        and not result.citations
        and not analysis.checks
    )
