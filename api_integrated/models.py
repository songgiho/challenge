from django.db import models
from django.contrib.auth.models import User

class MealLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    mealType = models.CharField(max_length=20, choices=[
        ('breakfast', '아침'),
        ('lunch', '점심'),
        ('dinner', '저녁'),
        ('snack', '간식'),
    ])
    foodName = models.CharField(max_length=100)
    calories = models.FloatField()
    carbs = models.FloatField(null=True, blank=True)
    protein = models.FloatField(null=True, blank=True)
    fat = models.FloatField(null=True, blank=True)
    nutriScore = models.CharField(max_length=1, choices=[
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E')
    ], null=True, blank=True)
    imageUrl = models.ImageField(upload_to='meal_images/', null=True, blank=True)
    time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.date} - {self.foodName}"

    class Meta:
        ordering = ['-date', '-time']

class AICoachTip(models.Model):
    message = models.TextField()
    type = models.CharField(max_length=20, choices=[
        ('warning', '경고'),
        ('suggestion', '제안'),
        ('encouragement', '격려'),
    ])
    priority = models.CharField(max_length=20, choices=[
        ('low', '낮음'),
        ('medium', '중간'),
        ('high', '높음'),
    ])
    createdAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message[:50]