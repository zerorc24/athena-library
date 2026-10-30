
import csv

from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from django.db.models import Q, Count
from django.utils import timezone

from .models import Book, Author, Category, Publisher, BorrowedBook

User = get_user_model()


# =====================================================
# AUTHENTICATION
# =====================================================

def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not username or not email or not password:
            messages.error(request, "All fields are required.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("register")

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(
            request,
            "Account created successfully. Please log in."
        )
        return redirect("login")

    return render(request, "library/register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            messages.error(request, "Invalid username or password.")
            return redirect("login")

        login(request, user)
        messages.success(request, "Welcome back!")
        return redirect("dashboard")

    return render(request, "library/login.html")


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


# =====================================================
# HOME
# =====================================================

def home(request):
    return render(request, "library/home.html")


# =====================================================
# LIBRARY / BOOK CATALOG
# =====================================================

def library(request):
    query = request.GET.get("q", "").strip()
    page_number = request.GET.get("page", 1)

    books_list = Book.objects.select_related(
        "author",
        "category",
        "publisher"
    )

    if query:
        books_list = books_list.filter(
            Q(title__icontains=query) |
            Q(author__full_name__icontains=query) |
            Q(category__name__icontains=query) |
            Q(publisher__name__icontains=query) |
            Q(isbn__icontains=query)
        ).distinct()

    paginator = Paginator(books_list, 12)

    try:
        books = paginator.page(page_number)
    except PageNotAnInteger:
        books = paginator.page(1)
    except EmptyPage:
        books = paginator.page(paginator.num_pages)

    # Identify books currently borrowed by this user.
    if request.user.is_authenticated:
        borrowed_book_ids = set(
            BorrowedBook.objects.filter(
                user=request.user,
                is_returned=False
            ).values_list("book_id", flat=True)
        )

        for book in books:
            book.is_borrowed = book.id in borrowed_book_ids

    return render(
        request,
        "library/library.html",
        {
            "books": books,
            "query": query,
        }
    )


# =====================================================
# USER DASHBOARD
# =====================================================

@login_required
def dashboard(request):
    user_borrowed = BorrowedBook.objects.select_related(
        "book",
        "book__author"
    ).filter(
        user=request.user,
        is_returned=False
    )

    context = {
        "total_books": Book.objects.count(),
        "borrowed_count": user_borrowed.count(),
        "user_borrowed": user_borrowed,
        "category_counts": Category.objects.annotate(
            count=Count("books")
        ),
    }

    return render(request, "library/dashboard.html", context)


# =====================================================
# MY BOOKS
# =====================================================

@login_required
def my_books(request):
    active_borrowed = BorrowedBook.objects.select_related(
        "book",
        "book__author",
        "book__category"
    ).filter(
        user=request.user,
        is_returned=False
    ).order_by("-borrowed_at")

    returned_history = BorrowedBook.objects.select_related(
        "book",
        "book__author",
        "book__category"
    ).filter(
        user=request.user,
        is_returned=True
    ).order_by("-return_date")

    context = {
        "active_borrowed": active_borrowed,
        "returned_history": returned_history,
    }

    return render(
        request,
        "library/my_books.html",
        context
    )


# =====================================================
# BULK CSV UPLOAD
# =====================================================

@staff_member_required
def bulk_upload_books(request):

    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")

        if not csv_file:
            messages.error(request, "Please upload a CSV file.")
            return redirect("bulk_upload_books")

        if not csv_file.name.lower().endswith(".csv"):
            messages.error(request, "Only CSV files are allowed.")
            return redirect("bulk_upload_books")

        try:
            decoded_file = csv_file.read().decode("utf-8-sig").splitlines()
            reader = csv.DictReader(decoded_file)

            added_count = 0

            for index, row in enumerate(reader, start=1):

                title = (row.get("name") or row.get("title") or "").strip()
                category_name = (row.get("category") or "Academics").strip()
                author_name = (row.get("author") or "REB").strip()
                publisher_name = (row.get("publisher") or "REB").strip()
                pdf_url = (row.get("pdf_url") or "").strip()

                # Handle CSV rows where the PDF URL is shifted.
                if not pdf_url and publisher_name.startswith("http"):
                    pdf_url = publisher_name
                    publisher_name = "REB"
                    author_name = "REB"

                if not title:
                    continue

                author_obj, _ = Author.objects.get_or_create(
                    full_name=author_name
                )

                category_obj, _ = Category.objects.get_or_create(
                    name=category_name
                )

                publisher_obj, _ = Publisher.objects.get_or_create(
                    name=publisher_name
                )

                _, created = Book.objects.get_or_create(
                    title=title,
                    defaults={
                        "author": author_obj,
                        "category": category_obj,
                        "publisher": publisher_obj,
                        "pdf_url": pdf_url or None,
                        "isbn": f"BULK-{index:05d}",
                        "total_copies": 1,
                        "available_copies": 1,
                    }
                )

                if created:
                    added_count += 1

            messages.success(
                request,
                f"{added_count} new books added successfully."
            )

            return redirect("library")

        except (UnicodeDecodeError, csv.Error) as error:
            messages.error(request, f"Invalid CSV file: {error}")
            return redirect("bulk_upload_books")

        except Exception as error:
            messages.error(request, f"CSV upload failed: {error}")
            return redirect("bulk_upload_books")

    return render(request, "library/bulk_upload.html")


# =====================================================
# BORROW BOOK
# =====================================================

@login_required
def borrow_book(request, book_id):

    with transaction.atomic():

        book = get_object_or_404(
            Book.objects.select_for_update(),
            id=book_id
        )

        already_borrowed = BorrowedBook.objects.filter(
            user=request.user,
            book=book,
            is_returned=False
        ).exists()

        if already_borrowed:
            messages.warning(
                request,
                "You have already borrowed this book."
            )
            return redirect("library")

        if book.available_copies <= 0:
            messages.error(
                request,
                "No available copies of this book left."
            )
            return redirect("library")

        Book.objects.filter(id=book.id).update(
            available_copies=models.F("available_copies") - 1
        )

        BorrowedBook.objects.create(
            user=request.user,
            book=book
        )

    messages.success(
        request,
        f"You have borrowed '{book.title}'."
    )

    return redirect("library")


# =====================================================
# RETURN BOOK
# =====================================================

@login_required
def return_book(request, book_id):

    with transaction.atomic():

        borrowed_book = BorrowedBook.objects.select_for_update().filter(
            user=request.user,
            book_id=book_id,
            is_returned=False
        ).first()

        if borrowed_book is None:
            messages.error(
                request,
                "This book was not found in your active borrowed books."
            )
            return redirect("my_books")

        borrowed_book.is_returned = True
        borrowed_book.return_date = timezone.now()
        borrowed_book.save(
            update_fields=["is_returned", "return_date"]
        )

        Book.objects.filter(id=book_id).update(
            available_copies=models.F("available_copies") + 1
        )

    messages.success(
        request,
        f"'{borrowed_book.book.title}' returned successfully."
    )

    return redirect("my_books")


# =====================================================
# READ BOOK
# =====================================================

@login_required
def read_book(request, book_id=None, pk=None):

    target_id = book_id or pk

    book = get_object_or_404(
        Book,
        id=target_id
    )

    if book.pdf_url:
        return redirect(book.pdf_url)

    if book.pdf:
        return redirect(book.pdf.url)

    messages.warning(
        request,
        "A reading file is not available for this book yet."
    )

    return redirect("library")
