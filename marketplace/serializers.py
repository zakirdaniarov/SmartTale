from rest_framework import serializers

from .models import Equipment, EquipmentCategory, EquipmentImages


class EquipmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentCategory
        fields = '__all__'


class EquipmentImagesSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(max_length=5, allow_empty_file=False, use_url=False),
        write_only=True
    )

    class Meta:
        model = EquipmentImages
        fields = '__all__'

    def create(self, validated_data):
        images_data = self.context.get('request').data.get('images')
        equipment = Equipment.objects.create(**validated_data)
        for image_data in images_data:
            image = EquipmentImages.objects.create(image=image_data)
            equipment.images.add(image)
        return equipment


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = ['title', 'price', 'description', 'author']


class EquipmentDetailSerializer(serializers.ModelSerializer):
    images = EquipmentImagesSerializer(many=True, read_only=True)

    class Meta:
        model = Equipment
        fields = ['title', 'category', 'images', 'price', 'description',
                  'phone_number', 'author', 'liked_by', 'hide', 'sold']
