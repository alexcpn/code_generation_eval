def paginate(items: list, page: int, page_size: int) -> dict:
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size <= 0:
        raise ValueError("page_size must be > 0")
    
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
    
    # Optional: validate page is within bounds
    # if page > total_pages and total_items > 0:
    #     raise ValueError(f"page {page} exceeds total_pages {total_pages}")
    
    start_idx = (page - 1) * page_size
    paginated_items = items[start_idx : start_idx + page_size]
    
    return {
        "items": paginated_items,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
