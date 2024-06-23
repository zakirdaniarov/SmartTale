from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from authorization.models import UserProfile, Organization
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages, \
    Notification
from .models import Service, ServiceCategory, ServiceImages, Size


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['slug', 'first_name', 'last_name', 'profile_image', 'phone_number']


class OrderCategoryListAPI(ModelSerializer):
    class Meta:
        model = OrderCategory
        fields = ['title', 'slug']


class UserProfileAPI(ModelSerializer):

    class Meta:
        model = UserProfile
        fields = ['slug', 'first_name', 'last_name', 'profile_image', 'phone_number']


class OrgAPI(ModelSerializer):
    owner = UserProfileAPI(read_only=True)

    class Meta:
        model = Organization
        fields = ['slug', 'title', 'owner', 'phone_number', 'description']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        detail = self.context.get('detail')
        if not detail:
            representation.pop('owner')
        return representation


class OrderImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderImages
        fields = [
            "id",
            "images",
        ]


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ['id', 'size']


class OrderDetailAPI(ModelSerializer):
    author = UserProfileAPI(read_only=True)
    images = OrderImageSerializer(many=True, read_only=True)
    category_slug = serializers.ReadOnlyField(source='category.slug')
    size = SizeSerializer(read_only=True, many=True)
    type = serializers.SerializerMethodField()
    is_applied = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['title', 'slug', 'author', 'images', 'type', 'description', 'deadline', 'price', 'org_work'
                  'currency', 'category_slug', 'phone_number', 'is_applied', 'email', 'size', 'hide', 'is_finished']

    def get_type(self, instance):
        if isinstance(instance, Equipment):
            return "Equipment"
        elif isinstance(instance, Order):
            return "Order"
        elif isinstance(instance, Service):
            return "Service"
        return None

    def get_is_applied(self, instance):
        user = self.context['request'].user if self.context.get('request') else None
        if user and not user.is_anonymous:
            if Organization.objects.filter(founder=user.user_profile):
                organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
                return organization in instance.org_applicants.all()
            else:
                # If user is None or anonymous, set 'is_liked' to False
                return False
        else:
            return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = self.context['request'].user if self.context.get('request') else None
        if user and not user.is_anonymous:
            representation['is_liked'] = instance.liked_by.filter(user=user).exists()
        else:
            # If user is None or anonymous, set 'is_liked' to False
            representation['is_liked'] = False

        if not self.context['author']:
            representation.pop('hide')
            representation.pop('org_work')
            representation.pop('is_finished')
        else:
            representation.pop('is_liked')
            representation.pop('is_applied')
            representation['booked_at'] = instance.booked_at
            representation['created_at'] = instance.created_at
            representation['is_booked'] = instance.is_booked
        return representation


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'created_at', 'read']


