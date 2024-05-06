from django.core.paginator import Paginator
from .serializers import OrderListAPI, EquipmentSerializer


def get_paginated_data(queryset, request, list_type):
    page_number = request.query_params.get('page', 1)
    page_limit = request.query_params.get('limit', 10)

    paginator = Paginator(queryset, page_limit)
    page_obj = paginator.get_page(page_number)

    serializer = OrderListAPI(page_obj, many=True, context={'request': request, 'list_type': list_type})

    data = {
        'data': serializer.data,
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next_page': page_obj.has_next(),
        'has_prev_page': page_obj.has_previous(),
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'prev_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
    }
    return data


def equipment_paginated(queryset, request):
    page_number = request.query_params.get('page', 1)
    max_page = request.query_params.get('limit', 10)

    paginator = Paginator(queryset, max_page)
    page_obj = paginator.get_page(page_number)

    serializer = EquipmentSerializer(page_obj, many=True, context={'request': request})

    data = {
        'data': serializer.data,
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next_page': page_obj.has_next(),
        'has_prev_page': page_obj.has_previous(),
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'prev_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
    }

    return data
