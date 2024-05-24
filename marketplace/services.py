from django.core.paginator import Paginator
from .serializers import OrderListAPI, EquipmentSerializer, MyOrderEquipmentSerializer, ServiceSerializer


def get_paginated_data(queryset, request, list_type):
    page_number = request.query_params.get('page', 1)
    page_limit = request.query_params.get('limit', 10)

    paginator = Paginator(queryset, page_limit)
    page_obj = paginator.get_page(page_number)

    serializer = OrderListAPI(page_obj, many=True, context={'request': request, 'list_type': list_type})
    content = {"data": serializer.data}
    data = {
        'data': content,
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next_page': page_obj.has_next(),
        'has_prev_page': page_obj.has_previous(),
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'prev_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
    }
    return data


def get_services_paginated_data(queryset, request, author):
    page_number = request.query_params.get('page', 1)
    page_limit = request.query_params.get('limit', 10)

    paginator = Paginator(queryset, page_limit)
    page_obj = paginator.get_page(page_number)

    serializer = ServiceSerializer(page_obj, many=True, context={'request': request, 'author': author})

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


def get_equipment_paginated(queryset, request, equipment_type):
    page_number = request.query_params.get('page', 1)
    max_page = request.query_params.get('limit', 10)

    paginator = Paginator(queryset, max_page)
    page_obj = paginator.get_page(page_number)

    serializer = EquipmentSerializer(page_obj, many=True, context={'request': request, 'equipment_type': equipment_type})

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


def get_order_or_equipment(queryset, request):
    page_number = request.query_params.get('page', 1)
    max_page = request.query_params.get('limit', 10)

    paginator = Paginator(queryset, max_page)
    page_objs = paginator.get_page(page_number)
    instance_list = list(page_objs.object_list)

    serializer = MyOrderEquipmentSerializer(instance=instance_list, many=True, context={"request": request})

    data = {
        'data': serializer.data,
        'total_pages': paginator.num_pages,
        'current_page': page_objs.number,
        'has_next_page': page_objs.has_next(),
        'has_prev_page': page_objs.has_previous(),
        'next_page_number': page_objs.next_page_number() if page_objs.has_next() else None,
        'prev_page_number': page_objs.previous_page_number() if page_objs.has_previous() else None
    }

    return data
