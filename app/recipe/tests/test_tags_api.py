from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework.test import APITestCase
from rest_framework import status

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def make_detail_url(**kwargs):
    return reverse('recipe:tag-detail', kwargs=kwargs)


class PublicTagsApiTests(APITestCase):
    """Test the publicly available tags API"""

    def test_login_required_for_list(self):
        """Test that login is required to access the endpoint"""
        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_required_for_details(self):
        """Test that login is required to access the endpoint"""
        response = self.client.get(make_detail_url(pk=1))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTest(APITestCase):
    """Test the authorized user tags API"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieves tags"""
        Tag.objects.create(user=self.user, name='Raw')
        Tag.objects.create(user=self.user, name='Vegan')

        response = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test that tags returned are for the authenticated user"""
        # create Tag for a new user
        user2 = get_user_model().objects.create_user(
            'other@test.com',
            'testpass'
        )
        Tag.objects.create(user=user2, name='Fruity')
        # create Tag for authorized user
        tag_for_auth_user = Tag.objects.create(user=self.user,
                                               name='Healthy food')
        serializer = TagSerializer([tag_for_auth_user], many=True)

        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_tag_successful(self):
        """Test creating a new tag"""
        payload = {'name': 'Raw test tag'}
        self.client.post(TAGS_URL, payload)

        exists = Tag.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()

        self.assertTrue(exists)

    def test_create_tag_invalid_name(self):
        """Test creating a new tag with invalid payload"""
        payload = {'name': ''}
        response = self.client.post(TAGS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_tag(self):
        """Test retrieving a single tag"""
        tag = Tag.objects.create(user=self.user, name='Raw')
        response = self.client.get(make_detail_url(pk=tag.pk))

        self.assertEqual(response.data, TagSerializer(tag).data)

    def test_retrieve_others_tag_returns_not_found(self):
        """Test that effort to retrieve another user's tag returns Not found"""
        # create Tag for a new user
        user2 = get_user_model().objects.create_user(
            'other@test.com',
            'testpass'
        )
        tag = Tag.objects.create(user=user2, name='Fruity')

        response = self.client.get(make_detail_url(pk=tag.pk))
        self.assertEqual(response.data['detail'], 'Not found.')

    def test_retrieve_tags_assigned_to_recipes(self):
        """Test filtering tags by those assigned to recipes"""
        tag1 = Tag.objects.create(user=self.user, name='Breakfast')
        tag2 = Tag.objects.create(user=self.user, name='Lunch')
        recipe = Recipe.objects.create(
            title='Coriander eggs on toast',
            time_mins=10,
            user=self.user
        )
        recipe.tags.add(tag1)

        response = self.client.get(TAGS_URL, {'assigned_only': 1})
        serializer1 = TagSerializer(tag1)
        serializer2 = TagSerializer(tag2)
        self.assertEqual(len(response.data), 1)
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_retrieve_tags_assigned_unique(self):
        """Test filtering tags by assigned returns unique items"""
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        Tag.objects.create(user=self.user, name='Lunch')
        recipe1 = Recipe.objects.create(
            title='Pancakes',
            time_mins=5,
            user=self.user
        )
        recipe1.tags.add(tag)
        recipe2 = Recipe.objects.create(
            title='Porridge',
            time_mins=3,
            user=self.user
        )
        recipe2.tags.add(tag)

        response = self.client.get(TAGS_URL, {'assigned_only': 1})
        self.assertEqual(len(response.data), 1)

    def test_wrong_assign_only_filter_tags(self):
        """Test that wrong filter returns error"""
        response = self.client.get(TAGS_URL, {'assigned_only': 'wrong'})

        self.assertEqual(response.data['detail'],
                         _('assigned_only must be an integer'))
