import math

def paginate(items: list, page: int, page_size: int) -> dict:
    """
    Paginates a list of items, returning a dictionary with pagination metadata.

    Args:
        items: The list of items to paginate.
        page: The requested page number (1-indexed).
        page_size: The number of items per page.

    Returns:
        A dictionary containing:
        - "items": items for the requested page
        - "page": current page number (adjusted for empty items)
        - "page_size": requested page size
        - "total_items": total number of items
        - "total_pages": total number of pages
        - "has_next": whether there is a next page
        - "has_prev": whether there is a previous page

    Raises:
        ValueError: If page_size is not greater than 0 or page is not greater than or equal to 1.
    """
    if page_size <= 0:
        raise ValueError("page_size must be greater than 0")
    if page < 1:
        raise ValueError("page must be greater than or equal to 1")

    total_items = len(items)

    # Calculate total_pages. If total_items is 0, total_pages is 0.
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

    current_page_items = []
    # Only attempt to slice items if there are items and the requested page is within valid range
    if total_items > 0 and 1 <= page <= total_pages:
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        current_page_items = items[start_index:end_index]

    # Determine the 'page' value for the output dictionary based on requirements:
    # - "If items is empty, return total_pages=0, page=1"
    # - "If page is out of range, return empty items but correct metadata" (implies requested page)
    output_page = 1 if total_items == 0 else page

    # Determine has_next and has_prev based on the output_page and total_pages
    has_next = output_page < total_pages
    has_prev = output_page > 1

    return {
        "items": current_page_items,
        "page": output_page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev,
    }