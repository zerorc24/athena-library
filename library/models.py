from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name="profile"
    )
    location = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.user.username


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Author(models.Model):
    full_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.full_name


class Publisher(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255)
    
    publisher = models.ForeignKey(
        Publisher, 
        on_delete=models.CASCADE, 
        related_name="books"
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name="books"
    )
    author = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name="books"
    )
    
    isbn = models.CharField(max_length=50, unique=True)
    
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    
    pdf = models.FileField(upload_to="books/pdfs/", null=True, blank=True)
    pdf_url = models.URLField(max_length=500, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Updated auto_now for timestamp tracking

    def __str__(self):
        return self.title


# --- MISSING MODEL FOR BORROW SYSTEM ---
class BorrowedBook(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="borrowed_books"
    )
    book = models.ForeignKey(
        Book, 
        on_delete=models.CASCADE, 
        related_name="borrow_records"
    )
    borrowed_at = models.DateTimeField(auto_now_add=True)
    return_date = models.DateTimeField(null=True, blank=True)
    is_returned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"