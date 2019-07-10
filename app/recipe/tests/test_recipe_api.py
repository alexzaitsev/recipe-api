import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import gettext as _

from core.models import Recipe, Tag, Ingredient
from rest_framework import status
from rest_framework.test import APITestCase

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    """Return recipe image upload URL"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Sample tag'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Sample ingredient'):
    """Create and return a sample ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_mins': 10
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(APITestCase):
    """Test unauthenticated recipe API access"""

    def test_auth_required(self):
        """Test that authentication is required"""
        response = self.client.get(RECIPES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(APITestCase):
    """Test authenticated recipe API access"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user"""
        user2 = get_user_model().objects.create_user(
            'other@test.com',
            'testpass'
        )
        sample_recipe(user=user2)
        auth_recipe = sample_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)
        serializer = RecipeSerializer([auth_recipe], many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test viewing a recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user,
                                                 name="Ingr 1"))
        recipe.ingredients.add(sample_ingredient(user=self.user,
                                                 name="Ingr 2"))

        url = detail_url(recipe.id)
        response = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_basic_recipe(self):
        """Test creating a recipe"""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_mins': 30
        }
        response = self.client.post(RECIPES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        """Test creating a recipe with tags"""
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Dessert')
        payload = {
            'title': 'Avocado lime cheesecake',
            'tags': [tag1.id, tag2.id],
            'time_mins': 60
        }

        response = self.client.post(RECIPES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        """Test creating a recipe with ingredients"""
        ingr1 = sample_ingredient(user=self.user, name='Prawns')
        ingr2 = sample_ingredient(user=self.user, name='Ginger')
        payload = {
            'title': 'Thai prawn red curry',
            'ingredients': [ingr1.id, ingr2.id],
            'time_mins': 30
        }

        response = self.client.post(RECIPES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingr1, ingredients)
        self.assertIn(ingr2, ingredients)

    def test_partial_update_recipe(self):
        """Test updating a recipe with PATCH"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))

        new_tag = sample_tag(user=self.user, name='Curry')
        payload = {'title': 'Chicken tikka', 'tags': [new_tag.id]}

        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        """Test updating a recipe with PUT"""
        # create a sample recipe with tag
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        # new recipe without tag
        payload = {
            'title': 'Spaghetti carbonara',
            'time_mins': 25
        }

        url = detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        # check that all fields are updated
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
        # check that recipe contains no tags
        self.assertEqual(recipe.tags.all().count(), 0)

    def test_filter_recipes_by_tags(self):
        """Test returning recipes with specific tags"""
        recipe1 = sample_recipe(user=self.user, title='Thai vegetable curry')
        recipe2 = sample_recipe(user=self.user, title='Aubergine with tahini')
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Vegeterian')
        tag3 = sample_tag(user=self.user, name='Easy')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        recipe2.tags.add(tag3)
        recipe3 = sample_recipe(user=self.user, title='Fish and chips')

        response = self.client.get(
            RECIPES_URL,
            {'tags': f'{tag1.id},{tag2.id},{tag3.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertEqual(len(response.data), 2)
        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_filter_recipes_by_ingredients(self):
        """Test returning recipes with specific ingredients"""
        recipe1 = sample_recipe(user=self.user, title='Posh beans on toast')
        recipe2 = sample_recipe(user=self.user, title='Chicken cacciatore')
        ingr1 = sample_ingredient(user=self.user, name='Feta cheese')
        ingr2 = sample_ingredient(user=self.user, name='Chicken')
        ingr3 = sample_ingredient(user=self.user, name='Oil')
        recipe1.ingredients.add(ingr1)
        recipe2.ingredients.add(ingr2)
        recipe2.ingredients.add(ingr3)
        recipe3 = sample_recipe(user=self.user, title='Steak and mushrooms')

        response = self.client.get(
            RECIPES_URL,
            {'ingredients': f'{ingr1.id},{ingr2.id},{ingr3.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertEqual(len(response.data), 2)
        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_wrong_tags_filter(self):
        """Test that wrong filter returns error message"""
        response = self.client.get(
            RECIPES_URL,
            {'tags': 'wrong'}
        )

        self.assertEqual(response.data['detail'],
                         _('tags must be a comma separated '
                           'list of integers'))

    def test_wrong_ingredients_filter(self):
        """Test that wrong filter returns error message"""
        response = self.client.get(
            RECIPES_URL,
            {'ingredients': 'wrong'}
        )

        self.assertEqual(response.data['detail'],
                         _('ingredients must be a comma '
                           'separated list of integers'))


class RecipeImageUploadTests(APITestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image_to_recipe_ok(self):
        """Test uploading image to recipe"""
        url = image_upload_url(self.recipe.id)

        with tempfile.NamedTemporaryFile(suffix='.jpg') as temp:
            img = Image.new('RGB', (10, 10))
            img.save(temp, format='JPEG')
            temp.seek(0)

            response = self.client.post(url, {'image': temp},
                                        format='multipart')
            self.recipe.refresh_from_db()
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('image', response.data)
            self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_to_recipe_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.recipe.id)
        response = self.client.post(url, {'image': 'notimage'},
                                    format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
