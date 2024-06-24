from datetime import datetime

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg import openapi
from rest_framework.generics import ListAPIView

from job.models import Vacancy, Resume
from job.serializers import VacancyListSerializer, ResumeListSerializer
from monitoring.models import Employee
from .firebase_service import send_fcm_notification
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages, \
    Notification
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
from operator import attrgetter
from rest_framework.test import APIRequestFactory
from django.db import transaction

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
        user = self.request.user
        if Organization.objects.filter(founder=user.user_profile):
            organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
            return Order.objects.filter(org_work=organization).order_by('booked_at')
        else:
            try:
                organization = user.user_profile.working_orgs.get().org
                return Order.objects.filter(org_work=organization).order_by('booked_at')
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)

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
        user = self.request.user
        if Organization.objects.filter(founder=user.user_profile):
            organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
        else:
            try:
                organization = user.user_profile.working_orgs.get().org
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)
        stage = self.request.query_params.get('stage')
        if stage == 'active':
            return Order.objects.filter(org_work=organization, is_finished=False).order_by('booked_at')
        elif stage == 'finished':
            return Order.objects.filter(org_work=organization, is_finished=True).order_by('booked_at')
        else:
            # Handle invalid status parameter
            return Order.objects.filter(org_work=organization).order_by('booked_at')

    def get_list_type(self):
        stage = self.request.query_params.get('stage')
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
        user = self.request.user
        if Organization.objects.filter(founder=user.user_profile):
            organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
        else:
            try:
                organization = user.user_profile.working_orgs.get().org
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)

        self.stage = self.request.query_params.get('stage')
        queryset = Order.objects.filter(org_work=organization)

        if self.stage == 'active':
            # Return orders with statuses other than "Arrived"
            queryset = queryset.filter(is_finished=False)
        elif self.stage == 'finished':
            # Return orders with status "Arrived"
            queryset = queryset.filter(is_finished=True)
        else:
            # Handle invalid status parameter
            return Order.objects.filter(org_work=organization).order_by('booked_at')

        # Apply default ordering
        queryset = queryset.order_by('-created_at')
        return queryset

    def get_list_type(self):
        if self.stage == 'active':
            return "orders-history-active"
        elif self.stage == 'finished':
            return "orders-history-finished"
        else:
            # Handle invalid status parameter or return None
            return None

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


