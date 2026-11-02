"""log_info: the log's length and page size."""

from .checks import PAGE_SIZE, result, seed_problem


def verify_input(value):
    problem = seed_problem(value.seed)
    return result(problem is None, problem or "input is valid")


def verify_output(input_value, output_value, workspace):
    if output_value.seed != input_value.seed:
        return result(False, "the info is for another seed")
    if output_value.events < 1 or output_value.page_size != PAGE_SIZE:
        return result(False, f"a log has events and a page size of {PAGE_SIZE}")
    return result(True, f"{output_value.events} events")
