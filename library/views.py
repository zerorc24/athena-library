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


# --- Authentication Views ---

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
        messages.success(request, "Account created successfully. Please log in.")
        return redirect("login")

    return render(request, "library/register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if not user:
            messages.error(request, "Invalid username or password.")
            return redirect("login")

        login(request, user)
        return redirect("dashboard")

    return render(request, "library/login.html")


def logout_view(request):
    logout(request)
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect("home")


# --- Core Views ---

def home(request):
    return render(request, "library/home.html")


def library(request):
    query = request.GET.get('q', '').strip()

    base_query = Book.objects.select_related('author', 'category', 'publisher')

    if query:
        books = base_query.filter(
            Q(title__icontains=query) |
            Q(author__full_name__icontains=query) |
            Q(category__name__icontains=query) |
            Q(publisher__name__icontains=query) |
            Q(isbn__icontains=query)
        ).distinct()
    else:
        books = base_query.all()

    # Annotate whether the logged-in user has borrowed each book
    if request.user.is_authenticated:
        borrowed_book_ids = set(
            BorrowedBook.objects.filter(
                user=request.user, 
                is_returned=False
            ).values_list('book_id', flat=True)
        )

        for book in books:
            book.is_borrowed = book.id in borrowed_book_ids

    return render(request, "library/library.html", {"books": books, "query": query})


@login_required
def dashboard(request):
    user_borrowed = BorrowedBook.objects.select_related('book', 'book__author').filter(
        user=request.user, 
        is_returned=False
    )

    context = {
        "total_books": Book.objects.count(),
        "borrowed_count": user_borrowed.count(),
        "user_borrowed": user_borrowed,
        "category_counts": Category.objects.annotate(count=Count("books")),
    }
    return render(request, "library/dashboard.html", context)


@login_required
def my_books(request):
    active_borrowed = BorrowedBook.objects.select_related(
        'book', 'book__author', 'book__category'
    ).filter(user=request.user, is_returned=False).order_by('-borrow_date')

    returned_history = BorrowedBook.objects.select_related(
        'book', 'book__author', 'book__category'
    ).filter(user=request.user, is_returned=True).order_by('-return_date')

    context = {
        "active_borrowed": active_borrowed,
        "returned_history": returned_history,
    }
    return render(request, "library/my_books.html", context)


# --- Bulk CSV Upload ---

@staff_member_required
def bulk_upload_books(request):
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")

        if not csv_file:
            messages.error(request, "Please upload a CSV file.")
            return redirect("bulk_upload_books")

        if not csv_file.name.endswith(".csv"):
            messages.error(request, "Only CSV files are allowed.")
            return redirect("bulk_upload_books")

        try:
            decoded_file = csv_file.read().decode("utf-8-sig").splitlines()
            reader = csv.DictReader(decoded_file)
            added_count = 0

            for index, row in enumerate(reader, start=1):
                name = row.get("name") or row.get("title")
                category_name = row.get("category") or "Academics"
                author_name = row.get("author") or "REB"
                publisher_name = row.get("publisher") or "REB"
                pdf_url = row.get("pdf_url")

                # Handle shifted CSV rows
                if not pdf_url and publisher_name and publisher_name.startswith("http"):
                    pdf_url = publisher_name
                    publisher_name = "REB"
                    author_name = "REB"

                if name:
                    author_obj, _ = Author.objects.get_or_create(full_name=author_name.strip())
                    category_obj, _ = Category.objects.get_or_create(name=category_name.strip())
                    publisher_obj, _ = Publisher.objects.get_or_create(name=publisher_name.strip())

                    Book.objects.get_or_create(
                        title=name.strip(),
                        defaults={
                            'author': author_obj,
                            'category': category_obj,
                            'publisher': publisher_obj,
                            'pdf_url': pdf_url.strip() if pdf_url else None,
                            'isbn': f"BULK-{index:05d}",
                            'total_copies': 1,
                            'available_copies': 1,
                        }
                    )
                    added_count += 1

            messages.success(request, f"{added_count} books processed successfully.")
            return redirect("library")

        except Exception as e:
            messages.error(request, f"CSV upload failed: {e}")
            return redirect("bulk_upload_books")

    return render(request, "library/bulk_upload.html")


# --- Borrow & Return Operations ---

@login_required
def borrow_book(request, book_id):
    with transaction.atomic():
        book = get_object_or_404(Book.objects.select_for_update(), id=book_id)

        if book.available_copies <= 0:
            messages.error(request, "No available copies of this book left.")
            return redirect("library")

        already_borrowed = BorrowedBook.objects.filter(
            user=request.user,
            book=book,
            is_returned=False
        ).exists()

        if already_borrowed:
            messages.warning(request, "You have already borrowed this book.")
            return redirect("library")

        Book.objects.filter(id=book_id).update(
            available_copies=models.F("available_copies") - 1
        )

        BorrowedBook.objects.create(
            user=request.user,
            book=book
        )

        messages.success(request, f"You have borrowed '{book.title}'.")
        return redirect("library")


@login_required
def return_book(request, book_id):
    with transaction.atomic():
        borrowed_book = BorrowedBook.objects.select_for_update().filter(
            user=request.user,
            book_id=book_id,
            is_returned=False
        ).first()

        if not borrowed_book:
            messages.error(request, "This book record was not found in your borrowed books.")
            return redirect("library")

        borrowed_book.is_returned = True
        borrowed_book.return_date = timezone.now()
        borrowed_book.save()

        Book.objects.filter(id=book_id).update(
            available_copies=models.F("available_copies") + 1
        )

        messages.success(request, "Book returned successfully.")
        return redirect("library")


@login_required
def read_book(request, book_id=None, pk=None):
    target_id = book_id or pk
    book = get_object_or_404(Book, id=target_id)

    if book.pdf_url and book.pdf_url.startswith("http"):
        return redirect(book.pdf_url)

    return render(request, "library/book_detail.html", {"book": book})

def library(request):
    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)

    base_query = Book.objects.select_related('author', 'category', 'publisher')

    if query:
        books_list = base_query.filter(
            Q(title__icontains=query) |
            Q(author__full_name__icontains=query) |
            Q(category__name__icontains=query) |
            Q(publisher__name__icontains=query) |
            Q(isbn__icontains=query)
        ).distinct()
    else:
        books_list = base_query.all()

    # Paginate: Show 12 books per page
    paginator = Paginator(books_list, 12)

    try:
        books = paginator.page(page)
    except PageNotAnInteger:
        books = paginator.page(1)
    except EmptyPage:
        books = paginator.page(paginator.num_pages)

    # Annotate borrowed status for current page items
    if request.user.is_authenticated:
        borrowed_book_ids = set(
            BorrowedBook.objects.filter(
                user=request.user, 
                is_returned=False
            ).values_list('book_id', flat=True)
        )

        for book in books:
            book.is_borrowed = book.id in borrowed_book_ids

    return render(request, "library/library.html", {"books": books, "query": query})