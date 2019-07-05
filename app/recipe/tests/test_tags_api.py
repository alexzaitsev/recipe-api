from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from core.models import Tag
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

        tags = Tag.objects.all().order_by('-name')
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
