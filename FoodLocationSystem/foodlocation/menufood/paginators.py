from rest_framework import pagination


class StorePaginator(pagination.PageNumberPagination):
    page_size = 5