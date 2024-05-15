from datetime import datetime
from django.utils import timezone
from drf_yasg import openapi
from rest_framework.generics import ListAPIView
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages
from .models import ServiceCategory, ServiceImages, Service
from .serializers import *
from rest_framework.permissions import IsAuthenticated, AllowAny
from .services import get_paginated_data, get_services_paginated_data, get_equipment_paginated, get_order_or_equipment
from drf_yasg.utils import swagger_auto_schema
from authorization.models import UserProfile, Organization
from django.db.models import Q
from rest_framework.filters import SearchFilter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Equipment
from .serializers import EquipmentDetailSerializer
from .permissions import CurrentUserOrReadOnly


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


class MyOrderApplicationsListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrgAPI

    @swagger_auto_schema(
        operation_summary="Displaying lists of applications for my order",
        operation_description="This endpoint allows you to get information about applications for my order",
        responses={200: OrgAPI},
        tags=["Order"]
    )
    def get(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != order.author:
            return Response({'Error':'User does not have permissions to see this page.'},
                            status=status.HTTP_403_FORBIDDEN)
        queryset = order.org_applicants.all()
        serializer = self.serializer_class(queryset, many=True, context={'detail': False})
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrgDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrgAPI

    @swagger_auto_schema(
        operation_summary="Displaying organization detail page",
        operation_description="This endpoint allows you to get information about detailed page about organization",
        responses={200: OrgAPI},
        tags=["Order"]
    )
    def get(self, request, org_slug):
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            return Response({"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(org, context={'detail': True})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
        organization = self.request.user.user_profile.working_org.org
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
        organization = self.request.user.user_profile.working_org.org
        status = self.request.query_params.get('status')
        if status == 'active':
            return Order.objects.filter(org_work=organization, is_finished=False).order_by('booked_at')
        elif status == 'finished':
            return Order.objects.filter(org_work=organization, is_finished=True).order_by('booked_at')
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
            openapi.Parameter(
                "stage",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Shows in which stage is order, active or finished",
            )
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
        organization = self.request.user.user_profile.working_org.org
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
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        return Order.objects.filter(hide=False, is_booked=False).order_by('-created_at')

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
        organization = user.user_profile.working_org.org
        if not organization:
            return Response({'Error': 'User does not have access to this organization or organization not found.'},
                            status=status.HTTP_403_FORBIDDEN)

        orders_data = self.get_orders_data(organization)
        return Response(orders_data, status=status.HTTP_200_OK)

    def get_orders_data(self, org):
        orders_data = {
            "Waiting": [],
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
        organization = self.request.user.user_profile.working_org.org
        status = self.request.query_params.get('status')
        min_booked_at = self.request.query_params.get('min_booked_at')

        queryset = Order.objects.filter(org_work=organization)

        if status == 'active':
            # Return orders with statuses other than "Arrived"
            queryset = queryset.filter(is_finished=False)
        elif status == 'finished':
            # Return orders with status "Arrived"
            queryset = queryset.filter(is_finished=True)

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
        status = self.request.query_params.get('stage')
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
            openapi.Parameter(
                "stage",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Shows in which stage is order, active or finished",
            )
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


class MyAppliedOrdersListView(BaseOrderListView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        user = self.request.user
        return user.user_profile.current_org.applied_orders.all().order_by('-created_at')

    def get_list_type(self):
        return "applied-orders"

    @swagger_auto_schema(
        operation_summary="List of orders applied by the current organization of the user",
        operation_description="Retrieve a list of orders applied by the current organization of the user.",
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        category_title = self.request.query_params.get('category')
        try:
            category = OrderCategory.objects.get(title=category_title)
        except OrderCategory.DoesNotExist:
            return Response({"message": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

        return Order.objects.filter(category=category, is_hide=False, is_booked=False).order_by('-created_at')

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
    permission_classes = [IsAuthenticated]

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


class FinishOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Finish an order",
        operation_description="Endpoint to finish status of an order.",
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
            return Response({'Error': 'User does not have permissions to finish this order.'},
                            status=status.HTTP_403_FORBIDDEN)
        if order.status != "Arrived":
            return Response({'Error': 'The order is not arrived yet.'},
                            status=status.HTTP_403_FORBIDDEN)

        if order.is_finished:
            return Response({'Error': 'The order is already finished.'},
                            status=status.HTTP_403_FORBIDDEN)
        order.is_finished = True
        order.finished_at = timezone.now()
        order.save()
        return Response({"Message": "Order finished status is changed."}, status=status.HTTP_200_OK)


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


class ApplyOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Apply for order",
        operation_description="Endpoint to apply for order for the current organization.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the order to be applied",
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
        organization = user.user_profile.working_org.org
        if not organization:
            return Response({'Error':'User does not have access to this organization or organization not found.'},
                            status=status.HTTP_403_FORBIDDEN)

        order.org_applicants.add(organization)
        order.save()
        return Response({"Success": "Order applied successfully."}, status=status.HTTP_200_OK)


class BookOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Choose a received org for order",
        operation_description="Endpoint to choose a received org for order.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the order to be applied",
            ),
            openapi.Parameter(
                "org_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the org which is appled",
            ),
        ],
        responses={
            200: "OK",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Order"]
    )
    def post(self, request, order_slug, org_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.is_booked:
            return Response({'Message':'The order is already booked by another organization.'},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            return Response({"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != order.author:
            return Response({'Error':'User does not have permissions to do this action.'},
                            status=status.HTTP_403_FORBIDDEN)

        order.org_work = org
        order.is_booked = True
        order.booked_at = timezone.now()
        order.save()
        return Response({"Success": "Order booked successfully."}, status=status.HTTP_200_OK)


STATUS = (('Waiting', 'Waiting'), ('Process', 'Process'), ('Checking', 'Checking'), ('Sending', 'Sending'), ('Arrived', 'Arrived'),)


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
                description="New status of the order. Must be one of ['Waiting', 'Process', 'Checking', 'Sending', 'Arrived']",
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
        organization = user.user_profile.working_org.org
        if not organization:
            return Response({'Error': 'User does not have access to this organization or organization not found.'},
                            status=status.HTTP_403_FORBIDDEN)

        if order not in organization.received_orders.all():
            return Response({'Error': 'This order is not booked by this organization'},
                            status=status.HTTP_403_FORBIDDEN)

        order_status = request.query_params.get('status')
        if order_status not in ["Waiting", "Process", "Checking", "Sending", "Arrived"]:
            return Response({'Error':'The new status name is incorrect. The new status has to be one of'
                                     '["Waiting", "Process", "Checking", "Sending", "Arrived"]'},
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
            order.arrived_at = timezone.now()

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
    def get_equipments(self):
        try:
            equipments = Equipment.objects.all().order_by('-created_at')
        except Equipment.DoesNotExist:
            return Response({"error": "Equipments does not exist"})
        return equipments

    def get_equipments_type(self):
        return 'equipments-list'

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "список всех оборудований",
        responses={
            201: EquipmentSerializer,
            404: "Equipments does not exist",
            500: "Server error",
        }
    )
    def get(self, request, *args, **kwargs):
        equipments = self.get_equipments()
        data = get_equipment_paginated(equipments, request, self.get_equipments_type())
        return Response(data, status=status.HTTP_200_OK)


class CreateEquipmentAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "добавлять собственные оборудования",
        responses={
            201: EquipmentDetailSerializer,
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
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность изменить"
                              "существующее оборудование",
        responses={
            200: EquipmentDetailSerializer,
            400: "Only the author can change",
            404: "Equipment does not exist",
            500: "Server error",
        }
    )
    def put(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipments doe not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentDetailSerializer(instance=equipment,
                                                         data=request.data,
                                                         context={'request': request})
        if equipment_serializer.is_valid():
            author = request.user.user_profile
            equipment_serializer.save(author=author)
            return Response(equipment_serializer.data, status=status.HTTP_200_OK)
        return Response({"message": "Only the author can change"}, status=status.HTTP_400_BAD_REQUEST)


class DeleteEquipmentAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "удалить свое оборудование",
        responses={
            200: "Successfully deleted",
            400: "Only the author can delete",
            404: "Equipment does not exist",
            500: "Server error",
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)

        author = request.user.user_profile

        if author == "equipment_ads":
            equipment.delete()
        else:
            return Response({"message": "Only the author can delete"})
        return Response({"data": "Successfully deleted"}, status=status.HTTP_200_OK)


class EquipmentSearchAPIView(APIView):
    filter_backends = [SearchFilter]
    search_fields = ['title']

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность найти"
                              "нужное оборудование",
        responses={
            200: EquipmentSerializer,
            404: "Equipment does not exist",
            500: "Server error",
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get('search', '')
            equipments = Equipment.objects.filter(title__icontains=search_query)
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)
        search_equipments = get_equipment_paginated(equipments, request, "equipments-list")
        return Response(search_equipments, status=status.HTTP_200_OK)


class EquipmentDetailPageAPIView(APIView):
    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность посмотреть"
                              "детальную страницу оборудования",
        responses={
            200: EquipmentDetailSerializer,
            404: "Equipment does not exist",
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


class EquipmentLikeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность поставить"
                              "лайк определенному оборудованию",
        responses = {
            200: EquipmentSerializer,
            400: "Error when removing like or error when adding like",
            404: "Equipment does not exist",
            500: "Server error",
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)

        author = request.user.user_profile

        if author in equipment.liked_by.all():
            try:
                equipment.liked_by.remove(author)
            except Exception as e:
                return Response({"error": "Error when removing like"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"data": "Equipment's favourite status is remove successfully."},
                            status=status.HTTP_200_OK)
        else:
            try:
                equipment.liked_by.add(author)
            except Exception as e:
                return Response({"error": "Error when adding like"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"data": "Equipment's favourite status is add successfully."},
                            status=status.HTTP_200_OK)


class EquipmentByAuthorLikeAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    def get_liked_equipments(self):
        author = self.request.user.user_profile
        return author.liked_equipment.all().order_by('-created_at')

    def get_equipments_type(self):
        return "my-like-equipments"

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность посмотреть"
                              "залайканные оборудования"
                              "на своей личной странице",
        responses={
            200: EquipmentSerializer,
            404: "Equipment does not exist",
            500: "Server error",
        }
    )
    def get(self, request, *args, **kwargs):
        like = self.get_liked_equipments()
        data = get_equipment_paginated(like, request, self.get_equipments_type())
        return Response(data, status=status.HTTP_200_OK)


class HideEquipmentAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность скрыть"
                              "свои оборудования",
        responses={
            200: EquipmentSerializer,
            400: "Only the author can hide the equipment or error when hiding equipment",
            404: "Equipment does not exist",
            500: "Server error",
        }
    )
    def put(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)

        try:
            if equipment.author == request.user.user_profile:
                equipment.hide = True if not equipment.hide else False
                equipment.save()
            else:
                return Response({"message": "Only the author can hide the equipment"},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "Error when hiding equipment"},
                            status=status.HTTP_400_BAD_REQUEST)

        if equipment.hide:
            return Response({"data": "Equipment hidden"})
        else:
            return Response({"data": "Equipment is not hidden"})


class SoldEquipmentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "купить оборудование",
        responses={
            200: "Equipment is available for purchase",
            400: "Equipment has already been sold or you are trying to buy your own equipment",
            404: "Equipment does not exist",
            500: "Server error",
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if equipment.sold:
            return Response({"error": "Equipment has already been sold"}, status=status.HTTP_400_BAD_REQUEST)

        if equipment.author == request.user:
            return Response({"error": "You cannot buy your own equipment"}, status=status.HTTP_400_BAD_REQUEST)

        equipment.sold = True
        equipment.save()

        request.user.user_profile.add(equipment)

        return Response({"message": "Equipment is available for purchase"}, status=status.HTTP_200_OK)


class OrdersAndEquipmentsListAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    def get_orders_and_equipments(self):
        author = self.request.user.user_profile

        equipments = Equipment.objects.filter(author=author).order_by('-created_at')
        orders = Order.objects.filter(author=author).order_by('-created_at')

        services_queryset = list(equipments) + list(orders)

        return services_queryset

    def get_orders_and_equipments_type(self):
        return 'orders-and-equipments-type'

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "свои заказы и оборудования",
        responses={
            200: "Orders and equipments list",
            404: "Orders or Equipments does not exist",
            500: "Server error",
        }
    )
    def get(self, request, *args, **kwargs):
        services = self.get_orders_and_equipments()
        data = get_order_or_equipment(services, request, self.get_orders_and_equipments_type())
        return Response(data, status=status.HTTP_200_OK)


#Service related views
class ServiceCategoriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Displaying lists of service categories",
        operation_description="This endpoint allows you to get information about various service categories",
        responses={200: ServiceCategoryListAPI},
        tags=["Service"]
    )
    def get(self, request):
        categories = ServiceCategory.objects.all()
        categories_api = ServiceCategoryListAPI(categories, many=True)
        content = {"Categories": categories_api.data}
        return Response(content, status=status.HTTP_200_OK)


class BaseServiceListView(APIView):

    def get_queryset(self):
        raise NotImplementedError("Subclasses must implement get_queryset method.")

    def get_author_type(self):
        raise NotImplementedError("Subclasses must implement get_queryset method.")

    def get_search_query(self):
        return self.request.query_params.get('title', '')

    def filter_queryset_by_search(self, queryset):
        search_query = self.get_search_query()
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query))
        return queryset

    def get(self, request):
        queryset = self.get_queryset()
        if isinstance(queryset, Response):
            return queryset
        queryset = self.filter_queryset_by_search(queryset)
        paginated_data = get_services_paginated_data(queryset, request, self.get_author_type())
        return Response(paginated_data, status=status.HTTP_200_OK)


class MyServiceAdsListView(BaseServiceListView):
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceSerializer

    def get_queryset(self):
        return Service.objects.filter(author=self.request.user.user_profile).order_by('-created_at')

    def get_author_type(self):
        return True

    @swagger_auto_schema(
        operation_summary="List of services created by the current organization",
        operation_description="Retrieve a list of services created by the current authenticated user organization.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter services by title (case-insensitive)",
            ),
        ],
        responses={200: serializer_class},
        tags=["Service"]
    )
    def get(self, request):
        return super().get(request)


class ServicesAPIView(BaseServiceListView):
    permission_classes = [AllowAny]
    serializer_class = ServiceSerializer

    def get_queryset(self):
        return Service.objects.filter(hide=False).order_by('-created_at')

    def get_author_type(self):
        return False

    @swagger_auto_schema(
        operation_summary="List of all services",
        operation_description="Retrieve a list of all services.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter services by title (case-insensitive)",
            ),
        ],
        responses={200: serializer_class},
        tags=["Service"]
    )
    def get(self, request):
        return super().get(request)


class LikedByUserServicesAPIView(BaseServiceListView):
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceSerializer

    def get_queryset(self):
        user = self.request.user
        return user.user_profile.liked_services.all().order_by('-created_at')

    def get_author_type(self):
        return False

    @swagger_auto_schema(
        operation_summary="List of all services liked by the current user",
        operation_description="Retrieve a list of all services liked by the current user.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter services by title (case-insensitive)",
            ),
        ],
        responses={200: serializer_class},
        tags=["Service"]
    )
    def get(self, request):
        return super().get(request)


class ServiceDetailAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Get service details",
        operation_description="Get details of a specific service by its slug.",
        manual_parameters=[
            openapi.Parameter(
                "service_slug",
                openapi.IN_PATH,
                description="Slug of the service",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={
            200: ServiceSerializer,
            404: "Service not found",
        },
        tags=["Service"]
    )
    def get(self, request, service_slug):
        try:
            service = Service.objects.get(slug=service_slug)
        except Service.DoesNotExist:
            return Response({"Error": "Service is not found."}, status=status.HTTP_404_NOT_FOUND)

        author = request.user.is_authenticated and request.user.user_profile == service.author
        service_api = ServiceSerializer(service, context={'request': request, 'author': author})
        content = {"Service Info": service_api.data}

        return Response(content, status=status.HTTP_200_OK)


class CreateServiceAPIView(APIView):
    serializer_class = ServicePostSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create a new service",
        operation_description="Endpoint to create a new service.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["title", "uploaded_images", "description", "price", "category_slug", "phone_number", "size"],
            properties={
                "title": openapi.Schema(type=openapi.TYPE_STRING, description="Title of the service"),
                "uploaded_images": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
                    description="List of uploaded images"
                ),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Description of the service"),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price of the service"),
                "category_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Slug of the service category"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number for contact"),
            },
        ),
        responses={
            201: "Created",
            400: "Bad Request",
            403: "Forbidden"
        },
        tags=["Service"]
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        if not user.user_profile:
            return Response({'Error':'The user has to have a user profile.'},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateServiceAPIView(APIView):
    serializer_class = ServicePostSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Update an existing service",
        operation_description="Endpoint to update an existing service.",
        manual_parameters=[
            openapi.Parameter(
                "service_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the service to be updated",
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[],
            properties={
                "title": openapi.Schema(type=openapi.TYPE_STRING, description="Title of the service (optional)"),
                "uploaded_images": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
                    description="List of uploaded images (optional)"
                ),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Description of the service (optional)"),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price of the service (optional)"),
                "category_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Slug of the service category (optional)"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number for contact (optional)"),
            },
        ),
        responses={
            201: "Created",
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Service"]
    )
    def put(self, request, service_slug):
        try:
            service = Service.objects.get(slug=service_slug)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != service.author:
            return Response({'Error':'User does not have permissions to update this service.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(service, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteServiceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Delete an service",
        operation_description="Endpoint to delete an service.",
        manual_parameters=[
            openapi.Parameter(
                "service_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the service to be updated",
            ),
        ],
        responses={
            200: "OK",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Service"]
    )
    def post(self, request, service_slug):
        try:
            service = Service.objects.get(slug=service_slug)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != service.author:
            return Response({'Error':'User does not have permissions to update this service.'},
                            status=status.HTTP_403_FORBIDDEN)

        service.delete()
        return Response({"Message": "Service has been deleted successfully."}, status=status.HTTP_200_OK)


class ServiceLikeAPIView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_summary="Like or unlike an service",
        operation_description="Endpoint to like or unlike an service.",
        manual_parameters=[
            openapi.Parameter(
                "service_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the service to like/unlike",
            ),
        ],
        responses={
            200: "OK",
            404: "Not Found"
        },
        tags=["Service"]
    )
    def post(self, request, service_slug):
        try:
            service = Service.objects.get(slug=service_slug)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user

        if user.user_profile in service.liked_by.all():
            service.liked_by.remove(user.user_profile)
        else:
            service.liked_by.add(user.user_profile)
        service.save()
        return Response({"Message": "Service's favourite status is changed successfully."}, status=status.HTTP_200_OK)


class HideServiceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Hide or unhide a service",
        operation_description="Endpoint to toggle the hide status of an service.",
        manual_parameters=[
            openapi.Parameter(
                "service_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the service to be hidden or unhidden",
            ),
        ],
        responses={
            200: "OK",
            403: "Forbidden",
            404: "Not Found"
        },
        tags=["Service"]
    )
    def post(self, request, service_slug):
        try:
            service = Service.objects.get(slug=service_slug)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != service.author:
            return Response({'Error':'User does not have permissions to update this service.'},
                            status=status.HTTP_403_FORBIDDEN)
        if service.hide:
            service.hide = False
        else:
            service.hide = True
        service.save()
        return Response({"Message": "Service hidden status is changed."}, status=status.HTTP_200_OK)
