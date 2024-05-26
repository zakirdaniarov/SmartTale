from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from authorization.models import UserProfile, Organization
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages
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
        fields = ['slug', 'first_name', 'last_name', 'profile_image']


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

    class Meta:
        model = Order
        fields = ['title', 'slug', 'author', 'images', 'type', 'description', 'deadline', 'price',
                  'currency', 'category_slug', 'phone_number', 'email', 'size', 'hide', 'is_finished']

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
            representation.pop('is_finished')
        else:
            representation.pop('is_liked')
            representation.pop('author')
            representation['booked_at'] = instance.booked_at
            representation['created_at'] = instance.created_at
            representation['is_booked'] = instance.is_booked
        return representation


class ServiceCategoryListAPI(ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['title', 'slug']


class ServiceImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImages
        fields = ['images']


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


class ServicePostSerializer(ModelSerializer):
    category_slug = serializers.SlugField(write_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=100000, allow_empty_file=False, use_url=False),
        write_only=True,
    )

    class Meta:
        model = Service
        fields = ['title', 'uploaded_images', 'description', 'price', 'currency',
                  'category_slug', 'phone_number', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if the instance is being created or updated
        if self.instance is None:
            # Fields required for creating a new order
            self.fields['title'].required = True
            self.fields['uploaded_images'].required = True
            self.fields['description'].required = True
            self.fields['price'].required = True
            self.fields['category_slug'].required = False
            self.fields['phone_number'].required = True
            self.fields['email'].required = False
            self.fields['currency'].required = True
        else:
            self.fields['title'].required = False
            self.fields['uploaded_images'].required = False
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
        if 'uploaded_images' in validated_data:
            images_data = validated_data.pop('uploaded_images', [])
            current_images = list(instance.images.all())
            for image in current_images:
                image.delete()

            max_images = 5
            for index, image_data in enumerate(images_data):
                # Check if the maximum number of images has been reached
                if index >= max_images:
                    break
                # create the image
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
    first_image = serializers.SerializerMethodField()
    category_slug = serializers.ReadOnlyField(source='category.slug')
    type = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['title', 'slug', 'author', 'currency', 'type', 'category_slug', 'first_image', 'description',
                  'price', 'is_liked', 'is_booked', 'booked_at', 'is_finished']

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

    def get_first_image(self, instance):
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
            representation['status'] = instance.status
        elif list_type == "my-received-orders":
            representation.pop('is_booked')
            representation.pop('is_liked')
            representation.pop('booked_at')
            representation.pop('is_finished')
        elif list_type in ["my-history-orders-active", "my-history-orders-finished"]:
            representation.pop('author')
            representation.pop('first_image')
            representation.pop('description')
            representation.pop('is_booked')
            representation.pop('is_liked')
            representation.pop('is_finished')
            representation['status'] = instance.status
        elif list_type in ["my-org-orders", "orders-history-active", "orders-history-finished"]:
            representation.pop('author')
            representation.pop('price')
            representation.pop('currency')
            representation.pop('is_liked')
            representation.pop('is_booked')
            representation.pop('is_finished')
        elif list_type == "marketplace-orders":
            representation.pop('is_booked')
            representation.pop('is_liked')
            representation.pop('booked_at')
            representation.pop('is_finished')

        if list_type == "my-history-orders-finished":
            representation['finished_at'] = instance.finished_at
            representation.pop('booked_at')

        if list_type == "applied-orders":
            representation.pop('is_booked')
            representation.pop('is_finished')
            representation.pop('status')
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

    class Meta:
        model = Order
        fields = ['title', 'uploaded_images', 'description', 'deadline', 'price', 'currency', 'category_slug', 'phone_number', 'email', 'size']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if the instance is being created or updated
        if self.instance is None:
            # Fields required for creating a new order
            self.fields['title'].required = True
            self.fields['uploaded_images'].required = True
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
        if 'category_slug' in validated_data:
            category_slug = validated_data.pop('category_slug')
            # Retrieve the category instance based on the slug
            try:
                category = OrderCategory.objects.get(slug=category_slug)
                validated_data['category'] = category
            except OrderCategory.DoesNotExist:
                raise serializers.ValidationError("Category with this slug does not exist")
        if 'uploaded_images' in validated_data:
            images_data = validated_data.pop('uploaded_images', [])
            current_images = list(instance.images.all())
            for image in current_images:
                image.delete()

            max_images = 5
            for index, image_data in enumerate(images_data):
                # Check if the maximum number of images has been reached
                if index >= max_images:
                    break
                # create the image
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
        fields = ['images']


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
    sale_status = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['title', 'slug', 'category', 'images', 'uploaded_images', 'price', 'currency',
                  'description', 'phone_number', 'email', 'author', 'hide', 'sale_status']

    def get_sale_status(self, instance):
        sale_status = instance.sold
        if sale_status:
            return "Equipment sold"
        return "Equipment available"

    def create(self, validated_data):
        images_data = validated_data.pop('uploaded_images')
        equipment = Equipment.objects.create(**validated_data)

        max_images = 5
        if len(images_data) > max_images:
            raise serializers.ValidationError(f"You can't add more then {max_images} images")

        for image_data in images_data:
            EquipmentImages.objects.create(equipment=equipment, images=image_data)
        return equipment

    def update(self, instance, validated_data):
        images_data = validated_data.pop('uploaded_images')

        if images_data:
            current_images = list(instance.images.all())

            max_images = 5
            if len(images_data) > max_images:
                raise serializers.ValidationError(f"You can't add more then {max_images} images")

            for image in current_images:
                if image not in images_data:
                    image.delete()

            for image_data in images_data:
                EquipmentImages.objects.update_or_create(equipment=instance, images=image_data)
        else:
            return instance

        instance.title = validated_data.pop('title', instance.title)
        instance.description = validated_data.pop('description', instance.description)
        instance.category = validated_data.pop('category', instance.category)
        instance.price = validated_data.pop('price', instance.price)
        instance.currency = validated_data.pop('price', instance.currency)
        instance.phone_number = validated_data.pop('phone_number', instance.phone_number)
        instance.email = validated_data.pop('email', instance.email)
        instance.author = validated_data.pop('author', instance.author)
        instance.hide = validated_data.pop('hide', instance.hide)
        instance.sold = validated_data.pop('sold', instance.sold)
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
    liked = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['title', 'slug', 'type', 'price', 'currency', 'description', 'image', 'author', 'liked']

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

    def get_liked(self, instance):
        author = self.context['request'].user.user_profile
        return instance.liked_by.filter(slug=author.slug).exists()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        equipments = self.context.get('equipments_type')

        if equipments == 'my-like-equipments':
            representation.pop('author')
            representation.pop('liked')
        elif equipments == 'equipments-list':
            representation.pop('title')
            representation.pop('slug')
            representation.pop('price')
            representation.pop('currency')
            representation.pop('image')
            representation.pop('author')
            representation.pop('liked')

        return representation


class MyOrderEquipmentSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = None  # Placeholder for dynamic model assignment
        fields = ['title', 'slug', 'description', 'type', 'image', 'status']  # Adjust fields as needed

    def __init__(self, instance, *args, **kwargs):
        if isinstance(instance, list) and instance:  # Check if instance is a non-empty list
            # model = instance[0].__class__  # Get the class of the first instance in the list
            model = Order
        else:
            raise ValueError("Expected a non-empty list of instances")

        super().__init__(instance, *args, **kwargs)
        self.Meta.model = model

    def get_image(self, instance):
        image = instance.images.first()
        if image:
            return image.images.url
        return 'Images does not exist'

    def get_type(self, instance):
        if isinstance(instance, Equipment):
            return "Equipment"
        elif isinstance(instance, Order):
            return "Order"
        elif isinstance(instance, Service):
            return "Service"
        return None
