from datetime import datetime
from django.utils import timezone
from drf_yasg import openapi
from rest_framework.generics import ListAPIView
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages
from .serializers import *
from rest_framework.permissions import IsAuthenticated, AllowAny
from .services import get_paginated_data
from drf_yasg.utils import swagger_auto_schema
from authorization.models import UserProfile, Organization
from django.db.models import Q
from rest_framework.filters import SearchFilter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Equipment
from .serializers import EquipmentDetailSerializer


# Create your views here.
class OrderCategoriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Displaying lists of order categories",
        operation_description="This endpoint allows you to get information about various order categories",
        responses={200: OrderCategoryListAPI},
        tags=["Order"]
    )
    def get(self, request):
        categories = OrderCategory.objects.all()
        categories_api = OrderCategoryListAPI(categories, many=True)
        content = {"Categories": categories_api.data}
        return Response(content, status=status.HTTP_200_OK)


class BaseOrderListView(APIView):

    def get_queryset(self):
        raise NotImplementedError("Subclasses must implement get_queryset method.")

    def get_list_type(self):
        raise NotImplementedError("Subclasses must implement get_list_type method.")

    def get_search_query(self):
        return self.request.query_params.get('title', '')

    def filter_queryset_by_search(self, queryset):
        search_query = self.get_search_query()
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query))
        return queryset

    def get(self, request):
        queryset = self.get_queryset()
        print(queryset)
        if isinstance(queryset, Response):
            return queryset
        queryset = self.filter_queryset_by_search(queryset)
        paginated_data = get_paginated_data(queryset, request, self.get_list_type())
        return Response(paginated_data, status=status.HTTP_200_OK)


class MyOrderAdsListView(BaseOrderListView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        return Order.objects.filter(author=self.request.user.user_profile).order_by('-created_at')

    def get_list_type(self):
        return "my-order-ads"

    @swagger_auto_schema(
        operation_summary="List of orders created by the current user",
        operation_description="Retrieve a list of orders created by the current authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            ),
        ],
        responses={200: serializer_class},
        tags=["Order List"]
    )
    def get(self, request):
        return super().get(request)


class MyReceivedOrdersListView(BaseOrderListView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        organization = self.request.user.user_profile.current_org
        return Order.objects.filter(org_work=organization).order_by('booked_at')

    def get_list_type(self):
        return "my-received-orders"

    @swagger_auto_schema(
        operation_summary="List of orders received by the current user's organization",
        operation_description="Retrieve a list of orders received by the current authenticated user's organization.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            ),
        ],
        responses={200: serializer_class},
        tags=["Order List"]
    )
    def get(self, request):
        return super().get(request)


class MyHistoryOrdersListView(BaseOrderListView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        organization = self.request.user.user_profile.current_org
        status = self.request.query_params.get('status')
        if status == 'active':
            return Order.objects.filter(org_work=organization).exclude(status='Arrived').order_by('booked_at')
        elif status == 'finished':
            return Order.objects.filter(org_work=organization, status='Finished').order_by('booked_at')
        else:
            # Handle invalid status parameter
            return Order.objects.all()

    def get_list_type(self):
        status = self.request.query_params.get('status')
        if status == 'active':
            return "my-history-orders-active"
        elif status == 'finished':
            return "my-history-orders-finished"
        else:
            # Handle invalid status parameter
            return None

    @swagger_auto_schema(
        operation_summary="List of received orders for the current user org",
        operation_description="Retrieve a list of received orders for the current authenticated user org.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            ),
        ],
        responses={200: serializer_class},
        tags=["Order List"]
    )
    def get(self, request):
        return super().get(request)


class MyOrgOrdersListView(BaseOrderListView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        organization = self.request.user.user_profile.current_org
        return Order.objects.filter(org_work=organization).order_by('-booked_at')

    def get_list_type(self):
        return "my-org-orders"

    @swagger_auto_schema(
        operation_summary="List of received orders for the current user's organization",
        operation_description="Retrieve a list of received orders for the current authenticated user's organization.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            ),
        ],
        responses={200: serializer_class},
        tags=["Order List"]
    )
    def get(self, request):
        return super().get(request)


class MarketplaceOrdersListView(BaseOrderListView):
    permission_classes = [AllowAny]
    serializer_class = OrderListAPI

    def get_queryset(self):
        return Order.objects.exclude(status='Arrived').filter(hide=False).order_by('-created_at')

    def get_list_type(self):
        return "marketplace-orders"

    @swagger_auto_schema(
        operation_summary="List of orders available in the marketplace",
        operation_description="Retrieve a list of orders available in the marketplace.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            ),
        ],
        responses={200: serializer_class},
        tags=["Order List"]
    )
    def get(self, request):
        return super().get(request)


class ReceivedOrderStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListStatusAPI

    def get_search_query(self):
        return self.request.query_params.get('title', '')

    def filter_queryset_by_search(self, queryset):
        search_query = self.get_search_query()
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query))
        return queryset

    @swagger_auto_schema(
        tags=["Order List"],
        operation_summary="Get received order status",
        operation_description="Get the status of orders received by the user's organization.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            ),
        ],
        responses={
            200: serializer_class,
            403: "User does not have access to the organization or organization not found.",
        }
    )
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
        queryset = self.filter_queryset_by_search(queryset)
        for order in queryset:
            status_key = order.status
            if status_key:
                orders_data[status_key].append(self.serializer_class(order).data)
        return orders_data


class OrdersHistoryListView(BaseOrderListView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        organization = self.request.user.user_profile.current_org
        status = self.request.query_params.get('status')
        min_booked_at = self.request.query_params.get('min_booked_at')

        queryset = Order.objects.filter(org_work=organization)

        if status == 'active':
            # Return orders with statuses other than "Arrived"
            queryset = queryset.exclude(status='Arrived')
        elif status == 'finished':
            # Return orders with status "Arrived"
            queryset = queryset.filter(status='Arrived')

        # Apply additional filtering based on min_booked_at
        if min_booked_at:
            # Convert min_booked_at string to a date object
            min_booked_date = datetime.strptime(min_booked_at, '%Y-%m-%d').date()
            # Filter orders where booked_at date is greater than or equal to min_booked_date
            queryset = queryset.filter(booked_at__gte=min_booked_date)

        # Apply default ordering
        queryset = queryset.order_by('booked_at')
        return queryset

    def get_list_type(self):
        status = self.request.query_params.get('status')
        if status == 'active':
            return "orders-history-active"
        elif status == 'finished':
            return "orders-history-finished"
        else:
            # Handle invalid status parameter or return None
            return None

    @swagger_auto_schema(
        operation_summary="List of received orders state in user's org history",
        operation_description="Retrieve a list of received orders state from the user's org history.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            ),
        ],
        responses={200: serializer_class},
        tags=["Order List"]
    )
    def get(self, request):
        return super().get(request)


class LikedByUserOrdersAPIView(BaseOrderListView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        user = self.request.user
        return user.user_profile.liked_orders.all().order_by('-created_at')

    def get_list_type(self):
        return "marketplace-orders"

    @swagger_auto_schema(
        operation_summary="List of orders liked by the current user",
        operation_description="Retrieve a list of orders that are liked by the current authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            ),
        ],
        responses={200: "OK"},
        tags=["Order List"]
    )
    def get(self, request):
        return super().get(request)


class OrdersByCategoryAPIView(BaseOrderListView):
    permission_classes = [AllowAny]

    def get_queryset(self):
        category_title = self.request.query_params.get('category')
        try:
            category = OrderCategory.objects.get(title=category_title)
        except OrderCategory.DoesNotExist:
            return Response({"message": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

        return Order.objects.filter(category=category).exclude(status='Arrived').order_by('-created_at')

    def get_list_type(self):
        return "marketplace-orders"

    @swagger_auto_schema(
        tags=["Order List"],
        operation_summary="Get orders by category",
        operation_description="Get a list of orders belonging to a specific category.",
        manual_parameters=[
            openapi.Parameter(
                "category",
                openapi.IN_QUERY,
                description="Slug of the category",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            )
        ],
        responses={
            200: OrderListAPI,
            404: "Category not found",
        }
    )
    def get(self, request):
        return super().get(request)


class OrderDetailAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Get order details",
        operation_description="Get details of a specific order by its slug.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                description="Slug of the order",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={
            200: OrderDetailAPI,
            404: "Order not found",
        },
        tags=["Order"]
    )
    def get(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"Error": "Order is not found."}, status=status.HTTP_404_NOT_FOUND)

        author = request.user.is_authenticated and request.user.user_profile == order.author
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

    @swagger_auto_schema(
        operation_summary="Create a new order",
        operation_description="Endpoint to create a new order.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["title", "uploaded_images", "description", "deadline", "price", "category_slug", "phone_number", "size"],
            properties={
                "title": openapi.Schema(type=openapi.TYPE_STRING, description="Title of the order"),
                "uploaded_images": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
                    description="List of uploaded images"
                ),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Description of the order"),
                "deadline": openapi.Schema(type=openapi.TYPE_STRING, format="date", description="Deadline of the order"),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price of the order"),
                "category_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Slug of the order category"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number for contact"),
                "size": openapi.Schema(type=openapi.TYPE_STRING, description="Size of the order")
            },
        ),
        responses={
            201: "Created",
            400: "Bad Request"
        },
        tags=["Order"]
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateOrderAPIView(APIView):
    serializer_class = OrderPostAPI
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Update an existing order",
        operation_description="Endpoint to update an existing order.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the order to be updated",
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[],
            properties={
                "title": openapi.Schema(type=openapi.TYPE_STRING, description="Title of the order (optional)"),
                "uploaded_images": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
                    description="List of uploaded images (optional)"
                ),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Description of the order (optional)"),
                "deadline": openapi.Schema(type=openapi.TYPE_STRING, format="date", description="Deadline of the order (optional)"),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price of the order (optional)"),
                "category_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Slug of the order category (optional)"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number for contact (optional)"),
                "size": openapi.Schema(type=openapi.TYPE_STRING, description="Size of the order (optional)")
            },
        ),
        responses={
            201: "Created",
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Order"]
    )
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

    @swagger_auto_schema(
        operation_summary="Hide or unhide an order",
        operation_description="Endpoint to toggle the hide status of an order.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the order to be hidden or unhidden",
            ),
        ],
        responses={
            200: "OK",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Order"]
    )
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

    @swagger_auto_schema(
        operation_summary="Delete an order",
        operation_description="Endpoint to delete an order.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the order to be deleted",
            ),
        ],
        responses={
            200: "OK",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Order"]
    )
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

    @swagger_auto_schema(
        operation_summary="Book an order",
        operation_description="Endpoint to book an order for the current organization.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the order to be booked",
            ),
        ],
        responses={
            200: "OK",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Order"]
    )
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

    @swagger_auto_schema(
        operation_summary="Update order status",
        operation_description="Endpoint to update the status of an order.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the order to update status",
            ),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="New status of the order. Must be one of ['New', 'Process', 'Checking', 'Sending', 'Arrived']",
            ),
        ],
        responses={
            200: "OK",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Order"]
    )
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
    @swagger_auto_schema(
        operation_summary="Like or unlike an order",
        operation_description="Endpoint to like or unlike an order.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the order to like/unlike",
            ),
        ],
        responses={
            200: "OK",
            404: "Not Found"
        },
        tags=["Order"]
    )
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


class ReviewOrderAPIView(APIView):
    serializer_class = ReviewPostAPI
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Review an order",
        operation_description="Endpoint to review an order when its status is 'Arrived'.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["rating", "comment"],
            properties={
                "rating": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    format=openapi.FORMAT_INT32,
                    description="Rating for the order (1-5)",
                    minimum=1,
                    maximum=5
                ),
                "comment": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Comment for the review"
                )
            },
        ),
        responses={
            201: "Created",
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Order"]
    )
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


class EquipmentsListAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            equipments = Equipment.objects.all()
        except Equipment.DoesNotExist:
            return Response({"error": "Equipments does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentDetailSerializer(equipments, many=True)
        return Response(equipment_serializer.data, status=status.HTTP_200_OK)


class CreateEquipmentAPIView(APIView):
    def post(self, request, *args, **kwargs):
        equipment_serializer = EquipmentDetailSerializer(data=request.data)
        if equipment_serializer.is_valid():
            equipment_serializer.save()
            return Response(equipment_serializer.data, status=status.HTTP_201_CREATED)
        return Response(equipment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EquipmentSearchAPIView(APIView):
    filter_backends = [SearchFilter]
    search_fields = ['title']

    def get(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get('search', '')
            equipment = Equipment.objects.filter(title__icontains=search_query)
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentDetailSerializer(equipment, many=True)
        return Response(equipment_serializer.data, status=status.HTTP_200_OK)


class EquipmentDetailPageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentDetailSerializer(equipment)
        return Response(equipment_serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentDetailSerializer(instance=equipment, data=request.data)
        if equipment_serializer.is_valid():
            equipment_serializer.save()
            return Response(equipment_serializer.data, status=status.HTTP_200_OK)
        return Response(equipment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Error when deleting"}, status=status.HTTP_400_BAD_REQUEST)
        equipment.delete()
        return Response({"data": "Successfully deleted"}, status=status.HTTP_200_OK)
