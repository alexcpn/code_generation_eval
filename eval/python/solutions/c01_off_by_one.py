def paginate(items: list, page: int, page_size: int) -> dict:
    # Validate inputs
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size <= 0:
        raise ValueError("page_size must be > 0")

    total_items = len(items)

    # Handle empty list edge case
    if total_items == 0:
        return {
            "items": [],
            "page": 1,
            "page_size": page_size,
            "total_items": 0,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False
        }

    # Calculate total pages using ceiling division logic
    total_pages = (total_items + page_size - 1) // page_size

    # Calculate slice indices
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Python's list slicing safely handles out-of-range indices
    # by just returning an empty list.
    paginated_items = items[start_idx:end_idx]

    return {
        "items": paginated_items,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }
