def paginate(items: list, page: int, page_size: int) -> dict:
    # 1. Input Validation
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size <= 0:
        raise ValueError("page_size must be > 0")

    total_items = len(items)
    
    # 2. Handle Empty List Edge Case
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

    # 3. Calculate Metadata
    # Ceiling division: (a + b - 1) // b
    total_pages = (total_items + page_size - 1) // page_size
    
    # 4. Determine Slice Indices
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Python slicing is "safe": if start_idx > len(items), it returns []
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
