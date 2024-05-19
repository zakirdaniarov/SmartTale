from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class MyCustomPagination(PageNumberPagination):
    page_size = 10

    def get_paginated_response(self, data):
        return Response({"links": {
            "next": self.get_next_link(),
            "previous": self.get_previous_link()
        },
            "page count": self.page.paginator.num_pages,
            "current page": self.page.number,
            "data": data
        })
