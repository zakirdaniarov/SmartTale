from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.views import Response, status, APIView
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from .services import get_paginated_data
from drf_yasg.utils import swagger_auto_schema
from authorization.models import UserProfile, Organization
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django_filters.rest_framework import FilterSet, DateFilter
from django.db.models import Q


# Create your views here.
class OrderCategoriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Displaying lists of order categories",
        description="This endpoint allows you to get information about various order categories",

    )
    def get(self, request):
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
        return Order.objects.filter(author=self.request.user.user_profile).order_by('-created_at')

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
        return Order.objects.all().exclude(status='Arrived').order_by('-created_at')

    def get_list_type(self):
        return "marketplace-orders"


class ReceivedOrderStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListStatusAPI

    def get(self, request):
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


class LikedByUserOrdersAPIView(BaseOrderListView):
    def get_queryset(self):
        user = self.request.user
        return user.user_profile.liked_orders.all().order_by('-created_at')

    def get_list_type(self):
        return "marketplace-orders"


class OrdersByCategoryAPIView(APIView):
    def get(self, request):
        category_title = request.query_params.get('category')

        try:
            category = OrderCategory.objects.get(title=category_title)
        except OrderCategory.DoesNotExist:
            return Response({"message": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

        queryset = Order.objects.filter(category=category).exclude(status='Arrived').order_by('-created_at')
        data = get_paginated_data(queryset, request, "marketplace-orders")
        return Response(data, status=status.HTTP_200_OK)


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"Error": "Order is not found."}, status=status.HTTP_404_NOT_FOUND)

        author = request.user.user_profile == order.author
        order_api = OrderDetailAPI(order, context={'request': request, 'author': author})
        content = {"Order Info": order_api.data}

        try:
            review = order.order_reviews
            review_api = ReviewListAPI(review)
            content["Review"] = review_api.data
        except Reviews.DoesNotExist:
            pass

        return Response(content, status=status.HTTP_200_OK)


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
        if user.user_profile != order.author:
            return Response({'Error':'User does not have permissions to update this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(order, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HideOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != order.author:
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
        if user.user_profile != order.author:
            return Response({'Error':'User does not have permissions to hide this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        order.delete()
        return Response({"Message": "Order has been deleted successfully."}, status=status.HTTP_200_OK)


class BookOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_slug):
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
        order.booked_at = timezone.now()
        order.save()

        return Response({"Success": "Order received successfully."}, status=status.HTTP_200_OK)


STATUS = (('New', 'New'), ('Process', 'Process'), ('Checking', 'Checking'), ('Sending', 'Sending'), ('Arrived', 'Arrived'),)


class UpdateOrderStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_slug):
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

        # Check if the current status is "Arrived"; if so, do not allow status change
        if order.status == "Arrived":
            return Response({'Error': 'Cannot change the status of an order that is already "Arrived"'},
                            status=status.HTTP_403_FORBIDDEN)

        # Get the current index of the order's status in the STATUS choices
        current_status_index = [statuses[0] for statuses in STATUS].index(order.status)

        # Get the index of the new status in the STATUS choices
        new_status_index = [statuses[0] for statuses in STATUS].index(order_status)

        # Check if the new status is within one position (left or right) of the current status
        if abs(current_status_index - new_status_index) != 1:
            return Response({'Error': 'The new status must be one position (left or right) of the current status'},
                            status=status.HTTP_403_FORBIDDEN)

        # If the new status is "Arrived", set the finished_at timestamp
        if order_status == "Arrived":
            order.finished_at = timezone.now()

        # Update the order status and save
        order.status = order_status
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

        if user.user_profile in order.liked_by.all():
            order.liked_by.remove(user.user_profile)
        else:
            order.liked_by.add(user.user_profile)
        order.save()
        return Response({"Message": "Order's favourite status is changed successfully."}, status=status.HTTP_200_OK)


class SearchOrderAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Get the search query parameter from the request
        search_query = request.query_params.get('title', None)

        if search_query:
            # Filter recipes based on search query
            orders = Order.objects.filter(
                Q(title__icontains=search_query)
            )
        else:
            # If no search query provided, return all recipes
            orders = Order.objects.none()

        data = get_paginated_data(orders, request, "marketplace-orders")
        return Response(data, status=status.HTTP_200_OK)


class ReviewOrderAPIView(APIView):
    serializer_class = ReviewPostAPI
    permission_classes = [IsAuthenticated]

    def post(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.status != "Arrived":
            return Response({'Error': 'Review is possible only when the order status is "Arrived"'},
                            status=status.HTTP_403_FORBIDDEN)
        user = request.user
        if user.user_profile != order.author:
            return Response({'Error':'User does not have permissions to review this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(data=request.data, context={'order': order, 'reviewer': user.user_profile})
        if serializer.is_valid():
            serializer.save(order=order, reviewer=user.user_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


