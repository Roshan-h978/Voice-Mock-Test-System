"""Django admin pages for attempts and their answers (read-mostly)."""

from django.contrib import admin

from .models import Answer, Attempt


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    can_delete = False
    fields = ("question_order", "question_text", "audio", "overall", "fluency", "pronunciation", "grammar", "needs_review")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "test", "status", "overall", "submitted_at", "reviewer")
    list_filter = ("status", "test")
    search_fields = ("student__email", "student__full_name", "test__title")
    date_hierarchy = "started_at"
    readonly_fields = ("started_at", "submitted_at", "reviewed_at", "alerted_at")
    raw_id_fields = ("student", "reviewer")
    inlines = [AnswerInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question_order", "overall", "needs_review", "is_demo", "created_at")
    list_filter = ("needs_review", "is_demo")
    search_fields = ("attempt__student__email", "question_text", "transcript")
    raw_id_fields = ("attempt", "question")
