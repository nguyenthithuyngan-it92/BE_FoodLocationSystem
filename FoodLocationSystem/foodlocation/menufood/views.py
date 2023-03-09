from rest_framework import viewsets, permissions
from .models import Food
from .serializers import FoodSerializer


class FoodViewSet(viewsets.ModelViewSet):
    queryset = Food.objects.filter(active=True)
    serializer_class = FoodSerializer
