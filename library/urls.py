from django.urls import path
from . import views

urlpatterns = [
    # ---------------- HOME & AUTH ---------------- 
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),

    # ---------------- USER AREA ----------------
    path("library/", views.library, name="library"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # ---------------- BOOK ACTIONS & MANAGEMENT ----------------
    path("read/<int:book_id>/", views.read_book, name="read_book"),
    path("borrow/<int:book_id>/", views.borrow_book, name="borrow_book"),
    path("return/<int:book_id>/", views.return_book, name="return_book"),
    path("my-books/", views.my_books, name="my_books"),
    path("bulk-upload/", views.bulk_upload_books, name="bulk_upload_books"),
]