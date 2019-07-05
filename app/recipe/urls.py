from recipe import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('tags', views.TagViewSet)
router.register('ingredients', views.IngredientViewSet)

app_name = 'recipe'

urlpatterns = router.urls
