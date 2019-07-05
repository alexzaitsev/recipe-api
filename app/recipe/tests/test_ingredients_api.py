from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Ingredient
from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientsApiTest(APITestCase):
    """Test the publicly available ingredients API"""

    def test_login_required(self):
        """Test that login is required to access the endpoint"""
        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientApiTest(APITestCase):
    """Test the private ingredients API"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients_list(self):
        """Test retrieving a list of ingredients"""
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Salt')

        response = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """
        Test that only ingredients for the authenticated user
        are returned
        """
        # create Ingredient for a new user
        user2 = get_user_model().objects.create_user(
            'other@test.com',
            'testpass'
        )
        Ingredient.objects.create(user=user2, name='Vinegar')
        # create Inredient for authorized user
        ingr_for_auth_user = Ingredient.objects.create(user=self.user,
                                                       name='Tumeric')
        serializer = IngredientSerializer([ingr_for_auth_user], many=True)

        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
