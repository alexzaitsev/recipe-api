from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Ingredient
from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def make_detail_url(**kwargs):
    return reverse('recipe:ingredient-detail', kwargs=kwargs)


class PublicIngredientsApiTest(APITestCase):
    """Test the publicly available ingredients API"""

    def test_login_required_for_list(self):
        """Test that login is required to access the endpoint"""
        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_required_for_details(self):
        """Test that login is required to access the endpoint"""
        response = self.client.get(make_detail_url(pk=1))

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

        ingredients = Ingredient.objects.all().order_by('name')
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

    def test_create_ingredients_successful(self):
        """Test creating a new ingredient"""
        payload = {'name': 'Cabbage'}
        self.client.post(INGREDIENTS_URL, payload)

        exists = Ingredient.objects.filter(user=self.user,
                                           name=payload['name'])
        self.assertTrue(exists)

    def test_create_ingredient_invalid_name(self):
        """Test creating invalid ingredient fails"""
        payload = {'name': ''}
        response = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_ingredient(self):
        """Test retrieving a single ingredient"""
        ingr = Ingredient.objects.create(user=self.user, name='Apricot')
        response = self.client.get(make_detail_url(pk=ingr.pk))

        self.assertEqual(response.data, IngredientSerializer(ingr).data)

    def test_retrieve_others_ingredient_returns_not_found(self):
        """
        Test that effort to retrieve another user's ingredient
        returns Not found
        """
        # create Ingredient for a new user
        user2 = get_user_model().objects.create_user(
            'other@test.com',
            'testpass'
        )
        ingr = Ingredient.objects.create(user=user2, name='Vinegar')

        response = self.client.get(make_detail_url(pk=ingr.pk))
        self.assertEqual(response.data['detail'], 'Not found.')