class OrgOrdersListView(BaseOrderListView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListAPI

    def get_queryset(self):
        org_slug = self.kwargs.get('org_slug')
        organization = get_object_or_404(Organization, slug=org_slug)

        self.stage = self.request.query_params.get('stage')
        queryset = Order.objects.filter(org_work=organization)

        if self.stage == 'active':
            # Return orders with statuses other than "Arrived"
            queryset = queryset.filter(is_finished=False)
        elif self.stage == 'finished':
            # Return orders with status "Arrived"
            queryset = queryset.filter(is_finished=True)
        else:
            # Handle invalid status parameter
            queryset = Order.objects.filter(org_work=organization).order_by('booked_at')

        # Apply default ordering
        queryset = queryset.order_by('-created_at')
        return queryset

    def get_list_type(self):
        if self.stage == 'active':
            return "orders-history-active"
        elif self.stage == 'finished':
            return "orders-history-finished"
        else:
            # Handle invalid status parameter or return None
            return None

    @swagger_auto_schema(
        operation_summary="List of received orders for a specific organization",
        operation_description="Retrieve a list of received orders for a specified organization by slug.",
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
    def get(self, request, org_slug):
        return super().get(request)


class MarketplaceOrdersListView(BaseOrderListView):
    permission_classes = [AllowAny]
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
        user = self.request.user
        if Organization.objects.filter(founder=user.user_profile):
            organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
        else:
            try:
                organization = user.user_profile.working_orgs.get().org
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)

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
        user = self.request.user
        if Organization.objects.filter(founder=user.user_profile):
            organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
        else:
            try:
                organization = user.user_profile.working_orgs.get().org
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)

        stage = self.request.query_params.get('stage')
        min_booked_at = self.request.query_params.get('min_booked_at')

        queryset = Order.objects.filter(org_work=organization)

        if stage == 'active':
            # Return orders with statuses other than "Arrived"
            queryset = queryset.filter(is_finished=False)
        elif stage == 'finished':
            # Return orders with status "Arrived"
            queryset = queryset.filter(is_finished=True)
        else:
            # Handle invalid status parameter
            pass

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
        stage = self.request.query_params.get('stage')
        if stage == 'active':
            return "orders-history-active"
        elif stage == 'finished':
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
        if Organization.objects.filter(founder=user.user_profile):
            organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
        else:
            try:
                organization = user.user_profile.working_orgs.get().org
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)
        return organization.applied_orders.all().order_by('-created_at')

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
            return Response({"error": "Order is not found."}, status=status.HTTP_404_NOT_FOUND)

        author = request.user.is_authenticated and request.user.user_profile == order.author
        order_api = OrderDetailAPI(order, context={'request': request, 'author': author})
        content = {"data": order_api.data}

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
            required=["title", "uploaded_images", "description", "deadline", "price", 'currency', "phone_number", "size"],
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
                "currency": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price currency"),
                "category_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Slug of the order category"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number for contact"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="Email of the order"),
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
                "deleted_images": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description="List of IDs of images to be deleted (optional)"
                ),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Description of the order (optional)"),
                "deadline": openapi.Schema(type=openapi.TYPE_STRING, format="date", description="Deadline of the order (optional)"),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price of the order (optional)"),
                "currency": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price currency (optional)"),
                "category_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Slug of the order category (optional)"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number for contact (optional)"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="Email of the order (optional)"),
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
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != order.author:
            return Response({'error':'User does not have permissions to update this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(order, data=request.data, context={'request': request})
        if serializer.is_valid():
            updated_order = serializer.save()
            response_data = serializer.data
            response_data['slug'] = updated_order.slug
            return Response(response_data, status=status.HTTP_200_OK)
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
    def put(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != order.author:
            return Response({'error':'User does not have permissions to hide this order.'},
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
    def put(self, request, order_slug):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != order.author:
            return Response({'error': 'User does not have permissions to finish this order.'},
                            status=status.HTTP_403_FORBIDDEN)
        if order.status != "Arrived":
            return Response({'error': 'The order is not arrived yet.'},
                            status=status.HTTP_403_FORBIDDEN)

        if order.is_finished:
            return Response({'error': 'The order is already finished.'},
                            status=status.HTTP_403_FORBIDDEN)
        order.is_finished = True
        order.finished_at = timezone.now()
        order.save()

        org = order.org_work
        founder_or_owner_profile = org.founder if org.founder else org.owner
        if founder_or_owner_profile.device_token:
            try:
                send_fcm_notification(
                founder_or_owner_profile.device_token,
                "Order Finished",
                f"Your sent order '{order.title}' has been received successfully."
                )
            except Exception as e:
                print(f"Failed to send FCM notification: {e}")

        Notification.objects.create(
            user=founder_or_owner_profile,
            title="Application Successful",
            message=f"The order '{order.title}' has been marked as finished."
        )

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
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != order.author:
            return Response({'error':'User does not have permissions to hide this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        order.delete()
        return Response({"Message": "Order has been deleted successfully."}, status=status.HTTP_200_OK)


class UserNotificationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get user notifications",
        operation_description="Endpoint to retrieve all notifications for the authenticated user.",
        responses={
            200: NotificationSerializer(many=True)
        },
        tags=["Notification"]
    )
    def get(self, request):
        user = self.request.user.user_profile
        notifications = Notification.objects.filter(user=user).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

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
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.is_booked:
            return Response({'error':'The order is already booked by another organization.'},
                            status=status.HTTP_403_FORBIDDEN)

        user = self.request.user
        if Organization.objects.filter(founder=user.user_profile):
            organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
        else:
            try:
                organization = user.user_profile.working_orgs.get().org
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)
        if organization in order.org_applicants.all():
            return Response({'error': 'You already applied for this order.'},
                            status=status.HTTP_403_FORBIDDEN)
        order.org_applicants.add(organization)
        order.save()

        fcm_token = request.data.get('fcm_token')
        if fcm_token:
            user.user_profile.device_token = fcm_token
            user.user_profile.save()

        author_profile = order.author
        if author_profile.device_token:
            print(author_profile.device_token)
            try:
                send_fcm_notification(
                    author_profile.device_token,
                    "New Order Application",
                    f"Your order '{order.title}' has received a new application from {organization.title}."
                )
            except Exception as e:
                print(f"Failed to send FCM notification: {e}")

        Notification.objects.create(
            user=author_profile,
            title="New Order Application",
            message=f"Your order '{order.title}' has received a new application from {organization.title}."
        )

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
            return Response({"order": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.is_booked:
            return Response({'Message':'The order is already booked by another organization.'},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            return Response({"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != order.author:
            return Response({'error':'User does not have permissions to do this action.'},
                            status=status.HTTP_403_FORBIDDEN)

        order.org_work = org
        order.is_booked = True
        order.booked_at = timezone.now()
        order.save()

        founder_or_owner_profile = org.founder if org.founder else org.owner
        if founder_or_owner_profile.device_token:
            try:
                send_fcm_notification(
                founder_or_owner_profile.device_token,
                "Application Successful",
                f"Your application for order '{order.title}' has been successful."
            )
            except Exception as e:
                print(f"Failed to send FCM notification: {e}")

        Notification.objects.create(
            user=founder_or_owner_profile,
            title="Application Successful",
            message=f"Your application for the order '{order.title}' has been accepted."
        )
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

        user = self.request.user
        if Organization.objects.filter(founder=user.user_profile):
            organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
        else:
            try:
                organization = user.user_profile.working_orgs.get().org
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)

        if order not in organization.received_orders.all():
            return Response({'error': 'This order is not booked by this organization'},
                            status=status.HTTP_403_FORBIDDEN)

        order_status = request.query_params.get('status')
        if order_status not in ["Waiting", "Process", "Checking", "Sending", "Arrived"]:
            return Response({'error':'The new status name is incorrect. The new status has to be one of'
                                     '["Waiting", "Process", "Checking", "Sending", "Arrived"]'},
                            status=status.HTTP_403_FORBIDDEN)

        # Check if the current status is "Arrived"; if so, do not allow status change
        if order.status == "Arrived":
            return Response({'error': 'Cannot change the status of an order that is already "Arrived"'},
                            status=status.HTTP_403_FORBIDDEN)

        # Get the current index of the order's status in the STATUS choices
        current_status_index = [statuses[0] for statuses in STATUS].index(order.status)

        # Get the index of the new status in the STATUS choices
        new_status_index = [statuses[0] for statuses in STATUS].index(order_status)

        # Check if the new status is within one position (left or right) of the current status
        if abs(current_status_index - new_status_index) != 1:
            return Response({'error': 'The new status must be one position (left or right) of the current status'},
                            status=status.HTTP_403_FORBIDDEN)

        # If the new status is "Arrived", set the finished_at timestamp
        if order_status == "Arrived":
            order.arrived_at = timezone.now()

        # Update the order status and save
        order.status = order_status
        order.save()

        creator_profile = order.author
        if creator_profile.device_token:
            try:
                send_fcm_notification(
                creator_profile.device_token,
                "Order Status Update",
                f"Your order '{order.title}' status has changed to {order_status}"
            )
            except Exception as e:
                print(f"Failed to send FCM notification: {e}")

        Notification.objects.create(
                user=creator_profile,
                title="Order Status Updated",
                message=f"The status of the order '{order.title}' has been updated to '{order_status}'."
            )

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
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        if order.status != "Arrived":
            return Response({'error': 'Review is possible only when the order status is "Arrived"'},
                            status=status.HTTP_403_FORBIDDEN)
        user = request.user
        if user.user_profile != order.author:
            return Response({'error':'User does not have permissions to review this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(data=request.data, context={'order': order, 'reviewer': user.user_profile})
        if serializer.is_valid():
            serializer.save(order=order, reviewer=user.user_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderAddEmployeeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def has_permission(self, user_profile, org):
        # Check if user is founder or owner
        if user_profile == org.founder or user_profile == org.owner:
            return True

        # Check if user is an employee with the appropriate job title flag
        employee = Employee.objects.filter(user=user_profile, org=org).first()
        if employee and employee.job_title and employee.job_title.flag_add_employee:
            return True

        return False

    @swagger_auto_schema(
        operation_summary="Add employee to order",
        operation_description="Endpoint to add an employee to the specified order if the user has the necessary permissions.",
        responses={
            200: "Employee added successfully",
            400: "Bad Request",
            403: "Forbidden",
            404: "Order or Employee not found"
        },
        tags=["Order"]
    )
    def post(self, request, order_slug, employee_slug):
        user_profile = request.user.user_profile
        try:
            order = Order.objects.get(slug=order_slug)
            employee = Employee.objects.get(user__slug=employee_slug)
        except (Order.DoesNotExist, Employee.DoesNotExist):
            return Response({"error": "Order or Employee not found"}, status=status.HTTP_404_NOT_FOUND)

        org = order.org_work
        if not org:
            return Response({'error': 'Order is not received by any organization yet.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not self.has_permission(user_profile, org):
            return Response({'error': 'User does not have permissions to add employee to this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        if employee in order.workers.all():
            return Response({"error": "Employee is already involved in this order."}, status=status.HTTP_400_BAD_REQUEST)

        order.workers.add(employee)
        order.save()

        return Response({"message": "Employee added successfully"}, status=status.HTTP_200_OK)


class OrderRemoveEmployeeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def has_permission(self, user_profile, org):
        # Check if user is founder or owner
        if user_profile == org.founder or user_profile == org.owner:
            return True

        # Check if user is an employee with the appropriate job title flag
        employee = Employee.objects.filter(user=user_profile, org=org).first()
        if employee and employee.job_title and employee.job_title.flag_remove_employee:
            return True

        return False

    @swagger_auto_schema(
        operation_summary="Remove employee from order",
        operation_description="Endpoint to remove an employee from the specified order if the user has the necessary permissions.",
        responses={
            200: "Employee removed successfully",
            400: "Bad Request",
            403: "Forbidden",
            404: "Order or Employee not found"
        },
        tags=["Order"]
    )
    def post(self, request, order_slug, employee_slug):
        user_profile = request.user.user_profile
        try:
            order = Order.objects.get(slug=order_slug)
            employee = Employee.objects.get(user__slug=employee_slug)
        except (Order.DoesNotExist, Employee.DoesNotExist):
            return Response({"error": "Order or Employee not found"}, status=status.HTTP_404_NOT_FOUND)

        org = order.org_work
        if not org:
            return Response({'error': 'Order is not received by any organization yet.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not self.has_permission(user_profile, org):
            return Response({'error': 'User does not have permissions to remove employee from this order.'},
                            status=status.HTTP_403_FORBIDDEN)

        if employee not in order.workers.all():
            return Response({"error": "Employee is not involved in this order."}, status=status.HTTP_400_BAD_REQUEST)

        order.workers.remove(employee)
        order.save()

        return Response({"message": "Employee removed successfully"}, status=status.HTTP_200_OK)


class EquipmentsListAPIView(APIView):
    permission_classes = [AllowAny]

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
    permission_classes = [IsAuthenticated]

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
                              "существующее оборудование" 
                              "при удалении картинки в поле deleted_images" 
                              "нужно передать id картинки",
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

        if request.user.user_profile != equipment.author:
            return Response({"error": "Only the author can change"}, status=status.HTTP_400_BAD_REQUEST)

        equipment_serializer = EquipmentDetailSerializer(instance=equipment,
                                                         data=request.data,
                                                         context={'request': request})

        if equipment_serializer.is_valid():
            equipment_serializer.save()
            return Response(equipment_serializer.data, status=status.HTTP_200_OK)
        return Response(equipment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({"error": "Only the author can delete"})
        return Response({"data": "Successfully deleted"}, status=status.HTTP_200_OK)


class EquipmentSearchAPIView(APIView):
    permission_classes = [AllowAny]
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


class EquipmentModalPageAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "возможность посмотреть"
                              "модальную страницу оборудования",
        responses={
            200: EquipmentModalPageSerializer,
            404: "Equipment does not exist",
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)

        serializer = EquipmentModalPageSerializer(equipment)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        content = {"data": equipment_serializer.data}
        return Response(content, status=status.HTTP_200_OK)


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
                return Response({"error": "Only the author can hide the equipment"},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Error when hiding equipment"},
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
            200: "Equipment purchased",
            400: "Equipment is out of stock OR you are trying to buy your own equipment",
            404: "Equipment does not exist",
            500: "Server error",
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if equipment.author == request.user:
            return Response({"error": "You cannot buy your own equipment"}, status=status.HTTP_400_BAD_REQUEST)

        if equipment.quantity < 1:
            return Response({"error": "Equipment is out of stock"}, status=status.HTTP_400_BAD_REQUEST)

        request.user.user_profile.equipment_ads.add(equipment)

        equipment.quantity -= 1
        equipment.save()

        return Response({"data": "Equipment purchased"}, status=status.HTTP_200_OK)


class MyPurchasesAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    def get_my_purchases(self):
        author = self.request.user.user_profile
        return author.equipment_ads.all().order_by('-created_at')

    def get_equipments_type(self):
        return "my-purchases-equipments"

    @swagger_auto_schema(
        tags=['Equipment'],
        operation_description="Этот эндпоинт"
                              "предостовляет пользователю"
                              "посмотреть купленные оборудования",
        responses={
            200: EquipmentSerializer,
            404: "Equipment does not exist",
            500: "Server error",
        }
    )
    def get(self, request, *args, **kwargs):
        purchases = self.get_my_purchases()
        data = self.get_paginated_response(purchases, request, self.get_equipments_type())
        return Response(data, status=status.HTTP_200_OK)

    def get_paginated_response(self, queryset, request, equipments_type):
        page_number = request.query_params.get('page', 1)
        max_page = request.query_params.get('limit', 10)

        paginator = Paginator(queryset, max_page)
        page_obj = paginator.get_page(page_number)

        serializer = EquipmentSerializer(page_obj, many=True, context={'request': request, 'equipments_type': equipments_type})

        data = {
            'data': serializer.data,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next_page': page_obj.has_next(),
            'has_prev_page': page_obj.has_previous(),
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'prev_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None
        }

        return data


class MyAdsListAPIView(APIView):
    permission_classes = [CurrentUserOrReadOnly]

    def get_search_query(self):
        return self.request.query_params.get('title', '')

    def filter_queryset_by_search(self, queryset):
        search_query = self.get_search_query()
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query))
        return queryset

    def get_orders_and_equipments(self, ads=None):
        author = self.request.user.user_profile

        if ads == 'order':
            queryset = Order.objects.filter(author=author).order_by('-created_at')
        elif ads == 'equipment':
            queryset = Equipment.objects.filter(author=author).order_by('-created_at')
        elif ads == 'service':
            queryset = Service.objects.filter(author=author).order_by('-created_at')
        elif ads is None:
            queryset = list(Equipment.objects.filter(author=author)) + list(Order.objects.filter(author=author)) + list(Service.objects.filter(author=author))
            queryset = sorted(queryset, key=attrgetter('created_at'), reverse=True)
        else:
            queryset = []

        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'title',
                openapi.IN_QUERY,
                description="Filter the results by title (case insensitive).",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'ads',
                openapi.IN_QUERY,
                description="Filter the results by the type of advertisement (order, equipment, service). If not provided, returns all.",
                type=openapi.TYPE_STRING,
                enum=['order', 'equipment', 'service'],
                required=False
            )
        ],
        tags=['Orders and Equipments'],
        operation_description="This endpoint provides the user with their orders, equipments, and services.",
        responses={
            200: "Orders, services, and equipments list",
            404: "Orders, services, or equipments do not exist",
            500: "Server error",
        }
    )
    def get(self, request, *args, **kwargs):
        ads = request.query_params.get('ads')
        queryset = self.get_orders_and_equipments(ads)
        queryset = self.filter_queryset_by_search(queryset)
        data = get_order_or_equipment(queryset, request)
        return Response(data, status=status.HTTP_200_OK)


class SearchAdsAPIView(APIView):
    permission_classes = [AllowAny]

    def get_search_query(self):
        return self.request.query_params.get('title', '')

    def filter_queryset_by_search(self, queryset, ads):
        search_query = self.get_search_query()
        if ads in ['order', 'equipment', 'service'] and search_query:
            queryset = queryset.filter(Q(title__icontains=search_query))
        elif ads in ['vacancy', 'resume'] and search_query:
            queryset = queryset.filter(Q(job_title__icontains=search_query))
        return queryset

    def get_orders_and_equipments(self, ads=None):
        if ads == 'order':
            queryset = Order.objects.all().order_by('-created_at')
        elif ads == 'equipment':
            queryset = Equipment.objects.all().order_by('-created_at')
        elif ads == 'service':
            queryset = Service.objects.all().order_by('-created_at')
        elif ads == 'vacancy':
            queryset = Vacancy.objects.all().order_by('-created_at')
        elif ads == 'resume':
            queryset = Resume.objects.all().order_by('-created_at')
        elif ads is None:
            queryset = []
        else:
            queryset = []

        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'title',
                openapi.IN_QUERY,
                description="Filter the results by title (case insensitive).",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'ads',
                openapi.IN_QUERY,
                description="Filter the results by the type of advertisement (order, equipment, service, vacancy, resume). If not provided, returns all.",
                type=openapi.TYPE_STRING,
                enum=['order', 'equipment', 'service', 'vacancy', 'resume'],
                required=False
            )
        ],
        tags=['Search Orders, Equipments, Services, Vacancies, Resumes'],
        operation_description="This endpoint provides the user with their orders, equipments, services, vacancies, and resumes.",
        responses={
            200: "Orders, services, equipments, vacancies, and resumes list",
            404: "Orders, services, equipments, vacancies, or resumes do not exist",
            500: "Server error",
        }
    )
    def get(self, request, *args, **kwargs):
        ads = request.query_params.get('ads')
        queryset = self.get_orders_and_equipments(ads)
        queryset = self.filter_queryset_by_search(queryset, ads)
        data = self.get_paginated_response(queryset, request, ads)
        return Response(data, status=status.HTTP_200_OK)

    def get_paginated_response(self, queryset, request, ads):
        page_number = request.query_params.get('page', 1)
        max_page = request.query_params.get('limit', 10)

        paginator = Paginator(queryset, max_page)
        page_obj = paginator.get_page(page_number)

        if ads in ['order', 'equipment', 'service']:
            serializer = MyAdsSerializer(page_obj, many=True, context={'request': request})
        elif ads == 'vacancy':
            serializer = VacancyListSerializer(page_obj, many=True, context={'request': request})
        elif ads == 'resume':
            serializer = ResumeListSerializer(page_obj, many=True, context={'request': request})
        else:
            serializer = MyAdsSerializer(page_obj, many=True, context={'request': request})

        data = {
            'data': serializer.data,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next_page': page_obj.has_next(),
            'has_prev_page': page_obj.has_previous(),
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'prev_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None
        }

        return data


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
        paginated_data = get_services_paginated_data(queryset, request)
        return Response(paginated_data, status=status.HTTP_200_OK)


class MyServiceAdsListView(BaseServiceListView):
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceListAPI

    def get_queryset(self):
        return Service.objects.filter(author=self.request.user.user_profile).order_by('-created_at')

    @swagger_auto_schema(
        operation_summary="List of services created by the current organization",
        operation_description="Retrieve a list of services created by the current authenticated user.",
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
    serializer_class = ServiceListAPI

    def get_queryset(self):
        return Service.objects.filter(hide=False).order_by('-created_at')

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
    serializer_class = ServiceListAPI

    def get_queryset(self):
        user = self.request.user
        return user.user_profile.liked_services.all().order_by('-created_at')

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
            return Response({"error": "Service is not found."}, status=status.HTTP_404_NOT_FOUND)

        author = request.user.is_authenticated and request.user.user_profile == service.author
        service_api = ServiceSerializer(service, context={'request': request, 'author': author})

        return Response(service_api.data, status=status.HTTP_200_OK)


class CreateServiceAPIView(APIView):
    serializer_class = ServicePostSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create a new service",
        operation_description="Endpoint to create a new service.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["title", "uploaded_images", "description", "price", 'currency', "category_slug", "phone_number", "size"],
            properties={
                "title": openapi.Schema(type=openapi.TYPE_STRING, description="Title of the service"),
                "uploaded_images": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
                    description="List of uploaded images"
                ),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Description of the service"),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price of the service"),
                "currency": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price currency"),
                "category_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Slug of the service category"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number for contact"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="Email of the order")
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
            return Response({'error':'The user has to have a user profile.'},
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
                "deleted_images": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description="List of IDs of images to be deleted (optional)"
                ),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Description of the service (optional)"),
                "price": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price of the service (optional)"),
                "currency": openapi.Schema(type=openapi.TYPE_NUMBER, description="Price currency (optional)"),
                "category_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Slug of the service category (optional)"),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number for contact (optional)"),
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="Email of the order")
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
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != service.author:
            return Response({'error':'User does not have permissions to update this service.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(service, data=request.data, context={'request': request})
        if serializer.is_valid():
            updated_service = serializer.save()
            response_data = serializer.data
            response_data['slug'] = updated_service.slug
            return Response(response_data, status=status.HTTP_200_OK)
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
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != service.author:
            return Response({'error':'User does not have permissions to update this service.'},
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
    def put(self, request, service_slug):
        try:
            service = Service.objects.get(slug=service_slug)
        except Service.DoesNotExist:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

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
    def put(self, request, service_slug):
        try:
            service = Service.objects.get(slug=service_slug)
        except Service.DoesNotExist:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.user_profile != service.author:
            return Response({'error':'User does not have permissions to update this service.'},
                            status=status.HTTP_403_FORBIDDEN)
        if service.hide:
            service.hide = False
        else:
            service.hide = True
        service.save()
        return Response({"Message": "Service hidden status is changed."}, status=status.HTTP_200_OK)


class LikedByUserItemsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def filter_queryset_by_search(self, queryset):
        search_query = self.request.query_params.get('title', '')
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query))
        return queryset

    def get_orders_and_equipments(self, author, item_type=None):
        if item_type == 'order':
            queryset = author.liked_orders.order_by('-created_at')
        elif item_type == 'equipment':
            queryset = author.liked_equipment.order_by('-created_at')
        elif item_type == 'service':
            queryset = author.liked_services.order_by('-created_at')
        elif item_type is None:
            queryset = list(author.liked_orders.all()) + list(author.liked_equipment.all()) + list(author.liked_services.all())
            queryset = sorted(queryset, key=attrgetter('created_at'), reverse=True)
        else:
            queryset = []

        return queryset

    @swagger_auto_schema(
        operation_summary="List of liked items by the current user",
        operation_description="Retrieve a list of items (orders, services, or equipment) liked by the current authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                "type",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Type of items to retrieve (orders, services, equipment)",
                enum=['orders', 'services', 'equipment']
            ),
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter items by title (case-insensitive)",
            ),
        ],
        responses={
            200: "OK",
            400: "Bad Request",
            404: "Not Found"
        },
        tags=["Liked Items"]
    )
    def get(self, request, *args, **kwargs):
        item_type = request.query_params.get('type')
        user = request.user.user_profile
        queryset = self.get_orders_and_equipments(user, item_type)
        queryset = self.filter_queryset_by_search(queryset)
        data = get_order_or_equipment(queryset, request)
        return Response(data, status=status.HTTP_200_OK)
