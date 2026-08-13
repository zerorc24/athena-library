from urllib.parse import quote

from django.core.management.base import BaseCommand

from library.models import Book


class Command(BaseCommand):
    help = "Generate R.E.B Rwanda themed cover_image URLs for books."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Regenerate cover_image URL even when one already exists.",
        )

    def handle(self, *args, **options):
        overwrite = options["overwrite"]

        books = Book.objects.all() if overwrite else Book.objects.filter(cover_image="")
        updated = 0

        for book in books:
            book.cover_image = self._build_cover_data_url(book)
            book.save(update_fields=["cover_image"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Updated {updated} book cover image URL(s).")
        )

    def _build_cover_data_url(self, book):
        palette = self._subject_palette(book.subject)
        title = self._escape_svg(book.title)
        subject = self._escape_svg(book.subject)
        level = self._escape_svg(book.level)

        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='600' height='800' viewBox='0 0 600 800'>
<defs>
  <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
    <stop offset='0%' stop-color='{palette["start"]}' />
    <stop offset='100%' stop-color='{palette["end"]}' />
  </linearGradient>
</defs>
<rect width='600' height='800' fill='url(#bg)' />
<rect x='24' y='24' width='552' height='752' rx='28' fill='none' stroke='rgba(255,255,255,0.42)' stroke-width='2' />
<rect x='52' y='70' width='496' height='120' rx='16' fill='rgba(255,255,255,0.16)' />
<text x='300' y='115' text-anchor='middle' fill='#ffffff' font-size='30' font-family='Segoe UI, Arial, sans-serif' font-weight='700'>R.E.B RWANDA</text>
<text x='300' y='152' text-anchor='middle' fill='#e6f0ff' font-size='19' font-family='Segoe UI, Arial, sans-serif'>Curriculum Textbook</text>
<text x='60' y='290' fill='#ffffff' font-size='44' font-family='Segoe UI, Arial, sans-serif' font-weight='700'>{subject}</text>
<text x='60' y='340' fill='#e8efff' font-size='30' font-family='Segoe UI, Arial, sans-serif' font-weight='600'>{level}</text>
<rect x='52' y='390' width='496' height='2' fill='rgba(255,255,255,0.36)' />
<foreignObject x='56' y='420' width='488' height='200'>
  <div xmlns='http://www.w3.org/1999/xhtml' style='color:#ffffff;font-family:Segoe UI, Arial, sans-serif;font-size:29px;font-weight:700;line-height:1.25;word-wrap:break-word;'>{title}</div>
</foreignObject>
<text x='300' y='750' text-anchor='middle' fill='#d6e4ff' font-size='18' font-family='Segoe UI, Arial, sans-serif'>Rwanda Basic Education Board</text>
</svg>"""
        return f"data:image/svg+xml,{quote(svg)}"

    def _subject_palette(self, subject):
        palettes = {
            "math": {"start": "#0b3d91", "end": "#2463d3"},
            "physics": {"start": "#0f172a", "end": "#334155"},
            "chemistry": {"start": "#1f2937", "end": "#4b5563"},
            "biology": {"start": "#0a5f2a", "end": "#16a34a"},
            "english": {"start": "#3b0764", "end": "#7e22ce"},
            "history": {"start": "#7c2d12", "end": "#b45309"},
            "geography": {"start": "#0f766e", "end": "#14b8a6"},
            "religion": {"start": "#312e81", "end": "#4338ca"},
            "ict": {"start": "#0c4a6e", "end": "#0284c7"},
            "computer science": {"start": "#111827", "end": "#1f2937"},
        }
        key = (subject or "").strip().lower()
        for token, colors in palettes.items():
            if token in key:
                return colors
        return {"start": "#1d4ed8", "end": "#2563eb"}

    def _escape_svg(self, text):
        return (
            str(text or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
