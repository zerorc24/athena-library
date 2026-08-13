import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from library.models import Book, Author, Category, Publisher


class Command(BaseCommand):
    help = "Import books from library/data/books.csv into database"

    def handle(self, *args, **kwargs):
        # Locate the CSV file inside library/data/books.csv
        file_path = os.path.join(settings.BASE_DIR, "library", "data", "books.csv")

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found at: {file_path}"))
            return

        with open(file_path, mode="r", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            added_count = 0

            for index, row in enumerate(reader, start=1):
                # Safely extract fields with fallback values
                title = row.get("name") or row.get("title")
                category_name = row.get("category") or "Academics"
                author_name = row.get("author") or "REB"
                publisher_name = row.get("publisher") or "REB"
                pdf_url = row.get("pdf_url")

                # Fix for shifted rows like French (where columns are missing)
                if not pdf_url and publisher_name and publisher_name.startswith("http"):
                    pdf_url = publisher_name
                    publisher_name = "REB"
                    author_name = "REB"

                # Skip completely empty rows
                if not title:
                    continue

                title = title.strip()
                category_name = category_name.strip()
                author_name = author_name.strip()
                publisher_name = publisher_name.strip()

                # Get or Create Related Foreign Key Objects
                author_obj, _ = Author.objects.get_or_create(full_name=author_name)
                category_obj, _ = Category.objects.get_or_create(name=category_name)
                publisher_obj, _ = Publisher.objects.get_or_create(name=publisher_name)

                # Get or Create Book
                book, created = Book.objects.get_or_create(
                    title=title,
                    defaults={
                        "author": author_obj,
                        "category": category_obj,
                        "publisher": publisher_obj,
                        "pdf_url": pdf_url.strip() if pdf_url else None,
                        "isbn": f"REB-{index:05d}",  # Generates unique ISBN like REB-00001
                        "total_copies": 5,
                        "available_copies": 5,
                    },
                )

                if created:
                    added_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported {added_count} books!")
        )