class ServiceCategoryListAPI(ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['title', 'slug']


class ServiceImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImages
        fields = ['id', 'images']


class ServiceSerializer(ModelSerializer):
    author = UserProfileAPI(read_only=True)
    images = ServiceImagesSerializer(many=True, read_only=True)
    category_slug = serializers.ReadOnlyField(source='category.slug')
    type = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['title', 'slug', 'author', 'images', 'type', 'description', 'price',
                  'currency', 'category_slug', 'phone_number', 'email', 'hide', 'created_at']

    def get_type(self, instance):
        if isinstance(instance, Equipment):
            return "Equipment"
        elif isinstance(instance, Order):
            return "Order"
        elif isinstance(instance, Service):
            return "Service"
        return None


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = self.context['request'].user if self.context.get('request') else None
        if user and not user.is_anonymous:
            representation['is_liked'] = instance.liked_by.filter(user=user).exists()
        else:
            # If user is None or anonymous, set 'is_liked' to False
            representation['is_liked'] = False
        if not self.context['author']:
            representation.pop('hide')
        else:
            representation.pop('is_liked')
        return representation


class ServiceListAPI(serializers.ModelSerializer):
    author = UserProfileAPI(read_only=True)
    is_liked = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    category_slug = serializers.ReadOnlyField(source='category.slug')
    type = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['title', 'slug', 'author', 'currency', 'type', 'category_slug', 'image', 'description',
                  'price', 'is_liked']

    def get_type(self, instance):
        if isinstance(instance, Equipment):
            return "Equipment"
        elif isinstance(instance, Order):
            return "Order"
        elif isinstance(instance, Service):
            return "Service"
        return None

    def get_is_liked(self, instance):
        user = self.context['request'].user if self.context.get('request') else None
        if user and not user.is_anonymous:
            return instance.liked_by.filter(user=user).exists()
        else:
            # If user is None or anonymous, set 'is_liked' to False
            return False

    def get_image(self, instance):
        first_image = instance.images.first()
        if first_image:
            return first_image.images.url
        return None


class ServicePostSerializer(ModelSerializer):
    category_slug = serializers.SlugField(write_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=100000, allow_empty_file=False, use_url=False),
        write_only=True,
    )

    deleted_images = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Service
        fields = ['title', 'uploaded_images', 'deleted_images', 'description', 'price', 'currency',
                  'category_slug', 'phone_number', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if the instance is being created or updated
        if self.instance is None:
            # Fields required for creating a new order
            self.fields['title'].required = True
            self.fields['uploaded_images'].required = True
            self.fields['deleted_images'].required = False
            self.fields['description'].required = True
            self.fields['price'].required = True
            self.fields['category_slug'].required = False
            self.fields['phone_number'].required = True
            self.fields['email'].required = False
            self.fields['currency'].required = True
        else:
            self.fields['title'].required = False
            self.fields['uploaded_images'].required = False
            self.fields['deleted_images'].required = False
            self.fields['description'].required = False
            self.fields['price'].required = False
            self.fields['category_slug'].required = False
            self.fields['phone_number'].required = False
            self.fields['email'].required = False
            self.fields['currency'].required = False

    def create(self, validated_data):
        category = None
        if 'category_slug' in validated_data:
            category_slug = validated_data.pop('category_slug')
            # Retrieve the category instance based on the slug
            try:
                category = ServiceCategory.objects.get(slug=category_slug)
                validated_data['category'] = category
            except ServiceCategory.DoesNotExist:
                raise serializers.ValidationError("Category with this slug does not exist")
        uploaded_images = validated_data.pop('uploaded_images')

        # Create the order object
        author = self.context['request'].user.user_profile
        service = Service.objects.create(author=author, **validated_data)

        # Create OrderImages objects for uploaded images
        for image_data in uploaded_images:
            ServiceImages.objects.create(service=service, images=image_data)
        return service

    def update(self, instance, validated_data):
        if 'category_slug' in validated_data:
            category_slug = validated_data.pop('category_slug')
            # Retrieve the category instance based on the slug
            try:
                category = ServiceCategory.objects.get(slug=category_slug)
                validated_data['category'] = category
            except ServiceCategory.DoesNotExist:
                raise serializers.ValidationError("Category with this slug does not exist")

        deleted_images_data = validated_data.pop("deleted_images", [])
        if deleted_images_data:
            ServiceImages.objects.filter(id__in=deleted_images_data).delete()

        if 'uploaded_images' in validated_data:
            images_data = validated_data.pop('uploaded_images', [])
            for index, image_data in enumerate(images_data):
                ServiceImages.objects.create(service=instance, images=image_data)

        for field, value in validated_data.items():
                setattr(instance, field, value)

        instance.save()
        return instance


class EquipmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentCategory
        fields = '__all__'


class OrderListAPI(serializers.ModelSerializer):
    author = UserProfileAPI(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_applied = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    category_slug = serializers.ReadOnlyField(source='category.slug')
    type = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['title', 'slug', 'author', 'currency', 'type', 'category_slug', 'image', 'description',
                  'price', 'is_liked', 'is_applied', 'status', 'deadline', 'finished_at', 'is_booked', 'booked_at', 'is_finished']

    def get_type(self, instance):
        if isinstance(instance, Equipment):
            return "Equipment"
        elif isinstance(instance, Order):
            return "Order"
        elif isinstance(instance, Service):
            return "Service"
        return None


    def get_is_liked(self, instance):
        user = self.context['request'].user if self.context.get('request') else None
        if user and not user.is_anonymous:
            return instance.liked_by.filter(user=user).exists()
        else:
            # If user is None or anonymous, set 'is_liked' to False
            return False

    def get_is_applied(self, instance):
        user = self.context['request'].user if self.context.get('request') else None
        if user and not user.is_anonymous:
            if Organization.objects.filter(founder=user.user_profile):
                organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
                return organization in instance.org_applicants.all()
            else:
                # If user is None or anonymous, set 'is_liked' to False
                return False
        else:
            return False

    def get_image(self, instance):
        first_image = instance.images.first()
        if first_image:
            return first_image.images.url
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        list_type = self.context.get('list_type')

        if list_type in ["my-order-ads", "applied-orders"]:
            representation.pop('author')
            # representation.pop('category_slug')
            representation.pop('price')
            representation.pop('currency')
            representation['created_at'] = instance.created_at
            representation.pop('is_liked')
            representation.pop('booked_at')
        elif list_type == "my-received-orders":
            representation.pop('is_booked')
            representation.pop('is_liked')
            representation.pop('booked_at')
            representation.pop('is_finished')
        elif list_type in ["my-history-orders-active", "my-history-orders-finished"]:
            #representation.pop('author')
            representation.pop('image')
            representation.pop('description')
            representation.pop('is_booked')
            representation.pop('is_liked')
            representation.pop('is_finished')
        elif list_type in ["my-org-orders", "orders-history-active", "orders-history-finished"]:
            representation.pop('author')
            representation.pop('price')
            representation.pop('currency')
            representation.pop('is_liked')
            representation.pop('is_booked')
            representation.pop('is_finished')
        elif list_type == "marketplace-orders":
            representation.pop('is_booked')
            representation.pop('booked_at')
            representation.pop('is_finished')

        if list_type == "my-history-orders-finished":
            representation.pop('booked_at')

        if list_type == "applied-orders":
            representation.pop('is_booked')
            representation.pop('is_finished')
            if instance.is_booked:
                if instance.org_work == self.context['request'].user.user_profile.current_org:
                    representation['application_status'] = "approved"
                else:
                    representation['application_status'] = "rejected"
            else:
                representation['application_status'] = "waiting"
        return representation


class OrderListStatusAPI(ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'title', 'slug', 'description', 'deadline', 'status']


class OrderPostAPI(ModelSerializer):
    size = serializers.ListField(child=serializers.CharField(max_length=10), write_only=True)
    category_slug = serializers.SlugField(write_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=100000, allow_empty_file=False, use_url=False),
        write_only=True,
    )
    deleted_images = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Order
        fields = ['title', 'uploaded_images', 'deleted_images', 'description', 'deadline', 'price', 'currency', 'category_slug', 'phone_number', 'email', 'size']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if the instance is being created or updated
        if self.instance is None:
            # Fields required for creating a new order
            self.fields['title'].required = True
            self.fields['uploaded_images'].required = True
            self.fields['deleted_images'].required = False
            self.fields['description'].required = True
            self.fields['deadline'].required = True
            self.fields['price'].required = True
            self.fields['category_slug'].required = False
            self.fields['size'].required = True
            self.fields['phone_number'].required = True
            self.fields['email'].required = False
            self.fields['currency'].required = True
        else:
            # Fields not required for updating an existing order
            self.fields['title'].required = False
            self.fields['uploaded_images'].required = False
            self.fields['deleted_images'].required = False
            self.fields['description'].required = False
            self.fields['deadline'].required = False
            self.fields['price'].required = False
            self.fields['category_slug'].required = False
            self.fields['size'].required = False
            self.fields['phone_number'].required = False
            self.fields['email'].required = False
            self.fields['currency'].required = False

    def create(self, validated_data):
        sizes_data = validated_data.pop('size')
        uploaded_images = validated_data.pop('uploaded_images')
        if 'category_slug' in validated_data:
            category_slug = validated_data.pop('category_slug')
            # Retrieve the category instance based on the slug
            try:
                category = OrderCategory.objects.get(slug=category_slug)
                validated_data['category'] = category
            except OrderCategory.DoesNotExist:
                raise serializers.ValidationError("Category with this slug does not exist")
        # Create the order object
        author = self.context['request'].user.user_profile
        order = Order.objects.create(author=author, **validated_data)
        size_objs = []
        for size_data in sizes_data:
            size_obj, created = Size.objects.get_or_create(size=size_data)
            size_objs.append(size_obj)
        order.size.set(size_objs)

        # Create OrderImages objects for uploaded images
        for image_data in uploaded_images:
            OrderImages.objects.create(order=order, images=image_data)

        return order

    def update(self, instance, validated_data):
        deleted_images = validated_data.pop('deleted_images', [])
        if 'category_slug' in validated_data:
            category_slug = validated_data.pop('category_slug')
            # Retrieve the category instance based on the slug
            try:
                category = OrderCategory.objects.get(slug=category_slug)
                validated_data['category'] = category
            except OrderCategory.DoesNotExist:
                raise serializers.ValidationError("Category with this slug does not exist")

        if deleted_images:
            OrderImages.objects.filter(id__in=deleted_images).delete()

        if 'uploaded_images' in validated_data:
            images_data = validated_data.pop('uploaded_images', [])
            for index, image_data in enumerate(images_data):
                OrderImages.objects.create(order=instance, images=image_data)

        sizes_data = validated_data.pop('size', [])
        if sizes_data:
            size_objs = []
            for size_data in sizes_data:
                size_obj, created = Size.objects.get_or_create(size=size_data)
                size_objs.append(size_obj)
            instance.size.set(size_objs)

        for field, value in validated_data.items():
                setattr(instance, field, value)

        instance.save()
        return instance


class ReviewListAPI(ModelSerializer):
    order_slug = serializers.ReadOnlyField(source='order.slug')
    reviewer_slug = serializers.ReadOnlyField(source='reviewer.slug')

    class Meta:
        model = Reviews
        fields = ['order_slug', 'reviewer_slug', 'review_text', 'rating', 'created_at']


class EquipmentImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentImages
        fields = ['id', 'images']


class EquipmentModalPageSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    images = EquipmentImagesSerializer(many=True, read_only=True)

    class Meta:
        model = Equipment
        fields = ['title', 'images', 'price', 'currency', 'author', 'description']


class EquipmentDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    images = EquipmentImagesSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=100000, allow_empty_file=False, use_url=False),
        write_only=True
    )
    deleted_images = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['title', 'slug', 'images', 'uploaded_images', 'deleted_images', 'price', 'currency',
                  'description', 'phone_number', 'email', 'author', 'hide', 'quantity', 'is_liked']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if the instance is being created or updated
        if self.instance is None:
            # Fields required for creating a new equipment
            self.fields['title'].required = True
            self.fields['uploaded_images'].required = True
            self.fields['deleted_images'].required = False
            self.fields['description'].required = False
            self.fields['price'].required = True
            self.fields['phone_number'].required = True
            self.fields['email'].required = False
            self.fields['currency'].required = True
            self.fields['quantity'].required = True
            self.fields['is_liked'].required = False
        else:
            # Fields not required for updating an existing equipment
            self.fields['title'].required = False
            self.fields['uploaded_images'].required = False
            self.fields['deleted_images'].required = False
            self.fields['description'].required = False
            self.fields['price'].required = False
            self.fields['phone_number'].required = False
            self.fields['email'].required = False
            self.fields['currency'].required = False
            self.fields['quantity'].required = False
            self.fields['is_liked'].required = False

    def get_is_liked(self, instance):
        author = self.context['request'].user if self.context.get('request') else None

        if author and not author.is_anonymous:
            return instance.liked_by.filter(id=author.id).exists()
        else:
            return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.is_anonymous:
            representation.pop('is_liked', None)
            representation.pop('hide', None)
        return representation

    def create(self, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        equipment = Equipment.objects.create(**validated_data)

        max_images = 5
        if len(images_data) > max_images:
            raise serializers.ValidationError(f"You can't add more then {max_images} images")

        for image_data in images_data:
            EquipmentImages.objects.create(equipment=equipment, images=image_data)
        return equipment

    def update(self, instance, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        deleted_images = validated_data.pop('deleted_images', [])

        if deleted_images:
            EquipmentImages.objects.filter(id__in=deleted_images).delete()

        if images_data:
            max_images = 5
            if len(images_data) > max_images:
                raise serializers.ValidationError(f"You can't add more then {max_images} images")

            for image_data in images_data:
                EquipmentImages.objects.create(equipment=instance, images=image_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class ReviewPostAPI(ModelSerializer):
    class Meta:
        model = Reviews
        fields = ['review_text', 'rating']

    def create(self, validated_data):
        order = validated_data.pop('order')
        reviewer = validated_data.pop('reviewer')
        review = Reviews.objects.create(order=order, reviewer=reviewer, **validated_data)
        return review


class EquipmentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    image = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['title', 'slug', 'type', 'price', 'currency', 'description', 'image', 'author', 'is_liked']

    def get_type(self, instance):
        if isinstance(instance, Equipment):
            return "Equipment"
        elif isinstance(instance, Order):
            return "Order"
        elif isinstance(instance, Service):
            return "Service"
        return None

    def get_image(self, instance):
        image = instance.images.first()
        if image:
            return image.images.url
        return 'Images does not exist'

    def get_is_liked(self, instance):
        author = self.context['request'].user if self.context.get('request') else None

        if author and not author.is_anonymous:
            return instance.liked_by.filter(id=author.id).exists()
        else:
            return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        equipments = self.context.get('equipments_type')
        request = self.context.get('request')

        if equipments == 'my-like-equipments':
            fields_to_remove = ['author', 'is_liked']
        elif equipments == 'equipments-list':
            fields_to_remove = ['title', 'slug', 'price', 'currency', 'image', 'author', 'is_liked']
        elif equipments == 'my-purchases-equipments':
            fields_to_remove = ['is_liked']
        else:
            fields_to_remove = []

        for field in fields_to_remove:
            representation.pop(field, None)

        if request and request.user.is_anonymous:
            representation.pop('is_liked', None)

        return representation


class MyAdsSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    author = UserProfileAPI(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Order  # Placeholder for dynamic model assignment
        fields = ['title', 'slug', 'author', 'description', 'type', 'image', 'status', 'is_liked', 'price', 'currency']  # Adjust fields as needed

    def get_image(self, instance):
        image = instance.images.first()
        if image:
            return image.images.url
        return 'Images does not exist'

    def get_is_liked(self, instance):
        user = self.context['request'].user if self.context.get('request') else None
        if user and not user.is_anonymous:
            return instance.liked_by.filter(user=user).exists()
        else:
            # If user is None or anonymous, set 'is_liked' to False
            return False

    def get_type(self, instance):
        if isinstance(instance, Equipment):
            return "Equipment"
        elif isinstance(instance, Order):
            return "Order"
        elif isinstance(instance, Service):
            return "Service"
        return None

