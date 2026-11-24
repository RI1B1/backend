from fastapi import Query


class PageParams:
    """Pakai: params: PageParams = Depends(). Query: ?page=1&limit=20"""

    def __init__(
        self,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
    ):
        self.page = page
        self.limit = limit

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit
