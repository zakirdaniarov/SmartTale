import datetime
from rest_framework.generics import ListAPIView
from rest_framework.views import Response, status, APIView
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from .services import get_paginated_data
from drf_yasg.utils import swagger_auto_schema
from authorization.models import UserProfile, Organization
from rest_framework import filters
from django_filters.rest_framework import FilterSet, DateFilter, DjangoFilterBackend
from rest_framework.filters import SearchFilter
from .permissions import CurrentUserOrReadOnly

# Create your views here.
class OrderCategoriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self):
        categories = OrderCategory.objects.all()
        categories_api = OrderCategoryListAPI(categories, many=True)
        content = {"Categories": categories_api.data}
        return Response(content, status=status.HTTP_200_OK)


class BaseOrderListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        raise NotImplementedError("Subclasses must implement get_queryset method.")

    def get_list_type(self):
        raise NotImplementedError("Subclasses must implement get_list_type method.")

    def get(self, request):
        queryset = self.get_queryset()
        paginated_data = get_paginated_data(queryset, request, self.get_list_type())
        return Response(paginated_data, status=status.HTTP_200_OK)


class MyOrderAdsListView(BaseOrderListView):
    def get_queryset(self):
        return Order.objects.filter(author=self.request.user).order_by('-created_at')

    def get_list_type(self):
        return "my-order-ads"


class MyReceivedOrdersListView(BaseOrderListView):
    def get_queryset(self):
        organization = self.request.user.user_profile.current_org
        return Order.objects.filter(org_work=organization).order_by('booked_at')

    def get_list_type(self):
        return "my-received-orders"


class MyHistoryOrdersListView(BaseOrderListView):
    def get_queryset(self):
        organization = self.request.user.user_profile.current_org
        status = self.request.query_params.get('status')
        if status == 'active':
            return Order.objects.filter(org_work=organization).exclude(status='Arrived').order_by('booked_at')
        elif status == 'finished':
            return Order.objects.filter(org_work=organization, status='Finished').order_by('booked_at')
        else:
            # Handle invalid status parameter
            return Order.objects.none()

    def get_list_type(self):
        status = self.request.query_params.get('status')
        if status == 'active':
            return "my-history-orders-active"
        elif status == 'finished':
            return "my-history-orders-finished"
        else:
            # Handle invalid status parameter
            return None


class MyOrgOrdersListView(BaseOrderListView):
    def get_queryset(self):
        organization = self.request.user.user_profile.current_org
        return Order.objects.filter(org_work=organization).order_by('-booked_at')

    def get_list_type(self):
        return "my-org-orders"


class MarketplaceOrdersListView(BaseOrderListView):
    def get_queryset(self):
        return Order.objects.all().order_by('-created_at')

    def get_list_type(self):
        return "marketplace-orders"


class ReceivedOrderStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListStatusAPI

    def get(self, request, org_slug):
        user = request.user
        organization = user.user_profile.current_org
        if not organization:
            return Response({'Error': 'User does not have access to this organization or organization not found.'},
                            status=status.HTTP_403_FORBIDDEN)

        orders_data = self.get_orders_data(organization)
        return Response(orders_data, status=status.HTTP_200_OK)

    def get_orders_data(self, org):
        orders_data = {
            "New": [],
            "Process": [],
            "Checking": [],
            "Sending": [],
            "Arrived": []
        }

        queryset = Order.objects.filter(org_work=org)
        for order in queryset:
            status_key = order.status
            if status_key:
                orders_data[status_key].append(self.serializer_class(order).data)
        return orders_data


class OrderDateFilter(FilterSet):
    min_booked_at = DateFilter(field_name='booked_at', lookup_expr='gte')

    class Meta:
        model = Order
        fields = ['min_booked_at']


class OrdersHistoryListView(BaseOrderListView):
    serializer_class = OrderListAPI
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderDateFilter

    def get_queryset(self):
        organization = self.request.user.user_profile.current_org
        status = self.request.query_params.get('status')
        if status == 'active':
            # Return orders with statuses other than "Arrived"
            return Order.objects.filter(org_work=organization).exclude(status='Arrived').order_by('booked_at')
        elif status == 'finished':
            # Return orders with status "Arrived"
            return Order.objects.filter(org_work=organization, status='Arrived').order_by('booked_at')
        else:
            # Handle invalid status parameter or return all orders
            return Order.objects.none()

    def get_list_type(self):
        status = self.request.query_params.get('status')
        if status == 'active':
            return "orders-history-active"
        elif status == 'finished':
            return "orders-history-finished"
        else:
            # Handle invalid status parameter or return None
            return None


class OrdersByCategoryAPIView(APIView):
    def get(self, request):
        category = request.query_params.get('category')
        if category not in OrderCategory.objects.all():
            return Response({'Error': 'written category is not one of the order categories'},
                            status=status.HTTP_403_FORBIDDEN)
        queryset = OrderCategory.objects.filter(category=category).order_by('-created_at')
        data = get_paginated_data(queryset, request, "marketplace-orders")
        return Response(data, status=status.HTTP_200_OK)


class LikedByUserOrdersAPIView(APIView):
    def get_queryset(self):
        user = self.request.user
        return user.liked_orders.all().order_by('-created_at')

    def get_list_type(self):
        return "marketplace-orders"


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Exception:
            return Response({"Error": "Order is not found."}, status=status.HTTP_404_NOT_FOUND)
        author = False
        if request.user.id == order.author.id:
            author = True
        serializer = OrderDetailAPI(order, context={'request': request,
                                                    'author': author})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddOrderAPIView(APIView):
    serializer_class = OrderPostAPI
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateOrderAPIView(APIView):
    serializer_class = OrderPostAPI
    permission_classes = [IsAuthenticated]

    def put(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user != order.author:
            return Response({'Error':'User does not have permissions to update this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(order, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HideOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user != order.author:
            return Response({'Error':'User does not have permissions to hide this order.'},
                            status=status.HTTP_403_FORBIDDEN)
        if order.hide:
            order.hide = False
        else:
            order.hide = True
        order.save()
        return Response({"Message": "Order hidden status is changed."}, status=status.HTTP_200_OK)


class DeleteOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user != order.author:
            return Response({'Error':'User does not have permissions to hide this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        order.delete()
        return Response({"Message": "Order has been deleted successfully."}, status=status.HTTP_200_OK)


class BookOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_slug, org_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.is_booked:
            return Response({'Message':'The order is already booked by another organization.'},
                            status=status.HTTP_403_FORBIDDEN)

        user = request.user
        organization = user.user_profile.current_org
        if not organization:
            return Response({'Error':'User does not have access to this organization or organization not found.'},
                            status=status.HTTP_403_FORBIDDEN)

        order.org_work = organization
        order.is_booked = True
        order.booked_at = datetime.now()
        order.save()

        return Response({"Success": "Order received successfully."}, status=status.HTTP_200_OK)


class UpdateOrderStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_slug, org_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        organization = user.user_profile.current_org
        if not organization:
            return Response({'Error': 'User does not have access to this organization or organization not found.'},
                            status=status.HTTP_403_FORBIDDEN)

        if order not in organization.received_orders.all():
            return Response({'Error': 'This order is not booked by this organization'},
                            status=status.HTTP_403_FORBIDDEN)

        order_status = request.query_params.get('status')
        if order_status not in ["New", "Process", "Checking", "Sending", "Arrived"]:
            return Response({'Error':'The new status name is incorrect. The new status has to be one of'
                                     '["New", "Process", "Checking", "Sending", "Arrived"]'},
                            status=status.HTTP_403_FORBIDDEN)
        order.status = order_status
        if order_status == "Arrived":
            order.finished_at = datetime.now()
        order.save()
        return Response({"Success": "Order status changed successfully."}, status=status.HTTP_200_OK)


class LikeOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user

        if user in order.liked_by.all():
            order.liked_by.remove(user)
        else:
            order.liked_by.add(user)
        return Response({"Message": "Order's favourite status is changed successfully."}, status=status.HTTP_200_OK)


class SearchOrderAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    search_fields = ['title']
    filter_backends = (filters.SearchFilter,)

    def get(self, request, *args, **kwargs):
        queryset = Order.objects.all()
        queryset = self.filter_queryset(queryset)
        data = get_paginated_data(queryset, request, "marketplace-orders")
        return Response(data, status=status.HTTP_200_OK)


class ReviewOrderAPIView(APIView):
    serializer_class = ReviewPostAPI
    permission_classes = [IsAuthenticated]

    def post(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        user = request.user
        serializer = self.serializer_class(data=request.data, order=order, reviewer=user)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EquipmentsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            equipments = Equipment.objects.all()
        except Equipment.DoesNotExist:
            return Response({"error": "Equipments does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentSerializer(equipments, many=True)
        return Response(equipment_serializer.data, status=status.HTTP_200_OK)


class CreateEquipmentAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        tags=['Equipments create'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "добавлять свои оборудования",
        responses={
            201: EquipmentDetailSerializer(),
            404: "Bad request",
            500: "Server error",
        }
    )
    def post(self, request, *args, **kwargs):
        equipment_serializer = EquipmentDetailSerializer(data=request.data, context={'request': request})
        if equipment_serializer.is_valid():
            author = request.user.user_profile
            equipment_serializer.save(author=author)
            return Response(equipment_serializer.data, status=status.HTTP_201_CREATED)
        return Response(equipment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeEquipmentAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        tags=['Equipments change'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность изменить"
                              "существующее оборудование",
        responses={
            200: EquipmentDetailSerializer(),
            400: "Bad request",
            404: "Equipments does not exist",
            500: "Server error",
        }
    )
    def put(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipments does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentDetailSerializer(instance=equipment,
                                                         data=request.data,
                                                         context={'request': request})
        if equipment_serializer.is_valid():
            author = request.user.user_profile
            equipment_serializer.save(author=author)
            return Response(equipment_serializer.data, status=status.HTTP_200_OK)
        return Response({"error": "Bad request"}, status=status.HTTP_400_BAD_REQUEST)


class DeleteEquipmentAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        tags=['Equipments delete'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "удалить оборудование",
        responses={
            200: EquipmentDetailSerializer(),
            404: "Equipments does not exist",
            500: "Server error",
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipments does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment.delete()
        return Response({"data": "Successfully deleted"}, status=status.HTTP_200_OK)


class EquipmentSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['title']

    @swagger_auto_schema(
        tags=['Equipments list'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность найти"
                              "нужное оборудование",
        responses={
            200: EquipmentSerializer(),
            404: "Equipments does not exist",
            500: "Server error",
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get('search', '')
            equipment = Equipment.objects.filter(title__icontains=search_query)
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentSerializer(equipment, many=True)
        return Response(equipment_serializer.data, status=status.HTTP_200_OK)


class EquipmentDetailPageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Equipment detail'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность посмотреть"
                              "детальную страницу оборудования"
                              "а также изменять его, и удалять",
        responses={
            200: EquipmentDetailSerializer(),
            400: "Bad request",
            404: "Equipments does not exist",
            500: "Server error",
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentDetailSerializer(equipment)
        return Response(equipment_serializer.data, status=status.HTTP_200_OK)
