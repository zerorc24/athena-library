from django import forms
from .models import Book

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["name", "category", "author", "publisher", "pdf_url",]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'border p-2 w-full'}),
            'category': forms.TextInput(attrs={'class': 'border p-2 w-full'}),
            'author': forms.Select(attrs={'class': 'border p-2 w-full'}),
            'publisher': forms.FileInput(attrs={'class': 'border p-2 w-full'}),
            'pdf_url': forms.FileInput(attrs={'class': 'border p-2 w-full'}),
        }