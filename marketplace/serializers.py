from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from authorization.models import UserProfile
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'profile_image']


class OrderCategoryListAPI(ModelSerializer):
    class Meta:
        model = OrderCategory
        fields = ['title', 'slug']


class OrderDetailAPI(ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.username')
    author_slug = serializers.ReadOnlyField(source='author.slug')
    images = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['title', 'slug', 'author_name', 'author_slug', 'images', 'description', 'deadline', 'price',
                  'category', 'phone_number', 'size', 'is_booked', 'hide', 'booked_at', 'created_at']

    def get_images(self, instance):
        images_queryset = instance.images.all()  # Get all images associated with the order
        return [image.images.url for image in images_queryset]

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


class EquipmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentCategory
        fields = '__all__'


class OrderListAPI(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.username')
    author_slug = serializers.ReadOnlyField(source='author.slug')
    is_liked = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    is_finished = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['title', 'slug', 'author_name', 'author_slug', 'category', 'images', 'description',
                  'price', 'is_booked', 'booked_at', 'is_finished']

    def get_images(self, instance):
        images_queryset = instance.images.all()  # Get all images associated with the order
        return [image.images.url for image in images_queryset]

    def get_is_liked(self, instance):
        user = self.context['request'].user
        return instance.liked_by.filter(id=user.id).exists()

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
            representation.pop('category')
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


class ImageSerializer(ModelSerializer):
    class Meta:
        model = OrderImages
        fields = ['images']


class OrderPostAPI(ModelSerializer):
    images = ImageSerializer(many=True)

    class Meta:
        model = Order
        fields = ['title', 'images', 'description', 'deadline', 'price', 'category', 'phone_number', 'size']

    def create(self, validated_data):
        images_data = validated_data.pop('images')
        author = self.context['request'].user
        order = Order.objects.create(author=author, **validated_data)
        for image_data in images_data:
            OrderImages.objects.create(order=order, images=image_data)
        return order

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', [])
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.deadline = validated_data.get('deadline', instance.deadline)
        instance.price = validated_data.get('price', instance.price)
        instance.category = validated_data.get('category', instance.category)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.size = validated_data.get('size', instance.size)
        instance.save()
        # Update or create images
        for image_data in images_data:
            OrderImages.objects.update_or_create(order=instance, defaults={'images': image_data})
        return instance


class ReviewListAPI(ModelSerializer):
    class Meta:
        model = Reviews
        fields = ['order', 'reviewer', 'review_text', 'rating', 'created_at']


class EquipmentImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentImages
        fields = ['images']


class EquipmentDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    images = EquipmentImagesSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=100000, allow_empty_file=False, use_url=False),
        write_only=True
    )

    class Meta:
        model = Equipment
        fields = ['id', 'title', 'category', 'images', 'uploaded_images', 'price',
                  'description', 'phone_number', 'author', 'hide', 'sold']

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
        images_data = validated_data.pop('uploaded_images', [])

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
        instance.phone_number = validated_data.pop('phone_number', instance.phone_number)
        instance.author = validated_data.pop('author', instance.author)
        instance.hide = validated_data.pop('hide', instance.hide)
        instance.sold = validated_data.pop('sold', instance.sold)
        instance.save()

        return instance


class ReviewPostAPI(ModelSerializer):
    class Meta:
        model = Reviews
        fields = ['review_text', 'rating']


class EquipmentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    image = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['title', 'slug', 'price', 'description', 'image', 'author', 'liked']

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
            representation.pop('image')
            representation.pop('author')
            representation.pop('liked')

        return representation


class AllEquipmentsSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['title', 'description', 'service', 'image']

    def get_image(self, instance):
        image = instance.images.first()
        if image:
            return image.images.url
        return 'Images does not exist'

    def get_service(self, instance):
        return "Оборудование"


class AllOrdersSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['title', 'description', 'service', 'image']

    def get_image(self, instance):
        image = instance.images.first()
        if image:
            return image.images.url
        return 'Images does not exist'

    def get_service(self, instance):
        return "Заказ"
