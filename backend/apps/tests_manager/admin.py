"""Django admin pages for mock tests and questions."""

from django.contrib import admin

from .models import MockTest, Question


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ("order", "text", "hint", "answer_seconds")


@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "status", "question_total", "created_by", "published_at", "created_at")
    list_filter = ("status", "level")
    search_fields = ("title", "description")
    readonly_fields = ("published_at", "created_at", "updated_at")
    inlines = [QuestionInline]

    @admin.display(description="Questions")
    def question_total(self, obj):
        return obj.questions.count()

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("test", "order", "short_text", "answer_seconds")
    list_filter = ("test",)
    search_fields = ("text",)
    ordering = ("test", "order")

    @admin.display(description="Question")
    def short_text(self, obj):
        return obj.text[:80]
