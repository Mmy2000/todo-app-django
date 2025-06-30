from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "per_page"
    max_page_size = 100

    def get_pagination_meta(self):
        return {
            "first_page": 1,
            "last_page": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "per_page": self.page.paginator.per_page,
            "total_count": self.page.paginator.count,
        }
