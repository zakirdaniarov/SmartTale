from django.urls import path

from .views import *


urlpatterns = [
    path('my-order-ads/', MyOrderAdsListView.as_view(), name='smarttale-my-order-ads'),
    path('my-received-orders/', MyReceivedOrdersListView.as_view(), name='smarttale-my-received-orders'),
    path('my-history-orders/', MyHistoryOrdersListView.as_view(), name='smarttale-my-history-orders'),
    path('my-org-orders/', MyOrgOrdersListView.as_view(), name='smarttale-my-org-orders'),
    path('marketplace-orders/', MarketplaceOrdersListView.as_view(), name='smarttale-marketplace-orders'),
    path('received-orders-status/', ReceivedOrderStatusAPIView.as_view(), name='smarttale-orders-received'),
    path('orders-history/', OrdersHistoryListView.as_view(), name='smarttale-orders-history'),
    path('order-detail/<slug:order_slug>/', OrderDetailAPIView.as_view(), name='smarttale-order-detail'),
    path('order-add-employee/<slug:order_slug>/<slug:employee_slug>/', OrderAddEmployeeAPIView.as_view(), name='smarttale-order-add-employee'),
    path('order-remove-employee/<slug:order_slug>/<slug:employee_slug>/', OrderRemoveEmployeeAPIView.as_view(), name='smarttale-order-remove-employeee'),

    path('add-order/', AddOrderAPIView.as_view(), name='smarttale-order-add'),
    path('update-order/<slug:order_slug>/', UpdateOrderAPIView.as_view(), name='smarttale-order-add'),
    path('order-hide/<slug:order_slug>/', HideOrderAPIView.as_view(), name='smarttale-hide-order'),
    path('order-finish/<slug:order_slug>/', FinishOrderAPIView.as_view(), name='smarttale-hide-order'),
    path('order-delete/<slug:order_slug>/', DeleteOrderAPIView.as_view(), name='smarttale-delete-order'),
    path('update-status/<slug:order_slug>/', UpdateOrderStatusAPIView.as_view(), name='smarttale-receive-order'),

    path('order-apply/<slug:order_slug>/', ApplyOrderAPIView.as_view(), name='smarttale-apply-order'),
    path('applied-orgs/<slug:order_slug>/', MyOrderApplicationsListView.as_view(), name='smarttale-my-order-applications'),
    path('order-book/<slug:order_slug>/<slug:org_slug>/', BookOrderAPIView.as_view(), name='smarttale-book-order'),
    path('my-applied-orders/', MyAppliedOrdersListView.as_view(), name='smarttale-my-applied-orders'),

    path('like-order/<slug:order_slug>/', LikeOrderAPIView.as_view(), name='smarttale-like-order'),
    path('review-order/<slug:order_slug>/', ReviewOrderAPIView.as_view(), name='smarttale-review-orders'),
    path('order-categories/', OrderCategoriesAPIView.as_view(), name='smarttale-order-categories'),
    path('orders-by-category/', OrdersByCategoryAPIView.as_view(), name='smarttale-order--by-categories'),
    path('liked-orders/', LikedByUserOrdersAPIView.as_view(), name='smarttale-liked-orders'),
    path('liked-items/', LikedByUserItemsAPIView.as_view(), name='smarttale-liked-items'),
    path('org-orders/<str:org_slug>/', OrgOrdersListView.as_view(), name='org-orders-list'),

    path('service-categories/', ServiceCategoriesAPIView.as_view()),
    path('my-services/', MyServiceAdsListView.as_view()),
    path('services/', ServicesAPIView.as_view()),
    path('service/<str:service_slug>/', ServiceDetailAPIView.as_view()),
    path('service-create/', CreateServiceAPIView.as_view()),
    path('service-update/<str:service_slug>/', UpdateServiceAPIView.as_view()),
    path('service-delete/<str:service_slug>/', DeleteServiceAPIView.as_view()),
    path('service-like/<str:service_slug>/', ServiceLikeAPIView.as_view()),
    path('service-hide/<str:service_slug>/', HideServiceAPIView.as_view()),
    path('liked-services/', LikedByUserServicesAPIView.as_view()),

    path('ads-search/', SearchAdsAPIView.as_view()),
    path('my-ads/', MyAdsListAPIView.as_view()),

    path('equipments/', EquipmentsListAPIView.as_view()),
    path('equipment/search/', EquipmentSearchAPIView.as_view()),
    path('equipment/create/', CreateEquipmentAPIView.as_view()),
    path('equipment/change/<str:equipment_slug>/', ChangeEquipmentAPIView.as_view()),
    path('equipment/delete/<str:equipment_slug>/', DeleteEquipmentAPIView.as_view()),

    path('equipments/like/<str:equipment_slug>/', EquipmentLikeAPIView.as_view()),
    path('hide-equipment/<str:equipment_slug>/', HideEquipmentAPIView.as_view()),
    path('sold-equipment/<str:equipment_slug>/', SoldEquipmentAPIView.as_view()),
    path('my-purchases/', MyPurchasesAPIView.as_view()),
    path('liked-equipments/', EquipmentByAuthorLikeAPIView.as_view()),
    path('equipment/<str:equipment_slug>/', EquipmentDetailPageAPIView.as_view()),
    path('equipment-modal/<slug:equipment_slug>/', EquipmentModalPageAPIView.as_view()),
]
