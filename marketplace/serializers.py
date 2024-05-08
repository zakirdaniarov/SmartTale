from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages


class OrderCategoryListAPI(ModelSerializer):
    class Meta:
        model = OrderCategory
        fields = ['title', 'slug']


class OrderImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderImages
        fields = [
            "id",
            "images",
        ]


class OrderDetailAPI(ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.username')
    author_slug = serializers.ReadOnlyField(source='author.slug')
    images = OrderImageSerializer(many=True, read_only=True)
    category_slug = serializers.ReadOnlyField(source='category.slug')

    class Meta:
        model = Order
        fields = ['title', 'slug', 'author_name', 'author_slug', 'images', 'description', 'deadline', 'price',
                  'category_slug', 'phone_number', 'size', 'is_booked', 'hide', 'booked_at', 'created_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = self.context['request'].user
        representation['is_liked'] = instance.liked_by.filter(user=user).exists()
        representation['is_finished'] = (instance.status == 'Arrived')
        if not self.context['author']:
            representation.pop('hide')
            representation.pop('booked_at')
        else:
            representation.pop('is_liked')
        return representation


class OrderListAPI(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.first_name')
    author_slug = serializers.ReadOnlyField(source='author.slug')
    is_liked = serializers.SerializerMethodField()
    first_image = serializers.SerializerMethodField()
    is_finished = serializers.SerializerMethodField()
    category_slug = serializers.ReadOnlyField(source='category.slug')

    class Meta:
        model = Order
        fields = ['title', 'slug', 'author_name', 'author_slug', 'category_slug', 'first_image', 'description',
                  'price', 'is_liked', 'is_booked', 'booked_at', 'is_finished']

    def get_is_liked(self, instance):
        user = self.context['request'].user
        return instance.liked_by.filter(user=user).exists()

    def get_first_image(self, instance):
        first_image = instance.images.first()
        if first_image:
            return first_image.images.url
        return None

    def get_is_finished(self, instance):
        return instance.status == 'Arrived'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        list_type = self.context.get('list_type')

        if list_type == "my-order-ads":
            representation.pop('author_name')
            representation.pop('author_slug')
            representation.pop('price')
        elif list_type == "my-received-orders":
            representation.pop('is_booked')
        elif list_type in ["my-history-orders-active", "my-history-orders-finished"]:
            representation.pop('author_name')
            representation.pop('author_slug')
            representation.pop('category_slug')
            representation.pop('images')
            representation.pop('description')
            representation.pop('is_booked')
        elif list_type == "my-org-orders":
            representation.pop('author_name')
            representation.pop('author_slug')
            representation.pop('is_liked')
            representation.pop('is_booked')
        elif list_type in ["marketplace-orders", "orders-history-active", "orders-history-finished"]:
            representation.pop('is_finished')
            representation.pop('booked_at')

        if list_type in ["my-history-orders-finished", "orders-history-active", "orders-history-finished"]:
            representation['finished_at'] = instance.finished_at

        return representation


class OrderListStatusAPI(ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'title', 'slug', 'description', 'deadline', 'status']


class OrderPostAPI(ModelSerializer):
    category_slug = serializers.SlugField(write_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=100000, allow_empty_file=False, use_url=False),
        write_only=True,
    )

    class Meta:
        model = Order
        fields = ['title', 'uploaded_images', 'description', 'deadline', 'price', 'category_slug', 'phone_number', 'size']

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
            self.fields['category_slug'].required = True
            self.fields['size'].required = True
            self.fields['phone_number'].required = True
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

    def create(self, validated_data):
        category_slug = validated_data.pop('category_slug')
        uploaded_images = validated_data.pop('uploaded_images')

        # Retrieve the category instance based on the slug
        try:
            category = OrderCategory.objects.get(slug=category_slug)
        except OrderCategory.DoesNotExist:
            raise serializers.ValidationError("Category with this slug does not exist")

        # Create the order object
        validated_data['category'] = category
        author = self.context['request'].user.user_profile
        order = Order.objects.create(author=author, **validated_data)

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


class ReviewPostAPI(ModelSerializer):
    class Meta:
        model = Reviews
        fields = ['review_text', 'rating']

    def create(self, validated_data):
        order = validated_data.pop('order')
        reviewer = validated_data.pop('reviewer')
        review = Reviews.objects.create(order=order, reviewer=reviewer, **validated_data)
        return review
