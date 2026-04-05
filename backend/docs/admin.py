from django.contrib import admin
from django.contrib.admin import register

from docs.models import Document, DocumentAccess

@register(Document)
class DocumentAdmin(admin.ModelAdmin):
    readonly_fields = ('dt_created', 'dt_updated')

    class Meta:
        model = Document


@register(DocumentAccess)
class DocumentAccessAdmin(admin.ModelAdmin):
    readonly_fields = ('dt_created', 'dt_updated')

    class Meta:
        model = DocumentAccess
