from django.contrib import admin

from docs.models import Document, DocumentAccess

admin.site.register(Document)
admin.site.register(DocumentAccess)
