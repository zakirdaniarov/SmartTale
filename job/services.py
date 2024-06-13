from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class MyCustomPagination(PageNumberPagination):
    page_size = 10

    def get_paginated_response(self, data):
        return Response({
            'data': data,
            'total_page': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'has_next_page': self.get_next_link(),
            'has_prev_page': self.get_previous_link()
        })
